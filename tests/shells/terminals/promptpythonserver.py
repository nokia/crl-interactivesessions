import logging
from crl.interactivesessions.shells.remotemodules import servers
from crl.interactivesessions.shells.remotemodules.msgs import (
    ExecCommandErrorObj)
from crl.interactivesessions.shells.remotemodules.compatibility import to_bytes
from .serverterminal import (
    LineServerBase,
    LineServerExit)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class PromptPythonServer(LineServerBase, servers.PythonServer):
    _prompt = b'>>> '

    def __init__(self):
        LineServerBase.__init__(self)
        servers.PythonServer.__init__(self)
        self.processlocalsysmanager = None

    def _server_setup(self):
        self._setup_standard_streams()
        self._write(self._prompt)

    def _setup_standard_streams(self):
        self._setup_own_out()
        self._setup_messaging_inout()

    def _setup_own_out(self):
        self.stdout = self._inout.write_file
        self.stderr = self._inout.write_file

    def _setup_messaging_inout(self):
        servers.sys.stdin = self._inout.read_file
        servers.sys.stdout = self._inout.write_file
        servers.sys.stderr = self._inout.write_file

    def _handle_line(self, line):
        self._send_reply_out(self._exec_and_create_reply_msg(line))

    def _exec_and_create_reply_msg(self, cmd):
        return self._exec_command(cmd)

    def _exec_command(self, cmd):
        try:
            ret = self.pythoncmdline.exec_command(cmd)
            return b'' if ret is None else to_bytes(repr(ret))
        except SystemExit:
            raise LineServerExit
        except Exception as e:  # pylint: disable=broad-except
            return str(ExecCommandErrorObj(e, cmd))

    def _send_reply_out(self, out):
        LOGGER.debug('PromptPythonServer: %s', out)
        self._write(out + self._prompt)

    def _write(self, s):
        LOGGER.debug('Writing %s', s)
        self._strcomm.comm.write(s)

    @property
    def _stop_cmd(self):
        return 'exit()'
