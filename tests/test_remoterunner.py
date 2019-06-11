# pylint: disable=unused-argument
import logging
import signal
import os
import json
from contextlib import contextmanager
import mock
import pytest
from crl.interactivesessions.remoterunner import (
    RemoteRunner,
    TargetIsNotSet)
from crl.interactivesessions.pexpectplatform import is_windows
from crl.interactivesessions._targetproperties import _TargetProperties
from .mock_killpg import MockKillpg


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


def test_properties(mock_interactivesession):
    runner = RemoteRunner()
    runner.set_default_target_property('name', 'value')
    runner.set_target(shelldicts=[{'shellname': 'ExampleShell'}])
    assert runner.get_target_properties('default')['name'] == 'value'
    runner.set_target_property(target_name='default',
                               property_name='name',
                               property_value='newvalue')
    assert runner.get_target_properties('default')['name'] == 'newvalue'


def test_property_exceptions(mock_interactivesession, remoterunner):
    with pytest.raises(AttributeError) as excinfo:
        remoterunner.set_target_property('default', 'not_existing', 'value')
    assert str(excinfo.value) == "Property 'not_existing' not in defaultproperties"
    with pytest.raises(AttributeError) as excinfo:
        _TargetProperties().get_property('not_existing')
    assert str(excinfo.value) == "Property 'not_existing' not found"


@pytest.fixture
def mock_terminalpools():
    with mock.patch('crl.interactivesessions.remoterunner._TerminalPools',
                    spec_set=True) as p:
        yield p


@pytest.mark.parametrize('maxsize', [50, '50'])
def test_set_terminalpools_maxsize(mock_terminalpools, maxsize):
    runner = RemoteRunner()
    runner.set_terminalpools_maxsize(maxsize)
    set_maxsize = mock_terminalpools.return_value.set_maxsize
    set_maxsize.assert_called_once_with(int(maxsize))


@pytest.mark.parametrize('method', [
    lambda: RemoteRunner().get_target_properties(target='na'),
    lambda: RemoteRunner().set_target_property(target_name='na',
                                               property_name='n',
                                               property_value='v'),
    lambda: RemoteRunner().get_target_properties(target='na'),
    lambda: RemoteRunner().execute_command_in_target('cmd', target='na')])
def test_targetisnotset(method):
    with pytest.raises(TargetIsNotSet) as excinfo:
        method()
    assert str(excinfo.value) == 'na'


def test_close(mock_interactivesession,
               remoterunner):
    remoterunner.set_target(shelldicts=[{'shellname': 'ExampleShell'}],
                            name='target')

    remoterunner.execute_command_in_target('echo out', target='target')
    remoterunner.close()
    with pytest.raises(TargetIsNotSet):
        remoterunner.execute_command_in_target('echo out', target='target')
    verify_close(mock_interactivesession)


def verify_result(result, expected_status=0):
    assert result.status == str(expected_status)
    assert result.stdout == 'out'
    assert result.stderr == ''


def verify_results_of_handles(remoterunner, handles):
    for exec_id in handles:
        verify_result(remoterunner.kill_background_execution(exec_id),
                      -signal.SIGTERM)
        verify_result(remoterunner.wait_background_execution(exec_id,
                                                             timeout=1),
                      -signal.SIGTERM)


def verify_close(mock_interactivesession):
    session_factory = mock_interactivesession.side_effect
    for s in session_factory.get_mock_interactivesessions():
        s.close_terminal.assert_called_once_with()


def close_and_verify_close(remoterunner, mock_interactivesession):
    remoterunner.close()
    verify_close(mock_interactivesession)


def foreground():
    return pytest.mark.parametrize('foreground', [0])


def start_and_verify_processes(remoterunner,
                               targetname,
                               numberofprocesses,
                               foreground):
    handles = range(numberofprocesses - foreground)
    for i in handles:
        LOGGER.debug('======== Executing sleep ====== %d', i)
        remoterunner.execute_background_command_in_target(
            'echo out; sleep 10', target=targetname, exec_id=i)
    if foreground:
        verify_result(remoterunner.execute_command_in_target(
            'echo out', target=targetname))
    verify_results_of_handles(remoterunner, handles)


@pytest.mark.usefixtures('mock_term_functions')
@foreground()
def test_max_processes_in_target(remoterunner,
                                 foreground,
                                 targetname,
                                 normal_shelldicts):
    max_processes = 3
    remoterunner.set_target(shelldicts=normal_shelldicts, name=targetname)
    remoterunner.set_target_property(target_name=targetname,
                                     property_name='max_processes_in_target',
                                     property_value=max_processes)

    for _ in range(max_processes + 1):
        start_and_verify_processes(remoterunner,
                                   targetname,
                                   max_processes,
                                   foreground)


@pytest.mark.xfail(is_windows(), reason="Windows")
def test_close_when_background_processes(mock_interactivesession,
                                         remoterunner,
                                         targetname):
    remoterunner.set_target(shelldicts=[{'shellname': 'ExampleShell'}],
                            name=targetname)
    remoterunner.execute_background_command_in_target(
        'echo out; sleep 10', target=targetname)
    close_and_verify_close(remoterunner, mock_interactivesession)


class ExampleException(Exception):
    pass


def raise_test_exception():
    raise ExampleException('message')


@pytest.mark.xfail(is_windows(), reason='Windows')
def test_close_background_process_kill_raises(mock_interactivesession,
                                              remoterunner,
                                              targetname,
                                              intcaplog):
    remoterunner.set_target(shelldicts=[{'shellname': 'ExampleShell'}],
                            name=targetname)
    remoterunner.execute_background_command_in_target(
        'echo out; sleep 0.5', target=targetname)

    with MockKillpg(ignoresignals=[9], side_effect=raise_test_exception):
        remoterunner.close()

    assert ('Termination of run (echo out; sleep 0.5) failed: '
            'ExampleException: message') in intcaplog.text
    remoterunner.close()


def setdicttoenv(monkeypatch, envdict):
    for n, v in envdict.items():
        monkeypatch.setenv(n, v)


@pytest.mark.xfail(is_windows(), reason="Windows")
@pytest.mark.parametrize('orig_env, update_env', [
    ({'name': 'value'}, {'name': 'new_value'}),
    ({'name1': 'value1', 'name2': 'value2'},
     {'name1': 'new_value1', 'name3': 'value3'})])
def test_update_env_dict(mock_interactivesession,
                         remoterunner,
                         monkeypatch,
                         orig_env,
                         update_env):
    setdicttoenv(monkeypatch, orig_env)
    expected_env = os.environ.copy()
    expected_env.update(update_env)
    remoterunner.set_target_property(target_name='default',
                                     property_name='update_env_dict',
                                     property_value=update_env)

    envcmd = 'import os, json; print(json.dumps(os.environ.copy()))'
    result = remoterunner.execute_command_in_target(envcmd, executable='python')

    assert json.loads(result.stdout) == expected_env


proxytestsource = """
class TestResponse(object):
    def __init__(self, testid, status):
        self.testid = testid
        self.status = status


class ProxyTest(object):
        def __init__(self, testid):
            self.testid = testid

        def test(self, status):
            return TestResponse(self.testid, status)
"""


@pytest.fixture(scope='function')
def proxytestpath(tmpdir):
    p = tmpdir.join('proxytest.py')
    p.write(proxytestsource)
    return os.path.join(p.dirname, p.basename)


def test_get_proxy_from_call_in_terminal(remoterunner,
                                         mock_interactivesession,
                                         proxytestpath):
    term = remoterunner.get_terminal()
    remoterunner.import_local_path_module_in_terminal(term,
                                                      proxytestpath)

    ret = remoterunner.get_proxy_from_call_in_terminal(
        term, 'proxytest.ProxyTest', 1).test(0)

    assert (1, 0) == (ret.testid, ret.status)


def test_get_proxy_object_in_terminal(remoterunner,
                                      mock_interactivesession):
    term = remoterunner.get_terminal()

    osproxy = remoterunner.get_proxy_object_in_terminal(term, 'os')

    assert osproxy.uname() == os.uname()


def test_readline_history(remoterunner, normal_shelldicts):
    with bash_remoterunner() as r:
        t = r.get_terminal()
        t.runnerterminal.run('import readline')
        lengths = set()
        for _ in range(5):
            t.runnerterminal.run('a = 1')
            lengths.add(t.runnerterminal.run('readline.get_current_history_length()'))

        assert len(lengths) == 1


@contextmanager
def bash_remoterunner():
    r = RemoteRunner()
    try:
        r.set_target([{'shellname': 'BashShell'}])
        ret = r.execute_command_in_target('echo hello')
        assert not int(ret.status)
        yield r
    finally:
        r.close()
