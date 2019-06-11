import logging
import time
import uuid
import os
from pickle import Unpickler
from io import StringIO
import base64
import itertools
import traceback
from contextlib import contextmanager
import pexpect
from . import ShellSubprocess
from .InteractiveSession import PythonShell
from .shells.pythonshell import PythonRunNotStarted
from .shells.pythonshellbase import UnexpectedOutputInPython
from .shells.shell import TimeoutError


__copyright__ = 'Copyright (C) 2019, Nokia'


class CommandExecutionFailed(Exception):
    pass


class FailedToRunInteractiveHandler(Exception):
    pass


class UnexpectedTerminalOutput(Exception):
    # pylint: disable=unsubscriptable-object
    def __str__(self):
        return ("Unexpected terminal output in run {0} ({1}): '{2}',"
                " {3}: {4}".format(self.args[0],
                                   self.args[1],
                                   self.args[2],
                                   self.args[3].__class__.__name__,
                                   self.args[3]))


class RunNotStarted(Exception):
    pass


class SessionNotInitialized(Exception):
    pass


class FailedToCreateSession(Exception):
    pass


class RestoreTimedOut(Exception):
    pass


class ShellSubprocessPickler(Unpickler):
    """
    In remote side the ShellSubprocess full module name is different than in
    the local side.  This class is for mapping the remote modules to their
    counterparts in the local side. In this fashion the unpickler can
    instantiate ShellSubprocess classes correctly according the pickled data.
    """

    def find_class(self, module, name):
        """
        Return imported ShellSubprocess module classes, otherwise return
        classes as usual.
        """
        if module == ShellSubprocess.ShellSubprocess.get_module_name():
            return getattr(ShellSubprocess, name)
        return Unpickler.find_class(self, module, name)


class LocalShellSubprocess(ShellSubprocess.ShellSubprocess):
    def __init__(self, node):
        super(LocalShellSubprocess, self).__init__(0)
        self._shell = None
        self._cmd = None
        self._node = node
        self._is_running = False
        self._executable = '/bin/bash'

    def __str__(self):
        return "Run ID: {0}, cmd: '{1}'".format(self._run_id,
                                                self._cmd)

    def set_shell(self, shell):
        self._shell = shell

    def run(self, cmd, timeout=60):
        with self._run_wrapper():
            self._cmd = cmd
            logging.log(7, "Runing command %d: %s", self._run_id, cmd)
            return self._run_with_error_serialization(
                self._get_run_creation_command(timeout), timeout=timeout)

    @contextmanager
    def _run_wrapper(self):
        try:
            self._run_id += 1
            self._is_running = True
            yield
        except SystemExit:
            self._handle_system_exit()
        finally:
            self._is_running = False

    def _handle_system_exit(self):
        try:
            self.stop_and_warn_if_running()
        finally:
            raise SystemExit

    def is_running(self):
        return self._is_running

    def is_hung(self, timeout=1):
        return self._shell.is_terminal_hung(timeout=timeout)

    def stop_and_warn_if_running(self):
        if self.is_running() or self._shell.is_terminal_hung(timeout=1):
            result = self._try_to_get_result_from_output(
                self._shell.stop_run())
            logging.warning("Forcefully terminated in node %s: %s",
                            self._node,
                            result)

    def get_backed_up_result(self, timeout=10):
        expect_timeout = self._get_expect_timeout(timeout)
        max_retries = expect_timeout if expect_timeout > 1 else 1
        for retry_count in range(int(max_retries)):
            try:
                return self._run_with_error_serialization(
                    self._get_backup_creation_command(),
                    timeout=1)
            except ShellSubprocess.ResultNotStoredYet:
                logging.log(7, "%d/%d Waiting for result of run %d (%s)",
                            retry_count,
                            max_retries,
                            self._run_id,
                            self._cmd)
                time.sleep(1)
        raise RestoreTimedOut(self._run_id, self._cmd)

    def set_executable(self, executable):
        self._executable = executable

    def _run_with_error_serialization(self, creation_command, timeout):
        return self._get_result_from_output(
            self._shell.exec_single_with_trigger(
                "{0}.run()".format(creation_command),
                self.get_start_trigger(),
                timeout=self._get_expect_timeout(timeout)))

    @staticmethod
    def _get_expect_timeout(timeout):
        return timeout + 1 if timeout > 0 else timeout

    def _try_to_get_result_from_output(self, output):
        result = None
        try:
            result = self._get_result_from_output(output)
        except UnexpectedTerminalOutput as e:
            result = e
        return result

    def _get_result_from_output(self, output):
        return self._get_result_wrapper_from_output(output).get_result(
            self._run_id)

    def _get_result_wrapper_from_output(self, output):
        with self.unify_deserialize_errors(output):
            decoded_output = base64.b64decode(output)
            outputstream = StringIO(decoded_output)
            return ShellSubprocessPickler(outputstream).load()

    def _get_run_creation_command(self, timeout):
        join_timeout = timeout if timeout > 0 else None
        return "{0}({1}, '{2}', timeout={3}, executable='{4}')".format(
            ShellSubprocess.RunShellSubprocess.__name__,
            self._run_id,
            self._serialize(self._cmd),
            join_timeout,
            self._executable)

    def _get_backup_creation_command(self):
        return "{0}({1})".format(ShellSubprocess.ReadonlyShellSubprocess.__name__,
                                 self._run_id)

    @contextmanager
    def unify_deserialize_errors(self, output):
        try:
            yield

        except Exception as e:
            e.trace = self._extract_tb()
            # pylint: disable=no-member
            logging.log(7, "Failed to deseriliaze, traceback:: \n%s",
                        ''.join(e.trace))
            raise UnexpectedTerminalOutput(self._run_id,
                                           self._cmd,
                                           output,
                                           e)


class SelfRepairingSession(object):
    """
        .. warning::

            This class is deprecated. Please use it only for legacy purposes.
    """
    def __init__(self,
                 node_name,
                 create_runner_session,
                 max_retries=10,
                 sleep_between_retries=3):
        self._create_runner_session = create_runner_session
        self._node_name = node_name
        self._max_retries = int(max_retries)
        self._sleep_between_retries = int(sleep_between_retries)
        self._session = None
        self._sessions = set([])
        self._work_dir = os.path.join('/tmp', str(uuid.uuid4()))
        self._saved_delaybeforesend = 0.05
        self._runner = LocalShellSubprocess(node_name)
        self._old_workdir = False

    def run(self,
            cmd,
            ignore_statuses=None,
            timeout=-1,
            executable='/bin/bash'):
        if ignore_statuses is None:
            ignore_statuses = [0]
        result = self.run_no_validate(cmd, timeout, executable=executable)
        if result[0] not in ignore_statuses and '*' not in ignore_statuses:
            raise CommandExecutionFailed(result)
        return result

    def run_ignore_all_exceptions(
            self,
            cmd,
            timeout=-1,
            executable='/bin/bash'):
        result = None
        try:
            result = self.run_no_validate(cmd,
                                          timeout=timeout,
                                          executable=executable)
        except Exception as exception:  # pylint: disable=broad-except
            logging.debug('Ignoring exception: %s', exception)
        return result

    def run_no_validate(  # pylint:disable=unused-argument
            self,
            cmd,
            timeout=-1,
            executable='/bin/bash'):
        for retry_count in itertools.count():
            with self._handle_run_exceptions(retry_count, cmd):
                return self._strip_from_right(
                    self._verify_session_and_run(cmd, timeout=timeout))

    @contextmanager
    def _handle_run_exceptions(self, retry_count, cmd):
        try:
            yield
        except SessionNotInitialized as exception:
            logging.log(7, "%d/%d: Session not initialized for run %s, %s",
                        retry_count, self._max_retries, cmd, exception)
            self._handle_session_not_working(retry_count, exception)
        except RunNotStarted:
            logging.log(7, "%d/%d: Run not started, running again "
                        "'%s'", retry_count, self._max_retries, cmd)
        except TimeoutError:
            logging.debug('TimeoutError: stop run')
            self._session.get_current_shell().stop_run()
            raise

    def _handle_session_not_working(self, retry_count, exception):
        if retry_count < self._max_retries:
            self._try_to_create_new_session()
        else:
            raise FailedToCreateSession(exception)

    def _try_to_create_new_session(self):
        try:
            logging.debug("Creating a new session for %s",
                          self.__class__.__name__)
            self._create_new_session()
        except (pexpect.TIMEOUT, TimeoutError):
            logging.log(7, 'Session creation timed out: sleeping %d',
                        self._sleep_between_retries)
            time.sleep(self._sleep_between_retries)

    def _verify_session_and_run(self, cmd, timeout=-1):
        self._verify_session()
        return self._run_with_backup(cmd, timeout=timeout)

    def _verify_session(self):
        if not self._session:
            raise SessionNotInitialized()

    def _run_with_backup(self, cmd, timeout=-1):
        result = None
        try:
            result = self._runner.run(cmd, timeout=timeout)
        except UnexpectedTerminalOutput as e:
            logging.warning(self._get_exception_log(e))
            self._try_to_create_new_session()
            result = self._runner.get_backed_up_result(timeout=timeout)
        except PythonRunNotStarted as e:
            logging.debug(self._get_exception_log(e))
            result = self._try_to_get_hung_run_result(timeout=timeout)
        return result

    def _try_to_get_hung_run_result(self, timeout):
        result = None
        original_session = self._session
        self._session = None
        try:
            self._try_to_create_new_session()
            result = self._try_to_get_backup_result(timeout=timeout)
        finally:
            if original_session:
                self._session_close(original_session)
        return result

    def _try_to_get_backup_result(self, timeout):
        if not self._old_workdir:
            raise RunNotStarted(self._runner)
        try:
            return self._runner.get_backed_up_result(timeout=timeout)
        except (ShellSubprocess.MismatchInRunId,
                ShellSubprocess.BackupNotFound):
            raise RunNotStarted(self._runner)

    @staticmethod
    def _strip_from_right(result):
        return (result[0], result[1].rstrip('\r\n'), result[2].rstrip('\r\n'))

    def _create_new_session(self):
        try:
            if self._session:
                self._runner.stop_and_warn_if_running()
                self._session_close()
            self._create_session()
        except Exception as e:
            logging.debug(self._get_exception_log(e))
            if self._session:
                self._session_close()
            raise

    def _get_exception_log(self, exception):
        return "{0}: {1}, backtrace: {2}".format(exception.__class__.__name__,
                                                 exception,
                                                 self._formatted_trace())

    @staticmethod
    def _formatted_trace():
        trace_list = traceback.format_list(traceback.extract_stack())
        if len(trace_list) > 2:
            trace_list = trace_list[:-2]
        formatted_trace_list = (
            [frame for frame in trace_list
             if 'robot' not in frame and 'pydev' not in frame])
        return ''.join(formatted_trace_list)

    def _session_close(self, session=None):
        session = session if session else self._session
        logging.debug('Closing session for %s %s',
                      repr(session),
                      self.__class__.__name__)
        self._restore_delaybeforesend()
        self._session.close()
        self._sessions.remove(self._session)
        self._session = None

    def _create_session(self):
        self._session = self._create_runner_session(self._node_name,
                                                    work_dir=self._work_dir)
        self._sessions.add(self._session)
        self._prepare_session()

    def _prepare_session(self):
        self._clear_delaybeforesend()
        self._session.setup_working_directory()
        self._session.get_session().push(PythonShell())
        self._import_in_shell(self._session.get_current_shell())
        self._runner.set_shell(self._session.get_current_shell())

    def _clear_delaybeforesend(self):
        self._saved_delaybeforesend = (
            self._session.get_current_shell().delaybeforesend)
        self._session.get_current_shell().delaybeforesend = 0

    def _restore_delaybeforesend(self):
        self._session.get_current_shell().delaybeforesend = (
            self._saved_delaybeforesend)

    def _import_in_shell(self, shell):
        try:
            self._send_import_command(shell)
            self._old_workdir = True
        except UnexpectedOutputInPython:
            self._old_workdir = False
            shell.transfer_text_file(
                ShellSubprocess.ShellSubprocess.get_python_file_path())
            self._send_import_command(shell)

    @staticmethod
    def _send_import_command(shell):
        shell.single_command_no_output("from {0} import {1}, {2}".format(
            ShellSubprocess.ShellSubprocess.get_module_name(),
            ShellSubprocess.RunShellSubprocess.__name__,
            ShellSubprocess.ReadonlyShellSubprocess.__name__))

    def close(self):
        for session in self._sessions.copy():
            self._session = session
            self._close()

    def _close(self):
        try:
            self._finalize_session()
        except Exception as e:  # pylint: disable=broad-except
            logging.warning("Failed to finalize %s: %s: %s",
                            self.__class__.__name__,
                            e, e.args)
        self._session_close()

    def _finalize_session(self):
        self._runner.stop_and_warn_if_running()
        self._session.get_session().pop()
        self._session.remove_working_directory()

    def reset(self):
        try:
            self._create_new_session()
        except Exception as e:  # pylint: disable=broad-except
            logging.debug(self._get_exception_log(e))
