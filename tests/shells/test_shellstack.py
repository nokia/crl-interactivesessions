from __future__ import print_function
import pytest
import mock
from crl.interactivesessions.shells.shellstack import (
    ShellStack, DefaultSshShell)
from crl.interactivesessions.InteractiveSession import SshShell
from crl.interactivesessions.shells.registershell import (
    RegisterShell, UnregisteredShell, ShellAlreadyRegistered)
from .mock_interactivesession import lambda_none, ExampleShell, ExampleShellBase


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockSshShell(object):
    mock_shellinit = lambda_none

    def __init__(self, *args, **kwargs):
        self.mockinit = mock.create_autospec(
            SshShell.__init__, spec_set=True)
        self.mockinit(self, *args, **kwargs)
        self.mock_shellinit(*args, **kwargs)


@pytest.fixture(scope='function')
def mock_sshshell(request):
    patcher = mock.patch.object(
        DefaultSshShell, '__bases__', (MockSshShell,))
    mpatch = patcher.start()
    request.addfinalizer(patcher.stop)
    patcher.is_local = True
    return mpatch


class NotRegisteredShell(ExampleShell):
    pass


@pytest.fixture(scope='function')
def mock_shellinit():
    m = mock.Mock()
    MockSshShell.mock_shellinit = m
    ExampleShell.mock_shellinit = m

    return m


class ShellTester(object):
    def __init__(self, shelldict, expected_kwargs, expected_class_name):
        self.shelldict = shelldict
        self.expected_kwargs = expected_kwargs
        self.expected_class_name = expected_class_name

    def verify(self, actual_mock_calls, actual_shell):
        assert actual_mock_calls == mock.call(**self.expected_kwargs)
        assert actual_shell.__class__.__name__ == self.expected_class_name


class SshShellTester(ShellTester):
    def __init__(self, hostid):
        host = 'host{}'.format(hostid)
        user = 'user{}'.format(hostid)
        password = 'password{}'.format(hostid)

        super(SshShellTester, self).__init__(
            shelldict={'host': host,
                       'user': user,
                       'password': password},
            expected_kwargs={'ip': host,
                             'username': user,
                             'password': password},
            expected_class_name='DefaultSshShell')


class SshShellTesterWithPort(SshShellTester):
    def __init__(self, hostid, port):
        super(SshShellTesterWithPort, self).__init__(hostid)
        self.shelldict['port'] = port
        self.expected_kwargs['port'] = port


class ExampleShellTester(ShellTester):
    def __init__(self, **shelldict):
        expected_class_name = 'ExampleShell'
        expected_kwargs = shelldict.copy()
        shelldict['shellname'] = expected_class_name
        super(ExampleShellTester, self).__init__(
            shelldict=shelldict,
            expected_kwargs=expected_kwargs,
            expected_class_name=expected_class_name)


@pytest.mark.parametrize('shelltesters', [
    [SshShellTester(1)],
    [SshShellTester(1),
     SshShellTesterWithPort(2, 'port2')],
    [SshShellTester(1),
     SshShellTesterWithPort(2, None),
     SshShellTesterWithPort(3, '')],
    [SshShellTester(1),
     ExampleShellTester()],
    [ExampleShellTester(a='a', b='b')]])
def test_shells(shelltesters,
                mock_sshshell,  # pylint: disable=unused-argument
                mock_shellinit):
    ss = ShellStack()
    ss.initialize([s.shelldict for s in shelltesters])
    for i, s in enumerate(shelltesters):
        actual_shell = ss.shells[i]
        s.verify(mock_shellinit.mock_calls[i], actual_shell)


def test_notregisteredshell():
    ss = ShellStack()
    ss.initialize(shelldicts=[{'shellname': 'NotRegisteredShell'}])
    with pytest.raises(UnregisteredShell) as excinfo:
        print(ss.shells)

    assert 'NotRegisteredShell' in excinfo.value.args[0]


def test_dublicate_registration():

    with pytest.raises(ShellAlreadyRegistered) as excinfo:

        @RegisterShell()  # pylint: disable=unused-variable
        class ExampleShell(ExampleShellBase):
            pass

    assert excinfo.value.args[0].__name__ == 'ExampleShell'
