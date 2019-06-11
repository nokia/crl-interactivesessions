from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .sshoptions import sshoptions
from .registershell import RegisterShell
from .shell import (
    Shell,
    DEFAULT_STATUS_TIMEOUT)


__copyright__ = 'Copyright (C) 2019, Nokia'


class SftpConnectionError(InteractiveSessionError):
    pass


@RegisterShell()
class SftpShell(Shell):
    """SFTP Shell"""
    _sftp_prompt = "sftp>"

    def __init__(self, ip, username, password, cmd="sftp"):
        super(SftpShell, self).__init__()
        self._start_cmd = cmd
        self.ip = ip
        self.username = username
        self.password = password

    def get_start_cmd(self):
        return "{0} {1} {2}@{3}".format(
            self._start_cmd,
            sshoptions,
            self.username,
            self.ip)

    def get_prompt(self):
        return SftpShell._sftp_prompt

    def start(self):
        if self._terminal.expect(["word:", "Connection reset by peer"]) == 1:
            raise SftpConnectionError("Connection refused ({0})".format(
                ''.join(self._terminal_contents)))

        self._terminal.sendline(self.password)

        if self._terminal.expect_exact([self._sftp_prompt, "word:"]) == 1:
            self._send_interrupt()
            raise SftpConnectionError("Bad password ({0})".format(
                ''.join(self._terminal_contents)))
        return self._terminal.before.decode("utf-8")

    def _terminal_contents(self):
        for s in [self._terminal.before, self._terminal.after]:
            yield s.decode("utf-8")

    def exit(self):
        self._exec_cmd("exit")

    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        raise NotImplementedError("No status code available in SFTP shell")
