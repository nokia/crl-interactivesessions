from contextlib import contextmanager
from .terminals.bashserver import BashServer


__copyright__ = 'Copyright (C) 2019, Nokia'


class BashTerminalShell(object):
    def __init__(self, shell, server_terminal_factory):
        self._shell = shell
        self._server_terminal_factory = server_terminal_factory
        self._terminal = None

    @contextmanager
    def in_terminal(self):
        self._terminal = self._create()
        try:
            self._shell.set_terminal(self._terminal)
            yield self._terminal
        finally:
            self._terminal.close()

    @property
    def terminal(self):
        return self._terminal

    @property
    def shell(self):
        return self._shell

    def _bash_server_factory(self):
        b = BashServer()
        b.set_prompt(self._shell.get_prompt())
        return b

    def _create(self):
        return self._server_terminal_factory(self._bash_server_factory)
