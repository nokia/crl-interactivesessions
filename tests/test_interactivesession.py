# pylint: disable=unused-argument
import mock
import pytest
from crl.interactivesessions import InteractiveSession
from crl.interactivesessions.pexpectplatform import is_windows
from crl.interactivesessions.runnerexceptions import \
    RunnerTerminalSessionBroken


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture(scope='function')
def session():
    return InteractiveSession.InteractiveSession()


@pytest.fixture(scope='function')
def mock_shell():
    m = mock.create_autospec(InteractiveSession.Shell)
    m.start.return_value = mock.Mock()
    if is_windows():
        m.spawn = mock.Mock()
    return m


@pytest.fixture(scope='function')
def mock_spawn_shell(mock_shell):
    mock_shell.spawn = mock.Mock()
    return mock_shell


@pytest.fixture(scope='function')
def mock_spawn(request):
    if not is_windows():
        m = mock.patch('pexpect.spawn')
        request.addfinalizer(m.stop)
        return m.start()


def test_init(session):
    assert session.terminal is None
    assert session.shells == []
    assert session.dump_received is None
    assert session.dump_outgoing is None
    assert session.terminal_spawn_timeout == 30
    assert session.terminal_expect_timeout == 60


def test_spawn(session, mock_shell, mock_spawn):
    mock_shell.get_start_cmd.return_value = 'bash'

    assert mock_shell.start.return_value == session.spawn(mock_shell)

    mock_shell.get_start_cmd.assert_called_once_with()
    mock_spawn.assert_called_once_with(
        mock_shell.get_start_cmd.return_value,
        env={'TERM': "dumb"},
        timeout=session.terminal_spawn_timeout,
        ignore_sighup=False)
    assert mock_spawn.return_value == session.terminal
    assert session.terminal_expect_timeout == session.terminal.timeout
    mock_shell.set_terminal.assert_called_once_with(session.terminal)
    mock_shell.start.assert_called_once_with()
    assert mock_shell == session.shells[-1]


def test_spawn_shell(session, mock_spawn_shell):
    assert session.spawn(
        mock_spawn_shell) == mock_spawn_shell.start.return_value
    mock_spawn_shell.spawn.assert_called_once_with(
        session.terminal_spawn_timeout)
    assert session.terminal == mock_spawn_shell.spawn.return_value


def test_push(session, mock_spawn, mock_shell):
    mock_spawn_shell = mock.create_autospec(InteractiveSession.Shell)
    # pylint: disable=protected-access
    mock_spawn_shell._tty_echo = True
    mock_shell.get_start_cmd.return_value = "ssh"

    session.spawn(mock_spawn_shell)

    assert mock_shell.start.return_value == session.push(mock_shell)
    mock_shell.get_start_cmd.assert_called_once_with()
    mock_spawn_shell._exec_cmd.assert_called_once_with(
        mock_shell.get_start_cmd.return_value)
    mock_shell.set_terminal.assert_called_once_with(session.terminal)
    mock_shell.start.assert_called_once_with()
    assert mock_shell == session.shells[-1]


def test_pop(session, mock_spawn, mock_shell):
    mock_spawn_shell = mock.MagicMock(spec=InteractiveSession.Shell)
    mock_shell.get_prompt_from_terminal.return_value = "PROMPT"
    mock_shell.is_terminal_prompt_matching.return_value = True

    session.spawn(mock_spawn_shell)
    session.push(mock_shell)
    session.pop()

    mock_shell.get_prompt_from_terminal.assert_called_once_with(timeout=3)
    mock_shell.is_terminal_prompt_matching.assert_called_once_with(
        mock_shell.get_prompt_from_terminal.return_value)
    mock_shell.exit.assert_called_once_with()
    assert mock_spawn_shell == session.shells[-1]


def test_current_shell():
    intsess = InteractiveSession.InteractiveSession()
    with pytest.raises(RunnerTerminalSessionBroken) as excinfo:
        intsess.current_shell()

    assert "InteractiveSession is already closed." in excinfo.value.args[0]
