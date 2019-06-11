import abc
import os
import signal
import logging
import errno
from contextlib import contextmanager
import pytest
import six
from crl.interactivesessions.remoterunner import (
    RemoteRunner,
    BackgroundExecIdAlreadyInUse)
from crl.interactivesessions.pexpectplatform import is_windows
from crl.interactivesessions._process import (
    RunnerTimeout,
    RunResult,
    FailedToKillProcess)
from crl.interactivesessions.runnerexceptions import SessionInitializationFailed
from crl.interactivesessions._terminalpools import TerminalPoolsBusy
from .mock_killpg import MockKillpg

LOGGER = logging.getLogger(__name__)
__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.mark.usefixtures('mock_term_functions')
@pytest.mark.parametrize('kwargs', [
    {},
    {'executable': '/bin/sh'},
    {'target': 'target'},
    {'timeout': '10'},
    {'timeout': 10}])
def test_execute_command_in_target(kwargs, remoterunner, normal_shelldicts):
    targetarg = {'name': kwargs['target']} if 'target' in kwargs else {}
    remoterunner.set_target(shelldicts=normal_shelldicts, **targetarg)
    ret = remoterunner.execute_command_in_target('echo out;>&2 echo err',
                                                 **kwargs)
    assert_result_success(ret)


def assert_result_success(result):
    assert_result_status(result, expected_status='0')


def assert_result_status(result, expected_status):
    assert result.status == expected_status
    assert result.stdout == 'out'
    assert result.stderr == 'err'


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
def test_execute_command_in_target_timeout(remoterunner):
    remoterunner.set_default_target_property('prompt_timeout', 0.01)
    with pytest.raises(RunnerTimeout) as excinfo:
        remoterunner.execute_command_in_target('echo out;sleep 1',
                                               timeout=0.01)

    assert excinfo.value.args[0].status == -15
    assert excinfo.value.args[0].stdout == b'out\n'
    assert excinfo.value.args[0].stderr == b''


@pytest.mark.usefixtures('mock_time_sleep')
def test_run_raises_sessioninitalizationfailed(remoterunner):
    exception = Exception('message')
    remoterunner.set_target(shelldicts=[{'shellname': 'SpawnRaisesShell',
                                         'exception': exception}],
                            name='target')

    funcs = [
        lambda: remoterunner.copy_file_to_target('source', target='target'),
        lambda: remoterunner.execute_command_in_target('cmd', target='target')]

    for f in funcs:
        with pytest.raises(SessionInitializationFailed) as execinfo:
            f()

    assert str(execinfo.value) == 'message'


def setup_target_with_timeout(remoterunner, termination_timeout):
    remoterunner.set_default_target_property('prompt_timeout', 1)
    remoterunner.set_default_target_property('termination_timeout',
                                             termination_timeout)
    remoterunner.set_target(shelldicts=[{'shellname': 'ExampleShell'}])


def execute_timeout_command(remoterunner):
    remoterunner.execute_command_in_target("echo out; sleep 0.5",
                                           timeout=0.05)


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
@pytest.mark.parametrize('ignoresignals,expected_exception,expected_args', [
    ([], RunnerTimeout, RunResult(status=-signal.SIGTERM,
                                  stdout=b'out\n',
                                  stderr=b'')),
    ([signal.SIGTERM], RunnerTimeout, RunResult(status=-9,
                                                stdout=b'out\n',
                                                stderr=b'')),
    ([signal.SIGTERM, 9], FailedToKillProcess, 'failedtokill')])
def test_execute_timeout_cleaning(remoterunner,
                                  ignoresignals,
                                  expected_exception,
                                  expected_args):
    setup_target_with_timeout(remoterunner, 0.05)
    with MockKillpg(ignoresignals=ignoresignals):
        with pytest.raises(expected_exception) as excinfo:
            execute_timeout_command(remoterunner)

    if expected_args == 'failedtokill':
        assert 'Killing of the process with pid' in str(excinfo.value)
    else:
        assert excinfo.value.args[0] == expected_args
    remoterunner.execute_command_in_target('echo out')


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
@pytest.mark.parametrize('oserror_errno,expintcaplog,expexception', [
    (errno.ESRCH, 'already terminated', RunnerTimeout),
    (errno.EPERM, '', OSError)])
def test_execute_kill_raises_oserror(remoterunner,
                                     oserror_errno,
                                     expintcaplog,
                                     expexception,
                                     intcaplog):
    def raise_oserror(*_):
        raise OSError(oserror_errno, os.strerror(oserror_errno))

    setup_target_with_timeout(remoterunner, 1)

    with MockKillpg(side_effect=raise_oserror):
        with pytest.raises(expexception):
            execute_timeout_command(remoterunner)

    assert expintcaplog in intcaplog.text


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
def test_progress_log(remoterunner, intcaplog):
    ret = remoterunner.execute_command_in_target(
        'echo -n progress;echo log;>&2 echo err', progress_log=True)

    LOGGER.debug("===== test_progress_log: intcaplog.text == %s",
                 intcaplog.text)
    assert ': progresslog' in intcaplog.text
    assert ret == RunResult(status='0', stdout='progresslog', stderr='err')


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
def test_execute_background_command_in_target(remoterunner):
    remoterunner.execute_background_command_in_target(
        'echo out;>&2 echo err', exec_id='exec_id')
    assert remoterunner.wait_background_execution('exec_id') == RunResult(
        status='0', stdout='out', stderr='err')


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
def test_kill_background_execution(remoterunner):
    remoterunner.execute_background_command_in_target(
        'echo out;>&2 echo err;sleep 10', exec_id='exec_id')

    expected_result = RunResult(
        status=str(-signal.SIGTERM), stdout='out', stderr='err')

    assert remoterunner.kill_background_execution('exec_id') == expected_result
    assert remoterunner.wait_background_execution('exec_id') == expected_result


@pytest.mark.usefixtures('mock_interactivesession')
@pytest.mark.xfail(is_windows(), reason="Windows")
def test_execute_background_command_in_target_raises(remoterunner):
    with pytest.raises(BackgroundExecIdAlreadyInUse) as excinfo:

        for _ in range(2):
            remoterunner.execute_background_command_in_target(
                'echo out;>&2 echo err', exec_id='exec_id')
    assert excinfo.value.args[0] == 'exec_id'


@pytest.mark.usefixtures('mock_subprocess_popen', 'mock_os_killpg')
def test_execute_backgrounds(mock_interactivesession,
                             remoterunner):
    for cmd in cmds():
        remoterunner.execute_background_command_in_target(cmd, exec_id=cmd)

    for cmd in cmds():
        assert_ret_for_cmd(remoterunner.execute_command_in_target(cmd), cmd)

    for cmd in cmds():
        assert_ret_for_cmd(remoterunner.wait_background_execution(cmd), cmd)

    assert len(mock_interactivesession.side_effect.get_mock_interactivesessions()) == 2


@pytest.mark.usefixtures('mock_interactivesession')
def test_backgrounds_with_close_between(remoterunner,
                                        runner_initializer):
    cmd = 'echo out;>&2 echo err'
    cmd2 = 'echo out2;>&2 echo err2'
    remoterunner.execute_background_command_in_target(cmd, exec_id='id')
    remoterunner.close()
    runner_initializer(remoterunner)
    remoterunner.execute_background_command_in_target(cmd2, exec_id='id')
    ret = remoterunner.wait_background_execution('id')
    assert ret.status == '0'
    assert ret.stdout == 'out2'
    assert ret.stderr == 'err2'


@six.add_metaclass(abc.ABCMeta)
class MultiTargetsBase(object):
    basecmd = 'echo out;  >&2 echo err'
    postcmd = ''
    expected_status = '0'

    def __init__(self, plain_runner_factory):
        self.remoterunner = plain_runner_factory()
        self.targets_size = 5
        self.maxsize = self.targets_size
        self.setup_targets()

    @property
    def cmd(self):
        return '{base}{post}'.format(base=self.basecmd, post=self.postcmd)

    def setup_targets(self):
        for t in self.targets():
            self.remoterunner.set_target([{'shellname': 'ExampleShell',
                                           'target_name': t}], name=t)

    def targets(self):
        for i in range(self.maxsize):
            yield 'target_{}'.format(i)

    @contextmanager
    def runner_with_maxsize(self):
        origsize = self.remoterunner.terminalpools.maxsize
        try:
            self.remoterunner.set_terminalpools_maxsize(self.maxsize)
            yield None
        finally:
            self.remoterunner.set_terminalpools_maxsize(origsize)

    def execute_background_in_every_target(self):
        for t in self.targets():
            self.remoterunner.execute_background_command_in_target(
                self.cmd, target=t, exec_id=t)

    def execute_foreground_in_every_target(self):
        for t in self.targets():
            assert_result_success(self.remoterunner.execute_command_in_target(
                self.basecmd, target=t))

    def execute_command_in_one_target(self):
        t = next(self.targets())
        self.remoterunner.execute_command_in_target(self.cmd, target=t)

    def assert_after_end_operation(self):
        for t in self.targets():
            assert_result_status(self._end_operation(t),
                                 expected_status=self.expected_status)

    @abc.abstractmethod
    def _end_operation(self, target):
        """Operation which ends started background execution in *target*.
        """


class MultiTargetsWait(MultiTargetsBase):

    def _end_operation(self, target):
        return self.remoterunner.wait_background_execution(target)


class MultiTargetsKill(MultiTargetsBase):

    postcmd = ';sleep 10'
    expected_status = '-15'

    def _end_operation(self, target):
        ret = self.remoterunner.kill_background_execution(target)
        self.remoterunner.wait_background_execution(target)
        return ret


@pytest.fixture(params=[MultiTargetsKill, MultiTargetsWait])
def multitargets(plain_runner_factory, request):
    return request.param(plain_runner_factory)


@pytest.mark.usefixtures('mock_interactivesession')
def test_backgrounds_persistence(multitargets):
    with multitargets.runner_with_maxsize():
        multitargets.execute_background_in_every_target()

        with pytest.raises(TerminalPoolsBusy):
            multitargets.execute_command_in_one_target()

        multitargets.assert_after_end_operation()
        multitargets.execute_foreground_in_every_target()


@pytest.fixture
def nohup_runner(nohup_runner_factory):
    return nohup_runner_factory()


@pytest.fixture
def nohup_runner_factory():
    def fact():
        r = RemoteRunner()
        r.set_target([{'shellname': 'ExampleShell'}])
        return r

    return fact


def test_execute_nohup_background_in_target(mock_runnerintarget,
                                            executable_kwargs,
                                            nohup_runner):
    run = mock_runnerintarget.return_value.run_in_nocomm_background
    assert nohup_runner.execute_nohup_background_in_target(
        'cmd', **executable_kwargs) == run.return_value
    expected_executable_args = ([executable_kwargs['executable']]
                                if executable_kwargs else
                                [None])
    run.assert_called_once_with('cmd', *expected_executable_args)


@pytest.mark.usefixtures('mock_nohup_runnerintarget')
def test_execute_nohup_background(nohup_runner_factory,
                                  runner_in_target_factory):
    r = nohup_runner_factory()

    pid = r.execute_nohup_background_in_target('cmd')

    run = runner_in_target_factory.return_value.run_in_nocomm_background

    assert pid == run.return_value


def cmds():
    for i in range(3):
        yield 'cmd_{}'.format(i)


def assert_ret_for_cmd(ret, cmd):
    assert ret.status == '0'
    assert ret.stdout == cmd
    assert ret.stderr == ''
