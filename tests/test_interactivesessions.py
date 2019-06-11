from collections import namedtuple
import mock
import pytest
from crl.interactivesessions.InteractiveSessions import (
    InteractiveSessions,
    InteractiveSessionFactory,
    TerminalAlreadyExists)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture(scope='function')
def mock_interactivesession(request):
    m = mock.patch('crl.interactivesessions'
                   '.InteractiveSession.InteractiveSession')
    request.addfinalizer(m.stop)
    return m.start()


MockSessions = namedtuple('MockSessions', ['sessions',
                                           'mock_interactivesession'])


@pytest.fixture(scope='function')
def sessions(mock_interactivesession):
    return MockSessions(InteractiveSessions(InteractiveSessionFactory()),
                        mock_interactivesession)


def test_create_terminal(sessions):
    sessions.sessions.create_terminal(
        'terminal', 'dump_received', 'dump_outgoing')
    calls_of_mock = sessions.mock_interactivesession.mock_calls
    assert calls_of_mock == [mock.call('dump_received', 'dump_outgoing')]


def test_create_terminal_existing_name(sessions):
    with pytest.raises(TerminalAlreadyExists) as excinfo:
        for _ in range(2):
            sessions.sessions.create_terminal(
                'terminal', 'dump_received', 'dump_outgoing')

    assert excinfo.value.args[0] == (
        'Terminal name exists in terminals list: terminal')


def test_create_terminal_default_terminal_name(sessions):
    sessions.sessions.create_terminal(
        dump_received='dump_received', dump_outgoing='dump_outgoing')
    calls_of_mock = sessions.mock_interactivesession.mock_calls
    assert [mock.call('dump_received', 'dump_outgoing')] == calls_of_mock


def test_create_terminal_default_terminal_name_no_dump(sessions):
    sessions.sessions.create_terminal()
    calls_of_mock = sessions.mock_interactivesession.mock_calls
    assert [mock.call(None, None)] == calls_of_mock
