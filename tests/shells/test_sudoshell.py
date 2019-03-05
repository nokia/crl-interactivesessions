# pylint: disable=protected-access
import sys
import pytest
import mock
import pexpect

from crl.interactivesessions.shells.sudoshell import SudoShell, SudoError


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture()
def mock_spawn():
    return mock.create_autospec(pexpect.spawn)


@pytest.fixture()
def get_sudoshell_with_terminal(mock_spawn):
    sudo = SudoShell()
    sudo.set_terminal(mock_spawn('sudo shell'))
    return sudo


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_sudoshell_start_with_passwd_prompt(platform,
                                            monkeypatch, mock_spawn):
    monkeypatch.setattr(sys, 'platform', platform)
    mock_spawn.return_value.expect.return_value = 0

    sudo = SudoShell('sudo bash', 'testpassword')
    sudo.set_terminal(mock_spawn('sudo shell'))
    sudo._read = mock.Mock()
    sudo._common_start = mock.Mock()
    sudo.start()
    mock_spawn.return_value.sendline.assert_called_once_with(
        'testpassword')


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_sudoshell_start_fails(platform, monkeypatch,
                               mock_spawn, get_sudoshell_with_terminal):
    monkeypatch.setattr(sys, 'platform', platform)
    mock_spawn.return_value.expect.return_value = 1
    with pytest.raises(SudoError) as errinfo:
        get_sudoshell_with_terminal.start()
    assert errinfo.value.args[0] == 'Failed to start new sudo shell.'


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_sudoshell_start_normal(platform, monkeypatch,
                                mock_spawn, get_sudoshell_with_terminal):
    monkeypatch.setattr(sys, 'platform', platform)
    mock_spawn.return_value.expect.return_value = 2
    get_sudoshell_with_terminal._set_bash_environment = mock.Mock()
    get_sudoshell_with_terminal.start()
    get_sudoshell_with_terminal._set_bash_environment.\
        assert_called_once_with()


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_sudoshell_exit(platform, monkeypatch,
                        mock_spawn, get_sudoshell_with_terminal):
    monkeypatch.setattr(sys, 'platform', platform)
    get_sudoshell_with_terminal._exec_cmd = mock.Mock()
    get_sudoshell_with_terminal.exit()
    get_sudoshell_with_terminal._exec_cmd.assert_called_once_with('exit')
    mock_spawn.return_value.close()
    mock_spawn.return_value.close.assert_called_once_with()


@pytest.mark.parametrize('platform,shell,expected_cmd', [
    ('linux', SudoShell, 'sudo bash')])
def test_sudoshell_get_start_cmd(monkeypatch, platform, shell,
                                 expected_cmd):
    monkeypatch.setattr(sys, 'platform', platform)
    assert shell().get_start_cmd() == expected_cmd
