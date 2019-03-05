from contextlib import contextmanager
import socket
from io import BytesIO
import pytest

from crl.interactivesessions.shells.paramikospawn import (
    ParamikoSpawn, EOF, TIMEOUT)

from .echochannel import EchoChannel


__copyright__ = 'Copyright (C) 2019, Nokia'


class Reader(object):
    def __init__(self, read):
        self._read = read

    def read_until_size(self, n):
        io = BytesIO()
        while n - io.tell() > 0:
            io.write(self._read(n - io.tell()))

        return io.getvalue()


@contextmanager
def spawn(chan, *args, **kwargs):
    p = ParamikoSpawn(chan, *args, **kwargs)
    try:
        chan.wait_until_all_recv()
        yield p
    finally:
        p.close()


@pytest.mark.parametrize('recvlist', [
    [b'123'],
    [b'1', b'2', b'3'],
    [b'12', b'3']])
def test_read_nonblocking(recvlist):
    with spawn(EchoChannel(recvlist)) as p:
        r = Reader(lambda n: p.read_nonblocking(n, 1))
        assert r.read_until_size(3) == b'123'


def test_read_nonblocking_eof():
    with spawn(EchoChannel([b'recv', b''])) as p:
        assert p.read_nonblocking(5, 0.001) == b'recv'
        with pytest.raises(EOF):
            p.read_nonblocking(1, 1)


def test_read_nonblocking_raises_eof():
    chan = EchoChannel()
    chan.close()
    with spawn(chan) as p:
        for _ in range(2):
            with pytest.raises(EOF):
                p.read_nonblocking(1, 1)


@pytest.mark.parametrize('timeout', [-1, 0, 1, None])
def test_read_nonblocking_timeout(timeout):
    with spawn(EchoChannel([b'receive'])) as p:
        assert p.read_nonblocking(10, timeout) == b'receive'


def test_read_nonblocking_raises_timeout():
    with spawn(EchoChannel(list())) as p:
        with pytest.raises(TIMEOUT):
            p.read_nonblocking(1, 0.01)


def test_write_and_read():
    with spawn(EchoChannel(list())) as p:
        p.write(b'write')
        assert p.read(5) == b'write'


def test_writelines_and_read():
    with spawn(EchoChannel(list())) as p:
        p.writelines(['1', '2'])
        assert p.read(2) == b'12'


def test_sendline():
    with spawn(EchoChannel(list())) as p:
        p.sendline('line')
        assert p.read(5) == b'line\n'


def test_socket_timeout():
    chan = EchoChannel(list())

    def raise_socket_timeout():
        raise socket.timeout()
    chan.recv_side_effect = raise_socket_timeout
    with spawn(chan) as p:
        with pytest.raises(EOF):
            p.read_nonblocking(1, 1)


def test_wait():
    with spawn(EchoChannel(list())) as p:
        with pytest.raises(NotImplementedError):
            p.wait()


def test_kill():
    with spawn(EchoChannel(list())) as p:
        with pytest.raises(NotImplementedError):
            p.kill(9)
