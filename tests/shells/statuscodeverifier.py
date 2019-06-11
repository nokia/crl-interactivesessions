import mock
from .terminals.serverterminal import ServerTerminal
from .terminals.bashserver import BashServer


__copyright__ = 'Copyright (C) 2019, Nokia'


class StatusCodeVerifier(object):
    def __init__(self, bash_shell_with_terminal, bash_terminal, timeout):
        self._bash_shell_with_terminal = bash_shell_with_terminal
        self._bash_terminal = bash_terminal
        self._timeout = timeout

    def verify_with_timeout(self, timeout):
        self._verify(timeout=self._get_expected_timeout(timeout))

    def _get_expected_timeout(self, timeout):
        return self._timeout.expected if self._timeout.kwargs else timeout

    def verify(self):
        self._verify(timeout=self._timeout.expected)

    def _verify(self, timeout):
        patcher = mock.patch.object(ServerTerminal, 'expect_exact',
                                    wraps=self._bash_terminal.expect_exact)
        with patcher as mock_expect_exact:
            actual_status_code = self._bash_shell_with_terminal.get_status_code(
                **self._timeout.kwargs)
            assert actual_status_code == BashServer.expected_status_code
            mock_calls_value = mock_expect_exact.mock_calls[0]
            mock_call = mock.call(self._bash_shell_with_terminal.get_prompt(), timeout)
            assert (mock_calls_value == mock_call), mock_expect_exact.mock_calls
