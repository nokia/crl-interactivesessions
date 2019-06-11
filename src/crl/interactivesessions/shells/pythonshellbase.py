import logging
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .shell import Shell


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)
_LOGLEVEL = 7


class UnexpectedOutputInPython(InteractiveSessionError):
    """
    Raised by PythonShell in case output have unexpected content
    """


class PythonShellBase(Shell):

    _prompt = [">>> ", "... "]
    short_timeout = 10

    def __init__(self, start_cmd):
        super(PythonShellBase, self).__init__()
        self._start_cmd = start_cmd
        self._prompt = PythonShellBase._prompt

    def get_start_cmd(self):
        return self._start_cmd

    def start(self):
        self._read_until_prompt(timeout=30)

    def exit(self):
        LOGGER.log(_LOGLEVEL, "Exit from Python shell")
        self._send_input_line('exit()')

    @classmethod
    def set_short_timeout(cls, timeout):
        cls.short_timeout = timeout

    def _single_command_no_output(self, cmd, timeout=10):
        LOGGER.log(_LOGLEVEL,
                   "(PythonShell) single_command_no_output send line: %s",
                   cmd)
        self._send_input_line(cmd)
        return self._verify_and_return_output(
            self._read_until(self._prompt[0], timeout=timeout))

    @staticmethod
    def _verify_and_return_output(output, expected_output=""):
        if output != expected_output:
            raise UnexpectedOutputInPython(output)
        return output

    def exec_command_rstrip(self, cmd, timeout=-1):
        return self.exec_command(cmd, timeout=timeout).rstrip('\r\n')
