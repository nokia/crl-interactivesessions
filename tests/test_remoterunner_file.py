import os
import logging
import stat
import filecmp
import errno
import mock
import pytest

from crl.interactivesessions.pexpectplatform import is_windows
from crl.interactivesessions._process import RunResult


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


# pylint: disable=unused-argument
@pytest.fixture(autouse=True)
def mock_term_functions_in_remoterunner_file(mock_term_functions):
    pass


def get_os_path_from_localpath(localpath):
    return os.path.join(localpath.dirname, localpath.basename)


@pytest.fixture(scope='function')
def source(tmpdir):
    s = tmpdir.mkdir('source').join('source')
    s.write('sourcecontent')
    return get_os_path_from_localpath(s)


@pytest.fixture(scope='function')
def sourcedir(tmpdir):
    s = tmpdir.mkdir('sourcedir')
    sfile = s.join('s')
    sfile.write('sfile')
    a = s.mkdir('a')
    aa = a.mkdir('aa')
    a.mkdir('ab')
    afile = a.join('a')
    afile.write('afile')
    aafile = aa.join('aafile')
    aafile.write('aafile')
    return get_os_path_from_localpath(s)


@pytest.fixture(scope='function')
def target(tmpdir):
    return tmpdir.mkdir('target')


def filecopyparams():
    return pytest.mark.parametrize('mode,destination_dir,expected_target', [
        (oct(0o755), None, os.path.join('.', 'source')),
        (oct(0o755), 'target', os.path.join('.', 'target', 'source')),
        (oct(0o755), os.path.join('target', ''),
         os.path.join('.', 'target', 'source')),
        (oct(0o755), os.path.join('new', 'target'),
         os.path.join('.', 'new', 'target', 'source')),
        (oct(0o755), os.path.join('new', 'target', ''),
         os.path.join('.', 'new', 'target', 'source')),
        (oct(0o444), None, os.path.join('.', 'source'))])


def filecopyparams_from_target():
    return pytest.mark.parametrize('destination,expected_target', [
        (None, os.path.join('.', 'source')),
        ('target', os.path.join('.', 'target')),
        (os.path.join('target', ''),
         os.path.join('.', 'target', 'source')),
        (os.path.join('new', 'target'),
         os.path.join('.', 'new', 'target')),
        (os.path.join('new', 'target', ''),
         os.path.join('.', 'new', 'target', 'source')),
        (None, os.path.join('.', 'source'))])


@pytest.fixture
def copyrunner(remoterunner, normal_shelldicts):
    for name in ['from_target', 'to_target', 'target']:
        remoterunner.set_target(shelldicts=normal_shelldicts,
                                name=name)
    return remoterunner


@filecopyparams()
def test_copy_file_between_targets(copyrunner,
                                   source,
                                   target,
                                   mode,
                                   destination_dir,
                                   expected_target,
                                   intcaplog):
    with target.as_cwd():
        assert copyrunner.copy_file_between_targets(
            from_target='from_target',
            source_file=source,
            to_target='to_target',
            destination_dir=destination_dir,
            mode=mode,
            timeout=1) == RunResult(status='0', stdout='', stderr='')

        logger.debug('pwd: %s, source: %s, exptected_target: %s',
                     os.getcwd(), source, expected_target)
        assert filecmp.cmp(source, expected_target)
        assert oct(os.stat(
            expected_target).st_mode & 0o777) == mode or is_windows()

    assert "write(*('sourcecontent',)" not in intcaplog.text


@filecopyparams_from_target()
def test_copy_file_from_target(copyrunner,
                               source,
                               target,
                               destination,
                               expected_target,
                               intcaplog):
    with target.as_cwd():
        assert copyrunner.copy_file_from_target(
            target='from_target',
            source_file=source,
            destination=destination,
            timeout=1) == RunResult(status='0', stdout='', stderr='')

        assert filecmp.cmp(source, expected_target)

    assert "write(*('sourcecontent',)" not in intcaplog.text


@filecopyparams()
def test_copy_file_to_target(copyrunner,
                             source,
                             target,
                             mode,
                             destination_dir,
                             expected_target,
                             intcaplog):
    destination_kwarg = {} if destination_dir is None else {'destination_dir':
                                                            destination_dir}
    with target.as_cwd():
        assert copyrunner.copy_file_to_target(
            source_file=source,
            mode=mode,
            target='to_target',
            timeout=1,
            **destination_kwarg) == RunResult(status='0', stdout='', stderr='')

        assert filecmp.cmp(source, expected_target)
        assert oct(os.stat(
            expected_target).st_mode & 0o777) == mode or is_windows()

    assert "write(*('sourcecontent',)" not in intcaplog.text


@pytest.mark.parametrize('create_target_dir_before', [True, False])
@pytest.mark.parametrize('target_dir', [
    'target', os.path.join('target', 'new')])
@pytest.mark.parametrize('mode', [oct(0o777), oct(0o755), oct(0o444)])
def test_copy_directory_to_target(copyrunner,
                                  sourcedir,
                                  target,
                                  create_target_dir_before,
                                  target_dir,
                                  mode):
    with target.as_cwd():
        if create_target_dir_before:
            os.makedirs(target_dir)
        assert copyrunner.copy_directory_to_target(
            source_dir=sourcedir,
            target_dir=target_dir,
            mode=mode,
            target='to_target') == RunResult(status='0', stdout='', stderr='')
        dircmp = filecmp.dircmp(sourcedir, target_dir)
        dircmp.report()
        for diff in [dircmp.left_only, dircmp.right_only, dircmp.diff_files]:
            assert not diff


@pytest.mark.parametrize('path,mode', [
    ('target', oct(0o777)),
    (os.path.join('target', 'new'), oct(0o755)),
    ('target', oct(0o444))])
def test_create_directory_in_target(copyrunner,
                                    target,
                                    path,
                                    mode):
    with target.as_cwd():
        assert copyrunner.create_directory_in_target(
            path,
            mode=mode,
            target='target') == RunResult(status='0', stdout='', stderr='')
        logger.debug('current dir: %s', os.getcwd())
        m = os.stat(path).st_mode
        assert stat.S_ISDIR(m)
        assert stat.S_IMODE(m) == int(mode, 8)


class MockOsMakedirs(object):
    def __init__(self, side_effect):
        self.side_effect = side_effect
        self.makedirspatcher = None
        self._setup_patcher()

    def _setup_patcher(self):
        self._define_makedirspatcher()

    def mock_makedirs(self, *_):
        self.side_effect()

    def _define_makedirspatcher(self):
        self.makedirspatcher = mock.patch.object(
            os, 'makedirs', side_effect=self.mock_makedirs)

    def __enter__(self):
        self.makedirspatcher.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.makedirspatcher.stop()


@pytest.mark.usefixtures('mock_interactivesession')
def test_create_directory_raises(remoterunner,
                                 target):
    def raise_oserror():
        raise OSError(errno.EPERM, os.strerror(errno.EPERM))

    with target.as_cwd():
        remoterunner.set_target(shelldicts=[{'shellname': 'ExampleShell'}],
                                name='target')
        with MockOsMakedirs(side_effect=raise_oserror):
            with pytest.raises(OSError) as e:
                remoterunner.create_directory_in_target(
                    'newfile',
                    mode=oct(0o755),
                    target='target')
            assert "Operation not permitted" in str(e.value)
