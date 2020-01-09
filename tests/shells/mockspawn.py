import logging
from pexpect.spawnbase import (
    SpawnBase,
    TIMEOUT)
from crl.interactivesessions.shells.remotemodules.chunkcomm import SharedBytesIO
from .interpreter import (
    Interpreter,
    InterpreterTimeout)

__copyright__ = 'Copyright (C) 2019, Nokia'


class Default(object):
    pass


DEFAULT = Default()

LOGGER = logging.getLogger(__name__)


class MockSpawn(SpawnBase):

    _handlers = None
    _state = None

    # pylint: disable=too-many-arguments
    def __init__(self,
                 command,
                 args=None,
                 timeout=DEFAULT,
                 maxread=DEFAULT,
                 searchwindowsize=DEFAULT,
                 logfile=DEFAULT,
                 env=None,
                 ignore_sighup=False,
                 encoding=DEFAULT,
                 codec_errors=DEFAULT):
        super(MockSpawn, self).__init__(**self._get_kwargs(
            timeout=timeout,
            maxread=maxread,
            searchwindowsize=searchwindowsize,
            logfile=logfile,
            encoding=encoding,
            codec_errors=codec_errors))
        self._state.env = {} if env is None else env
        self._state.ignore_sighup = ignore_sighup
        self._interpreter = Interpreter(self._handlers, self._state)
        self._io = SharedBytesIO()
        self.sendline(command if args is None else ' '.join([command] + args))

    @staticmethod
    def _get_kwargs(**kwargs):
        return {n: v for n, v in kwargs.items() if v != DEFAULT}

    def __str__(self):
        return 'interpreter={interpreter}, readable={readable}, buf={buf}'.format(
            interpreter=self._interpreter,
            readable=self._io.readable_size,
            buf=str(self._io.getvalue()))

    def read_nonblocking(self, size=1, timeout=None):
        LOGGER.debug('read_nonblocking called with size=%s, timeout=%s', size, timeout)
        if not self._io.readable_size:
            self._io.write(self._try_to_read(timeout))

        ret = self._io.read(min(size, self._io.readable_size))
        LOGGER.debug('read_nonblocking return %s', ret)
        return ret

    def _try_to_read(self, timeout):
        try:
            return self._interpreter.read(timeout)
        except InterpreterTimeout:
            raise TIMEOUT('Timeout exceeded')

    def send(self, s=''):
        LOGGER.debug('send called with %s', s)
        b = self._encoder.encode(self._coerce_send_string(s), final=False)
        self._interpreter.write(b)

    def sendline(self, s=''):
        return self.send(self._coerce_send_string(s) + b'\n')

    @classmethod
    def set_handlers(cls, handlers):
        cls._handlers = handlers

    @classmethod
    def set_state(cls, state):
        cls._state = state
