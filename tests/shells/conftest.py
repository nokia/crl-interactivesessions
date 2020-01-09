from contextlib import contextmanager
from collections import namedtuple
import mock
import pytest
from crl.interactivesessions import InteractiveSession
from crl.interactivesessions.shells.bashshell import BashShell
from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from crl.interactivesessions.shells.msgpythonshell import MsgPythonShell
from crl.interactivesessions.shells.terminalclient import TerminalClient
from crl.interactivesessions.shells.remotemodules.msgmanager import (
    StrComm,
    Retry)

from .loststrcomm import (
    LostStrComm,
    CustomTerminalComm)
from .bashterminalshell import BashTerminalShell
from .statuscodeverifier import StatusCodeVerifier
from .mockspawn import MockSpawn
from .interpreter import State


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


@pytest.fixture
def msgpythonshell(normal_pythonterminal):
    with msgpythonshell_context(normal_pythonterminal) as m:
        yield m


@pytest.fixture
def shortretry_msgpythonshell(retry_shellcontext):
    with retry_shellcontext(Retry(tries=20, interval=0.4, timeout=0.5)) as s:
        yield s


@pytest.fixture
def terminate_msgpythonshell(retry_shellcontext, normal_pythonterminal):
    with retry_shellcontext(Retry(tries=3, interval=0.4, timeout=0.5)) as s:
        try:
            yield s
        finally:
            normal_pythonterminal.terminate()

# pylint: disable=unused-argument
@pytest.fixture
def retry_shellcontext(mock_strcomm, simple_retry_shellcontext):
    return simple_retry_shellcontext


@pytest.fixture
def simple_retry_shellcontext(normal_pythonterminal):
    @contextmanager
    def ctx(retry):
        try:
            MsgPythonShell.set_retry(retry)
            with msgpythonshell_context(normal_pythonterminal) as m:
                yield m
        finally:
            MsgPythonShell.reset_retry()

    return ctx


@pytest.fixture
def client_rubbish_msgpythonshell(client_rubbish_pythonterminal_ctx):
    with msgpythonshell_context(client_rubbish_pythonterminal_ctx.pythonterminal) as m:
        yield m


@pytest.fixture
def server_rubbish_msgpythonshell(server_rubbish_pythonterminal_ctx):
    with msgpythonshell_context(server_rubbish_pythonterminal_ctx.pythonterminal) as m:
        yield m


@pytest.fixture
def mock_strcomm(request):
    lst = LostStrComm(**request.param)

    def strcomm_fact(*args, **kwargs):
        s = StrComm(*args, **kwargs)
        lst.set_strcomm(s)
        return lst

    with customterminalcomm_context():
        with mock.patch('crl.interactivesessions.shells.'
                        'remotemodules.msgmanager.StrComm') as p:
            p.side_effect = strcomm_fact
            yield lst


@contextmanager
def customterminalcomm_context():
    with mock.patch('crl.interactivesessions.shells.'
                    'terminalclient.TerminalComm',
                    side_effect=CustomTerminalComm) as p:
        yield p


class ShellContext(namedtuple('ShellContext', ['shell', 'context'])):
    pass


@pytest.fixture
def client_rubbish_pythonterminal_ctx(rubbish_context, request):
    with rubbish_context['client'] as ctx:
        yield ctx


@pytest.fixture
def server_rubbish_pythonterminal_ctx(rubbish_context, request):
    with rubbish_context['server'] as ctx:
        yield ctx


@pytest.fixture
def chunk_msgpythonshell(chunk_pythonterminal_ctx):
    with msgpythonshell_context(chunk_pythonterminal_ctx.pythonterminal) as m:
        yield m


class CustomTerminalClient(TerminalClient):
    def __init__(self):
        super(CustomTerminalClient, self).__init__()
        self.received_msgs = []

    def _receive(self, timeout):
        msg = super(CustomTerminalClient, self)._receive(timeout)
        self.received_msgs.append(msg)
        return msg


@pytest.fixture
def customterminalclient():
    with mock_terminalclient(CustomTerminalClient) as m:
        yield m


@pytest.fixture
def duplicateclient():
    with mock_terminalclient(DuplicateClient) as m:
        yield m


@contextmanager
def mock_terminalclient(termcls):
    t = termcls()
    with mock.patch('crl.interactivesessions.shells.msgpythonshell.TerminalClient',
                    spec_set=True) as p:
        p.return_value = t
        yield t


class DuplicateClient(TerminalClient):
    def send_and_receive(self, msg, timeout):
        reply = super(DuplicateClient, self).send_and_receive(msg, timeout)
        self.send(msg)
        return reply


@pytest.fixture
def custommsgpythonshell(customterminalclient, simple_retry_shellcontext):
    with simple_retry_shellcontext(Retry(tries=50, interval=0.1, timeout=0.5)) as s:
        yield s


@pytest.fixture
def duplicateshell(duplicateclient, normal_pythonterminal):
    with msgpythonshell_context(normal_pythonterminal) as s:
        yield s


@contextmanager
def msgpythonshell_context(terminal):
    m = MsgPythonShell()
    m.set_terminal(terminal)
    m.delaybeforesend = 1
    m.start()
    assert m.delaybeforesend == 0
    try:
        yield m
    finally:
        m.exit()
        assert m.delaybeforesend == 1
        terminal.join(timeout=3)


@pytest.fixture
def mockspawn(monkeypatch):
    monkeypatch.setattr(InteractiveSession.pexpect, 'spawn', MockSpawn)


@pytest.fixture
def mockspawn_state():
    state = State()
    MockSpawn.set_state(state)
    return state
