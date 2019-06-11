import logging
import mock
from crl.interactivesessions.InteractiveSession import (
    InteractiveSession)
from crl.interactivesessions.shells.registershell import RegisterShell
from crl.interactivesessions.shells.pythonshellbase import PythonShellBase
from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from .strpythoncmdline import StrPythonCmdline
from .mock_shell import MockShellBase

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
logger.addHandler(ch)


__copyright__ = 'Copyright (C) 2019, Nokia'


def lambda_none(*args, **kwargs):  # pylint: disable=unused-argument
    pass


class PythonShellEmulator(object):
    def __init__(self):
        self._pythoncmdline = StrPythonCmdline()
        self.mock_pythonshell_attrs = mock.Mock(spec_set=['delaybeforesend'])

    def __getattr__(self, name):
        return getattr(self.mock_pythonshell_attrs, name)

    def exec_command(self, cmd, timeout=-1):
        logger.debug('PythonShellEmulator running cmd: %s, timeout=%s',
                     cmd, timeout)
        ret = self._pythoncmdline.exec_command(cmd)
        logger.debug("PythonShellEmulator response: %s, type=%s", ret, type(ret))
        return ret

    def clear_cmdline(self):
        self._pythoncmdline = StrPythonCmdline()


class MockPythonInteractiveSession(object):
    """This class serves as a mock class for
    :class:`.InteractiveSession.InteractiveSession`. However, only the
    :class:`.InteractiveSession.PythonShell` have effect.
    The other shells are pushed as mocks which has no effect but all the
    operations to shells can be verified, if needed. In more
    detail, also the :class:`.InteractiveSession.PythonShell`
    """

    def __init__(self):
        self.mock_interactivesession = None
        self._setup_mock_interactivesession()
        self.shells = []

    def _setup_mock_interactivesession(self):
        self.mock_interactivesession = mock.create_autospec(
            InteractiveSession, spec_set=True)
        self._set_side_effects()

    def _set_side_effects(self):
        self.mock_interactivesession.push.side_effect = self.mock_push
        self.mock_interactivesession.spawn.side_effect = self.mock_spawn
        self.mock_interactivesession.current_shell.side_effect = (
            self.mock_current_shell)
        self.mock_interactivesession.close_terminal.side_effect = (
            self.mock_close_terminal)

    def __getattr__(self, name):
        return getattr(self.mock_interactivesession, name)

    def mock_push(self, shell):
        self.__add_shell(shell)

    def __add_shell(self, shell):
        if isinstance(shell, PythonShellBase):
            self.shells.append(PythonShellEmulator())
        else:
            self.shells.append(mock.create_autospec(shell))

    def mock_spawn(self, shell):
        self.__add_shell(shell)

    def mock_current_shell(self):
        return self.shells[-1]

    def mock_close_terminal(self):
        self.shells = []


class MockInteractiveSessionFactory(object):

    def __init__(self):
        self.sessions = []

    def __call__(self, *args, **kwargs):
        self.sessions.append(MockPythonInteractiveSession())
        logger.debug('Created new %s', self.sessions[-1])
        return self.sessions[-1]

    def current_shell(self):
        return self.sessions[-1].mock_current_shell()

    def current_session(self):
        return self.sessions[-1].mock_interactivesession

    def get_mock_interactivesessions(self):
        return [s.mock_interactivesession for s in self.sessions]


class ExampleShellBase(MockShellBase):

    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        pass


@RegisterShell()
class ExampleShell(ExampleShellBase):

    mock_shellinit = lambda_none

    def __init__(self, *args, **kwargs):
        super(ExampleShell, self).__init__()
        self.mock_shellinit(*args, **kwargs)


@RegisterShell()
class SpawnRaisesShell(ExampleShellBase):
    def __init__(self, exception):
        super(SpawnRaisesShell, self).__init__()
        self.exception = exception

    def spawn(self, *_):
        raise self.exception


def break_session(mock_interactivesession):
    current_shell = (
        mock_interactivesession.side_effect.sessions[-1].mock_current_shell())
    current_shell.clear_cmdline()
