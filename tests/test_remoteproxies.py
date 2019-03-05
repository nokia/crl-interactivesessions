import logging
import time
from collections import namedtuple
import pickle
import pytest
import mock
from fixtureresources.fixtures import create_patch
from crl.interactivesessions.runnerterminal import (
    RunnerTerminal,
    RunnerTerminalSessionBroken,
    RunnerTerminalUnableToDeserialize,
    RemoteTimeout)
from crl.interactivesessions.InteractiveSession import InteractiveSession
from crl.interactivesessions.pexpectplatform import is_windows
from crl.interactivesessions.shells.remotemodules.pythoncmdline import (
    get_code_object)


__copyright__ = 'Copyright (C) 2019, Nokia'

logging.basicConfig()
logger = logging.getLogger(__name__)


class MockPythonSessionClosed(Exception):
    pass


class MockPythonSession(object):

    def __init__(self, capsys):
        self.mock_interactivesession = mock.create_autospec(
            InteractiveSession, spec_set=True)
        self.mock_interactivesessionexecutor = None
        self.multilinecmd = ''
        self.namespace = {}
        self.capsys = capsys
        self._setup_mock_interactivesessionexecutor()

    def set_exec_command_side_effect(self, side_effect):
        cs = self.mock_interactivesession.current_shell.return_value
        cs.exec_command.side_effect = side_effect

    def _setup_mock_interactivesessionexecutor(self):
        self.mock_interactivesessionexecutor = mock.Mock(
            spec_set=['get_session'])
        self.mock_interactivesessionexecutor.get_session.return_value = (
            self.mock_interactivesession)
        self.set_exec_command_side_effect(self._run)
        self.mock_interactivesession.close_terminal.side_effect = self._close

    def __getattr__(self, name):
        return getattr(self.mock_interactivesessionexecutor, name)

    def _run(self, cmd, **kwargs):  # pylint: disable=unused-argument
        logger.debug('MockPythonSession running cmd: %s', cmd)

        try:
            code_obj = get_code_object(self.multilinecmd + cmd, mode='single')
            self.multilinecmd = ''
        except SyntaxError as e:
            if e.args[0].startswith('unexpected EOF'):
                self.multilinecmd += cmd + '\n'
                return ''
            raise
        return self._get_response(code_obj)

    def _get_response(self, code_obj):
        response = eval(code_obj, self.namespace)
        out, _ = self.capsys.readouterr()
        response = out if response is None else out + str(response)
        logger.debug("MockPythonSession response: %s", response)
        return response

    def _close(self):
        self.set_exec_command_side_effect(MockPythonSessionClosed)
        self.namespace = {}


@pytest.fixture(scope='function')
def runnerterminal():
    return RunnerTerminal()


@pytest.fixture(scope='function')
def mock_pythonshell(request):
    return create_patch(mock.patch(
        'crl.interactivesessions.runnerterminal.MsgPythonShell'),
                        request)


def test_get_proxy_object(capsys, runnerterminal):
    runnerterminal.initialize(session=MockPythonSession(capsys))
    runnerterminal.run_python('handle = 0')
    proxy = runnerterminal.get_proxy_object('handle', int)

    assert proxy.as_local_value() == 0


def test_get_proxy_object_from_call(capsys, runnerterminal):
    runnerterminal.initialize(session=MockPythonSession(capsys))
    runnerterminal.run("def function_name(arg, kwarg=None):")
    runnerterminal.run("    return 'arg: {arg}, kwarg: {kwarg}'.format("
                       "arg=arg, kwarg=kwarg)")

    proxy = runnerterminal.get_proxy_object_from_call(
        'function_name', 'arg', kwarg='kwarg')
    assert proxy.as_local_value() == 'arg: arg, kwarg: kwarg'


def test_get_proxy_object_from_call_raises(capsys, runnerterminal):
    runnerterminal.initialize(session=MockPythonSession(capsys))
    runnerterminal.run("def function_name():")
    runnerterminal.run("    raise Exception('message')")

    with pytest.raises(Exception) as excinfo:
        runnerterminal.get_proxy_object_from_call('function_name')

    assert excinfo.value.args[0] == 'message'


def test_import_libraries(capsys, runnerterminal):
    runnerterminal.initialize(session=MockPythonSession(capsys))

    runnerterminal.import_libraries('re')
    reproxy = runnerterminal.get_proxy_object('re', None)
    assert reproxy.sub('a', 'b', 'c') == 'c'


TupleAbc = namedtuple('TupleAbc', ['a', 'b', 'c'])


def test_as_recursive_proxy(capsys, runnerterminal):
    session = MockPythonSession(capsys)
    session.namespace['TupleAbc'] = TupleAbc
    runnerterminal.initialize(session=session)
    proxy = runnerterminal.get_proxy_object_from_call('TupleAbc',
                                                      a='a', b='b',
                                                      c=TupleAbc(1, 2, 3))
    recproxy = proxy.as_recursive_proxy()

    assert recproxy.a == 'a'
    assert recproxy.b == 'b'
    assert [v for v in recproxy.c] == [1, 2, 3]


class EmptyClass(object):
    pass


def _setup_with_empty_and_get_session(capsys, runnerterminal):
    session = MockPythonSession(capsys)
    session.namespace['EmptyClass'] = EmptyClass
    runnerterminal.initialize(session=session)
    return session


def test_set_attr(capsys, runnerterminal):
    _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    proxy.attribute = 0
    assert proxy.attribute == 0
    recproxy = proxy.as_recursive_proxy()
    assert recproxy.attribute == 0


def identity_call(*args, **kwargs):
    return (args, kwargs)


def _get_identity_call_proxy(capsys, runnerterminal):
    session = MockPythonSession(capsys)
    session.namespace['identity_call'] = identity_call
    runnerterminal.initialize(session=session)
    return runnerterminal.get_proxy_object('identity_call', None)


def test_proxy_call(capsys, runnerterminal):
    assert _get_identity_call_proxy(capsys, runnerterminal)(
        'arg', kwarg='kwarg') == (('arg',), {'kwarg': 'kwarg'})


def test_recursive_proxy_call(capsys, runnerterminal):

    recproxy = _get_identity_call_proxy(
        capsys, runnerterminal).as_recursive_proxy()

    assert recproxy('arg', kwarg='kwarg').as_local_value() == (
        ('arg',), {'kwarg': 'kwarg'})


def test_recursive_proxy_attribute_error(capsys, runnerterminal):
    _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    recproxy = proxy.as_recursive_proxy()

    with pytest.raises(AttributeError) as excinfo:
        # pylint: disable=pointless-statement
        recproxy.attr

    assert (excinfo.value.args[0] ==
            "'{handle}' has no attribute 'attr'".format(
                handle=recproxy.get_proxy_handle()))


def test_get_recursive_proxy(capsys, runnerterminal):
    session = MockPythonSession(capsys)
    session.namespace['identity_call'] = identity_call
    runnerterminal.initialize(session=session)

    recproxy = runnerterminal.get_recursive_proxy('identity_call')
    assert recproxy('value').__str__() == "(('value',), {})"


def test_del_after_close(capsys, runnerterminal):
    _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    assert proxy.as_local_value().__class__.__name__ == 'EmptyClass'
    runnerterminal.close()
    proxy.__del__()


def test_broken_session(capsys, runnerterminal):
    e = Exception()

    # pylint: disable=unused-argument
    def raise_exception(*args, **kwargs):
        raise e

    session = _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    session.set_exec_command_side_effect(raise_exception)

    with pytest.raises(RunnerTerminalSessionBroken) as excinfo:
        proxy.as_local_value()

    assert excinfo.value.args[0] == e


def test_broken_session_in_python(capsys, runnerterminal):
    _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    runnerterminal.run(
        "runnerhandlerns['_RUNNERHANDLER'].run = lambda *args, **kwargs: 0")
    with pytest.raises(RunnerTerminalSessionBroken) as excinfo:
        proxy.as_local_value()
    assert ("Unexpected output in terminal ('0'): unable to deserialize" in
            excinfo.value.args[0])
    assert 'when running command' in excinfo.value.args[0]
    assert 'TypeError: Incorrect padding' in excinfo.value.args[0]


def test_setup_same_session_twice(capsys, runnerterminal,
                                  mock_pythonshell):

    session = MockPythonSession(capsys)
    runnerterminal.initialize(session=session)
    runnerterminal.setup_session()

    session.get_session.return_value.push.assert_called_once_with(
        mock_pythonshell.return_value)


class MockLoad(object):

    def __init__(self):
        self.count = 0

    def load(self):
        self.count += 1
        if self.count > 1:
            raise Exception('message')
        else:
            return ('steeringstring', 'pickled')


def test_not_deserializable_objects(capsys, runnerterminal):
    _setup_with_empty_and_get_session(capsys, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    t = MockLoad()

    runnerterminal.UNPICKLER = mock.create_autospec(pickle.Unpickler,
                                                    spec_set=True)

    runnerterminal.UNPICKLER.return_value.load.side_effect = t.load

    with pytest.raises(RunnerTerminalUnableToDeserialize) as excinfo:
        proxy.as_local_value()

    assert excinfo.value.args[0] == (
        "steeringstring: 'pickled' (Exception: message)")


class Sleeper(object):
    @staticmethod
    def sleep_and_return(sleep_time):
        time.sleep(sleep_time)
        return 'return'


def _setup_sleeper_session(capsys, runnerterminal):
    session = MockPythonSession(capsys)
    session.namespace['Sleeper'] = Sleeper

    runnerterminal.initialize(session=session)


def _get_proxy_from_sleeper(runnerterminal, timeout, is_recursive, is_async):
    if is_recursive:
        sleeper = runnerterminal.get_proxy_object_from_call(
            'Sleeper').as_recursive_proxy()
        proxy = sleeper.sleep_and_return
    else:
        proxy = runnerterminal.get_proxy_object(
            'Sleeper().sleep_and_return', None)
    proxy.set_remote_proxy_timeout(timeout)
    if is_async:
        proxy.remote_proxy_use_asynchronous_response()

    return proxy


def _get_response_from_proxy(proxy, is_async, timeout):
    if is_async:
        response = proxy(timeout - 0.30)
    else:
        with pytest.raises(RemoteTimeout) as excinfo:
            proxy(timeout + 0.30)
        response = excinfo.value
    return response


def _verify_proxy_response(proxy, response):
    assert 'Remote response not got yet from response {}'.format(
        response.response_id) == str(response)

    assert (proxy.get_remote_proxy_response(response, timeout=0.6) ==
            'return')


@pytest.mark.parametrize('timeout,is_recursive,is_async', [
    (0.5, True, True), (0.5, False, True), (0.5, False, False)])
def test_remote_proxy_timeout(capsys,
                              runnerterminal,
                              timeout,
                              is_recursive,
                              is_async):
    _setup_sleeper_session(capsys, runnerterminal)
    proxy = _get_proxy_from_sleeper(runnerterminal, timeout, is_recursive,
                                    is_async)
    response = _get_response_from_proxy(proxy, is_async, timeout)

    _verify_proxy_response(proxy, response)


@pytest.mark.xfail(is_windows(), reason="Windows")
@pytest.mark.parametrize('is_recursive', [True, False])
def test_back_to_synchronous_response(capsys,
                                      runnerterminal,
                                      is_recursive):
    _setup_sleeper_session(capsys, runnerterminal)
    proxy = _get_proxy_from_sleeper(runnerterminal,
                                    timeout=0,
                                    is_recursive=is_recursive,
                                    is_async=True)
    proxy.remote_proxy_use_synchronous_response()
    response = _get_response_from_proxy(proxy, is_async=False, timeout=0.2)
    _verify_proxy_response(proxy, response)
