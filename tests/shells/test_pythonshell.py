import mock
import pytest
from crl.interactivesessions.shells.pythonshellbase import UnexpectedOutputInPython
from crl.interactivesessions.shells.pythonshell import PythonShell
from crl.interactivesessions.shells.rawpythonshell import RawPythonShell
from . mock_shell import MockPythonShell, EchoMockShell


__copyright__ = 'Copyright (C) 2019, Nokia'


class DerivedPythonShell(PythonShell):

    def __init__(self, *args, **kwargs):
        super(DerivedPythonShell, self).__init__(*args, **kwargs)
        self.input_lines = []
        self.mock_terminal = mock.Mock()
        self.set_terminal(self.mock_terminal)

    def _read_until_prompt(self, timeout=-1, suppress_timeout=False):
        return ''

    def _read_until(self, trigger, timeout=-1, suppress_timeout=False):
        pass

    def _send_input_line(self, cmd):
        self.input_lines.append(cmd)

    @staticmethod
    def _verify_and_return_output(output, expected_output=""):
        pass


@pytest.mark.parametrize('readline_init_args', [
    {},
    {'readline_init': 'cmd'}])
def test_pythonshell_readline_init(readline_init_args):
    python = DerivedPythonShell(**readline_init_args)
    python.start()
    if readline_init_args:
        assert 'import readline' in python.input_lines
        assert "readline.parse_and_bind('cmd')" in python.input_lines
    else:
        assert 'readline' not in python.input_lines


class DerivedMockPythonShell(MockPythonShell, PythonShell):
    def __init__(self, *args, **kwargs):
        MockPythonShell.__init__(self, *args, **kwargs)
        PythonShell.__init__(self, *args, **kwargs)


@pytest.fixture
def pythonshell(caplog):
    return create_mockpythonshell(DerivedMockPythonShell, caplog)


def create_mockpythonshell(cls, caplog):
    p = cls()
    p.set_caplog(caplog)
    p.set_terminal(p.mock_terminal)
    return p


@pytest.mark.parametrize('timeout_args', [{}, {'timeout': 1}])
def test_single_command_no_output(pythonshell, timeout_args):
    timeout = timeout_args.get('timeout', 10)

    def cmd_gen():
        yield 'cmd'

    with pythonshell.verify_single_commands(cmd_gen, timeout=timeout):
        for cmd in cmd_gen():
            pythonshell.single_command_no_output(cmd, **timeout_args)


def test_single_command_no_output_raises(pythonshell):
    with pythonshell.single_command_raises():
        pythonshell.single_command_no_output('cmd')


class MockRawPythonShell(MockPythonShell, RawPythonShell):
    def __init__(self, *args, **kwargs):
        MockPythonShell.__init__(self, *args, **kwargs)
        RawPythonShell.__init__(self, *args, **kwargs)


class EchoMockRawPythonShell(EchoMockShell, MockRawPythonShell):
    def __init__(self, *args, **kwargs):
        EchoMockShell.__init__(self, *args, **kwargs)
        MockRawPythonShell.__init__(self, *args, **kwargs)


@pytest.fixture(params=[DerivedMockPythonShell, MockRawPythonShell])
def anypythonshell(request, caplog):
    return create_mockpythonshell(request.param, caplog)


@pytest.fixture
def derivedmockpythonshell(caplog):
    return create_mockpythonshell(DerivedMockPythonShell, caplog)


@pytest.fixture(params=[MockRawPythonShell, EchoMockRawPythonShell])
def mockrawpythonshell(caplog, request):
    return create_mockpythonshell(request.param, caplog)


def test_tty_echo(anypythonshell):
    assert not anypythonshell.tty_echo


def test_get_start_cmd(anypythonshell):
    expected_args = (
        ' -u' if isinstance(anypythonshell, MockRawPythonShell) else '')
    assert anypythonshell.get_start_cmd() == 'python' + expected_args


def test_start_pythonshell(derivedmockpythonshell):
    derivedmockpythonshell.start()

    derivedmockpythonshell.mock_read_until_prompt.assert_called_once_with(
        timeout=30, suppress_timeout=False)


@pytest.mark.parametrize('mockrawpythonshell', [MockRawPythonShell], indirect=True)
def test_start_rawpythonshell(mockrawpythonshell):
    mockrawpythonshell.start()

    first_read = mock.call(timeout=30, suppress_timeout=False)
    set_echo_off_read = mock.call(timeout=10, suppress_timeout=False)

    expected_reads = [first_read, set_echo_off_read]
    assert mockrawpythonshell.mock_read_until_prompt.mock_calls == expected_reads

    assert mockrawpythonshell.mock_terminal.sendline.mock_calls == [
        mock.call(cmd) for cmd in mockrawpythonshell.setup_cmds]


def test_start_rawpythonshell_raises(mockrawpythonshell):
    mockrawpythonshell.mock_read_until_prompt.return_value = 'error'
    with pytest.raises(UnexpectedOutputInPython) as excinfo:
        mockrawpythonshell.start()

    assert 'error' in str(excinfo.value)


def test_exit(anypythonshell):
    with anypythonshell.log_recording():
        anypythonshell.exit()

    assert "Exit from Python shell" in anypythonshell.logs
    anypythonshell.mock_send_input_line.assert_called_once_with('exit()')
