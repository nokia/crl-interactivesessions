import logging
from contextlib import contextmanager
from crl.interactivesessions.interactivesessionexceptions import InteractiveSessionError
from crl.interactivesessions.shells.shell import TimeoutError
from .rawpythonshell import RawPythonShell

from .remotemodules import servers
from .modules import MainModule
from .remotemodules.commbase import CommWriterBase
from .remotemodules.chunkcomm import ChunkReaderBase
from .remotemodules.clients import Client
from .remotemodules.exceptions import FatalPythonError
from .remotemodules.msgs import (
    ExecCommandRequest,
    SendCommandRequest,
    ExitRequest,
    ServerIdRequest)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class TerminalComm(ChunkReaderBase, CommWriterBase):
    def __init__(self, terminal, timeout=-1):
        ChunkReaderBase.__init__(self)
        self._terminal = terminal
        self._timeout = timeout

    def _read(self, n):
        return self._terminal.read_nonblocking(n, timeout=self._timeout)

    def write(self, s):
        self._terminal.send(s)


class ShellAttributeError(AttributeError):
    pass


class ExecCommandError(InteractiveSessionError):
    pass


class MsgPythonShell(RawPythonShell):

    def __init__(self):
        super(MsgPythonShell, self).__init__()
        self._servers_mod = MainModule(servers)
        self._client = Client()
        self._fatalerror = FatalPythonError(Exception(
            'Python server is not started yet'))
        self._server_id = None

    def start(self):
        super(MsgPythonShell, self).start()

        for cmd in self._servers_mod.cmds_gen():
            self._single_command_no_output(cmd, timeout=self.short_timeout)

        self._serve()

    def _serve(self):
        self._terminal.sendline(
            '{servers_mod_var}.PythonServer.create_and_serve()'.format(
                servers_mod_var=self._servers_mod.module_var))
        self._server_id = self._get_server_id_in_start(timeout=self.short_timeout)
        self._fatalerror = None

    def _get_server_id_in_start(self, timeout):
        with self._client_timeout(timeout):
            r = self._client.receive()
            return r.server_id

    def exec_command(self, cmd, timeout=-1):
        if self._fatalerror is None:
            with self._fatalerror_handling():
                ret = self._exec_python_cmd(cmd, timeout)

        ret = ret if self._fatalerror is None else str(self._fatalerror)
        return ret

    def get_prompt(self):
        return self._server_id if self._fatalerror is None else self._prompt

    def get_prompt_from_terminal(self, empty_command='', timeout=-1):
        if self._fatalerror is None:
            return self._get_server_id(timeout)
        return super(MsgPythonShell, self).get_prompt_from_terminal(
            empty_command=empty_command,
            timeout=timeout)

    def send_command(self, cmd):
        """Send command *cmd* without waiting response.

        Note:
            This method should be used only with low-level terminal handling
            where the expected output is catched directly from *_terminal*.
            Please make sure that all the desired output is read from the
            terminal.
        """
        self._client.send(SendCommandRequest.create(cmd))

    @staticmethod
    def get_stdout_str():
        return servers.PythonServer.stdout_handle

    @contextmanager
    def _fatalerror_handling(self):
        try:
            yield None
        except FatalPythonError as e:
            self._fatalerror = e
        except TimeoutError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.info('FatalError %s: %s', e.__class__.__name__, e)
            self._fatalerror = FatalPythonError(e)
            self._exit_serve()

    def _exec_python_cmd(self, cmd, timeout):
        r = self._send_and_receive(ExecCommandRequest.create(cmd),
                                   timeout=timeout)
        return r.out

    def _send_and_receive(self, msg, timeout):
        with self._client_timeout(timeout):
            return self._client.send_and_receive(msg)

    def exit(self):
        if self._fatalerror is None:
            self._exit_serve()
            self._fatalerror = FatalPythonError(
                Exception('Python server stopped'))
        super(MsgPythonShell, self).exit()

    def _exit_serve(self):
        self._client.send(ExitRequest())

    @contextmanager
    def _client_timeout(self, timeout):
        self._set_client_comm(timeout)
        with self._wrap_timeout_exception():
            yield None

    def _set_client_comm(self, timeout):
        def comm_fact():
            return TerminalComm(self._terminal, timeout=timeout)
        self._client.set_comm_factory(comm_fact)

    def _get_server_id(self, timeout):
        r = self._send_and_receive(ServerIdRequest(), timeout=timeout)
        return r.server_id
