# pylint: disable=unused-argument
import logging
import pytest
import mock
from fixtureresources.fixtures import create_patch
from crl.interactivesessions.autorecoveringterminal import (
    AutoRecoveringTerminal)
from crl.interactivesessions.InteractiveSession import (
    InteractiveSession,
    SshShell,
    Shell)
from crl.interactivesessions.runnerexceptions import (
    SessionInitializationFailed)


__copyright__ = 'Copyright (C) 2019, Nokia'


logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def mock_interactivesession(request):
    return create_patch(
        mock.patch('crl.interactivesessions'
                   '.autorecoveringterminal.InteractiveSession',
                   return_value=mock.create_autospec(InteractiveSession)),
        request)


class RaiseMaxNTimes(object):
    def __init__(self, maxraises, exception=Exception):
        self._count = 0
        self.maxraises = maxraises
        self.return_value = mock.Mock()
        self.exception = exception

    def __call__(self, *args, **kwargs):
        self._count += 1
        if self._count <= self.maxraises:
            raise self.exception('message')
        return self.return_value


@pytest.fixture(scope='function')
def mock_shell():
    return mock.create_autospec(Shell)


@pytest.fixture(scope='function')
def mock_time_sleep(request):
    return create_patch(mock.patch('time.sleep', spec_set=True), request)


@pytest.mark.parametrize('spawn_maxraise,sleep_between_tries,max_tries', [
    (1, 1, 2),
    pytest.param(10, 3, 10, marks=[pytest.mark.xfail(
        raises=SessionInitializationFailed)])])
def test_initialize_raises(mock_interactivesession,
                           mock_shell,
                           mock_time_sleep,
                           spawn_maxraise,
                           sleep_between_tries,
                           max_tries):
    mspawn = mock_interactivesession.return_value.spawn
    mspawn.side_effect = RaiseMaxNTimes(spawn_maxraise)

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell,
                        sleep_between_tries=sleep_between_tries,
                        max_tries=max_tries)
    terminal.initialize_terminal()

    assert mspawn.mock_calls == [mock.call(mock_shell) for _ in range(
        spawn_maxraise + 1)]
    assert mock_time_sleep.mock_calls == [
        mock.call(sleep_between_tries) for _ in range(spawn_maxraise)]


class ExampleException1(Exception):
    pass


class ExampleException2(Exception):
    pass


@pytest.mark.parametrize('run_maxraise,exception,init_broken_exceptions', [
    (2, ExampleException1, ExampleException1)])
def test_initialize_with_init_broken_exceptions(mock_interactivesession,
                                                mock_shell,
                                                mock_time_sleep,
                                                run_maxraise,
                                                exception,
                                                init_broken_exceptions):
    mspawn = mock_interactivesession.return_value.spawn
    mspawn.side_effect = RaiseMaxNTimes(run_maxraise,
                                        exception=exception)
    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell,
                        init_broken_exceptions=init_broken_exceptions)
    terminal.initialize_terminal()

    assert mspawn.mock_calls == [
        mock.call(mock_shell) for _ in range(run_maxraise + 1)]


def test_close_terminal_raises(mock_interactivesession,
                               mock_shell,
                               mock_time_sleep):
    mspawn = mock_interactivesession.return_value.spawn
    mspawn.side_effect = RaiseMaxNTimes(1)

    mclose_terminal = mock_interactivesession.return_value.close_terminal
    mclose_terminal.side_effect = RaiseMaxNTimes(1)

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell)
    terminal.initialize_terminal()

    mclose_terminal.assert_called_once_with()


def test_initialize_multiple_shells(mock_interactivesession):
    shells = [mock.Mock(spec_set=SshShell),
              mock.Mock(spec_set=SshShell)]

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=shells)
    terminal.initialize_terminal()

    mock_interactivesession.return_value.spawn.assert_called_once_with(
        shells[0])
    mock_interactivesession.return_value.push.assert_called_once_with(
        shells[1])


def test_initialize_prepare(mock_interactivesession,
                            mock_shell):
    prepare = mock.Mock()

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell, prepare=prepare)
    terminal.initialize_terminal()

    prepare.assert_called_once_with()


def test_initialize_finalize(mock_interactivesession,
                             mock_shell):
    finalize = mock.Mock()

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell, finalize=finalize)
    terminal.initialize_terminal()

    terminal.close()

    finalize.assert_called_once_with()


def test_get_session(mock_interactivesession,
                     mock_shell):
    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell)
    terminal.initialize_terminal()

    assert terminal.get_session() == mock_interactivesession.return_value


class _BrokenException(Exception):
    pass


class _RaiseUntilCount(object):
    def __init__(self, raisecount):
        self.count = 0
        self.raisecount = raisecount

    def __call__(self, *args, **kwargs):
        self.count += 1
        if self.count <= self.raisecount:
            raise Exception('message')


@pytest.mark.parametrize('max_tries,spawn_side_effect', [
    (1, _RaiseUntilCount(1)),
    (2, _RaiseUntilCount(2)),
    (3, _RaiseUntilCount(3))])
def test_retry_run_raises(mock_interactivesession,
                          mock_shell,
                          mock_time_sleep,
                          max_tries,
                          spawn_side_effect):
    terminal = _create_terminal(mock_shell,
                                max_tries)
    mock_interactivesession.return_value.spawn.side_effect = (
        spawn_side_effect)

    with pytest.raises(SessionInitializationFailed) as excinfo:
        terminal.initialize_terminal()
    assert excinfo.value.args[0].args[0] == 'message'


def _create_terminal(mock_shell,
                     max_tries):
    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell,
                        max_tries=max_tries,
                        sleep_between_tries=3,
                        broken_exceptions=_BrokenException)
    terminal.initialize_terminal()
    return terminal


def test_verify_session(mock_interactivesession,
                        mock_time_sleep,
                        mock_shell):
    mock_finalize = mock.Mock()
    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell,
                        broken_exceptions=_BrokenException,
                        finalize=mock_finalize)
    terminal.initialize_terminal()
    m = mock.Mock(side_effect=_BrokenException)
    m.side_effect = _BrokenException
    with pytest.raises(_BrokenException):
        with terminal.auto_close():
            m()

    m.assert_called_once_with()
    mock_finalize.assert_called_once_with()


def test_finalize_raises(mock_interactivesession,
                         mock_shell,
                         intcaplog):
    def raise_exception():
        raise Exception('message')
    mock_finalize = mock.Mock(side_effect=raise_exception)

    terminal = AutoRecoveringTerminal()
    terminal.initialize(shells=mock_shell,
                        finalize=mock_finalize)
    terminal.initialize_terminal()
    terminal.close()

    assert 'Failed to finalize the terminal: message' in intcaplog.text
    mock_close_terminal = mock_interactivesession.return_value.close_terminal
    mock_close_terminal.assert_called_once_with()
