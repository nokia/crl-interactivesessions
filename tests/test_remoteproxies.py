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
from crl.interactivesessions.pexpectplatform import is_windows
from .mockpythonsession import MockPythonSession
from .garbageverifier import GarbageVerifier


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def runnerterminal():
    return RunnerTerminal()


@pytest.fixture
def mock_pythonshell(request):
    return create_patch(mock.patch(
        'crl.interactivesessions.runnerterminal.MsgPythonShell'), request)


@pytest.fixture
def initialized_terminal(session_factory, runnerterminal):
    runnerterminal.initialize(session_factory())
    return runnerterminal


@pytest.fixture
def session_factory(capsys):
    def fact():
        return MockPythonSession(capsys)

    return fact


def test_get_proxy_object(initialized_terminal):
    initialized_terminal.run_python('handle = 0')
    proxy = initialized_terminal.get_proxy_object('handle', int)

    assert proxy.as_local_value() == 0


def test_get_proxy_object_from_call(initialized_terminal):
    initialized_terminal.run("def function_name(arg, kwarg=None):")
    initialized_terminal.run("    return 'arg: {arg}, kwarg: {kwarg}'.format("
                             "arg=arg, kwarg=kwarg)")

    proxy = initialized_terminal.get_proxy_object_from_call(
        'function_name', 'arg', kwarg='kwarg')
    assert proxy.as_local_value() == 'arg: arg, kwarg: kwarg'


def test_get_proxy_object_from_call_raises(initialized_terminal):
    initialized_terminal.run("def function_name():")
    initialized_terminal.run("    raise Exception('message')")

    with pytest.raises(Exception) as excinfo:
        initialized_terminal.get_proxy_object_from_call('function_name()')

    assert excinfo.value.args[0] == 'message'


def test_import_libraries(initialized_terminal):
    initialized_terminal.import_libraries('re')
    reproxy = initialized_terminal.get_proxy_object('re', None)
    assert reproxy.sub('a', 'b', 'c') == 'c'


TupleAbc = namedtuple('TupleAbc', ['a', 'b', 'c'])


def test_as_recursive_proxy(session_factory, runnerterminal):
    session = session_factory()
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


def _setup_with_empty_and_get_session(session_factory, runnerterminal):
    session = session_factory()
    session.namespace['EmptyClass'] = EmptyClass
    runnerterminal.initialize(session=session)
    return session


def test_set_attr(session_factory, runnerterminal):
    _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    proxy.attribute = 0
    assert proxy.attribute == 0
    recproxy = proxy.as_recursive_proxy()
    assert recproxy.attribute == 0


def identity_call(*args, **kwargs):
    return (args, kwargs)


def _get_identity_call_proxy(session_factory, runnerterminal):
    session = session_factory()
    session.namespace['identity_call'] = identity_call
    runnerterminal.initialize(session=session)
    return runnerterminal.get_proxy_object('identity_call', None)


def test_proxy_call(session_factory, runnerterminal):
    assert _get_identity_call_proxy(session_factory, runnerterminal)(
        'arg', kwarg='kwarg') == (('arg',), {'kwarg': 'kwarg'})


def test_recursive_proxy_call(session_factory, runnerterminal):

    recproxy = _get_identity_call_proxy(
        session_factory, runnerterminal).as_recursive_proxy()

    assert recproxy('arg', kwarg='kwarg').as_local_value() == (
        ('arg',), {'kwarg': 'kwarg'})


def test_recursive_proxy_attribute_error(session_factory, runnerterminal):
    _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    recproxy = proxy.as_recursive_proxy()

    with pytest.raises(AttributeError) as excinfo:
        # pylint: disable=pointless-statement
        recproxy.attr
    res = "'{handle}' has no attribute 'attr'".format(handle=recproxy.get_proxy_handle())
    assert excinfo.value.args[0] == res


def test_get_recursive_proxy(session_factory, runnerterminal):
    session = session_factory()
    session.namespace['identity_call'] = identity_call
    runnerterminal.initialize(session=session)

    recproxy = runnerterminal.get_recursive_proxy('identity_call')
    assert recproxy('value').__str__() == "(('value',), {})"


def test_del_after_close(session_factory, runnerterminal):
    _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    assert proxy.as_local_value().__class__.__name__ == 'EmptyClass'
    runnerterminal.close()
    proxy.__del__()


def get_proxy_object_from_call(runnerterminal):
    return runnerterminal.get_proxy_object_from_call('dict')


def get_proxy_or_basic_from_call(runnerterminal):
    return runnerterminal.get_proxy_or_basic_from_call('dict')


def get_proxy_or_basic_from_call_with_timeout(runnerterminal):
    return runnerterminal.get_proxy_or_basic_from_call_with_timeout(
        timeout=1,
        function_name='dict',
        args=(),
        kwargs={})


@pytest.fixture(params=[get_proxy_object_from_call,
                        get_proxy_or_basic_from_call,
                        get_proxy_or_basic_from_call_with_timeout])
def garbageverifier(request, initialized_terminal):
    return GarbageVerifier(runnerterminal=initialized_terminal,
                           proxy_factory=request.param)


def test_garbage_cleaning(garbageverifier):
    garbageverifier.verify_garbage_cleaning(3)


def test_garbage_cleaning_session_reset(garbageverifier, session_factory):
    for _ in range(2):
        handles = garbageverifier.create_max_proxies()

        garbageverifier.reset_session(session_factory())

        garbageverifier.assert_all_proxies_cleaned(handles)
        garbageverifier.verify_garbage_cleaning(2)


def test_broken_session(session_factory, runnerterminal):
    e = Exception()

    # pylint: disable=unused-argument
    def raise_exception(*args, **kwargs):
        raise e

    session = _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    session.set_exec_command_side_effect(raise_exception)

    with pytest.raises(RunnerTerminalSessionBroken) as excinfo:
        proxy.as_local_value()

    assert excinfo.value.args[0] == e


def test_broken_session_in_python(session_factory, runnerterminal):
    _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')
    runnerterminal.run(
        "runnerhandlerns['_RUNNERHANDLER'].run = lambda *args, **kwargs: 0")
    with pytest.raises(RunnerTerminalSessionBroken) as excinfo:
        proxy.as_local_value()
    assert ("Unexpected output in terminal ('0'): unable to deserialize" in
            excinfo.value.args[0])
    assert 'when running command' in excinfo.value.args[0]


def test_setup_same_session_twice(session_factory, runnerterminal,
                                  mock_pythonshell):

    session = session_factory()
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

        return ('steeringstring', self._pickled)

    @property
    def expected_pickled(self):
        return repr(self._pickled)

    @property
    def _pickled(self):
        return b'pickled'


def test_not_deserializable_objects(session_factory, runnerterminal):
    _setup_with_empty_and_get_session(session_factory, runnerterminal)
    proxy = runnerterminal.get_proxy_object_from_call('EmptyClass')

    t = MockLoad()

    runnerterminal.UNPICKLER = mock.create_autospec(pickle.Unpickler,
                                                    spec_set=True)

    runnerterminal.UNPICKLER.return_value.load.side_effect = t.load

    with pytest.raises(RunnerTerminalUnableToDeserialize) as excinfo:
        proxy.as_local_value()

    assert excinfo.value.args[0] == (
        "steeringstring: {pickled} (Exception: message)".format(
            pickled=t.expected_pickled))


class Sleeper(object):
    @staticmethod
    def sleep_and_return(sleep_time):
        time.sleep(sleep_time)
        return 'return'


def _setup_sleeper_session(session_factory, runnerterminal):
    session = session_factory()
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

    res = proxy.get_remote_proxy_response(response, timeout=0.6)
    assert res == 'return'


@pytest.mark.parametrize('timeout,is_recursive,is_async', [
    (0.5, True, True), (0.5, False, True), (0.5, False, False)])
def test_remote_proxy_timeout(session_factory,
                              runnerterminal,
                              timeout,
                              is_recursive,
                              is_async):
    _setup_sleeper_session(session_factory, runnerterminal)
    proxy = _get_proxy_from_sleeper(runnerterminal, timeout, is_recursive,
                                    is_async)
    response = _get_response_from_proxy(proxy, is_async, timeout)

    _verify_proxy_response(proxy, response)


@pytest.mark.xfail(is_windows(), reason="Windows")
@pytest.mark.parametrize('is_recursive', [True, False])
def test_back_to_synchronous_response(session_factory,
                                      runnerterminal,
                                      is_recursive):
    _setup_sleeper_session(session_factory, runnerterminal)
    proxy = _get_proxy_from_sleeper(runnerterminal,
                                    timeout=0,
                                    is_recursive=is_recursive,
                                    is_async=True)
    proxy.remote_proxy_use_synchronous_response()
    response = _get_response_from_proxy(proxy, is_async=False, timeout=0.2)
    _verify_proxy_response(proxy, response)
