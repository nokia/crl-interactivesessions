import os
import stat
import pytest
import mock
import pexpect

from crl.interactivesessions._filecopier import (
    _RemoteFileProxy,
    RemoteFileReadingFailed,
    RemoteFileOperationTimeout,
    _OsProxiesForRemoteFile,
    _LocalFile)


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockSpawn(pexpect.spawnbase.SpawnBase):
    def __init__(self, buf=None):
        super(MockSpawn, self).__init__()
        self.buf = buf
        self.before = None

    def read_nonblocking(self, size=1, timeout=None):  # pylint: disable=unused-argument
        buf = self.buf[:size]
        self.buf = self.buf[size:]
        if buf:
            return buf
        raise pexpect.TIMEOUT('nothing to read')

    def send(self, buf):
        pass


@pytest.fixture(scope='function')
def mock_terminal():
    m = mock.Mock()
    m.get_session.return_value.terminal = MockSpawn()
    return m


@pytest.fixture(scope='function')
def mock_fileproxy():
    return mock.Mock()


def test_read_buffer_size_raises(mock_terminal, mock_fileproxy):
    mock_terminal.get_session.return_value.terminal.buf = (
        '0000000cannotbedecoded')
    with pytest.raises(RemoteFileReadingFailed):
        _RemoteFileProxy(mock_fileproxy, mock_terminal, 1).read(1)


@pytest.mark.parametrize('before,expmsg', [
    (None, ''), ('before', 'before')])
def test_read_timeout(mock_terminal, mock_fileproxy, before, expmsg):
    mock_terminal.get_session.return_value.terminal.buf = (
        '00000000001')
    mock_terminal.get_session.return_value.terminal.before = before
    with pytest.raises(RemoteFileOperationTimeout) as excinfo:
        _RemoteFileProxy(mock_fileproxy, mock_terminal, 1).read(1)

    assert str(excinfo.value) == expmsg


def test_osproxies_raises_attributeerror(mock_terminal):
    with pytest.raises(AttributeError):
        # pylint: disable=expression-not-assigned
        _OsProxiesForRemoteFile(mock_terminal, 1).notexist


@pytest.mark.parametrize('mode', ['0777', '0444', '0755'])
def test_localfile_chmod(tmpdir, mode):
    with tmpdir.as_cwd():
        l = _LocalFile('local')
        with l.open('w') as f:
            f.write('content')
        l.chmod(mode)
        with open('local') as f:
            assert f.read() == 'content'
        assert stat.S_IMODE(os.stat('local').st_mode) == int(mode, 8)


def test_localfile_with_existing_destination_dir(tmpdir):
    with tmpdir.as_cwd():
        _LocalFile(os.path.join('dir', 'f')).makedirs()
        l = _LocalFile('dir', source_file='source')
        with l.open('w') as f:
            f.write('content')
        with open(os.path.join('dir', 'source')) as f:
            assert f.read() == 'content'
