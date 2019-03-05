import mock
import pytest

from crl.interactivesessions.shells.remotemodules.msgs import ExecCommandRequest
from crl.interactivesessions.shells.remotemodules.servers import ServerBase


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def mock_msghandler_factory():
    msg_handler = mock.Mock()

    def fact():
        return msg_handler

    return fact


def test_execommandrequest(mock_msghandler_factory):
    m = ServerBase()
    m.set_msghandler_factory(ExecCommandRequest.__name__, mock_msghandler_factory)
    msg = ExecCommandRequest.create('cmd')
    m.handle_serialized(m.serialize(msg))

    _, args, _ = mock_msghandler_factory().handle_msg.mock_calls[0]

    msg = args[0]
    assert msg.cmd == 'cmd'
    assert isinstance(msg, ExecCommandRequest)
