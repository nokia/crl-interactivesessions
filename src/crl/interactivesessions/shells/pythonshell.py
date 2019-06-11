import os
import pickle
import base64
import logging
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .registershell import RegisterShell
from .pythonshellbase import PythonShellBase


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7


class PythonRunNotStarted(InteractiveSessionError):
    pass


@RegisterShell()
class PythonShell(PythonShellBase):
    """ The path to *Python* executable can be altered via *start_cmd*.

    **Args:**

    *start_cmd*: command to start Python shell (Default: python)

    *tty_echo*: if *True* then commands are echoed in shell. (Default: *False*)

    *readline_init*: If not *None*, then readline initialization commands in
        *readline_init* string are executed in terminal in start. Please see syntax
        from *readline* man pages (Default: *None*).
    """

    def __init__(self, start_cmd="python", tty_echo=False, readline_init=None):
        super(PythonShell, self).__init__(start_cmd)
        self._readline_init = readline_init
        super(PythonShell, self).set_tty_echo(tty_echo)

    def set_tty_echo(self, _):
        logger.debug("Python shell does not support echo setting changing,"
                     " keeping old value!")

    def start(self):
        super(PythonShell, self).start()
        self._setup_readline_if_needed()
        self._import_modules()

    def _setup_readline_if_needed(self):
        if self._readline_init:
            self.single_command_no_output("import readline")
            self.single_command_no_output("readline.parse_and_bind('{}')".format(
                self._readline_init))

    def _import_modules(self):
        return self.single_command_no_output("import pickle, base64")

    def transfer_text_file(self,
                           source_path,
                           destination_dir=''):
        """Transfer the text file source_path to current host of the shell"""
        filename = os.path.basename(source_path)
        destination_path = os.path.join(destination_dir, filename)
        logger.debug("Transferring text file from '%s' to remote node:'%s'",
                     source_path, destination_path)
        self._write_lines_to_file(self._read_lines_from_file(source_path),
                                  destination_path)

    def _write_lines_to_file(self, lines, destination_path):
        self.block_exec(
            "with open('{0}', 'w') as _f:".format(destination_path))
        self.block_exec(
            "  _f.writelines(pickle.loads(base64.b64decode('{0}')))".format(
                base64.b64encode(pickle.dumps(lines, protocol=0))))
        self.block_end_no_output()

    @staticmethod
    def _read_lines_from_file(source_path):
        with open(source_path, 'r') as readfile:
            return readfile.readlines()

    def single_command_no_output(self, cmd, timeout=10):
        return self._single_command_no_output(cmd, timeout=timeout)

    def single_command(self, cmd, timeout=10):
        logger.log(_LOGLEVEL,
                   "(PythonShell) single_command_exec send line: %s", cmd)
        self._send_input_line(cmd)
        output = self._read_until(self._prompt[0], timeout=timeout)
        logger.log(_LOGLEVEL,
                   "(PythonShell) single_command_exec return: %s", output)
        return output

    def exec_single_with_trigger(self, cmd, trigger, timeout=10):
        logger.log(_LOGLEVEL, "(PythonShell) sending '%s', trigger: '%s'",
                   cmd, trigger)
        try:
            self._send_input_line(cmd)
            self._read_until(trigger, timeout=1)
        except Exception as e:
            raise PythonRunNotStarted(e)
        logger.log(_LOGLEVEL, "(PythonShell) trigger received. "
                   "Waiting prompt for %d seconds", timeout)
        output = self._read_until(self._prompt[0], timeout=timeout)
        logger.log(_LOGLEVEL, "(PythonShell) output: '%s'", output)
        return output

    def block_exec(self, cmd, timeout=10):
        logger.log(_LOGLEVEL, "(PythonShell) bloc_exec send line: %s", cmd)
        self._send_input_line(cmd)
        return self._verify_and_return_output(
            self._read_until(self._prompt[1], timeout=timeout))

    def block_end_no_output(self, timeout=10):
        logger.log(_LOGLEVEL, "(PythonShell) block end")
        return self.single_command_no_output("", timeout=timeout)

    def stop_run(self, timeout=3):
        self._terminal.sendcontrol('c')
        return self._read_until(self._prompt[0], timeout=timeout)
