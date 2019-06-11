import time
import itertools


__copyright__ = 'Copyright (C) 2019, Nokia'


class MsgCaches(object):
    def __init__(self, retry, send_msg):
        self._retry = retry
        self._send_msg = send_msg
        self._msgcaches = {}
        self._monotonic = Monotonic()
        self._lap = self._monotonic.time()
        self._removed = ConsecutiveSet()

    @property
    def _elapsed(self):
        return self._monotonic.time() - self._lap

    def push_msg(self, msg):
        self._msgcaches[msg.uid] = MsgCache(msg, self._retry, send_msg=self._send_msg)

    def send_expired(self):
        for uid, c in list(self._msgcaches.items()):
            c.send_expired(self._elapsed)
            if c.timeout == Infinite():
                self._remove(uid)
        self._lap = self._monotonic.time()

    def remove(self, msg):
        if msg.uid in self._msgcaches:
            self._remove(msg.uid)

    def _remove(self, uid):
        del self._msgcaches[uid]
        self._removed.add(uid)

    def get_msg(self, uid):
        if uid in self._msgcaches:
            return self._msgcaches[uid].msg
        if uid in self._removed:
            raise MsgCachesAlreadyRemoved()
        raise MsgCachesNotFound()

    @property
    def timeout(self):
        return min(itertools.chain(self._timeouts_gen(),
                                   iter([Infinite()])))

    @property
    def timeout_args(self):
        t = self.timeout
        return [] if t == Infinite() else [t]

    def _timeouts_gen(self):
        for _, c in self._msgcaches.items():
            yield c.timeout

    @property
    def msgs(self):
        return list(self._msg_gen())

    def _msg_gen(self):
        for _, c in self._msgcaches.items():
            for m in c.msgs:
                yield m


class MsgCachesAlreadyRemoved(Exception):
    pass


class MsgCachesNotFound(Exception):
    pass


class ConsecutiveSet(object):
    """ Set for storing efficiently mostly consecutive integers.
    """
    def __init__(self):
        self._min = None
        self._max = None
        self._missing_nbrs = set()

    def add(self, i):
        if self._min is None:
            self._min = self._max = i
        elif i > self._max:
            self._missing_nbrs |= set(range(self._max + 1, i))
            self._max = i
        elif self._min < i < self._max and i in self._missing_nbrs:
            self._missing_nbrs.remove(i)
        elif i < self._min:
            self._missing_nbrs |= set(range(i + 1, self._min))
            self._min = i

    def __contains__(self, i):
        missing_test = i not in self._missing_nbrs
        return self._min is not None and self._min <= i <= self._max and missing_test

    def __len__(self):
        return len(self._missing_nbrs)


class MsgCache(object):
    def __init__(self, msg, retry, send_msg):
        self._msg = msg
        self._send_msg = send_msg
        self._retry = retry
        self._msgs = []
        self._timeout = 0
        self._timeouts = self._retry.timeouts()

    @property
    def msg(self):
        return self._msg

    @property
    def timeout(self):
        return self._timeout

    def send_expired(self, elapsed):
        if elapsed < self._timeout:
            self._timeout -= elapsed
        else:
            try:
                self._timeout = next(self._timeouts)
                self._send_msg(self.msg)
            except StopIteration:
                self._timeout = Infinite()


class Monotonic(object):
    def __init__(self):
        self._min_incr = 0.01
        self._delta = 0
        self._previous_time = time.time()

    def time(self):
        t = time.time()
        corrected_time = t + self._delta
        if corrected_time <= self._previous_time:
            corrected_time = self._previous_time + self._min_incr
            self._delta = corrected_time - t

        self._previous_time = corrected_time
        return corrected_time


class Infinite(object):
    def __gt__(self, timeout):
        return True

    def __lt__(self, timeout):
        return False

    def __eq__(self, timeout):
        return isinstance(timeout, self.__class__)
