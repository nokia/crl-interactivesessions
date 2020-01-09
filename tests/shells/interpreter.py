"""Shell command line emulator base
"""
import logging
import abc
from collections import namedtuple
import six


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class Interpreter(object):
    def __init__(self, handlers, state):
        self._responses = Responses()
        self._state = state
        self._handlers = []
        self._line = b''
        self._set_handlers(handlers)

    def __str__(self):
        return 'responses: {responses}, state={state}, line={line}'.format(
            responses=self._responses,
            state=self._state,
            line=self._line)

    def _set_handlers(self, handlers):
        for h in handlers:
            h.set_state(self._state)
            self._handlers.append(h)

    def read(self, timeout):
        ret = b''
        for r in self._try_to_get_responses(timeout):
            ret += r.response
        return ret

    def _try_to_get_responses(self, timeout):
        try:
            return self._responses.get_responses(timeout)
        except ResponsesTimeout:
            raise InterpreterTimeout

    def write(self, s):
        for line in self._lines(s):
            self._responses.add_responses(self._responses_for_line(line))

    def _lines(self, s):
        for c in self._bytes_gen(s):
            self._line += c
            if c == b'\n':
                yield self._line
                self._line = b''

    @staticmethod
    def _bytes_gen(s):
        for i in six.moves.range(len(s)):
            yield s[i:i + 1]

    def _responses_for_line(self, line):
        for h in self._handlers:
            try:
                for r in h.get_responses(line):
                    yield r
                break
            except HandlerNotMatching:
                continue


class InterpreterTimeout(Exception):
    pass


class State(object):
    def __init__(self):
        self.__dict__['_state'] = {}

    def __getattr__(self, name):
        try:
            return self._state[name]
        except KeyError:
            raise StateAttributeError('No such attribute: {}'.format(name))

    def __setattr__(self, name, value):
        self._state[name] = value

    def __str__(self):
        return str(self._state)

    def __repr__(self):
        return self.__str__()


class StateAttributeError(AttributeError):
    pass


@six.add_metaclass(abc.ABCMeta)
class HandlerBase(object):
    """Abstract class for :class:`.Interpreter` line handlers.
    """
    def __init__(self):
        self._state = None

    def set_state(self, state):
        self._state = state

    def get_responses(self, line):
        """Get :class:`.Response` instance non empty iterable list or iterator
        in case.

        Raises: :class:`.HandlerNotMatching` in case no match.
        """


class HandlerNotMatching(Exception):
    pass


class Responses(object):
    def __init__(self):
        self._responses = []
        self._current_time = 0

    def add_responses(self, responses):
        for r in responses:
            self._responses.append(r.create_with_start(self._next_free_time))

    @property
    def _next_free_time(self):
        return self._responses[-1].response_time if self._responses else 0

    def get_responses(self, timeout):
        responses = [r for r in self._responses_gen(timeout)]
        if not responses:
            raise ResponsesTimeout
        return responses

    def _responses_gen(self, timeout):
        # Side effect: This generator updates time and removes yielded
        # (consumed) responses
        expires_at = self._current_time + timeout
        for r in list(self._responses):
            if r.response_time > expires_at:
                break
            self._current_time = r.response_time
            self._responses.pop(0)
            yield r

    def __str__(self):
        return 'responses: {responses}, time: {time}'.format(responses=self._responses,
                                                             time=self._current_time)


class ResponsesTimeout(Exception):
    pass


class Response(namedtuple('Response', ['response', 'latency', 'interpretation_start'])):

    @property
    def response_time(self):
        return self.interpretation_start + self.latency

    @classmethod
    def create(cls, response, latency=0):
        return cls(response=response, latency=latency, interpretation_start=0)

    def create_with_start(self, interpretation_start):
        kwargs = self._asdict()
        kwargs['interpretation_start'] = interpretation_start
        return Response(**kwargs)
