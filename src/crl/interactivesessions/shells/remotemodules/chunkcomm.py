from datetime import datetime
import logging
from contextlib import contextmanager
from io import (
    BytesIO,
    SEEK_END)
if 'commbase' not in globals():
    from . import commbase
    from . import tokenreader
    from . import compatibility


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [commbase, tokenreader, compatibility]
CHUNKSIZE = 2000
MAX_BUFFER_SIZE = 100 * CHUNKSIZE
LOGGER = logging.getLogger(__name__)


class ChunkReaderError(Exception):
    """Error raised in case :class:`.ChunkReaderBase` is not able to read
    properly the output. This indicates that we need a better algorithm for
    reading and writing in this case.
    """


class ChunkIOBase(object):

    _token = b'^)}>?gDYs[ULFqAkSf~|'
    _chunk_id_width = 4
    _chunk_id_tmpl = '{{chunk_id:0{chunk_id_width}}}'.format(
        chunk_id_width=_chunk_id_width)
    _len_width = len(str(CHUNKSIZE))
    _chunk_len_tmpl = '{{chunk_len:0{len_width}}}'.format(len_width=_len_width)
    _hdr_tmpl = _chunk_id_tmpl + _chunk_len_tmpl
    _hdr_len = _chunk_id_width + _len_width

    @staticmethod
    def _write_log(message):
        timestamp = datetime.now().isoformat()
        log_entry = f'{timestamp} - {message!r}\n'
        with open('/tmp/pythonserver.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        LOGGER.debug(message)


class NoAck(object):
    pass


class ChunkWriterBase(ChunkIOBase, commbase.CommWriterBase):

    def _write(self, s):
        """Writes Bytes *s* to output Bytes stream.
        """
        raise NotImplementedError()

    def _flush(self):
        """Flushes output written by :meth:`._write`.
        """
        raise NotImplementedError()

    def write(self, s):
        """Write string or bytes *s* with *_write*"""
        for chunk_id, i in enumerate(compatibility.RANGE(0, len(s), CHUNKSIZE)):
            chunk_id = chunk_id % 10000
            chunk = s[i:i + CHUNKSIZE]
            self._write_with_size_and_token(chunk, chunk_id=chunk_id)
            self._flush()
            if chunk_id:
                self._read_and_verify_ack(chunk_id)

    def _write_with_size_and_token(self, chunk, chunk_id):
        io = BytesIO()
        for s in self._bytes_for_chunk_with_token(chunk, chunk_id=chunk_id):
            io.write(s)

        self._write(io.getvalue())

    def _bytes_for_chunk_with_token(self, chunk, chunk_id):
        self._write_log('Chunk writer: write chunk token 1')
        yield self._token
        hdr = self._hdr_tmpl.format(chunk_id=chunk_id, chunk_len=len(chunk))
        self._write_log('Chunk writer: write hdr')
        yield compatibility.to_bytes(hdr)
        self._write_log('Chunk writer: write chunk token 2')
        yield self._token
        self._write_log('Chunk writer: write chunk')
        yield chunk
        self._write_log('Chunk writer: write chunk token 3')
        yield self._token

    def _read_and_verify_ack(self, chunk_id):
        if not chunk_id:
            return
        chunk_id_str = self._read_ack()
        if not isinstance(chunk_id_str, NoAck):
            try:
                ack_chunk_id = int(chunk_id_str)
                if chunk_id != ack_chunk_id:
                    self._write_log('ChunkReaderError: expected chunk_id '
                                    f'{chunk_id} != {ack_chunk_id}')
                    raise ChunkReaderError(
                        f'Expected chunk_id {chunk_id}, got {ack_chunk_id}')
            except ValueError:
                self._write_log('ValueError: expected chunk_id '
                                f'{chunk_id} != {chunk_id_str}')
                raise ChunkReaderError(
                    'Unable to desirialize chunk_id {chunk_id_str}'.format(
                        chunk_id_str=chunk_id_str))

    def _read_ack(self):  # pylint: disable=no-self-use
        """Override this if ACK for each chunk is required and return chunk_id string.
        """
        return NoAck()


class ChunkReaderBase(ChunkIOBase, commbase.CommReaderBase):

    def __init__(self):
        self._sharedio = SharedBytesIO()
        self._tokenreader = tokenreader.TokenReader(
            self._token,
            read_until_size=self._read_until_size,
            matcher_factory=tokenreader.SingleGapMatcher)

    @property
    def readerror(self):
        return ChunkReaderError

    def _read(self, n):
        """Read maximum n bytes

        Returns: read byte string
        """
        raise NotImplementedError()

    def read_until_size(self, n):
        self._write_log('read_until_size: starting...')
        while self._sharedio.readable_size < n:
            self._write_log('read_until_size: reading token 1')
            self._read_token()
            self._write_log('read_until_size: reading hdr')
            hdr = self._read_until_size(self._hdr_len)
            self._write_log('read_until_size: verify_read_token 2')
            self._verify_read_token()
            chunk_size_str = hdr[self._chunk_id_width:]
            chunk_size = int(chunk_size_str)
            self._sharedio.write(self._read_until_size(chunk_size))
            self._write_log('read_until_size: verify_read_token 3')
            self._verify_read_token()
            chunk_id = hdr[:self._chunk_id_width]
            if chunk_id != b'0000':
                self._write_log(f'read_until_size: writing chunk ACK {chunk_id}')
                self._write_ack(chunk_id)
            self._write_log(f'read_until_size: read chunk {chunk_id}')
        ret = self._sharedio.read(n)
        self._write_log(f'read_until_size: returning {ret}')
        return ret

    def _write_ack(self, chunk_id):
        """Override this if ACK for each chunk is required.
        """

    def _read_until_size(self, n):
        sio = SharedBytesIO()
        while sio.readable_size < n:
            sio.write(self._read(n - sio.readable_size))

        return sio.read(n)

    def _read_token(self):
        s = self._read_until_token()
        if s:
            self._write_log(f'Unexpected read while trying to read until token: {s}')
            LOGGER.info('Unexpected read: %s', repr(s))
        return s

    def _read_until_token(self):
        return self._tokenreader.read_until_token()

    def _verify_read_token(self):
        s = self._read_token()
        if s:
            self._write_log('ChunkReaderError: '
                            f'Buffer: {self._sharedio.getvalue()!r}')
            raise ChunkReaderError('Buffer: {!r}'.format(self._sharedio.getvalue()))


class ChunkAckBase(ChunkReaderBase, ChunkWriterBase):

    def __init__(self):
        ChunkReaderBase.__init__(self)
        self._chunk_ack_reading = False

    def _read_ack(self):
        try:
            self._chunk_ack_reading = True
            self._write_log('Chunk writer: reading ACK')
            return self._read_until_size(self._chunk_id_width)
        finally:
            self._chunk_ack_reading = False

    def _write_ack(self, chunk_id):
        self._write_log(f'Chunk reader: writing ACK {chunk_id}')
        self._write(chunk_id)
        self._flush()


class SharedBytesIO(object):
    def __init__(self):
        self._io = BytesIO()
        self._reader = None
        self._writer = None
        self._setup_reader_and_writer()

    def _setup_reader_and_writer(self):
        self._reader = PosReader(self._io)
        self._io.seek(0, SEEK_END)
        self._writer = PosWriter(self._io)

    def read(self, size):
        if self._reader.pos + size > MAX_BUFFER_SIZE:
            self._clean_already_read()

        return self._reader.read(size)

    def _clean_already_read(self):
        self._io.seek(self._reader.pos)
        self._io = BytesIO(self._io.read())
        self._setup_reader_and_writer()

    def write(self, s):
        return self._writer.write(s)

    @property
    def readable_size(self):
        return self._writer.pos - self._reader.pos

    def getvalue(self):
        return self._io.getvalue()


class PosIOBase(object):

    def __init__(self, io):
        self._io = io
        self._pos = self._io.tell()

    @contextmanager
    def _in_pos(self):
        self._io.seek(self._pos)
        try:
            yield None
        finally:
            self._pos = self._io.tell()

    @property
    def pos(self):
        return self._pos


class PosWriter(PosIOBase):
    def write(self, s):
        with self._in_pos():
            return self._io.write(s)


class PosReader(PosIOBase):
    def read(self, size):
        with self._in_pos():
            return self._io.read(size)
