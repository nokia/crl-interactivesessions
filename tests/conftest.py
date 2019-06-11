import logging
from multiprocessing import Process
from collections import namedtuple
from contextlib import contextmanager
import pytest
import mock
from crl.interactivesessions._targetproperties import _TargetProperties
from crl.interactivesessions.remoterunner import RemoteRunner
from crl.interactivesessions._process import RunResult
from crl.interactivesessions.shells import remotemodules
from . import patch_subprocess  # pylint: disable=unused-import; # noqa: F401
from .shells.terminals.serverterminal import (
    ServerProcess,
    ServerTerminal)
from .shells.terminals.promptpythonserver import PromptPythonServer
from .shells.mock_interactivesession import MockInteractiveSessionFactory
from .shells.rubbishcontext import (
    ClientRubbishContext,
    ServerRubbishContext)
from .shells.chunkcontext import ChunkContext
from .shells.spawningshell import SpawningShell


__copyright__ = 'Copyright (C) 2019, Nokia'


def pytest_configure(config):  # pylint: disable=unused-argument
    logging.basicConfig(
        format='%(processName)s %(asctime)s.%(msecs)03d %(levelname)s %(message)s',
        level=logging.DEBUG)
    # TODO: remove workaround for too verbose flakes after
    # https://github.com/tholo/pytest-flake8/issues/42 corrected
    logging.getLogger('flake8').setLevel(logging.WARN)


@pytest.fixture
def intcaplog(caplog):
    caplog.set_level(7)
    return caplog


@pytest.fixture
def mock_interactivesession():
    m = MockInteractiveSessionFactory()
    with mock.patch('crl.interactivesessions'
                    '.autorecoveringterminal.InteractiveSession') as patcher:
        patcher.side_effect = m
        yield patcher


@pytest.fixture
def runner_initializer(plain_runner_initializer):
    def initializer(runner):
        plain_runner_initializer(runner)
        runner.set_target(shelldicts=[{'shellname': 'ExampleShell'}])
        return runner

    return initializer


@pytest.fixture
def plain_runner_initializer(request):
    def initializer(runner):
        request.addfinalizer(runner.close)
        return runner

    return initializer


@pytest.fixture
def runner_factory(runner_initializer):
    return create_runner_factory_with_initializer(runner_initializer)


@pytest.fixture
def plain_runner_factory(plain_runner_initializer):
    return create_runner_factory_with_initializer(plain_runner_initializer)


def create_runner_factory_with_initializer(initializer):
    def fact():
        return initializer(RemoteRunner())

    return fact


@pytest.fixture
def remoterunner(monkeypatch, runner_factory):
    props = _TargetProperties.defaultproperties.copy()
    monkeypatch.setattr(_TargetProperties, 'defaultproperties', props)
    return runner_factory()


@pytest.fixture
def mock_os_killpg():
    with mock.patch('os.killpg') as p:
        p.return_value = None
        yield p


@pytest.fixture
def targetname(request):
    return request.node.name


class EchoPopen(object):
    def __init__(self, args, **kwargs):
        self.args = args
        self._kwargs = kwargs
        self.returncode = 0
        self.pid = 0

    def communicate(self, **_):
        return (self.args, '')


@pytest.fixture
def mock_subprocess_popen():
    with mock.patch('subprocess.Popen', new=EchoPopen) as p:
        yield p


@pytest.fixture
def mock_time_sleep():
    with mock.patch('time.sleep') as p:
        yield p


@pytest.fixture(params=[{}, {'executable': 'executable'}])
def executable_kwargs(request):
    return request.param


@pytest.fixture
def mock_terminal():
    return mock.Mock()


@pytest.fixture
def runner_in_target_factory(mock_terminal):

    @contextmanager
    def mock_active_terminal():
        yield mock_terminal

    r_in_target_factory = mock.Mock()
    r_in_target_factory.mock_terminal = mock_terminal
    r_in_target_factory.return_value.active_terminal = mock_active_terminal
    r_in_target_factory.return_value.run.return_value = RunResult(
        '0', 'out\n', 'err\n')
    return r_in_target_factory


@pytest.fixture
def mock_runnerintarget():
    with mock.patch('crl.interactivesessions.remoterunner._RunnerInTarget') as p:
        yield p


@pytest.fixture
def mock_nohup_runnerintarget(mock_runnerintarget, runner_in_target_factory):
    mock_runnerintarget.side_effect = runner_in_target_factory
    yield mock_runnerintarget


@pytest.fixture
def normal_shelldicts(normal_pythonterminal_factory):
    return [{'shellname': SpawningShell.__name__,
             'terminal_factory': normal_pythonterminal_factory}]


@pytest.fixture
def normal_pythonterminal_factory(serverterminal_factory, normal_serverprocess_factory):
    def fact(*args):  # pylint: disable=unused-argument
        return serverterminal_factory(normal_serverprocess_factory)

    return fact


@pytest.fixture
def rubbish_context(terminalmockos_context_factory):
    return {'client': terminalmockos_context_factory(ClientRubbishContext()),
            'server': terminalmockos_context_factory(ServerRubbishContext())}


@pytest.fixture
def chunk_pythonterminal_ctx(terminalmockos_context_factory):
    with terminalmockos_context_factory(ChunkContext()) as ctx:
        yield ctx


@pytest.fixture
def terminalmockos_context_factory(pythonprocess_factory,
                                   serverterminal_factory):
    @contextmanager
    def ctx(terminalmockos):
        terminalmockos.set_serverprocess_factory(pythonprocess_factory)
        terminalmockos.set_pythonterminal_factory(serverterminal_factory)
        with terminalmockos.in_mock_os():
            yield terminalmockos

    return ctx


@pytest.fixture
def default_serverterminal_factory(serverterminal_factory, serverprocess_factory):
    def fact(server_fact):
        return serverterminal_factory(lambda: serverprocess_factory(server_fact))

    return fact


@pytest.fixture
def serverterminal_factory():
    def fact(serverprocess_fact):
        s = ServerTerminal()
        s.set_serverprocess_factory(serverprocess_fact)
        s.start()
        return s

    return fact


@pytest.fixture
def normal_serverprocess_factory(pythonprocess_factory):

    def fact():
        p = pythonprocess_factory()
        p.set_process_factory(Process)
        return p

    return fact


@pytest.fixture
def pythonprocess_factory(promptpythonserver_factory, serverprocess_factory):
    def fact():
        return serverprocess_factory(promptpythonserver_factory)

    return fact


@pytest.fixture
def serverprocess_factory():
    def fact(server_factory):
        s = ServerProcess()
        s.set_process_factory(Process)
        s.set_server_factory(server_factory)
        return s

    return fact


@pytest.fixture
def promptpythonserver_factory():

    def fact():
        p = PromptPythonServer()
        p.set_comm_factory(ChunklessServerComm.create)
        p.set_pythoncmdline_factory(remotemodules.pythoncmdline.PythonCmdline)
        return p

    return fact


class ChunklessServerComm(remotemodules.servercomm.ServerComm):
    def write(self, s):
        self._write(s)
        self._flush()


@pytest.fixture
def mock_termios_tcgetattr():
    with mock.patch('termios.tcgetattr') as p:
        yield p


@pytest.fixture
def mock_termios_tcsetattr():
    with mock.patch('termios.tcsetattr', return_value=None) as p:
        yield p


@pytest.fixture
def mock_tty_setraw():
    with mock.patch('tty.setraw', return_value=None) as p:
        yield p


class TermFunctions(namedtuple('TermFunctions', ['termios_tcgetattr',
                                                 'termios_tcsetattr',
                                                 'tty_setraw'])):
    pass


@pytest.fixture
def mock_term_functions(mock_termios_tcgetattr,
                        mock_termios_tcsetattr,
                        mock_tty_setraw):
    yield TermFunctions(termios_tcgetattr=mock_termios_tcgetattr,
                        termios_tcsetattr=mock_termios_tcsetattr,
                        tty_setraw=mock_tty_setraw)
