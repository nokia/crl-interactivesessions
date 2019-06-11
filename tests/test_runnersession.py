# pylint: disable=protected-access,unused-argument
from collections import namedtuple
import mock
import pytest
from crl.interactivesessions.RunnerSession import RunnerSession
from crl.interactivesessions.InteractiveSessionExecutor import (
    InteractiveSessionExecutor)


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockInteractiveSessionExecutor(object):

    def __init__(self, *args, **kwargs):
        self.mockinit = mock.create_autospec(
            InteractiveSessionExecutor.__init__,
            spec_set=True)
        self.mockinit(self, *args, **kwargs)
        self.__add_baseclass_to_dict(InteractiveSessionExecutor)

    def __add_baseclass_to_dict(self, baseclass):
        self.__add_to_dict(mock.create_autospec(baseclass,
                                                spec_set=True).__dict__)

    def __add_to_dict(self, objdict):
        for name in objdict:
            if not name.startswith('__'):
                self.__dict__[name] = objdict[name]


@pytest.fixture(scope='function')
def mock_session_bases(request):
    patcher = mock.patch.object(
        RunnerSession, '__bases__', (MockInteractiveSessionExecutor,))
    mpatch = patcher.start()
    request.addfinalizer(patcher.stop)
    patcher.is_local = True
    return mpatch


def test_init(mock_session_bases):
    rs = RunnerSession('node_name',
                       host_name='host_name',
                       host_user='host_user',
                       host_password='host_password')

    rs.mockinit.assert_called_once_with(rs,
                                        'node_name',
                                        host_name='host_name',
                                        host_user='host_user',
                                        host_password='host_password')


@pytest.mark.parametrize('non_existing_argument', [
    'non_existing_argument',
    '_get_random_handle_name'])
def test_getattr_non_exisitng_argument(mock_session_bases,
                                       non_existing_argument):
    with pytest.raises(AttributeError) as execinfo:
        getattr(RunnerSession('node_name',
                              host_name='host_name',
                              host_user='host_user',
                              host_password='host_password'),
                non_existing_argument)

    nearg = "'RunnerSession' object has no attribute '{}'".format(non_existing_argument)
    assert execinfo.value.args[0] == nearg


RunnerSessionPublic = namedtuple('RunnerSessionPublic', ['method', 'expected'])


@pytest.fixture(scope='function')
def runnersession(mock_session_bases):
    return RunnerSession('node_name',
                         host_name='host_name',
                         host_user='host_user',
                         host_password='host_password')


@pytest.fixture(scope='function', params=[
    'initialize',
    'close_session',
    'run_python',
    'run_python_call',
    'import_libraries',
    'get_proxy_object',
    'get_proxy_object_from_call',
    'get_proxy_or_basic_from_call',
    'run_and_return_handled_python',
    'get_recursive_proxy',
    'isproxy',
    'iscallable'])
def runnersession_publics(request, runnersession):
    return {
        'initialize': RunnerSessionPublic(
            runnersession.initialize,
            runnersession._terminal.initialize),
        'close_session': RunnerSessionPublic(
            runnersession.close_session,
            runnersession._terminal.close_session),
        'run_python': RunnerSessionPublic(
            runnersession.run_python,
            runnersession._terminal.run_python),
        'run_python_call': RunnerSessionPublic(
            runnersession.run_python_call,
            runnersession._terminal.run_python_call),
        'import_libraries': RunnerSessionPublic(
            runnersession.import_libraries,
            runnersession._terminal.import_libraries),
        'get_proxy_object': RunnerSessionPublic(
            runnersession.get_proxy_object,
            runnersession._terminal.get_proxy_object),
        'get_proxy_object_from_call': RunnerSessionPublic(
            runnersession.get_proxy_object_from_call,
            runnersession._terminal.get_proxy_object_from_call),
        'get_proxy_or_basic_from_call': RunnerSessionPublic(
            runnersession.get_proxy_or_basic_from_call,
            runnersession._terminal.get_proxy_or_basic_from_call),
        'run_and_return_handled_python': RunnerSessionPublic(
            runnersession.run_and_return_handled_python,
            runnersession._terminal.run_and_return_handled_python),
        'get_recursive_proxy': RunnerSessionPublic(
            runnersession.get_recursive_proxy,
            runnersession._terminal.get_recursive_proxy),
        'isproxy': RunnerSessionPublic(
            runnersession.isproxy,
            runnersession._terminal.isproxy),
        'iscallable': RunnerSessionPublic(
            runnersession.iscallable,
            runnersession._terminal.iscallable)}[request.param]


def test_getattr_public_methods(runnersession_publics):
    assert runnersession_publics.method == runnersession_publics.expected


def test_run(mock_session_bases):
    rs = RunnerSession('node_name',
                       host_name='host_name',
                       host_user='host_user',
                       host_password='host_password')
    rs.run('cmd')

    assert rs.run.mock_calls[-1] == mock.call('cmd')  # pylint: disable=no-member


def test_get_session(mock_session_bases):
    rs = RunnerSession('node_name',
                       host_name='host_name',
                       host_user='host_user',
                       host_password='host_password')

    assert rs.get_session() == rs.get_session.return_value  # pylint: disable=no-member


def test_close(mock_session_bases):
    rs = RunnerSession('node_name',
                       host_name='host_name',
                       host_user='host_user',
                       host_password='host_password')

    rs.close()
