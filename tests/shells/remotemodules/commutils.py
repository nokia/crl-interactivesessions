import logging
import threading
import os

import abc
import six
from crl.interactivesessions.shells.remotemodules.servercomm import ServerComm
from crl.interactivesessions.shells.remotemodules.chunkcomm import ChunkReaderBase
from .clients import Client


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class CommThreadBase(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(CommThreadBase, self).__init__(*args, **kwargs)
        self.servercomm_factory = None
        self.servercomm = None
        self.to_thread = os.pipe()
        self.from_thread = os.pipe()
        self._thread_in_fd = self.to_thread[0]
        self._thread_out_file = os.fdopen(self.from_thread[1], 'w')
        self.threadfds = (self.to_thread[0], self.from_thread[1])
        self.mainfds = self.mainfds = (self.from_thread[0], self.to_thread[1])

    @property
    def thread_in_fd(self):
        return self._thread_in_fd

    @property
    def thread_out_file(self):
        return self._thread_out_file

    def set_servercomm_factory(self, servercomm_factory):
        self.servercomm_factory = servercomm_factory

    def run(self):
        LOGGER.info('Running thread: threadfds=%s, mainfds=%s',
                    self.threadfds, self.mainfds)
        if self.servercomm_factory:
            self.servercomm = self.servercomm_factory()  # pylint: disable=not-callable
        self._work()

    @abc.abstractmethod
    def _work(self):
        """Do Comm thread communication"""


class EchoCommThread(CommThreadBase):

    echomessage = 'hello'

    def _work(self):
        self.servercomm.write(self.servercomm.read(len(self.echomessage)))


class ClientComm(ChunkReaderBase):

    def __init__(self, infd, outfd):
        super(ClientComm, self).__init__()
        self._infd = infd
        self._outfd = outfd

    def _read(self, n):
        return os.read(self._infd, n)

    def write(self, s):
        os.write(self._outfd, s)


class PythonTerminalThread(CommThreadBase):

    def __init__(self):
        super(PythonTerminalThread, self).__init__()
        self._pythoncmdline_factory = None
        self.comm_factory = self._comm_factory
        self.server_factory = None
        self.server = None

    def set_server_and_pythoncmdlinefactories(self,
                                              server_factory,
                                              pythoncmdline_factory):
        self._pythoncmdline_factory = pythoncmdline_factory
        self.server_factory = server_factory
        self.server = self._create_pythonserver()

    def _comm_factory(self, *args):  # pylint: disable=unused-argument
        return ServerComm(infd=self.thread_in_fd, outfile=self.thread_out_file)

    def _work(self):
        LOGGER.info('server: %s starting to serve', self.server)
        self.server.serve()

    def _create_pythonserver(self):
        s = self.server_factory()
        s.set_comm_factory(self.comm_factory)
        s.set_pythoncmdline_factory(self._pythoncmdline_factory)
        return s

    def create_client(self):
        c = Client()

        def comm_factory(*args):  # pylint: disable=unused-argument
            return ClientComm(*self.mainfds)

        c.set_comm_factory(comm_factory)
        return c
