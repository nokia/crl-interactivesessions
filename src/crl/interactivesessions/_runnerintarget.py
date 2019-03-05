from contextlib import contextmanager
from crl.interactivesessions._terminalpools import _TerminalPools
from ._process import (
    _AsyncProcessWithoutPty,
    _ForegroundProcessWithoutPty,
    _BackgroundProcessWithoutPty,
    _NoCommBackgroudProcess)
from ._targetproperties import _TargetProperties


__copyright__ = 'Copyright (C) 2019, Nokia'


class _RunnerInTarget(object):

    def __init__(self, shelldicts):
        self.shelldicts = shelldicts
        self.properties = _TargetProperties()
        self.terminalpools = _TerminalPools()

    @contextmanager
    def active_terminal(self):
        with self.terminalpools.active_terminal(self.shelldicts,
                                                self.properties) as terminal:
            yield terminal

    def run(self, cmd, timeout, executable=None, progress_log=False):
        processcls = (
            _AsyncProcessWithoutPty
            if progress_log else
            _ForegroundProcessWithoutPty)
        return processcls(
            cmd,
            executable=self._get_executable(executable),
            shelldicts=self.shelldicts,
            properties=self.properties,
            timeout=timeout).run()

    def run_in_background(self, cmd, executable=None):
        return _BackgroundProcessWithoutPty(
            **self._get_background_kwargs(cmd, executable)).run()

    def run_in_nocomm_background(self, cmd, executable=None):
        return _NoCommBackgroudProcess(
            **self._get_background_kwargs(cmd, executable)).run()

    def _get_background_kwargs(self, cmd, executable):
        return {'cmd': cmd,
                'executable': self._get_executable(executable),
                'shelldicts': self.shelldicts,
                'properties': self.properties}

    def _get_executable(self, executable):
        return (self.properties.default_executable
                if executable is None else
                executable)

    def get_terminal(self):
        return self.terminalpools.get(shelldicts=self.shelldicts,
                                      properties=self.properties)

    def put_terminal(self, terminal):
        return self.terminalpools.put(terminal)
