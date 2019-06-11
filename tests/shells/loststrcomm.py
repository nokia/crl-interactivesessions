import logging
from fractions import Fraction
from contextlib import contextmanager
import pexpect
from crl.interactivesessions.shells.terminalclient import TerminalComm


__copyright__ = 'Copyright (C) 2019, Nokia'


LOGGER = logging.getLogger(__name__)


class LostStrComm(object):

    def __init__(self, probability_of_lost, modifier=None):
        self._count = 0
        self._probability_of_lost = probability_of_lost
        self._modifier = modifier or self._default_modifier
        self._strcomm = None
        self._write_empty = False
        self._in_lost_context = False

    @staticmethod
    def _default_modifier(*_):
        return b''

    @contextmanager
    def in_lost(self):
        self._in_lost_context = True
        try:
            yield None
        finally:
            self._in_lost_context = False

    def set_strcomm(self, strcomm):
        self._strcomm = strcomm

    @property
    def comm(self):
        return self._strcomm.comm

    def write_str(self, s):
        self._strcomm.comm.clear()
        self._strcomm.write_str(s)
        written = self._strcomm.comm.written
        new_written = self._modified_s(written)
        if new_written or self._write_empty:
            LOGGER.debug('===== writing: %s', repr(new_written))
            self._strcomm.comm.write_direct(new_written)

    def read_str(self):
        ret = self._strcomm.read_str()
        modified_ret = self._modified_s(ret)
        LOGGER.debug('==== Received: %s, is lost: %d', ret, not modified_ret)
        LOGGER.debug('==== Modified return %s', modified_ret)
        if not modified_ret:
            raise pexpect.TIMEOUT('==== Message is lost: {!r}'.format(ret))

        return ret

    def _modified_s(self, s):
        if self._is_msg_lost():
            new_s = self._modifier(s)
            LOGGER.debug('==== Msg modified, count=%s, s=%s, new_s=%s',
                         self._count, s, repr(new_s))
            s = new_s
        else:
            LOGGER.debug('==== Msg success, count=%s, %s', self._count, s)
        return s

    def _is_msg_lost(self):
        p = Fraction(self._probability_of_lost)
        ret = self._count % p.denominator < p.numerator and self._in_lost_context
        self._count += 1
        if ret:
            LOGGER.debug('==== message LOST')
        else:
            LOGGER.debug('==== message SUCCESS')
        return ret


class CustomTerminalComm(TerminalComm):
    def __init__(self, *args, **kwargs):
        super(CustomTerminalComm, self).__init__(*args, **kwargs)
        self._written = b''

    @property
    def written(self):
        return self._written

    def clear(self):
        self._written = b''

    def _write(self, s):
        self._written += s

    def write_direct(self, s):
        super(CustomTerminalComm, self)._write(s)
