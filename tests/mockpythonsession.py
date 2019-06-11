import logging
import mock
from crl.interactivesessions.InteractiveSession import InteractiveSession
from crl.interactivesessions.shells.remotemodules.pythoncmdline import (
    get_code_object)


LOGGER = logging.getLogger(__name__)


class MockPythonSessionClosed(Exception):
    pass


class MockPythonSession(object):

    def __init__(self, capsys):
        self.mock_interactivesession = None
        self.mock_interactivesessionexecutor = None
        self.multilinecmd = ''
        self.namespace = {}
        self.capsys = capsys
        self._setup_mock_interactivesessionexecutor()

    def set_exec_command_side_effect(self, side_effect):
        cs = self.mock_interactivesession.current_shell.return_value
        cs.exec_command.side_effect = side_effect

    def _setup_mock_interactivesessionexecutor(self):
        self._setup_interactivesession()
        self.mock_interactivesessionexecutor = mock.Mock(
            spec_set=['get_session'])
        self.mock_interactivesessionexecutor.get_session.return_value = (
            self.mock_interactivesession)
        self.set_exec_command_side_effect(self.mock_run_cmdline)
        self.mock_interactivesession.close_terminal.side_effect = self._close

    def _setup_interactivesession(self):
        self.mock_interactivesession = mock.create_autospec(
            InteractiveSession, spec_set=True)

    def __getattr__(self, name):
        return getattr(self.mock_interactivesessionexecutor, name)

    def mock_run_cmdline(self, cmd, **kwargs):  # pylint: disable=unused-argument
        LOGGER.debug('MockPythonSession running cmd: %s', cmd)

        try:
            code_obj = get_code_object(self.multilinecmd + cmd, mode='single')
            self.multilinecmd = ''
        except SyntaxError as e:
            if e.args[0].startswith('unexpected EOF'):
                self.multilinecmd += cmd + '\n'
                return ''
            raise
        return self._get_response(code_obj)

    def _get_response(self, code_obj):
        response = eval(code_obj, self.namespace)
        LOGGER.debug("MockPythonSession response: %s; type == %s", response,
                     type(response))
        return response

    def _close(self):
        self.set_exec_command_side_effect(MockPythonSessionClosed)
        self.namespace = {}
