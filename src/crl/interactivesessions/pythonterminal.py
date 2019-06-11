from ._terminalpools import PoolNotFoundError

__copyright__ = 'Copyright (C) 2019, Nokia'


class PythonTerminal(object):
    def __init__(self, runnerintarget):
        self.runnerintarget = runnerintarget
        self.terminal = self.runnerintarget.get_terminal()

    @property
    def runnerterminal(self):
        return self.terminal.terminal

    @property
    def remoteimporter(self):
        return self.terminal.proxies.remoteimporter

    def __del__(self):
        try:
            self.runnerintarget.put_terminal(self.terminal)
        except PoolNotFoundError:
            pass
