import re
import sys
import mock
import pytest
from fixtureresources.fixtures import create_patch
from crl.interactivesessions.shells.bashshell import (
    BashShell, SourceInitFileFailed)
from crl.interactivesessions.shells.namespaceshell import NamespaceShell
from crl.interactivesessions.shells.sshshell import SshShell
from crl.interactivesessions.shells.shell import Shell
from crl.interactivesessions.shells.keyauthenticatedsshshell \
    import KeyAuthenticatedSshShell, ShellStartError
from crl.interactivesessions.shells.sudoshell import SudoShell
from crl.interactivesessions.shells.shellstack import DefaultSshShell
from crl.interactivesessions.shells.sshoptions import sshoptions
from .echochannel import EchoChannel


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockBaseCls(object):

    def __init__(self, cls, omit, *args, **kwargs):
        self.cls = cls
        self.omit = omit
        self.mockinit = mock.create_autospec(
            self.cls.__init__, spec_set=True)
        self.mockinit(self, *args, **kwargs)
        self.__add_baseclass_to_dict()

    def __add_baseclass_to_dict(self):
        self.__add_to_dict(mock.create_autospec(self.cls,
                                                spec_set=True).__dict__)

    def __add_to_dict(self, objdict):
        for name in objdict:
            if not name.startswith('__') and name not in self.omit:
                self.__dict__[name] = objdict[name]


class MockShell(MockBaseCls):
    def __init__(self, *args, **kwargs):
        super(MockShell, self).__init__(Shell, dir(BashShell),
                                        *args, **kwargs)
        self.tty_echo = False


class MockBash(MockBaseCls):
    def __init__(self, *args, **kwargs):
        super(MockBash, self).__init__(BashShell, [],
                                       *args, **kwargs)


class MockSsh(MockBaseCls):
    def __init__(self, *args, **kwargs):
        super(MockSsh, self).__init__(SshShell, [],
                                      *args, **kwargs)


def create_base_patcher(request, cls, mockbasecls):
    patcher = mock.patch.object(
        cls, '__bases__', (mockbasecls,))
    mpatch = patcher.start()
    request.addfinalizer(patcher.stop)
    patcher.is_local = True
    return mpatch


@pytest.fixture(scope='function')
def mock_detect_bash_prompt(request):
    def detect_bash_prompt_works():
        pass
    return create_patch(mock.patch.object(BashShell, '_detect_bash_prompt',
                                          side_effect=detect_bash_prompt_works,
                                          return_value='Hello'),
                        request)


@pytest.fixture(scope='function')
def mock_check_start_success(request):
    def check_start_success_pass(*_, **kwargs):  # pylint: disable=unused-argument
        pass

    return create_patch(mock.patch.object(
        BashShell, 'check_start_success',
        side_effect=check_start_success_pass), request)


@pytest.fixture(scope='function')
def mock_read_until_end_status_ok(request):
    return create_patch(mock.patch.object(KeyAuthenticatedSshShell,
                                          '_read_until_end',
                                          return_value='@0@'),
                        request)


@pytest.fixture(scope='function')
def mock_read_until_end_status_nok(request):
    return create_patch(mock.patch.object(KeyAuthenticatedSshShell,
                                          '_read_until_end',
                                          return_value='@255@'),
                        request)


@pytest.fixture(scope='function')
def mock_read_until_prompt_found(request):
    buffer = 'Warning: Permanently added ipaddr (RSA) to the list ' \
             'known hosts.USAGE OF THE ROOT ACCOUNT AND THE FULL BASH IS ' \
             'RECOMMENDED ONLY FOR LIMITED USE.PLEASE USE A NON-ROOT ACCOUNT' \
             ' AND THE SCLISHELL(fsclish) AND / OR LIMITED BASH SHELL.'
    return create_patch(mock.patch.object(KeyAuthenticatedSshShell,
                                          '_read_until',
                                          return_value=buffer),
                        request)


@pytest.fixture(scope='function')
def mock_read_until_prompt_not_found(request):
    return create_patch(mock.patch.object(KeyAuthenticatedSshShell,
                                          '_read_until',
                                          side_effect=ShellStartError(
                                              "Shell start to ipaddress "
                                              "did not succeed. "
                                              "Prompt not found.")),
                        request)


@pytest.fixture(scope='function')
def mock_send_input_line(request):
    def send_input_line_works(*_, **kwargs):  # pylint: disable=unused-argument
        pass
    return create_patch(mock.patch.object(KeyAuthenticatedSshShell,
                                          '_send_input_line',
                                          side_effect=send_input_line_works,),
                        request)


@pytest.fixture(scope='function')
def mock_bash_bases(request):
    return create_base_patcher(request, BashShell, MockShell)


@pytest.fixture(scope='function')
def mock_namespace_bases(request):
    return create_base_patcher(request, NamespaceShell, MockBash)


@pytest.fixture(scope='function')
def mock_ssh_bases(request):
    return create_base_patcher(request, SshShell, MockBash)


@pytest.fixture(scope='function')
def mock_defaultssh_bases(request):
    return create_base_patcher(request, DefaultSshShell, MockSsh)


@pytest.fixture(scope='function')
def mock_keyauthenticatedsshshell_bases(request):
    return create_base_patcher(request, KeyAuthenticatedSshShell, MockSsh)


@pytest.fixture(scope='function')
def mock_sudoshell_bases(request):
    return create_base_patcher(request, SudoShell, MockBash)


@pytest.fixture(scope='function')
def mock_paramiko(request):
    return create_patch(mock.patch(
        'crl.interactivesessions.shells.sshshell.paramiko'), request)


@pytest.mark.usefixtures('mock_bash_bases', 'mock_detect_bash_prompt')
def test_bash_init_env():
    b = BashShell(init_env='init_env')
    b.exec_command.return_value = '0'
    b.start()
    # pylint: disable=no-member
    assert b.exec_command.mock_calls == [
        mock.call('. init_env'),
        mock.call('echo $?', timeout=5)]


@pytest.mark.usefixtures('mock_bash_bases', 'mock_detect_bash_prompt')
def test_bash_init_env_fails():
    b = BashShell(init_env='init_env')
    b.exec_command.return_value = '1'
    with pytest.raises(SourceInitFileFailed) as execinfo:
        b.start()
    assert execinfo.value.args[0] == '1'


@pytest.mark.usefixtures('mock_namespace_bases')
def test_namespace_init_env():
    n = NamespaceShell('namespace', init_env='init_env')

    #  pylint: disable=no-member
    n.mockinit.assert_called_once_with(n, init_env='init_env')


@pytest.mark.usefixtures('mock_ssh_bases')
@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_ssh_init_env(platform, monkeypatch):
    #  pylint: disable=protected-access
    monkeypatch.setattr(sys, 'platform', platform)
    s = SshShell(ip='ip', init_env='init_env')
    s.mockinit.assert_called_once_with(s, tty_echo=False, init_env='init_env')
    s.start()
    s._set_bash_environment.assert_called_once_with()  # pylint: disable=no-member


@pytest.mark.usefixtures('mock_keyauthenticatedsshshell_bases')
def test_ketauthenticatedsshshell_init_env():
    #  pylint: disable=protected-access
    initial_prompt = '# '
    s = KeyAuthenticatedSshShell(host='host-0.local',
                                 initial_prompt=initial_prompt)
    s._confirmation_msg = None
    s.mockinit.assert_called_once_with(s, ip='host-0.local',
                                       tty_echo=False)


@pytest.mark.usefixtures('mock_send_input_line', 'mock_read_until_end_status_ok')
def test_keyauthenticatedsshshell_wait_for_prompt_ok(mock_read_until_prompt_found):
    s = KeyAuthenticatedSshShell(host='ipaddress',
                                 initial_prompt='# ')
    s.check_start_success()
    mock_read_until_prompt_found.assert_called_once_with(
        re.compile("# $"), timeout=20)


@pytest.mark.usefixtures('mock_send_input_line')
def test_keyauthenticatedsshshell_wait_for_prompt_nok(mock_read_until_prompt_not_found):
    s = KeyAuthenticatedSshShell(host='ipaddress',
                                 initial_prompt='# ')
    with pytest.raises(ShellStartError) as execinfo:
        s.check_start_success()
    assert \
        execinfo.value.args[0] == \
        'Shell start to ipaddress did not succeed. Prompt not found.'
    mock_read_until_prompt_not_found.assert_called_once_with(
        re.compile("# $"), timeout=20)


@pytest.mark.usefixtures('mock_defaultssh_bases')
def test_defaultssh_init_env():
    s = DefaultSshShell(host='host', init_env='init_env')
    s.mockinit.assert_called_once_with(s, ip='host', init_env='init_env')


@pytest.mark.usefixtures('mock_sudoshell_bases')
@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_sudoshell_init(platform, monkeypatch):
    monkeypatch.setattr(sys, 'platform', platform)
    s = SudoShell()
    # pylint: disable=no-member
    s.mockinit.assert_called_once_with(s, tty_echo=True)


def get_ssh_args(host):
    return sshoptions + ' ' + host


@pytest.mark.parametrize('platform,shell,shell_attrs,expected_cmd', [
    ('linux', BashShell, [], 'bash'),
    ('linux', SshShell, ['host'], 'ssh ' + get_ssh_args('host')),
    ('linux', SshShell, ['host', 'user'], 'ssh ' + get_ssh_args('user@host'))
])
def test_get_start_cmd(monkeypatch,
                       platform,
                       shell,
                       shell_attrs,
                       expected_cmd):
    monkeypatch.setattr(sys, 'platform', platform)
    assert shell(*shell_attrs).get_start_cmd() == expected_cmd


@pytest.mark.parametrize('kwargs,expected_kwargs', [
    ({'username': 'username', 'password': 'password', 'port': 5022},
     {'username': 'username', 'password': 'password', 'port': 5022}),
    ({},
     {'username': None, 'password': None, 'port': 22})])
def test_sshshell_spawn(monkeypatch, mock_paramiko, kwargs, expected_kwargs):
    monkeypatch.setattr(sys, 'platform', 'win32')
    mock_paramiko.SSHClient.return_value.invoke_shell.return_value = (
        EchoChannel(list([b'recv'])))
    ssh = SshShell('host', **kwargs)
    terminal = ssh.spawn(1)
    ssh.set_terminal(terminal)
    try:
        mock_paramiko.SSHClient.return_value.connect.assert_called_once_with(
            'host', **expected_kwargs)
        assert terminal.read_nonblocking(4, 1) == b'recv'
    finally:
        ssh.exit()
        terminal.close()
        mock_paramiko.SSHClient.return_value.close.assert_called_once_with()


def test_sshshell_no_spawn_in_linux(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    ssh = SshShell('host', 'user', 'password')
    with pytest.raises(AttributeError):
        ssh.spawn(1)
