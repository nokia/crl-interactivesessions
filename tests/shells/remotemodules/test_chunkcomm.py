import logging
import abc
import itertools
from collections import namedtuple
from io import BytesIO
import pytest
import six
from crl.interactivesessions.shells.remotemodules.chunkcomm import (
    ChunkWriterBase,
    ChunkReaderBase,
    ChunkReaderError,
    SharedBytesIO,
    CHUNKSIZE,
    MAX_BUFFER_SIZE)
from crl.interactivesessions.shells.remotemodules.compatibility import to_bytes


__copyright__ = 'Copyright (C) 2019, Nokia'

EXPECTED_TOKEN_LEN = 20
EXPECTED_LEN_WIDTH = len(str(CHUNKSIZE))
LOGGER = logging.getLogger(__name__)


class ExampleWriter(ChunkWriterBase):
    def __init__(self, value):
        self._io = BytesIO()
        self._buf = b''
        self._value = value

    @property
    def sio(self):
        return self._io

    @property
    def value(self):
        return self._value

    def _write(self, s):
        LOGGER.debug('writing %s', s)
        self._buf += s

    def _flush(self):
        LOGGER.debug('flushing %s', self._buf)
        self._io.write(self._buf)
        self._buf = b''


class BrokenChunkWriter(ExampleWriter):

    @property
    def rubbish_in_begin(self):
        return b'rubbish-in-begin'

    @property
    def rubbish_in_end(self):
        return b'rubbish-in-end'

    @property
    def sio(self):
        return self._io

    @property
    def value(self):
        return self._value

    def _write(self, s):
        self._buf += s

    def _flush(self):
        self._io.write(self.rubbish_in_begin)
        self._io.write(self._buf)
        self._io.write(self.rubbish_in_end)
        self._buf = b''


@six.add_metaclass(abc.ABCMeta)
class MiddleWriterBase(BrokenChunkWriter):
    def __init__(self, value, clean_portion):
        super(MiddleWriterBase, self).__init__(value)
        self._clean_portion = clean_portion

    @property
    def _middle_rubbish(self):
        return b'middle-rubbish'

    def _write(self, s):
        rubbish_start = self._get_rubbish_start(s)
        addition = s[:rubbish_start]
        addition += self._middle_rubbish
        addition += s[rubbish_start:]
        self._buf += addition

    @abc.abstractmethod
    def _get_rubbish_start(self, s):
        """Return start index of middle rubbish for
        """


class DataRubbishWriter(MiddleWriterBase):
    """Add rubbish in middle of data chunk. The full chunk follows the format::

        {token}{data_length}{token}{data_start}{rubbish}{data_end}{token}

    """
    def _get_rubbish_start(self, s):
        data_len = len(s) - 3 * EXPECTED_TOKEN_LEN - EXPECTED_LEN_WIDTH
        return 2 * EXPECTED_TOKEN_LEN + EXPECTED_LEN_WIDTH + int(
            data_len * self._clean_portion)


class LenRubbishWriter(MiddleWriterBase):
    """Add rubbish in the middle of data length field. The full chunk follows
    the format::

        {token}{data_len_start}{rubbish}{data_len_end}{token}{data}{token}
    """
    def _get_rubbish_start(self, s):  # pylint: disable=unused-argument
        return EXPECTED_TOKEN_LEN + int(EXPECTED_LEN_WIDTH * self._clean_portion)


class ExampleChunkReader(ChunkReaderBase):

    count = 0

    def __init__(self, sio):
        super(ExampleChunkReader, self).__init__()
        self._io = sio
        self._io.seek(0)
        assert isinstance(self._sharedio, SharedBytesIO)

    def _read(self, n):
        if self.count > 100:
            assert 0, 'count exceeded'
        self.count += 1
        ret = self._io.read(n)
        LOGGER.debug('_read: %s, n=%d', ret, n)
        return ret

    def _read_until(self, s):
        s_len = len(s)
        buf = self._io.read(s_len)
        LOGGER.debug('Read buf=%s', buf)
        for i in itertools.count():
            if s == buf[i:]:
                return buf[:-s_len]

            buf += self._io.read(1)
            LOGGER.debug('Read buf=%s', buf)

    def getvalue(self):
        return self._sharedio.getvalue()


class HalfChunkReader(ExampleChunkReader):
    def _read(self, n):
        return self._io.read(n // 2 if n > 1 else n)


@pytest.fixture(params=[
    pytest.param(s, id='write {} bytes'.format(len(s))) for s in [
        b'value',
        b'v' * CHUNKSIZE,
        b'value' * CHUNKSIZE,
        (b'value' * CHUNKSIZE)[:-4],
        b'value' * CHUNKSIZE + b'additional-string']])
def readerwriter_factory(request, reader_factory):
    def fact(writer_factory):
        writer = writer_factory(request.param)

        writer.write(writer.value)
        return ReaderWriter(reader=reader_factory(writer.sio),
                            writer=writer)

    return fact


@pytest.fixture(params=[ExampleChunkReader, HalfChunkReader])
def reader_factory(request):
    def fact(sio):
        return request.param(sio)

    return fact


class ReaderWriter(namedtuple('ReaderWriter', ['reader', 'writer'])):
    pass


def test_chunkwriter(readerwriter_factory):
    rw = readerwriter_factory(ExampleWriter)
    assert rw.reader.read_until_size(len(rw.writer.value)) == rw.writer.value


def test_brokenchunkwriter(readerwriter_factory, caplog):
    rw = readerwriter_factory(BrokenChunkWriter)

    assert rw.reader.read_until_size(len(rw.writer.value)) == rw.writer.value
    assert rw.writer.rubbish_in_begin in to_bytes(caplog.text)
    assert (len(rw.writer.value) > CHUNKSIZE) == (
        rw.writer.rubbish_in_end in to_bytes(caplog.text))


class WriterPortion(namedtuple('WriterPortion', ['writer', 'portion'])):
    pass


@pytest.fixture(params=[WriterPortion(writer=w, portion=p)
                        for w in [DataRubbishWriter, LenRubbishWriter]
                        for p in [0.1, 0.5, 0.9]])
def badwriter_factory(request):
    def fact(value):
        return request.param.writer(value, clean_portion=request.param.portion)

    return fact


def test_middlerubbish(readerwriter_factory, caplog, badwriter_factory):
    rw = readerwriter_factory(badwriter_factory)
    with pytest.raises(ChunkReaderError) as excinfo:
        rw.reader.read_until_size(len(rw.writer.value))

    assert 'Buffer: {!r}'.format(rw.reader.getvalue()) in str(excinfo.value)
    assert rw.writer.rubbish_in_begin in to_bytes(caplog.text)


class ExampleSharedBytesIO(SharedBytesIO):
    def getvalue(self):
        return self._io.getvalue()


def test_shared_bytesio_size():
    e = ExampleSharedBytesIO()
    value = b'value' * (MAX_BUFFER_SIZE // 10)
    for _ in range(10):
        e.write(value)
        assert e.read(len(value)) == value

    assert len(e.getvalue()) <= MAX_BUFFER_SIZE
