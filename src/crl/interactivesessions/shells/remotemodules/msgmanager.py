import json
import logging
from collections import namedtuple

LOGGER = logging.getLogger(__name__)

try:
    RANGE = xrange
except NameError:
    RANGE = range

if 'msgs' not in globals():
    from . import msgs
    from . import tokenreader
    from . import compatibility


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [msgs, tokenreader, compatibility]


class StrCommReadError(Exception):
    pass


class StrComm(object):

    _token = b'.;-jJ(8[)OwQaKsF=&Pu'
    len_width = 11
    len_tmpl = '{{s_len:0{len_width}}}'.format(
        len_width=len_width)

    def __init__(self, comm_factory):
        self._comm_factory = comm_factory
        self._comm = None
        self._tokenreader_int = None

    @property
    def comm(self):
        if self._comm is None:
            self._comm = self._comm_factory()
        return self._comm

    @property
    def _tokenreader(self):
        if self._tokenreader_int is None:
            self._tokenreader_int = tokenreader.TokenReader(
                self._token,
                read_until_size=self.comm.read_until_size,
                matcher_factory=tokenreader.SingleGapMatcher)
        return self._tokenreader_int

    def write_str(self, s):
        text = self._token + compatibility.to_bytes(self.len_tmpl.format(s_len=len(s)))
        self.comm.write(text + s)

    def read_str(self):
        while True:
            try:
                self._tokenreader.read_until_token()
                return self.comm.read_until_size(self._get_read_len())
            except (StrCommReadError, self.comm.readerror) as e:
                LOGGER.debug('Error in read_str: %s: %s', e.__class__.__name__, e)

    def _get_read_len(self):
        len_str = self.comm.read_until_size(self.len_width)
        try:
            return int(len_str)
        except ValueError:
            raise StrCommReadError()


class Retry(namedtuple('Retry', ['tries', 'interval', 'timeout'])):
    def serialize(self):
        return json.dumps(self._asdict())

    @classmethod
    def deserialize(cls, serialized_retry):
        return cls(**json.loads(serialized_retry))

    def timeouts(self):
        for _ in RANGE(1, self.tries):
            yield self.interval
        yield self.timeout


class MsgManagerBase(object):

    def __init__(self):
        msgs.set_msgclses()
        self._msghandler_factories = dict()
        self._strcomm = None
        self._handler_maps = []
        self._update_handler_maps()
        self._setup_handlers()
        self._retry = None

    def set_retry(self, retry):
        self._retry = retry

    def _update_handler_maps(self):
        """Add :class:`.HandlerMap` instance
        (request class, handler factory pairs) to *_handler_maps*.
        """

    @property
    def strcomm(self):
        return self._strcomm

    def _setup_handlers(self):
        for m in self._handler_maps:
            self.set_msghandler_factory(m.request_name, m.handler_factory)

    def set_msghandler_factory(self, cls_name, msghandler_factory):
        self._msghandler_factories[cls_name] = msghandler_factory

    def set_comm_factory(self, comm_factory):
        self._strcomm = StrComm(comm_factory)

    @staticmethod
    def serialize(msg):
        return msg.serialize()

    @staticmethod
    def deserialize(s):
        return msgs.MsgBase.deserialize(s)
