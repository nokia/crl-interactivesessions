import pytest

from crl.interactivesessions.shells.remotemodules.pythoncmdline import PythonCmdline
from crl.interactivesessions.shells.remotemodules.msgs import (
    ExecCommandRequest,
    ExitRequest)
from crl.interactivesessions.shells.remotemodules.servers import PythonServer
from .commutils import PythonTerminalThread


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def terminalthread():
    t = PythonTerminalThread()
    t.set_server_and_pythoncmdlinefactories(PythonServer, PythonCmdline)
    return t


def test_pythoninteractive(terminalthread):
    terminalthread.start()
    try:
        c = terminalthread.create_client()
        assert c.receive().server_id

        reply = c.send_and_receive(ExecCommandRequest.create('a=1'))
        assert reply.out == ''
        reply = c.send_and_receive(ExecCommandRequest.create('a'))
        assert reply.out == '1'

    finally:
        c.send(ExitRequest())
        terminalthread.join()
