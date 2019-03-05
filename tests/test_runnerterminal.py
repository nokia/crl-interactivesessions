# pylint: disable=unused-argument,protected-access
import pickle
import base64
import pytest
import mock
from fixtureresources.mockfile import MockFile
from fixtureresources.fixtures import create_patch
from crl.interactivesessions import RunnerHandler
from crl.interactivesessions.runnerterminal import RunnerTerminal
from crl.interactivesessions.remoteproxies import _RemoteProxy
from crl.interactivesessions.runnerexceptions import (
    RunnerTerminalSessionClosed,
    RunnerTerminalSessionBroken)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture(scope='function')
def mock_runnerhandler(request):
    return create_patch(MockFile(filename=RunnerHandler.get_python_file_path(),
                                 content='runnerhandlercontent'),
                        request)


@pytest.fixture(scope='function')
def mock_session():
    return mock.Mock(spec=['get_session'])


@pytest.fixture(scope='function')
def runnerterminal(mock_session,
                   mock_pythonshell):
    rt = RunnerTerminal()
    rt.initialize(session=mock_session)
    return rt


@pytest.fixture(scope='function')
def mock_pythonshell(request):
    return create_patch(
        mock.patch('crl.interactivesessions.runnerterminal.MsgPythonShell'),
        request)


@pytest.fixture(scope='function')
def mock_pickle_dumps(request):
    def mock_dumps(obj):
        return 'pickle.dumps({})'.format(obj)

    return create_patch(mock.patch('pickle.dumps',
                                   side_effect=mock_dumps),
                        request)


@pytest.fixture(scope='function')
def mock_run_in_session_raise_padding(request):

    return create_patch(mock.patch.object(
        RunnerTerminal, '_run_in_session',
        side_effect=TypeError('Incorrect padding')),
                        request)


@pytest.fixture(scope='function')
def mock_run_in_session_raise_padding_once(request):

    return create_patch(mock.patch.object(
        RunnerTerminal, '_run_in_session',
        side_effect=[TypeError('Incorrect padding'), '123']),
                        request)


@pytest.fixture(scope='function')
def mock_run_in_session_raise_no_padding(request):

    return create_patch(mock.patch.object(
        RunnerTerminal, '_run_in_session',
        side_effect=TypeError('Some other error')),
                        request)


@pytest.fixture(scope='function')
def mock_base64_b64encode(request):
    def mock_encode(content):
        return 'base64.b64encode({})'.format(content)

    return create_patch(mock.patch('base64.b64encode',
                                   side_effect=mock_encode),
                        request)


@pytest.fixture(scope='function')
def mock_base64_b64decode(request):
    return create_patch(mock.patch('base64.b64decode'),
                        request)


@pytest.fixture(scope='function')
def mock_pickle_unpickler(request):
    return create_patch(mock.patch('pickle.Unpickler'),
                        request)


class MockRemoteProxy(object):
    def __init__(self):
        self.mock = mock.create_autospec(_RemoteProxy, spec_set=True)
        self.mockinit = mock.create_autospec(_RemoteProxy.__init__,
                                             spec_set=True)

    def create(self, *args, **kwargs):
        self.mockinit(*args, **kwargs)
        return self.mock


@pytest.fixture(scope='function')
def mock_remoteproxy(request):
    m = MockRemoteProxy()
    create_patch(mock.patch(
        'crl.interactivesessions.runnerterminal._RemoteProxy',
        side_effect=m.create), request)
    return m


@pytest.fixture(scope='function')
def mock_uuid_uuid4(request):
    return create_patch(mock.patch('uuid.uuid4'), request)


class ExampleException(Exception):
    def __init__(self, message, trace=None):
        super(ExampleException, self).__init__(message)
        if trace is not None:
            self.trace = trace


def test_initialize_push_pythonshell(runnerterminal,
                                     mock_session,
                                     mock_pythonshell):
    session = mock_session.get_session.return_value
    session.push.assert_called_once_with(mock_pythonshell.return_value)


def test_mock_run_in_session_raise_padding_error(
        runnerterminal, mock_run_in_session_raise_padding):
    with pytest.raises(TypeError) as excinfo:
        runnerterminal._run_in_session()
    assert 'Incorrect padding' in str(excinfo)


def test_mock_run_in_session_raise_padding_error_once(
        runnerterminal, mock_run_in_session_raise_padding_once):
    with pytest.raises(TypeError) as excinfo:
        runnerterminal._run_in_session()
    assert 'Incorrect padding' in str(excinfo)


def test_run_raise_padding(runnerterminal,
                           mock_run_in_session_raise_padding):
    with pytest.raises(RunnerTerminalSessionBroken):
        runnerterminal.run('cmd')
    assert mock_run_in_session_raise_padding.call_count == 2


def test_mock_run_in_session_raise_padding_once(
        runnerterminal, mock_run_in_session_raise_padding_once):
    runnerterminal.run('cmd')
    assert mock_run_in_session_raise_padding_once.call_count == 2


def test_run_raise_no_padding(runnerterminal,
                              mock_run_in_session_raise_no_padding):
    with pytest.raises(RunnerTerminalSessionBroken):
        runnerterminal.run('cmd')
    assert mock_run_in_session_raise_no_padding.call_count == 1


def test_initialize_import_libraries(runnerterminal,
                                     mock_session):
    cs = mock_session.get_session.return_value.current_shell.return_value

    assert cs.exec_command.mock_calls[0] == mock.call(
        'import pickle, imp, base64, os', timeout=-1)


def test_close_session(runnerterminal,
                       mock_session):

    ms = mock_session.get_session.return_value
    runnerterminal.close()

    ms.close_terminal.assert_called_once_with()


@pytest.mark.parametrize('trace', [None, 'trace'])
def test_run_python_raises(runnerterminal,
                           mock_session,
                           trace):

    cs = mock_session.get_session.return_value.current_shell.return_value
    dumpexc = pickle.dumps(ExampleException('message', trace=trace))
    cs.exec_command.return_value = base64.b64encode(
        pickle.dumps(('exception', dumpexc)))

    with pytest.raises(ExampleException) as excinfo:
        runnerterminal.run_python('cmd')

    assert excinfo.value.args[0] == 'message'


def test_run_raises_runnerrerminalressionclosed():
    rt = RunnerTerminal()
    with pytest.raises(RunnerTerminalSessionClosed) as excinfo:
        rt.run('cmd')
    assert excinfo.value.args[0].find('closed session. Command has no effect.')


def test_get_proxy_object(runnerterminal,
                          mock_remoteproxy):
    assert (runnerterminal.get_proxy_object('remote_object', 'local_spec') ==
            mock_remoteproxy.mock)

    mock_remoteproxy.mockinit.assert_called_once_with(
        runnerterminal,
        'remote_object',
        'local_spec',
        is_remote_owned=False)
