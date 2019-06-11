import logging
import itertools
from contextlib import contextmanager
import pexpect
from monotonic import monotonic
from crl.interactivesessions.shells.shell import TimeoutError
from .remotemodules.msgmanager import MsgManagerBase
from .remotemodules.chunkcomm import (
    ChunkReaderBase,
    ChunkWriterBase)
from .remotemodules.msgs import Ack


__copyright__ = 'Copyright (C) 2019, Nokia'


LOGGER = logging.getLogger(__name__)


class TerminalClientError(Exception):
    pass


class TimerTimeout(Exception):
    pass


class Timer(object):
    def __init__(self, timeout):
        self._timeout = timeout
        self._start_time = monotonic()

    def remaining_timeouts(self):
        while True:
            r = self._remaining()
            if r <= 0:
                raise TimerTimeout()

            yield r

    def _remaining(self):
        return self._timeout - self._elapsed()

    def _elapsed(self):
        return monotonic() - self._start_time


class TerminalClient(MsgManagerBase):
    def __init__(self):
        super(TerminalClient, self).__init__()
        self._wrap_timeout_exception = None
        self._terminalcomm = None
        self._uid_iter = itertools.count()

    def set_wrap_timeout_exception(self, wrap_timeout_exception):
        self._wrap_timeout_exception = wrap_timeout_exception

    def set_terminal(self, terminal):
        self._terminalcomm = TerminalComm(terminal)
        self.set_comm_factory(lambda: self._terminalcomm)

    def send_and_receive(self, msg, timeout):
        msg.set_uid(next(self._uid_iter))
        for t in self._retry.timeouts():
            self.send(msg)
            try:
                ret = self._receive_ack_or_reply(msg, t)
                if isinstance(ret, Ack):
                    break
                return ret
            except (TerminalClientError, TimerTimeout) as e:
                LOGGER.debug('No reply yet for message uid %s: %s', msg.uid, e)

        return self._try_to_receive_until_reply(msg, timeout)

    def _try_to_receive_until_reply(self, msg, timeout):
        try:
            return self._receive_until_reply(msg, timeout)
        except TimerTimeout:
            raise TerminalClientError('Timeout')

    def _receive_until_reply(self, msg, timeout):
        return self._receive_until_condition(timeout,
                                             lambda r: self._is_reply(msg, r))

    def _receive_ack_or_reply(self, msg, timeout):
        return self._receive_until_condition(timeout,
                                             lambda r: self._is_reply_or_ack(msg, r))

    def _receive_until_condition(self, timeout, condition):
        timer = Timer(timeout)
        for remaining_timeout in timer.remaining_timeouts():
            try:
                r = self.receive(remaining_timeout)
            except TerminalClientError:
                continue
            self._send_ack_if_needed(r)
            if condition(r):
                return r

    def _is_reply(self, msg, reply):
        return (not isinstance(msg, Ack)) and self._is_reply_or_ack(msg, reply)

    @staticmethod
    def _is_reply_or_ack(msg, reply):
        return msg.uid == reply.uid

    def _send_ack_if_needed(self, msg):
        if not isinstance(msg, Ack):
            self._send_ack(msg)

    def _send_ack(self, msg):
        self.send(Ack.create_reply(msg))

    def send(self, msg):
        self._strcomm.write_str(self.serialize(msg))

    def receive(self, timeout):
        self._terminalcomm.set_timeout(timeout)
        with self._client_exception_wrap():
            return self.deserialize(self._strcomm.read_str())

    @contextmanager
    def _client_exception_wrap(self):
        with self._wrap_timeout_exception():
            try:
                yield None
            except (pexpect.TIMEOUT, TimeoutError) as e:
                LOGGER.debug('Timeout raised')
                raise TerminalClientError(e)
            except Exception as e:
                LOGGER.debug('Raised exception: %s: %s', e.__class__.__name__, e)
                raise


class TerminalComm(ChunkReaderBase, ChunkWriterBase):
    def __init__(self, terminal):
        ChunkReaderBase.__init__(self)
        self._terminal = terminal
        self._timeout = -1

    def set_timeout(self, timeout):
        self._timeout = timeout

    def _read(self, n):
        return self._terminal.read_nonblocking(n, timeout=self._timeout)

    def _flush(self):
        pass

    def _write(self, s):
        self._terminal.send(s)
