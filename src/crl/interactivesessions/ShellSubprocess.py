from __future__ import print_function
import pickle
import base64
import subprocess
import os
import sys
import traceback
import logging
import signal
import threading
from contextlib import contextmanager


__copyright__ = 'Copyright (C) 2019, Nokia'


class MismatchInRunId(Exception):
    pass


class RemoteTimeoutError(Exception):
    pass


class InterruptedWithSigint(Exception):
    pass


class ResultNotStoredYet(Exception):
    pass


class BackupNotFound(Exception):
    pass


class ExecutionResult(object):
    def __init__(self, run_id, cmd):
        self._run_id = run_id
        self._cmd = cmd

    def get_result(self, run_id):
        if self._run_id != run_id:
            raise MismatchInRunId(self._run_id, run_id)
        return self._get_result()

    @property
    def cmd(self):
        return self._cmd

    @property
    def run_id(self):
        return self._run_id

    def get_remote_result(self):
        return self._get_result()

    def _get_result(self):
        raise NotImplementedError()


class SuccessfulExecutionResult(ExecutionResult):

    def __init__(self, run_id, cmd, result):
        super(SuccessfulExecutionResult, self).__init__(run_id, cmd)
        self._result = result

    def _get_result(self):
        return self._result

    def __str__(self):
        return ("Run {0} ({1}): status: {2}\nout:\n{3}\nerr:\n{4}".format(
            self._run_id,
            self._cmd,
            self._result[0],
            self._result[1],
            self._result[2]))


class FailedExecutionResult(ExecutionResult):

    def __init__(self, run_id, cmd, exception):
        super(FailedExecutionResult, self).__init__(run_id, cmd)
        self._exception = exception

    def _get_result(self):
        if self._get_trace():
            logging.log(7, self._get_trace())
        raise self._exception

    def __str__(self):
        return "{0}: {1} {2}".format(self._exception.__class__.__name__,
                                     self._exception,
                                     self._get_trace())

    def _get_trace(self):
        trace = ""
        if hasattr(self._exception, 'trace'):
            trace = "Remote Traceback: \n%s" % ''.join(self._exception.trace)
        return trace


class ShellSubprocess(object):

    def __init__(self, run_id):
        self._run_id = run_id

    def get_start_trigger(self):
        return "Run {0} starting".format(self._run_id)

    @staticmethod
    def _serialize(python_object):
        return base64.b64encode(pickle.dumps(python_object, protocol=0))

    @staticmethod
    def _deserialize(serialized_object):
        return pickle.loads(base64.b64decode(serialized_object))

    @staticmethod
    def get_python_file_path():
        return os.path.abspath(ShellSubprocess.get_python_filename())

    @staticmethod
    def get_python_filename():
        return __file__ if __file__.endswith('y') else __file__[:-1]

    @staticmethod
    def get_module_name():
        return os.path.basename(ShellSubprocess.get_python_filename())[:-3]

    @staticmethod
    def _extract_tb():
        return traceback.format_list(
            traceback.extract_tb(sys.exc_info()[2]))


class RemoteShellSubprocess(ShellSubprocess):

    pickled_backup = 'pickled_backup'

    def __init__(self, run_id, serialized_cmd=""):
        super(RemoteShellSubprocess, self).__init__(run_id)
        self._cmd = self._deserialize(serialized_cmd) if serialized_cmd else ""

    def run(self):

        print(self.get_start_trigger())
        with self._error_serialization():
            print(self._serialize(self._run()))

    @contextmanager
    def _error_serialization(self):
        try:
            yield
        except Exception as e:  # pylint: disable=broad-except
            e.trace = self._extract_tb()

            print(self._serialize(FailedExecutionResult(self._run_id,
                                                        self._cmd,
                                                        e)))

    def _run(self):
        raise NotImplementedError()

    def _backup(self, python_object):
        with open(self.pickled_backup, 'w') as backup:
            pickle.dump(python_object, backup, protocol=0)

    def _restore(self):
        try:
            with open(self.pickled_backup, 'r') as backup:
                return pickle.load(backup)
        except IOError as e:
            if e.errno == 2:
                raise BackupNotFound()
            raise


class ReadonlyShellSubprocess(RemoteShellSubprocess):

    def _run(self):
        return self._restore()


class RunShellSubprocess(RemoteShellSubprocess):

    def __init__(self,
                 run_id,
                 serialized_cmd,
                 timeout=60,
                 executable='/bin/bash'):
        super(RunShellSubprocess, self).__init__(run_id, serialized_cmd)
        self._run_process = None
        self._thread = None
        self._timeout = timeout
        self._result = None
        signal.signal(signal.SIGINT, self._sigint_handler)
        self._executable = executable

    def _run(self):
        self._backup(FailedExecutionResult(self._run_id,
                                           self._cmd,
                                           ResultNotStoredYet()))
        self._run_in_thread()
        self._backup(self._result)
        return self._result

    def _sigint_handler(self, signum, frame):  # pylint:disable=unused-argument
        with self._error_serialization():
            self._terminate_and_raise_if_alive(InterruptedWithSigint,
                                               timeout=3)
            if self._result:
                print(self._serialize(self._result))

    def _run_in_thread(self):
        self._thread = threading.Thread(target=self._run_subprocess)
        self._thread.start()
        self._thread.join(self._timeout)
        self._terminate_and_raise_if_alive(RemoteTimeoutError)

    def _terminate_and_raise_if_alive(self, exception_class, timeout=None):
        if self._thread.is_alive():
            self._run_process.terminate()
            self._thread.join(timeout)
            raise exception_class(self._result)

    def _run_subprocess(self):
        self._run_process = subprocess.Popen(self._cmd,
                                             executable=self._executable,
                                             bufsize=-1,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             shell=True)
        out, err = self._run_process.communicate()
        self._result = SuccessfulExecutionResult(
            self._run_id, self._cmd, (self._run_process.returncode, out, err))
