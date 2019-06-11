import logging
import re

from crl.interactivesessions.shells.bashshell import (
    BashShell)
from crl.interactivesessions.shells.registershell import (
    RegisterShell)
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .msgreader import MsgReader


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7


class SudoError(InteractiveSessionError):
    """
    Raised when :class:`.SudoShell` start fails
    """


@RegisterShell()
class SudoShell(BashShell):
    """Running commands under sudo.

    For setting timeout for reading login banner, i.e. lecture, please use
    :meth:`.msgreader.MsgReader.set_timeout`.
    """
    def __init__(self, cmd="sudo bash", password=None):
        super(SudoShell, self).__init__(tty_echo=True)
        self._start_cmd = cmd
        self._password = "" if password is None else password

    def get_start_cmd(self):
        return self._start_cmd

    def start(self):
        prompt_re = re.compile(
            r"[[a-zA-Z]+@[a-zA-Z]{2,4}-[0-9]*(.+)\s(/.+)+]")

        logger.debug("Attemping to sudo")
        n = self._terminal.expect(["word:",
                                   "Sorry, try again.",
                                   prompt_re])

        if n == 0:
            logger.debug("Sending password %s", self._password)
            self._terminal.sendline(self._password)
            self._read(2)  # newline after password prompt
        elif n == 1:
            raise SudoError("Failed to start new sudo shell.")
        elif n == 2:
            return self._set_bash_environment()
        return self._common_start()

    def _common_start(self):
        reader = MsgReader(self._read_until_end)
        retval = reader.read_until_end()
        retval += self._set_bash_environment()
        return retval
