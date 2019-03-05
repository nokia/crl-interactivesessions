from crl.interactivesessions.shells.remotemodules.pythoncmdline import PythonCmdline


__copyright__ = 'Copyright (C) 2019, Nokia'


class StrPythonCmdline(PythonCmdline):
    def exec_command(self, cmd):
        response = super(StrPythonCmdline, self).exec_command(cmd)
        response = '' if response is None else response
        return response
