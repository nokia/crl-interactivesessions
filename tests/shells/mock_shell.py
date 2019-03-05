from contextlib import contextmanager
import mock
import pytest
from crl.interactivesessions.shells.shell import Shell
from crl.interactivesessions.shells.pythonshellbase import (
    _LOGLEVEL,
    UnexpectedOutputInPython)


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockShellBase(Shell):
    def exit(self):
        pass

    def get_start_cmd(self):
        pass

    def start(self):
        pass


class MockShell(Shell):
    def __init__(self):
        Shell.__init__(self)
        self.mock_send_input_line = mock.Mock()
        self.mock_read_until = mock.Mock()
        self.mock_exec_command = mock.Mock()
        self.mock_read_until_prompt = mock.Mock()
        self.mock_read_until.return_value = ''
        self.mock_read_until_prompt.return_value = ''
        self.mock_terminal = mock.Mock()
        self.mock_echo = False

    def _send_input_line(self, cmd):
        self.mock_send_input_line(cmd)

    def _read_until_prompt(self, timeout=-1, suppress_timeout=False):
        return self.mock_read_until_prompt(timeout=timeout,
                                           suppress_timeout=suppress_timeout)

    def _read_until(self, trigger, timeout=-1, suppress_timeout=False):
        return self.mock_read_until(trigger, timeout=timeout,
                                    suppress_timeout=suppress_timeout)

    def exec_command(self, cmd, timeout=-1):
        return self.mock_exec_command(cmd, timeout=timeout)

    def set_mock_echo_on(self):
        self.mock_echo = True


class EchoMockShell(MockShell):
    def _read_until_prompt(self, timeout=-1, suppress_timeout=False):
        with self._echo_retval_ctx():
            return super(EchoMockShell, self)._read_until_prompt(
                timeout=timeout, suppress_timeout=suppress_timeout)

    @contextmanager
    def _echo_retval_ctx(self):
        orig = self.mock_read_until_prompt.return_value
        self.mock_read_until_prompt.return_value = self._last_sendline + orig
        try:
            yield None
        finally:
            self.mock_read_until_prompt.return_value = orig

    @property
    def _last_sendline(self):
        return ('{}\r\n'.format(self.mock_sendline_cmds[-1])
                if self.mock_sendline_cmds else
                '')

    @property
    def mock_sendline_cmds(self):
        return [args[0] for _, args, _ in self.mock_terminal.sendline.mock_calls]


class MockPythonShell(MockShell):

    def __init__(self):
        super(MockPythonShell, self).__init__()
        self.caplog = None

    def set_caplog(self, caplog):
        self.caplog = caplog

    @contextmanager
    def verify_single_commands(self, cmd_gen, timeout=-1):
        with self.log_recording():
            yield None

        self.assert_single_command_no_output(cmd_gen, timeout=timeout)

    def assert_single_command_no_output(self, cmd_gen, timeout):
        assert self.mock_send_input_line.mock_calls == [mock.call(c) for c in cmd_gen()]
        assert self.mock_read_until.mock_calls == [
            mock.call('>>> ',
                      timeout=timeout,
                      suppress_timeout=False)
            for _ in cmd_gen()], self.mock_read_until.mock_calls

        logtmpl = "(PythonShell) single_command_no_output send line: {}"
        for cmd in cmd_gen():
            assert logtmpl.format(cmd) in self.logs

    @contextmanager
    def log_recording(self):
        with self.caplog.at_level(_LOGLEVEL):
            yield None

    @contextmanager
    def single_command_raises(self):
        origret = self.mock_read_until.return_value
        self.mock_read_until.return_value = 'error out'

        with pytest.raises(UnexpectedOutputInPython) as excinfo:
            try:
                yield None
            finally:
                self.mock_read_until.return_value = origret

        assert 'error out' in str(excinfo.value)

    @property
    def logs(self):
        return [r.message for r in self.caplog.get_records(
            'call') if r.levelno == _LOGLEVEL]
