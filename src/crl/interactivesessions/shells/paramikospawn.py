# pylint: disable=signature-differs
"""Provides an interface like pexpect.spawn interface using paramiko
   The implementation is based on 'pexpect.popen_spawn.PopenSpawn'.
"""
import threading
import socket
import logging
# CAUTION: spawnbase is not mentioned in __all__ so it is supposed to used
# internally only,
from pexpect.spawnbase import SpawnBase, PY3
from pexpect import EOF, TIMEOUT


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)

try:
    from queue import Queue, Empty  # Python 3
except ImportError:
    from Queue import Queue, Empty  # Python 2


class ParamikoSpawn(SpawnBase):
    """
    ParamikoSpawn uses the same mechanism than *PopenSpawn* for reading and
    writing from/to 'socket' but instead of *subprocess.Popen* it uses
    *paramiko.channel.Channel* which has to be given as an argument *chan*.
    """
    if PY3:
        crlf = '\n'.encode('ascii')
    else:
        crlf = '\n'

    def __init__(self, chan, timeout=30, maxread=40000, searchwindowsize=None,
                 logfile=None, encoding=None,
                 codec_errors='strict'):
        super(ParamikoSpawn, self).__init__(
            timeout=timeout,
            maxread=maxread,
            searchwindowsize=searchwindowsize,
            logfile=logfile,
            encoding=encoding,
            codec_errors=codec_errors)

        self.chan = chan
        self.closed = False
        self._buf = self.string_type()
        self._read_reached_eof = False
        self._chunk_size = 32000
        self._read_queue = Queue()
        self._read_thread = threading.Thread(target=self._read_incoming)
        self._read_thread.setDaemon(True)
        self._read_thread.start()

    def read_nonblocking(self, size, timeout):
        if self._read_reached_eof:
            self.flag_eof = True
            raise EOF('End Of File (EOF).')

        if timeout == -1:
            timeout = self.timeout
        elif timeout is None:
            timeout = 1e6

        return self._read_queue_and_buf(timeout, size) if size > 0 else ''

    def _read_queue_and_buf(self, timeout, size):

        buf = self._read_with_or_without_timeout(timeout=timeout,
                                                 size=size,
                                                 buf=self._buf)
        r, self._buf = buf[:size], buf[size:]

        if self._read_reached_eof and not r:

            self.flag_eof = True
            raise EOF('End-of-file from read_nonblocking')

        self._log(r, '_read_from_queue')
        return r

    def _read_with_or_without_timeout(self, timeout, size, buf):
        if not buf:
            try:
                buf = self._read_from_queue(timeout=timeout,
                                            size=size,
                                            buf=buf)
            except Empty:
                if not self._buf:
                    raise TIMEOUT('read_nonblocking: timeout exceeded')
        else:
            buf = self._read_from_queue_until_end_or_size(buf, size)

        return buf

    def _read_from_queue(self, timeout, size, buf):
        incoming = self._read_queue.get(timeout=timeout)
        if incoming is None:
            self._read_reached_eof = True
            return buf

        buf += self._decoder.decode(incoming, final=False)
        return self._read_from_queue_until_end_or_size(buf, size)

    def _read_from_queue_until_end_or_size(self, buf, size):
        while len(buf) < size:
            try:
                incoming = self._read_queue.get_nowait()
                if incoming is None:
                    self._read_reached_eof = True
                    break
                else:
                    buf += self._decoder.decode(incoming,
                                                final=False)
            except Empty:
                break
        return buf

    def _read_incoming(self):
        """Run in a thread to move output from the chan to a queue."""
        while True:
            buf = b''
            try:
                buf = self.chan.recv(32768)
            except socket.timeout as e:
                self._log(e, 'read_incoming')

            if not buf:
                # This indicates we have reached EOF
                self._read_queue.put(None)
                return

            self._read_queue.put(buf)

    def write(self, s):
        '''This is similar to send() except that there is no return value.
        '''
        self.send(s)

    def writelines(self, sequence):
        '''This calls write() for each element in the sequence.

        The sequence can be any iterable object producing strings, typically a
        list of strings. This does not add line separators. There is no return
        value.
        '''
        for s in sequence:
            self.send(s)

    def send(self, s):
        '''Send data to the Paramiko channel.

        Returns the number of bytes written.
        '''
        s = self._coerce_send_string(s)
        self._log(s, 'send')

        b = self._encoder.encode(s, final=False)
        return self._send_in_chunks(b)

    def _send_in_chunks(self, b):
        sbytes = 0
        for i in range(0, len(b), self._chunk_size):
            sbytes += self.chan.send(b[i:i + self._chunk_size])
        return sbytes

    def sendline(self, s=''):
        '''Wraps send(), sending string ``s`` to child process, with os.linesep
        automatically appended. Returns number of bytes written. '''

        n = self.send(s)
        return n + self.send(self.linesep)

    def wait(self):
        '''Not used by interactivesessions.
        '''
        raise NotImplementedError()

    def kill(self, sig):
        '''This is used by interactivesessions but rarely.
        Not implementing now.
        '''
        raise NotImplementedError()

    def sendeof(self):
        '''Closes channel.'''
        self.chan.close()

    def close(self, force=False):  # pylint: disable=unused-argument
        logger.debug('closing ParamikoSpawn %s', self)
        self.sendeof()
        self._read_thread.join(10)
