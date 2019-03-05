import os
import pytest

from crl.interactivesessions.shells.pythonshellbase import PythonShellBase
from .mock_shell import MockShellBase, MockPythonShell


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockPythonShellBase(MockShellBase, MockPythonShell, PythonShellBase):
    def __init__(self):
        MockShellBase.__init__(self)
        MockPythonShell.__init__(self)
        PythonShellBase.__init__(self, 'python')


@pytest.fixture
def mock_pythonshellbase_factory(caplog):
    def fact():
        p = MockPythonShellBase()
        p.start()
        p.set_caplog(caplog)
        return p

    return fact


def test_exec_command_rstrip(mock_pythonshellbase_factory):
    p = mock_pythonshellbase_factory()
    p.mock_exec_command.return_value = 'out\r\n'

    assert p.exec_command_rstrip('cmd', timeout=1) == 'out'

    p.mock_exec_command.assert_called_once_with('cmd', timeout=1)


@pytest.fixture
def tmpfile(tmpdir):
    t = tmpdir.join('tmpfile')
    t.write('content')
    return os.path.join(t.dirname, t.basename)
