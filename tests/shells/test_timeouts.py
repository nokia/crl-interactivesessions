from contextlib import contextmanager
from crl.interactivesessions.shells.timeouts import Timeouts
from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from crl.interactivesessions.shells.msgreader import MsgReader
from crl.interactivesessions.shells.rawpythonshell import RawPythonShell
from crl.interactivesessions.shells.msgpythonshell import MsgPythonShell


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_timeouts_status(statuscodeverifier):
    default = DEFAULT_STATUS_TIMEOUT.get()
    with in_timeouts(100) as timeout:
        statuscodeverifier.verify_with_timeout(timeout)

    statuscodeverifier.verify_with_timeout(default)


def test_timeouts_msgreader():
    default = MsgReader.get_timeout()
    with in_timeouts(100) as timeout:
        assert MsgReader.get_timeout() == timeout

    assert MsgReader.get_timeout() == default


@contextmanager
def in_timeouts(timeout):
    t = Timeouts()
    try:
        t.set(timeout)
        yield timeout
    finally:
        t.reset()


def test_python_short_timeout():
    t = Timeouts()
    assert_python_short_timeouts(10)
    t.set_python_short_timeout(60)
    assert_python_short_timeouts(60)
    t.reset_python_short_timeout()
    assert_python_short_timeouts(10)


def assert_python_short_timeouts(timeout):
    assert RawPythonShell.short_timeout == timeout
    assert MsgPythonShell.short_timeout == timeout
