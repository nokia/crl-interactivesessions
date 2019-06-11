from contextlib import contextmanager
import pytest
from crl.interactivesessions.shells.msgreader import MsgReader


__copyright__ = 'Copyright (C) 2019, Nokia'


def read_until_end(timeout):
    return timeout


@pytest.mark.parametrize('timeout, expected', [
    (100, 100),
    ('100', 100),
    ('0.5', 0.5),
    (0.5, 0.5)])
def test_msgreader(timeout, expected, caplog):
    m = MsgReader(read_until_end)
    assert m.read_until_end() == m.get_timeout()
    assert m.get_timeout() == 15

    with in_timeout(timeout):
        MsgReader.set_timeout(timeout)
        assert m.read_until_end() == expected

    assert m.read_until_end() == 15
    s = set(['Set timeout for reading post-login banner message to {} seconds'.format(
        timeout), 'Reset timeout for reading post-login banner message to 15 seconds'])
    assert s.issubset({r.message for r in caplog.records})


@contextmanager
def in_timeout(timeout):
    try:
        MsgReader.set_timeout(timeout)
        yield timeout
    finally:
        MsgReader.reset_timeout()
