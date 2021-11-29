# ////////////////////////////////////////////////////////////
#
# File: remoteshell.py
#
# ////////////////////////////////////////////////////////////
#
# Author: Robin Nyman
#
# Nokia - Confidential
# Do not use, distribute, or copy without consent of Nokia.
# Copyright (c) 2021 Nokia. All rights reserved.
#
# ////////////////////////////////////////////////////////////

import logging
import paramiko

from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .paramikospawn import ParamikoSpawn
from .bashshell import BashShell
from .registershell import RegisterShell
from .shell import TimeoutError
from .msgreader import MsgReader


LOGGER = logging.getLogger(__name__)


class RemoteError(InteractiveSessionError):
    """
    Raised when :class:`.SshShell` start fails
    """


@RegisterShell()
class RemoteShell(BashShell):
    """
    This class can be used in order to start a remote bash shell. See also
    :class:`.BashShell`.
    **Args:**
    *ip*: IP address of the host
    *username*: login username
    *password*: login passowrd. If not given, passwordless login is expected.
    *tty_echo*: If True, then terminal echo is set on.
    *port*: If *port* is not None, alternate port is used in the connection
            instead of the detfault 22.
    *init_env*: Path to initialization file which is sourced after the all
                other initialization is done.
    *source*: File to source to initial the terminal at the ssh host
    *sudo* If super user should be used for commands set this to true
           Default is false. It will initialize shell session with sudo -i
    For setting timeout for reading login banner, i.e. message-of-day, please use
    :meth:`.msgreader.MsgReader.set_timeout`.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, ip, username=None, password=None, tty_echo=False,
                 port=None, source=None, key_file=None, sudo=None):
        super(RemoteShell, self).__init__(tty_echo=tty_echo)
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
        self.key_file = key_file
        self.sudo = sudo
        self.source = source
        self.ssh = None
        self.chan = None

    def spawn(self, timeout=20):
        LOGGER.debug('Spawning RemoteShell using ParamikoSpawn')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.ip,
                         username=self.username,
                         password=self.password,
                         port=22 if self.port is None else self.port,
                         key_filename=None if self.key_file is None else self.key_file)
        self.chan = self.ssh.invoke_shell()
        LOGGER.debug('Connection channel: %s', self.chan)
        return ParamikoSpawn(self.chan, timeout=timeout)

    def start(self):
        reader = MsgReader(self._read_until_end)
        retval = reader.read_until_end()
        retval += self._set_bash_environment()
        self._sudo_if_needed()
        self._source_if_needed()
        return retval

    def _sudo_if_needed(self):
        if self.sudo:
            self.execute_init_command(cmd="sudo -i")

    def _source_if_needed(self):
        if self.source:
            self.execute_init_command(cmd="source " + self.source)

    def execute_init_command(self, cmd):
        self._terminal.sendline(cmd)
        self._validate_init_command_succes(cmd)

    def _validate_init_command_succes(self, cmd):
        if not self._custom_prompt_check():
            self._reset_prompt()
            if not self._custom_prompt_check():
                raise RemoteError(
                    "Remote shell startup error: {} command failed".format(cmd))
        else:
            if self.get_status_code() != 0:
                raise RemoteError(
                    "Remote shell startup error: {} command failed".format(cmd))

    def _custom_prompt_check(self):
        return self.get_prompt() == self._detect_prompt()

    def _reset_prompt(self):
        self._terminal.sendline('unset HISTFILE')
        self._terminal.sendline('stty cols 400 rows 400 -echo')
        self.set_prompt()
        self._read_empty()

    def _read_empty(self):
        try:
            self._read_until_end(timeout=1)
        except TimeoutError:
            pass

    def check_start_success(self):
        """
        This method is called right after the shell is pushed
        and the prompt is not set yet.
        To be implemented in derivative classes if needed
        Should raise ShellStartError if not successful.
        """

    def exit(self):
        super(RemoteShell, self).exit()
        if self.ssh is not None:
            self.ssh.close()
