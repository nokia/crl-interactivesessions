from contextlib import contextmanager
import abc
import six
import mock
import pytest
from crl.interactivesessions.shells.sshshell import SshShell
from crl.interactivesessions.shells.sudoshell import SudoShell
from crl.interactivesessions.shells.msgreader import MsgReader
from .terminals.serverterminal import ServerTerminal
from .bashterminalshell import BashTerminalShell


__copyright__ = 'Copyright (C) 2019, Nokia'


@six.add_metaclass(abc.ABCMeta)
class CommonStarter(object):
    def common_start(self):
        return self._common_start()

    @abc.abstractmethod
    def _common_start(self):
        """Read lecture or message-of-day.
        """


@six.add_metaclass(abc.ABCMeta)
class FakeShellBase(object):
    @staticmethod
    def _set_bash_environment():
        return ''

    @classmethod
    @abc.abstractmethod
    def create(cls):
        """Create FakeShell instance.
        """


class FakeSshShell(FakeShellBase, SshShell, CommonStarter):
    def check_start_success(self):
        pass

    @classmethod
    def create(cls):
        return cls(ip='ip')


class FakeSudoShell(FakeShellBase, SudoShell, CommonStarter):
    @classmethod
    def create(cls):
        return cls()


@pytest.fixture(params=[FakeSshShell, FakeSudoShell])
def bash_terminalshell(default_serverterminal_factory, request):
    b = BashTerminalShell(shell=request.param.create(),
                          server_terminal_factory=default_serverterminal_factory)
    with b.in_terminal():
        yield b


@pytest.fixture(params=[{}, {'timeout': 100}])
def timeout(request):
    with in_timeout(request.param) as timeout:
        yield timeout


@contextmanager
def in_timeout(timeout_kwargs):
    if timeout_kwargs:
        MsgReader.set_timeout(**timeout_kwargs)
    try:
        yield MsgReader.get_timeout()
    finally:
        MsgReader.reset_timeout()


def test_common_start(bash_terminalshell, timeout):
    patcher = mock.patch.object(ServerTerminal, 'read_nonblocking',
                                wraps=bash_terminalshell.terminal.read_nonblocking)

    with patcher as mock_read_nonblocking:
        bash_terminalshell.terminal.sendline('echo message')
        prompt = bash_terminalshell.shell.get_prompt()
        assert bash_terminalshell.shell.common_start() == 'message' + prompt
        mock_calls = mock_read_nonblocking.mock_calls[0]
        assert mock_calls == mock.call(size=1024, timeout=timeout)
