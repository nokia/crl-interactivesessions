from crl.interactivesessions._terminalpools import _TerminalPools


__copyright__ = 'Copyright (C) 2019, Nokia'


class SessionBroker(object):

    def __init__(self):
        self.terminalpools = _TerminalPools()

    def execute_command(self, shell, cmd):
        shell.execute_command(cmd)

    def pterms(self):
         for _, pool in self.terminalpools._pools.items():
             for s in [pool.inuse, pool.free]:
                 for t in s:
                    yield t.terminal.get_session().terminal

    def break_sessions(self):
        for pterm in self.pterms():
            pterm.send('exit()\n')

    def fake_send(self, s):
        return len(s)

    def hang_sessions(self):
        for pterm in self.pterms():
            pterm.send = self.fake_send
