import sys
from contextlib import contextmanager
from collections import namedtuple
from io import StringIO
import mock
import pytest
import pexpect
from crl.interactivesessions.shells.msgpythonshell import MsgPythonShell
from crl.interactivesessions.shells.terminalclient import (
    TerminalClientError,
    TerminalClientFatalError)
from crl.interactivesessions.shells.remotemodules.msgmanager import (
    StrComm,
    Retry)
from crl.interactivesessions.shells.remotemodules.compatibility import (
    PY3,
    to_bytes)
from .loststrcomm import (
    LostStrComm,
    CustomTerminalComm)


__copyright__ = 'Copyright (C) 2019, Nokia'


# pylint: disable=unused-argument
@pytest.fixture(autouse=True)
def mock_term_functions_in_msgpythonshell(mock_term_functions):
    pass


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


@pytest.fixture
def retry_shellcontext(mock_strcomm, normal_pythonterminal):
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


def corrupt(start, s):
    return s[:start] + len(s) * b'x'


def precorrupt(s):
    return len(s) * b'x' + s


def postcorrupt(s):
    return s + len(s) * b'x'


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


def test_exec_command_success(msgpythonshell):
    msgpythonshell.exec_command('a=1', timeout=1)
    assert msgpythonshell.exec_command('a', timeout=1) == '1'


def test_exec_command_fails(msgpythonshell):
    out = msgpythonshell.exec_command('syntax error', timeout=1)
    assert 'Traceback' in out
    assert 'SyntaxError' in out
    assert 'syntax error' in out


def test_exec_command_server_fails(server_rubbish_msgpythonshell,
                                   server_rubbish_pythonterminal_ctx):
    with server_rubbish_pythonterminal_ctx.in_context():
        in_rubbish_out = server_rubbish_msgpythonshell.exec_command('a=1', timeout=1)

    after_out = server_rubbish_msgpythonshell.exec_command('a=1', timeout=1)
    for out in [in_rubbish_out, after_out]:
        assert b'FatalPythonError' not in out
        assert server_rubbish_pythonterminal_ctx.expected_rubbish not in to_bytes(out)


def test_exec_command_client_fails(client_rubbish_msgpythonshell,
                                   client_rubbish_pythonterminal_ctx):
    with client_rubbish_pythonterminal_ctx.in_context():
        in_rubbish_out = client_rubbish_msgpythonshell.exec_command('a=1', timeout=1)

    after_out = client_rubbish_msgpythonshell.exec_command('a=1', timeout=1)
    for out in [in_rubbish_out, after_out]:
        assert b'FatalPythonError' not in out
        assert client_rubbish_pythonterminal_ctx.expected_rubbish not in to_bytes(out)


def some_lost_strcomm():
    return pytest.mark.parametrize('mock_strcomm', [
        {'probability_of_lost': '4/11'},
        {'probability_of_lost': '4/11', 'modifier': lambda s: corrupt(30, s)},
        {'probability_of_lost': '4/11', 'modifier': lambda s: corrupt(40, s)},
        {'probability_of_lost': '1', 'modifier': precorrupt},
        {'probability_of_lost': '1', 'modifier': postcorrupt}], indirect=True)


@some_lost_strcomm()
def test_exec_command_lostmsg(mock_strcomm, shortretry_msgpythonshell):
    shell = shortretry_msgpythonshell
    shell.exec_command('s = 0', timeout=2)
    expected_s = 0
    with mock_strcomm.in_lost():
        for i in range(3):
            shell.exec_command('s += {i}'.format(i=i), timeout=2)
            s = shell.exec_command('s', timeout=2)
            expected_s += i
            assert int(s.strip()) == expected_s
    shell.exec_command('s', timeout=2)


@pytest.mark.parametrize('mock_strcomm', [{'probability_of_lost': '1'}],
                         indirect=True)
def test_exec_command_all_lost(mock_strcomm, terminate_msgpythonshell):
    broken_msg = 'Connection broken'
    with mock_strcomm.in_lost():
        _expect_broken_shell(terminate_msgpythonshell, broken_msg)

    assert broken_msg in terminate_msgpythonshell.exec_command('s = 0')


def _expect_broken_shell(shell, broken_msg):
    with pytest.raises(TerminalClientFatalError) as excinfo:
        shell.exec_command('s = 0', timeout=1)

    assert broken_msg in str(excinfo.value)


@some_lost_strcomm()
def test_exec_command_timeout(mock_strcomm, shortretry_msgpythonshell):
    shortretry_msgpythonshell.exec_command('import time')
    with mock_strcomm.in_lost():
        with pytest.raises(TerminalClientError) as excinfo:
            shortretry_msgpythonshell.exec_command('time.sleep(0.5)', timeout=0.1)

    assert 'Timeout' in str(excinfo.value)


def test_msgpythonshell_noattrs():
    with pytest.raises(AttributeError):
        m = MsgPythonShell()
        getattr(m, 'notexisting')


def test_msgpythonshell_chunk_reads(chunk_msgpythonshell, chunk_pythonterminal_ctx):
    s = 30 * 's'
    with chunk_pythonterminal_ctx.in_context():
        out = chunk_msgpythonshell.exec_command(repr(s), timeout=1)
        assert out == s


def test_msgpythonshell_is_in_terminal(client_rubbish_msgpythonshell,
                                       client_rubbish_pythonterminal_ctx):
    assert is_in_terminal(client_rubbish_msgpythonshell)
    with client_rubbish_pythonterminal_ctx.in_context():
        client_rubbish_msgpythonshell.exec_command(repr('s'), timeout=1)
    assert is_in_terminal(client_rubbish_msgpythonshell)
    client_rubbish_msgpythonshell.exit()
    with pytest.raises(pexpect.EOF):
        is_in_terminal(client_rubbish_msgpythonshell)


def is_in_terminal(shell):
    p = shell.get_prompt_from_terminal(timeout=1)
    return shell.is_terminal_prompt_matching(p)


def test_msgpythonshell_send_stdout(msgpythonshell, normal_pythonterminal):
    out = 'out'
    msgpythonshell.send_command("{stdout}.write({out})".format(
        stdout=msgpythonshell.get_stdout_str(), out=repr(out)))
    msgpythonshell.send_command("{stdout}.flush()".format(
        stdout=msgpythonshell.get_stdout_str()))

    ret = normal_pythonterminal.read_nonblocking(len(out))
    assert ret == to_bytes(out), ret
    assert not msgpythonshell.exec_command('a = 1')


def test_msgpythonshell_outerr(msgpythonshell):
    msgpythonshell.exec_command('import sys')
    for f in ['out', 'err']:
        cmd = 'sys.std{f}.write({f!r})'.format(f=f)
        expected_result = str(len(f)) if PY3 else ''
        assert msgpythonshell.exec_command(cmd) == expected_result


def test_msgpythonshell_robot_framework_stdout(normal_pythonterminal, monkeypatch):
    """This test case is from Robot Framework test case running context where
    the sys.stdout is replaced by StringIO for capturing output. The only
    purpose is to verify that even in that case the MsgPythonShell can be
    started.
    """
    stringio = StringIO()
    monkeypatch.setattr(sys, 'stdout', stringio)
    m = MsgPythonShell()
    m.set_terminal(normal_pythonterminal)
    m.start()
    m.exit()
