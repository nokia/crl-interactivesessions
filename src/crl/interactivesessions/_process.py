import time
import signal
import logging
import errno
from collections import namedtuple
from contextlib import contextmanager
from crl.interactivesessions._terminalpools import _TerminalPools
from .runnerexceptions import RemoteTimeout
from .shells.remotemodules.compatibility import (
    to_string, to_bytes, py23_unic, unic_to_string)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class RunResult(namedtuple('RunResult', ['status', 'stdout', 'stderr'])):
    __slots__ = ()

    def __str__(self):
        return ('\n exit status:   {status}\n'
                ' stdout:\n {stdout}\n'
                ' stderr:\n {stderr}\n').format(
                    status=str(self.status),
                    stdout=unic_to_string(py23_unic(self.stdout)),
                    stderr=unic_to_string(py23_unic(self.stderr)))


def rstrip_runresult(result):
    return RunResult(status=str(result.status),
                     stdout=to_string(result.stdout).rstrip('\r\n'),
                     stderr=to_string(result.stderr).rstrip('\r\n'))


class RunnerTimeout(Exception):
    pass


class FailedToKillProcess(Exception):
    def __init__(self, pid, handle):
        super(FailedToKillProcess, self).__init__(pid, handle)
        self.pid = pid
        self.handle = handle

    def __str__(self):
        return 'Killing of the process with pid={pid} failed'.format(
            pid=self.pid)


class _ProcessBase(object):
    zone = None

    def __init__(self,
                 cmd,
                 executable,
                 shelldicts,
                 properties,
                 timeout=None):
        self.cmd = cmd
        self.executable = executable
        self.shelldicts = shelldicts
        self.properties = properties
        self.timeout = timeout
        self.terminalpools = _TerminalPools()
        self.terminal = None
        self.proxies = None
        self.termination_timeout = None
        self.pro = None
        self._communicate = None
        self.env = {}

    def run(self):
        self._initialize_terminal()
        self._set_pro()
        self._communicate = self.pro.communicate
        self.terminal.set_terminal_cleanup(self.kill_forcefully)
        return self.communicate()

    def _kill_run_and_raise(self, handle):
        for sig in [signal.SIGTERM, 9]:
            handle = self._kill_and_raise_or_return_handle(
                handle, sig)
        exc = FailedToKillProcess(pid=self.pro.pid, handle=handle)
        self.terminalpools.remove(self.terminal)
        raise exc

    def _kill_and_raise_or_return_handle(self, handle, sig):
        try:
            self._kill(sig)
            raise RunnerTimeout(
                self._get_result(
                    func=lambda: self.pro.get_remote_proxy_response(
                        handle,
                        self.termination_timeout).as_local_value()))
        except RemoteTimeout as remotetimeout:
            return remotetimeout

    def _kill(self, sig):
        try:
            self.proxies.killpg(self.proxies.getpgid(self.pro.pid), sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                LOGGER.debug('Not terminating: process already terminated')
            else:
                raise

    def kill_forcefully(self):
        try:
            self._kill(9)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.debug('Termination of run (%s) failed: %s: %s',
                         self.cmd, e.__class__.__name__, e)

    def _initialize_terminal(self):
        self.terminal = self.terminalpools.get(self.shelldicts,
                                               self.properties,
                                               zone=self.zone)
        self.proxies = self.terminal.proxies
        self.termination_timeout = (
            self.terminal.properties.termination_timeout)
        self.env = self.proxies.environ.as_local_value()
        self.env.update(self.terminal.properties.update_env_dict)

    def _finalize_terminal(self):
        self.terminal.set_terminal_cleanup(lambda: None)
        self.terminalpools.put(self.terminal)

    def _communicate_with_cleanup(self):
        try:
            return self._communicate_as_local_value()

        except RemoteTimeout as handle:
            self._kill_run_and_raise(handle)

        finally:
            self._finalize_terminal()

    def _communicate_as_local_value(self):
        return self._get_result(
            lambda: self._communicate().as_local_value())

    def _set_pro(self):
        raise NotImplementedError()

    def communicate(self):
        raise NotImplementedError()

    def _get_result(self, func):
        raise NotImplementedError()


class _ForegroundProcessWithoutPty(_ProcessBase):

    def _set_pro(self):
        self.pro = self.proxies.popen(
            self.cmd,
            executable=self.executable,
            bufsize=-1,
            stdout=self.proxies.pipe,
            stderr=self.proxies.pipe,
            shell=True,
            preexec_fn=self.proxies.setsid,
            env=self.env)

    def _get_result(self, func):
        stdout, stderr = func()
        return RunResult(status=self.pro.returncode,
                         stdout=stdout,
                         stderr=stderr)

    def communicate(self):
        self._communicate.set_remote_proxy_timeout(self.timeout)
        return self._communicate_with_cleanup()


def timeout_generator(generator, timeout):
    start = time.time()
    for item in generator:
        if time.time() - start > timeout:
            raise RunnerTimeout()
        yield item


class _AsyncProcessWithoutPty(_ForegroundProcessWithoutPty):

    def communicate(self):
        tmp_stdout = []
        lines_iterator = self._get_lines_iterator_proxy(self.pro,
                                                        self.timeout)
        pid = self.pro.pid
        for line in timeout_generator(lines_iterator, self.timeout):
            LOGGER.debug("tmp_stdout = %s; appending line: %s",
                         tmp_stdout,
                         line)
            tmp_stdout.append(to_bytes(line))
            LOGGER.debug("pid=%s: %s", pid, to_string(line))

        ret = super(_AsyncProcessWithoutPty, self).communicate()
        stdout = b''.join(tmp_stdout)
        return RunResult(ret.status, stdout, ret.stderr)

    def _get_lines_iterator_proxy(self, pro, timeout):
        lines_iterator = self.proxies.iter_until_empty(pro.stdout.readline)
        lines_iterator.set_remote_proxy_timeout(timeout)
        return lines_iterator


class _BackgroundProcessBase(_ProcessBase):
    def __init__(self, *args, **kwargs):
        super(_BackgroundProcessBase, self).__init__(*args, **kwargs)
        self.handle = None
        self.result = None

    def communicate(self):
        self._communicate.remote_proxy_use_asynchronous_response()
        self.handle = self._communicate()
        self.terminalpools.put_incr_shared(self.terminal)
        return self

    def wait_background_execution(self, timeout):
        if self.result is None:
            self.result = self._get_result(
                lambda: self.pro.get_remote_proxy_response(
                    self.handle, timeout))
            self.terminalpools.decr_shared(self.terminal)
        return self.result

    def kill_background_execution(self):
        try:
            self._kill_run_and_raise(self.handle)
        except RunnerTimeout as e:
            self.result = e.args[0]
            self.terminalpools.decr_shared(self.terminal)
            return self.result


class _BackgroundProcessWithoutPty(_BackgroundProcessBase,
                                   _ForegroundProcessWithoutPty):
    zone = 'background'


class _NoCommBackgroudProcess(_BackgroundProcessWithoutPty):

    def run(self):
        with self._in_terminal():
            return self._get_cmd_pid()

    @contextmanager
    def _in_terminal(self):
        try:
            self._initialize_terminal()
            yield None
        finally:
            self._finalize_terminal()

    def _get_cmd_pid(self):
        return self.proxies.daemon_popen(cmd=self.cmd,
                                         executable=self.executable,
                                         env=self.env)

    def _finalize_terminal(self):
        if self.terminal is not None:
            self.terminalpools.put(self.terminal)
