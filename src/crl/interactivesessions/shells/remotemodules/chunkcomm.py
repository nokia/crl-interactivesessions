import logging
from contextlib import contextmanager
from io import (
    BytesIO,
    SEEK_END)
if 'commbase' not in globals():
    from . import commbase
    from . import tokenreader
    from . import comp


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [commbase, tokenreader, comp]
CHUNKSIZE = 4096
MAX_BUFFER_SIZE = 100 * CHUNKSIZE
LOGGER = logging.getLogger(__name__)


class ChunkReaderError(Exception):
    """Error raised in case :class:`.ChunkReaderBase` is not able to read
    properly the output. This indicates that we need a better algorithm for
    reading and writing in this case.
    """


class ChunkIOBase(object):

    _token = '^)}>?gDYs[ULFqAkSf~|'
    _len_width = 4
    _chunk_tmpl = (
        '{{token}}{{chunk_len:0{len_width}}}{{token}}{{chunk}}{{token}}'.format(
            len_width=_len_width))


class ChunkWriterBase(ChunkIOBase, commbase.CommWriterBase):
    def _write(self, s):
        """Writes *s* to output stream.
        """
        raise NotImplementedError()

    def _flush(self):
        """Flushes output written by :meth:`._write`.
        """
        raise NotImplementedError()

    def write(self, s):
        for i in comp.comprange(0, len(s), CHUNKSIZE):
            chunk = s[i:i + CHUNKSIZE]
            self._write(self._chunk_tmpl.format(token=self._token,
                                                chunk_len=len(chunk),
                                                chunk=chunk))
            self._flush()


class ChunkReaderBase(ChunkIOBase, commbase.CommReaderBase):

    def __init__(self):
        self._sharedio = SharedBytesIO()
        self._tokenreader = tokenreader.TokenReader(
            self._token,
            read_until_size=self._read_until_size,
            matcher_factory=tokenreader.SingleGapMatcher)

    def _read(self, n):
        """Read maximum n bytes

        Returns: read byte string
        """
        raise NotImplementedError()

    def read_until_size(self, n):
        while self._sharedio.readable_size < n:
            self._read_token()
            chunk_size_str = self._read_until_size(self._len_width)
            self._verify_read_token()
            chunk_size = int(chunk_size_str)
            self._sharedio.write(self._read_until_size(chunk_size))
            self._verify_read_token()

        return self._sharedio.read(n)

    def _read_until_size(self, n):
        sio = SharedBytesIO()
        while sio.readable_size < n:
            sio.write(self._read(n - sio.readable_size))

        return sio.read(n)

    def _read_token(self):
        s = self._read_until_token()
        if s:
            LOGGER.info('Unexpected read: %s', repr(s))
        return s

    def _read_until_token(self):
        return self._tokenreader.read_until_token()

    def _verify_read_token(self):
        s = self._read_token()
        if s:
            raise ChunkReaderError('Buffer: {!r}'.format(self._sharedio.getvalue()))


class SharedBytesIO(object):
    def __init__(self):
        self._bytesio = BytesIO()
        self._reader = None
        self._writer = None
        self._setup_reader_and_writer()

    def _setup_reader_and_writer(self):
        self._reader = PosReader(self._bytesio)
        self._bytesio.seek(0, SEEK_END)
        self._writer = PosWriter(self._bytesio)

    def read(self, size):
        if self._reader.pos + size > MAX_BUFFER_SIZE:
            self._clean_already_read()

        return self._reader.read(size)

    def _clean_already_read(self):
        self._bytesio.seek(self._reader.pos)
        self._bytesio = BytesIO(self._bytesio.read())
        self._setup_reader_and_writer()

    def write(self, s):
        return self._writer.write(s)

    @property
    def readable_size(self):
        return self._writer.pos - self._reader.pos

    def getvalue(self):
        return self._bytesio.getvalue()


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
