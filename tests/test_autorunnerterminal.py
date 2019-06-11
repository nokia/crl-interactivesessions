from collections import namedtuple
import logging
import mock
import pytest
from fixtureresources.fixtures import create_patch
from crl.interactivesessions.autorecoveringterminal import (
    AutoRecoveringTerminal)
from crl.interactivesessions.autorunnerterminal import (
    AutoRunnerTerminal)
from crl.interactivesessions.runnerexceptions import (
    RunnerTerminalSessionClosed,
    InvalidProxySession,
    RunnerTerminalSessionBroken)
from .shells.mock_interactivesession import break_session


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def mock_session():
    return mock.create_autospec(AutoRecoveringTerminal, spec_set=True)


@pytest.fixture(scope='function')
def mock_get_response_or_raise(request):
    return create_patch(mock.patch.object(
        AutoRunnerTerminal, 'get_response_or_raise'), request)


def test_initialize(mock_session):
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session)
    # pylint: disable=protected-access
    mock_session.set_prepare.assert_called_once_with(terminal.setup_session)
    mock_session.set_finalize.assert_called_once_with(
        terminal._close_in_auto_close)
    mock_session.set_broken_exceptions.assert_called_once_with(
        RunnerTerminalSessionBroken)
    mock_session.set_verify.assert_called_once_with(terminal._verify)


def test_initialize_with_prepare(mock_session):
    mock_prepare = mock.Mock()
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session, prepare=mock_prepare)

    _, set_prepare_args, _ = mock_session.set_prepare.mock_calls[0]
    mock_session_prepare = set_prepare_args[0]
    mock_session_prepare()

    mock_prepare.assert_called_once_with()


def test_initialize_with_finalize(mock_session):
    mock_finalize = mock.Mock()
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session, finalize=mock_finalize)

    _, set_finalize_args, _ = mock_session.set_finalize.mock_calls[0]
    mock_session_finalize = set_finalize_args[0]
    mock_session_finalize()

    mock_finalize.assert_called_once_with()


def test_error_handling(mock_session, mock_get_response_or_raise):
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session)
    assert terminal.run_python('cmd') == (
        mock_get_response_or_raise.return_value.obj)

    mock_session.auto_close.assert_called_once_with()


def test_error_handling_session_broken(mock_session,
                                       mock_get_response_or_raise):
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session)
    mock_get_response_or_raise.side_effect = RunnerTerminalSessionBroken

    with pytest.raises(RunnerTerminalSessionBroken):
        terminal.run_python('cmd')

    mock_session.auto_close.assert_called_once_with()


def test_error_handling_closed_session(mock_session):
    terminal = AutoRunnerTerminal()
    terminal.initialize(session=mock_session)
    terminal.close()
    with pytest.raises(RunnerTerminalSessionClosed) as excinfo:
        terminal.run_python('cmd')

    assert "Trying to run command" in excinfo.value.args[0]


class SimpleProxyContainer(object):
    def __init__(self, terminal):
        self.terminal = terminal
        self.proxy = terminal.create_empty_remote_proxy()

    def prepare(self):
        self.proxy.set_from_remote_proxy(
            self.terminal.get_proxy_object_from_call('chr', 48))

    def finalize(self):
        self.proxy.set_from_remote_proxy(
            self.terminal.create_empty_remote_proxy())


@pytest.mark.parametrize('is_finalize', [True, False])
def test_autorecovery_as_local(mock_interactivesession,
                               is_finalize):

    terminal = AutoRunnerTerminal()
    p = SimpleProxyContainer(terminal)
    fkwargs = {'finalize': p.finalize} if is_finalize else {}
    terminal.initialize_with_shells(shells=mock.Mock(),
                                    prepare=p.prepare,
                                    **fkwargs)

    assert p.proxy.as_local_value() == '0'
    break_session(mock_interactivesession)
    assert p.proxy.as_local_value() == '0'


TupleFactory = namedtuple('TupleFactory', ['instance', 'create'])


class NamedtupleProxy(object):
    def __init__(self, terminal):
        self.terminal = terminal
        self.namedtuple = terminal.create_empty_recursive_proxy()
        self.tuples = []

    def create_recoverable_namedtuple(self, *args):
        def create():
            return self.namedtuple(*args)

        self.tuples.append(TupleFactory(instance=create(), create=create))
        return self.tuples[-1].instance

    def prepare(self):
        self.terminal.import_libraries('collections')
        self.namedtuple.set_from_remote_proxy(
            self.terminal.get_recursive_proxy('collections.namedtuple'))
        for t in self.tuples:
            t.instance.set_from_remote_proxy(t.create())


@pytest.fixture
def autorunnerterminal():
    a = AutoRunnerTerminal()
    try:
        yield a
    finally:
        a.close()


def test_autorecovery_recursive(mock_interactivesession, autorunnerterminal):
    p = NamedtupleProxy(autorunnerterminal)
    autorunnerterminal.initialize_with_shells(shells=mock.Mock(), prepare=p.prepare)
    # pylint: disable=invalid-name
    A = p.create_recoverable_namedtuple('A', ['a'])
    a = A(a=0)

    assert a.a == 0

    break_session(mock_interactivesession)
    assert A(a=1).a == 1

    with pytest.raises(InvalidProxySession):
        # pylint: disable=pointless-statement
        a.a
