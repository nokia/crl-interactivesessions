from collections import namedtuple
from contextlib import contextmanager
import itertools
import mock
from crl.interactivesessions.shells.remotemodules.msgcaches import (
    MsgCaches,
    MsgCache,
    Infinite,
    Monotonic,
    MsgCachesAlreadyRemoved,
    MsgCachesNotFound,
    ConsecutiveSet)
from crl.interactivesessions.shells.remotemodules.msgs import ExecCommandReply
from crl.interactivesessions.shells.remotemodules.msgmanager import Retry
import pytest


@pytest.fixture
def msgcache_factory(msgcacheargs):

    def fact(s):
        msg = msgcacheargs.msg_factory(s)
        return MsgCache(msg,
                        retry=msgcacheargs.retry,
                        send_msg=msgcacheargs.sender.send_msg)

    return fact


@pytest.fixture(params=[Retry(tries=1, interval=1, timeout=1),
                        Retry(tries=3, interval=1, timeout=30),
                        Retry(tries=3, interval=0.5, timeout=10),
                        Retry(tries=10, interval=2, timeout=20)])
def retry(request):
    return request.param


@pytest.fixture
def sender():
    return Sender()


@pytest.fixture
def msg_factory():
    def fact(s):
        return ExecCommandReply.create(s)

    return fact


@pytest.fixture
def msgcacheargs(msg_factory, retry, sender):
    return MsgCacheArgs(msg_factory=msg_factory, retry=retry, sender=sender)


class MsgCacheArgs(namedtuple('MsgCacheArgs', ['msg_factory', 'retry', 'sender'])):
    pass


@pytest.fixture
def timegen(faketime):
    return TimeGen.use(faketime)


@pytest.fixture
def monotonicgen(fakemonotonic):
    return TimeGen.use(fakemonotonic)


class TimeGen(object):
    def __init__(self):
        self._time = 0

    def __iter__(self):
        return self

    def consume(self, elapsed):
        self._time += elapsed

    def next(self):
        return self.__next__()

    def __next__(self):
        return self._time

    @classmethod
    def use(cls, fake):
        t = cls()
        fake.set_time_gen(t)
        return t


@pytest.fixture
def faketime():
    with FakeTime.context('time.time') as p:
        yield p


@pytest.fixture
def fakemonotonic():
    with FakeTime.context('crl.interactivesessions.shells.remotemodules.msgcaches.'
                          'Monotonic.time') as p:
        yield p


class FakeTime(object):
    def __init__(self):
        self._time_gen = itertools.count()

    def set_time_gen(self, time_gen):
        self._time_gen = time_gen

    def time(self):
        return next(self._time_gen)

    @classmethod
    @contextmanager
    def context(cls, timefunction):
        f = cls()
        with mock.patch(timefunction) as p:
            p.side_effect = f.time
            yield f


def test_msgcaches(msgcacheargs, monotonicgen):

    r = msgcacheargs.retry
    m = MsgCachesWrapper(msgcacheargs, monotonicgen)
    m.push(1)
    for _ in range(r.tries - 1):
        m.consume_and_send()
    m.push(3)
    expected_sent_time = monotonicgen.next()
    m.consume_and_send()
    for uid in [1, 3]:
        assert m.get_msg(uid).uid == uid
    with pytest.raises(MsgCachesNotFound):
        m.get_msg(2)
    m.remove(3)
    with pytest.raises(MsgCachesAlreadyRemoved):
        m.get_msg(3)

    assert r.tries > 1 or m.timeout == r.timeout
    m.consume_and_send()
    m.remove(3)

    if r.tries > 1:
        assert m.timeout == r.timeout
        assert m.timeout_args == [r.timeout]
        m.consume_and_send()

    with pytest.raises(MsgCachesAlreadyRemoved):
        m.get_msg(1)
    assert m.timeout == Infinite()
    assert m.timeout_args == []
    assert not list(m.msgs)
    assert m.get_sent_times(1) == [t * r.interval for t in range(r.tries)]
    assert m.get_sent_times(3) == [expected_sent_time]


class MsgCachesWrapper(object):
    def __init__(self, msgcacheargs, monotonicgen):
        self._msgcacheargs = msgcacheargs
        self._monotonicgen = monotonicgen
        self._msgcaches = MsgCaches(retry=msgcacheargs.retry,
                                    send_msg=msgcacheargs.sender.send_msg)
        self._msgcacheargs.sender.set_time_gen(monotonicgen)
        self._msgs = {}

    @property
    def timeout(self):
        return self._msgcaches.timeout

    @property
    def msgs(self):
        return self._msgcaches.msgs

    @property
    def timeout_args(self):
        return self._msgcaches.timeout_args

    def push(self, msg_nbr):
        if msg_nbr not in self._msgs:
            msg = ExecCommandReply.create('msg{}'.format(msg_nbr))
            msg.set_uid(msg_nbr)
            self._msgs[msg_nbr] = msg
        self._msgcaches.push_msg(self._msgs[msg_nbr])

    def remove(self, msg_nbr):
        self._msgcaches.remove(self._msgs[msg_nbr])

    def consume_and_send(self):
        self._msgcacheargs.sender.time_gen.consume(self._msgcaches.timeout)
        self._msgcaches.send_expired()

    def get_msg(self, uid):
        return self._msgcaches.get_msg(uid)

    def get_sent_times(self, msg_nbr):
        return self._msgcacheargs.sender.get_times_for_msg(self._msgs[msg_nbr])


class Sender(object):
    def __init__(self):
        self.all_msgs = []
        self.msgs = []
        self._time_gen = itertools.count()

    @property
    def time_gen(self):
        return self._time_gen

    def set_time_gen(self, time_gen):
        self._time_gen = time_gen

    def send_msg(self, msg):
        msgtime = MsgTime(msg, time=next(self._time_gen))
        for m in [self.msgs, self.all_msgs]:
            m.append(msgtime)

    def clear(self):
        self.msgs = []

    def get_times_for_msg(self, msg):
        return list(self.times_for_msg_gen(msg))

    def times_for_msg_gen(self, msg):
        for m in self.all_msgs:
            if msg.uid == m.msg.uid:
                yield m.time


class MsgTime(namedtuple('MsgTime', ['msg', 'time'])):
    pass


def test_msgcache(msgcache_factory, msgcacheargs):
    c = msgcache_factory('msg')
    s = msgcacheargs.sender
    r = msgcacheargs.retry
    expected_timeouts = r.timeouts()
    cumul = 0
    expected_timeout = 0
    for timeout in _msgcache_timeout_gen():
        s.clear()
        c.send_expired(timeout)
        cumul += timeout
        if cumul >= expected_timeout:
            try:
                expected_timeout = next(expected_timeouts)
                assert s.msgs[0].msg.uid == c.msg.uid
                assert c.timeout == expected_timeout
                cumul = 0
            except StopIteration:
                break

    assert not s.msgs
    assert [m.msg.uid for m in s.all_msgs] == r.tries * [c.msg.uid]
    assert c.timeout == Infinite()


def _msgcache_timeout_gen():
    yield 0
    while True:
        yield 1


@pytest.mark.usefixtures('faketime')
def test_monotonic():
    m = Monotonic()
    for _ in range(3):
        t1 = m.time()
        t2 = m.time()
        assert t2 - t1 == 1


def test_monotonic_decreasing_time(faketime):
    m = Monotonic()
    faketime.set_time_gen(itertools.count(step=-1))
    for _ in range(3):
        t1 = m.time()
        t2 = m.time()
        assert t2 > t1
        assert t2 - t1 < 1


@pytest.mark.parametrize('sequence', [
    range(0, 10, 2),
    range(10),
    [5, 2, 1, 3, 4],
    [3, 1],
    [1, 1, 3, 5, 2, 2],
    [1, 9, 4, 2, 7]])
def test_consecutiveset(sequence):
    c = ConsecutiveSet()
    for i in range(10):
        assert i not in c

    for i in sequence:
        c.add(i)

    for i in range(10):
        assert (i in c) == (i in sequence)

    assert len(c) == expected_missing_nbrs(sequence)


def expected_missing_nbrs(sequence):
    return len([i for i in range(min(sequence), max(sequence)) if i not in sequence])
