import pytest
from crl.interactivesessions.shells.bashshell import BashShell
from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from .bashterminalshell import BashTerminalShell
from .statuscodeverifier import StatusCodeVerifier


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def normal_pythonterminal(normal_pythonterminal_factory):
    return normal_pythonterminal_factory()


@pytest.fixture
def bash_shell_with_terminal(bash_shell, bash_terminal):
    bash_shell.set_terminal(bash_terminal)
    return bash_shell


@pytest.fixture
def bash_terminal(default_serverterminal_factory, bash_shell):
    b = BashTerminalShell(shell=bash_shell,
                          server_terminal_factory=default_serverterminal_factory)
    with b.in_terminal() as terminal:
        yield terminal


@pytest.fixture
def bash_shell():
    return BashShell()


@pytest.fixture(params=[{}, {'timeout': 100}])
def status_timeout(request):
    return StatusTimeout(request.param)


class StatusTimeout(object):
    def __init__(self, kwargs):
        self.kwargs = kwargs

    @property
    def expected(self):
        return self.kwargs['timeout'] if self.kwargs else DEFAULT_STATUS_TIMEOUT.get()


@pytest.fixture
def statuscodeverifier(bash_shell_with_terminal, bash_terminal, status_timeout):
    return StatusCodeVerifier(bash_shell_with_terminal=bash_shell_with_terminal,
                              bash_terminal=bash_terminal,
                              timeout=status_timeout)
