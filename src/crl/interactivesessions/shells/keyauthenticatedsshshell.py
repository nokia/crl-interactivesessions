import re
import logging
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .sshshell import SshShell
from .registershell import RegisterShell
from .shell import TimeoutError


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7


class ShellStartError(InteractiveSessionError):
    pass


@RegisterShell()
class KeyAuthenticatedSshShell(SshShell):
    """
    This class can be used in order to start a remote Ssh shell
    with keyauthentication instead of password authentication.
    It requires that ssh keys are set before pushing the shell.
    See also
    :class:`.SshShell`.

    **Args:**

    *host*: IP address or name of the host

    *initial_prompt*: check_start_success method requires prompt,
        status check command is sent when initial prompt is found,
        example:'$ '

    *tty_echo*: If True, then terminal echo is set on.

    """
    _ssh_options = (" -o CheckHostIP=no "
                    "-o PasswordAuthentication=no "
                    "-o StrictHostKeyChecking=no  "
                    "-o ServerAliveCountMax=3 "
                    "-o ServerAliveInterval=180 "
                    "-o BatchMode=yes "
                    "-o UpdateHostKeys=no "
                    "-o ConnectTimeout=10")

    def __init__(self, host, initial_prompt, tty_echo=False):
        super(KeyAuthenticatedSshShell, self).__init__(
            ip=host, tty_echo=tty_echo)
        self.ip = host
        self.initial_prompt = re.compile(initial_prompt + "$") \
            if initial_prompt else None

    def get_start_cmd(self):
        ssh_options = KeyAuthenticatedSshShell._ssh_options
        return "ssh {0} {1}".format(ssh_options, self.ip)

    def check_start_success(self):
        """
        check status after pushing KeyAuthenticatedSshShell
        raise ShellStartError if status is not 0

        Sending something after receiving status output is needed
        because sshshell _common_start keyword expects not empty buffer
        after check_start_success.

        """
        buffer = self.wait_for_initial_prompt()
        logger.log(_LOGLEVEL, "'%s'", buffer)
        self._send_input_line('echo @$?@')
        try:
            status_output = self._read_until_end(timeout=1)
            status = re.match("@(\d+)@", status_output).group(1)
            if status != '0':
                raise ShellStartError(
                    "Shell start to {} did not succeed".format(self.ip))
            self._send_input_line('echo $?')
        except TimeoutError:
            raise ShellStartError(
                "Shell start to {} did not succeed".format(self.ip))

    def wait_for_initial_prompt(self):
        """
        read until prompt is coming
        raise ShellStartError if prompt is not found
        """
        try:
            return self._read_until(self.initial_prompt, timeout=20)
        except TimeoutError:
            raise ShellStartError(
                "Shell start to {} did not succeed. "
                "Prompt not found".format(self.ip))
