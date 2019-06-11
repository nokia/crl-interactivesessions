import logging
import sys
import abc
import os
import re
import select
import time
from io import (
    BytesIO,
    StringIO)
from contextlib import contextmanager
import mock
import six
import pexpect
from pexpect.spawnbase import SpawnBase
from crl.interactivesessions.shells.remotemodules.compatibility import (
    to_bytes)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class InOut(object):

    def __init__(self, infd, outfd):
        self.infd = infd
        self.outfd = outfd
        self._read_file = None
        self._write_file = None

    def __str__(self):
        return 'infd={}, outfd={}'.format(self.infd, self.outfd)

    def read(self, n):
        return os.read(self.infd, n)

    @property
    def read_file(self):
        if self._read_file is None:
            self._read_file = os.fdopen(self.infd)
        return self._read_file

    @property
    def write_file(self):
        if self._write_file is None:
            self._write_file = os.fdopen(self.outfd, 'w')
        return self._write_file

    def write(self, s):
        self._write(s)

    def _write(self, s):
        LOGGER.debug('Writing %s to %d', repr(s), self.outfd)
        os.write(self.outfd, to_bytes(s))


class Pipes(object):
    def __init__(self):
        self.client_inout = None
        self.server_inout = None
        self._setup_pipes()

    def _setup_pipes(self):
        s_in_c_out = os.pipe()
        c_in_s_out = os.pipe()
        self.client_inout = InOut(infd=c_in_s_out[0], outfd=s_in_c_out[1])
        self.server_inout = InOut(infd=s_in_c_out[0], outfd=c_in_s_out[1])
        LOGGER.debug('server_inout: %s, client_inout: %s',
                     self.server_inout, self.client_inout)


class LineServerExit(Exception):
    """Raise when :class:`.LineServerBase` derivative serve should end
    """


@six.add_metaclass(abc.ABCMeta)
class LineServerBase(object):
    lines_re = re.compile('(\n)')

    def __init__(self):
        self._inout = None
        self._lines = []
        self._remainder = ''

    def serve(self):
        LOGGER.debug('Serve starting')
        self._server_setup()
        try:
            while True:
                self._handle_next_line()
        except LineServerExit:
            LOGGER.debug('Exit from serve')

    def _handle_next_line(self):
        line = self._readline()
        LOGGER.debug('Handling line: %s', line)
        self._handle_line(line)

    def _readline(self):
        io = BytesIO() if sys.version_info.major == 2 else StringIO()
        LOGGER.debug('Reading next line')
        while True:
            c = self._read()
            if c == '\n':
                break
            io.write(c)
        LOGGER.debug('Read line: %s', io.getvalue())
        return io.getvalue()

    def _read(self):
        while True:
            try:
                return self._inout.read_file.read(1)
            except IOError:
                pass

    @abc.abstractmethod
    def _server_setup(self):
        """Setup before serve loop
        """

    @abc.abstractmethod
    def _handle_line(self, line):
        """Handle *line*.

        Raises:
            LineServerExit: when serve should end
        """

    def stop(self, client_inout):
        client_inout.write_file.write('{stop_cmd}\n'.format(stop_cmd=self._stop_cmd))
        client_inout.write_file.flush()

    @abc.abstractproperty
    def _stop_cmd(self):
        """Return cmd which should stop the server.
        """

    def set_inout(self, inout):
        self._inout = inout


class ServerProcess(object):
    def __init__(self):
        self._inout = None
        self._process_factory = None
        self._process = None
        self._server_factory = None
        self._server = None

    def set_inout(self, inout):
        self._inout = inout

    def set_process_factory(self, process_factory):
        """Set factory which create  :class:`multiprocessing.Process` like object.
        """
        self._process_factory = process_factory

    def set_server_factory(self, server_factory):
        """Set factory which creates :class:`ServerBase` derivative instance.
        """
        self._server_factory = server_factory

    def start(self):
        self._setup_server()
        self._process = self._process_factory(target=self._server.serve)
        self._process.start()

    def _setup_server(self):
        self._server = self._server_factory()
        self._server.set_inout(self._inout)

    def is_alive(self):
        return self._process.is_alive()

    def join(self, timeout):
        self._process.join(timeout)

    def stop(self, client_inout):
        self._server.stop(client_inout)

    @property
    def server(self):
        return self._server


class ServerTerminal(SpawnBase):

    def __init__(self, *args, **kwargs):
        super(ServerTerminal, self).__init__(*args, **kwargs)
        self._pipes = Pipes()
        self._serverprocess = None
        self._serverprocess_factory = None
        self.mock_setwinsize = mock.Mock()
        self._raise_timeout_in_read = False
        self.child_fd = self._client_inout.infd

    def set_serverprocess_factory(self, serverprocess_factory):
        self._serverprocess_factory = serverprocess_factory

    @property
    def _client_inout(self):
        return self._pipes.client_inout

    @property
    def _server_inout(self):
        return self._pipes.server_inout

    @contextmanager
    def in_raise_read_timeout(self):
        self._raise_timeout_in_read = True
        try:
            yield None
        finally:
            self._raise_timeout_in_read = False

    @contextmanager
    def chunk_size(self, chunk_size):
        self._set_chunk_size(chunk_size)
        try:
            yield None
        finally:
            self._set_chunk_size()

    def _set_chunk_size(self, chunk_size=None):
        for c in [self._client_inout, self.server]:
            c.set_chunk_size(chunk_size)

    @property
    def server(self):
        return self._serverprocess.server

    def start(self):
        self._serverprocess = self._serverprocess_factory()
        self._serverprocess.set_inout(self._server_inout)
        self._serverprocess.start()

    def close(self, force=True):
        if force and self._serverprocess.is_alive():
            LOGGER.info('ServerProcess.stop() is not called, forcing exit')
            self._serverprocess.stop(self._client_inout)
        self.join(timeout=3)

    def join(self, timeout):
        self._serverprocess.join(timeout=timeout)

    def setwinsize(self, *args):
        self.mock_setwinsize(*args)

    @staticmethod
    def sendcontrol(cntrl):
        LOGGER.info('Send control (%s) has no effect', cntrl)

    def read_nonblocking(self, size=1, timeout=None):
        timeout = timeout if timeout is not None and timeout >= 0 else None
        LOGGER.debug('read_nonblocking, size=%d', size)
        if not self._serverprocess.is_alive():
            raise pexpect.EOF('Python terminal closed')

        if self._raise_timeout_in_read:
            time.sleep(0.01)
            raise pexpect.TIMEOUT('Timeout')
        rlist = [self.child_fd]
        LOGGER.info('Waiting for %s in select with timeout %s', rlist, timeout)
        r, _, _ = select.select(rlist, [], [], timeout)
        if not r:
            raise pexpect.TIMEOUT('Timeout in read_nonblocking')

        LOGGER.info('Calling super read_nonblocking')
        ret = super(ServerTerminal, self).read_nonblocking(size, timeout=timeout)
        LOGGER.debug('Read %s, type=%s, first=%s', ret, type(ret), ret[0] if ret else '')
        return ret

    def send(self, s):
        self._client_inout.write(s)

    def sendline(self, line):
        self.send(line + '\n')
