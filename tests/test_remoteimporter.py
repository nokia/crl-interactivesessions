import os
import pytest
import mock
from fixtureresources.fixtures import create_patch
from crl.interactivesessions.autorunnerterminal import (
    AutoRunnerTerminal)
from crl.interactivesessions.remoteimporter import RemoteImporter


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture(scope='function')
def mock_terminal():
    return mock.create_autospec(AutoRunnerTerminal, spec_set=True)


@pytest.fixture(scope='function')
def mock_exec_in_module(request):
    return create_patch(mock.patch(
        'crl.interactivesessions.'
        'remoteimporter.exec_in_module'), request)


@pytest.fixture(scope='function')
def mock_types_moduletype(request):
    return create_patch(mock.patch(
        'crl.interactivesessions.remoteimporter.types.ModuleType'), request)


def test_remoteimporter_init(mock_terminal):
    r = RemoteImporter(mock_terminal, 1)
    assert r.terminal == mock_terminal
    remote = mock_terminal.create_empty_remote_proxy.return_value
    recursive = mock_terminal.create_empty_recursive_proxy.return_value

    assert r.sys_modules == remote
    assert r.moduletype == recursive
    assert r.exec_in_module == remote


def test_remoteimporter_prepare(mock_terminal):
    r = RemoteImporter(mock_terminal, 1)
    r.prepare()

    remote_proxy = mock_terminal.get_proxy_object.return_value
    recursive_proxy = mock_terminal.get_recursive_proxy.return_value

    assert r.sys_modules.set_from_remote_proxy.called_once_with(
        remote_proxy)
    assert r.moduletype.set_from_remote_proxy.called_once_with(
        recursive_proxy)

    assert r.exec_in_module.set_from_remote_proxy.called_once_with(
        remote_proxy)


@pytest.fixture(scope='function')
def testdir(tmpdir):
    testind = tmpdir.mkdir('d').join('test.py')
    testind.write('content')
    testintmp = tmpdir.join('test.py')
    testintmp.write('content')
    return tmpdir


@pytest.mark.parametrize('filepath, expected_modulename', [
    ('test.py', 'test'),
    (os.path.join('d', 'test.py'), 'test')])
def test_importfile(mock_terminal, filepath, expected_modulename, testdir,
                    mock_exec_in_module, mock_types_moduletype):
    with testdir.as_cwd():
        r = RemoteImporter(mock_terminal, 1)
        r.importfile(filepath)

        r.moduletype.assert_called_once_with(expected_modulename)
        r.exec_in_module.assert_called_once_with('content',
                                                 r.moduletype.return_value)
        r.sys_modules.__setitem__.assert_called_once_with(
            expected_modulename, r.moduletype.return_value)
        mock_terminal.import_libraries.assert_called_once_with(
            expected_modulename)
        mock_exec_in_module.assert_called_once_with(
            'content', mock_types_moduletype.return_value)
