from io import BytesIO
from .serverterminal import (
    LineServerBase,
    LineServerExit)


__copyright__ = 'Copyright (C) 2019, Nokia'


class BashServer(LineServerBase):
    expected_status_code = 0

    def __init__(self):
        super(BashServer, self).__init__()
        self._prompt = None
        self._bytesio = BytesIO()

    def set_prompt(self, prompt):
        self._prompt = prompt

    def _server_setup(self):
        pass

    def _handle_line(self, line):
        if line == 'echo $?':
            self._write(str(self.expected_status_code))
        elif line.startswith('echo '):
            self._write(line[5:])
        if line == self._stop_cmd:
            raise LineServerExit()

        self._write(self._prompt)

    def _write(self, s):
        self._inout.write_file.write(s)
        self._inout.write_file.flush()

    @property
    def _stop_cmd(self):
        return 'exit'
