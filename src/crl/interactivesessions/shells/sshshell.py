import re
import logging
import paramiko
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from crl.interactivesessions.pexpectplatform import is_windows
from .bashshell import BashShell
from .sshoptions import sshoptions
from .registershell import RegisterShell
from .paramikospawn import ParamikoSpawn
from .msgreader import MsgReader


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7


class SshError(InteractiveSessionError):
    """
    Raised when :class:`.SshShell` start fails
    """


@RegisterShell()
class SshShell(BashShell):
    """
    This class can be used in order to start a remote bash shell. See also
    :class:`.BashShell`.

    **Args:**

    *ip*: IP address of the host

    *username*: login username

    *password*: login passowrd. If not given, passwordless login is expected.

    *tty_echo*: If True, then terminal echo is set on.

    *second_password*: if not *None*, this password is send to terminal after
                       the first password succesfully aplied.

    *port*: If *port* is not None, alternate port is used in the connection
            instead of the detfault 22.

    *init_env*: Path to initialization file which is sourced after the all
                other initialization is done.

    For setting timeout for reading login banner, i.e. message-of-day, please use
    :meth:`.msgreader.MsgReader.set_timeout`.
    """
    # TODO: add "-oLogLevel=error" to avoid banner...
    _ssh_options = sshoptions

    def __init__(self, ip, username=None, password=None, tty_echo=False,
                 second_password=None, port=None, init_env=None):
        super(SshShell, self).__init__(tty_echo=tty_echo, init_env=init_env)
        self.ip = ip
        self.username = username
        self.passwords = [] if password is None else [password]
        self.port = port
        self.ssh = None
        self.chan = None
        self.start = self._start_in_pexpect
        if second_password:
            self.passwords.append(second_password)

    def __getattr__(self, name):
        if name == 'spawn':
            if is_windows():
                return self._paramikospawn
            raise AttributeError(
                "{clsname} has no attribute 'spawn'".format(
                    clsname=self.__class__.__name__))

    def get_start_cmd(self):
        ssh_options = SshShell._ssh_options
        if self.port is not None:
            ssh_options += ' -p {}'.format(int(self.port))

        return ("ssh {0} {1}".format(ssh_options, self.ip)
                if self.username is None else
                "ssh {0} {1}@{2}".format(ssh_options, self.username, self.ip))

    def _start_in_pexpect(self):
        prompt_re = re.compile(
            br"\[[a-zA-Z]+@[a-zA-Z]{2,4}-[0-9]*\(.+\)\s(\/.+)+\]")

        logger.debug("Awaiting SSH connection to %s", self.ip)
        for password in self.passwords:
            n = self._terminal.expect(["word:",
                                       "Connection reset by peer",
                                       prompt_re])

            if n == 0:
                logger.debug("Sending password %s", password)
                self._terminal.sendline(password)
                self._read(2)  # newline after password prompt
            elif n == 1:
                raise SshError("Failed to start new ssh shell.")
            elif n == 2:
                return self._set_bash_environment()
        return self._common_start()

    def _common_start(self):
        self.check_start_success()
        reader = MsgReader(self._read_until_end)
        retval = reader.read_until_end()
        retval += self._set_bash_environment()
        return retval

    def check_start_success(self):
        """
        This method is called right after the shell is pushed
        and the prompt is not set yet.
        To be implemented in derivative classes if needed
        Should raise ShellStartError if not successful.
        """

    def _start_in_paramiko(self):
        return self._common_start()

    def _paramikospawn(self, timeout):
        logger.debug('Spawning SshShell using ParamikoSpawn')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.ip,
                         username=self.username,
                         password=self._pop_passwords(),
                         port=22 if self.port is None else self.port)
        self.chan = self.ssh.invoke_shell()
        self.start = self._start_in_paramiko
        logger.debug('Connection channel: %s', self.chan)
        return ParamikoSpawn(self.chan, timeout=timeout)

    def _pop_passwords(self):
        try:
            return self.passwords.pop(0)
        except IndexError:
            return None

    def exit(self):
        super(SshShell, self).exit()
        if self.ssh is not None:
            self.ssh.close()
