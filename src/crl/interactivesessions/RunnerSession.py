"""
The class :class:`.RunnerSession` is a factory class for remote
proxy objects. The available proxies are :class:`._RemoteProxy`
and :class:`._RecursiveProxy`.
"""
from crl.interactivesessions.InteractiveSessionExecutor import (
    InteractiveSessionExecutor)
from crl.interactivesessions.runnerterminal import RunnerTerminal


__copyright__ = 'Copyright (C) 2019, Nokia'


class RunnerSession(InteractiveSessionExecutor):
    """ Deprecated, use *RunnerTerminal* instead.
    """
    def __init__(self, node_name, **kwargs):
        super(RunnerSession, self).__init__(node_name, **kwargs)
        self._terminal = RunnerTerminal()
        self._terminal.initialize(session=self)

    def __getattr__(self, name):
        if not name.startswith('_'):
            try:
                return getattr(self._terminal, name)
            except AttributeError:
                pass
        raise AttributeError("'{cls}' object has no attribute '{name}'".format(
            cls=self.__class__.__name__, name=name))
