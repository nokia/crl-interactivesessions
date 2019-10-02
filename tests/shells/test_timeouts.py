from contextlib import contextmanager
import pytest
from crl.interactivesessions.shells.timeouts import Timeouts
from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from crl.interactivesessions.shells.msgreader import MsgReader
from crl.interactivesessions.shells.rawpythonshell import RawPythonShell
from crl.interactivesessions.shells.msgpythonshell import MsgPythonShell
from crl.interactivesessions.remoteproxies import _RemoteProxy


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


def timeout_expected():
    return pytest.mark.parametrize('timeout, expected', [
        (60, 60.0),
        ('60', 60.0),
        (60.0, 60.0)])


@timeout_expected()
def test_python_short_timeout(timeout, expected):
    t = Timeouts()
    assert_python_short_timeouts(10)
    t.set_python_short_timeout(timeout)
    assert_python_short_timeouts(expected)
    t.reset_python_short_timeout()
    assert_python_short_timeouts(10)


def assert_python_short_timeouts(timeout):
    assert RawPythonShell.short_timeout == timeout
    assert MsgPythonShell.short_timeout == timeout


@timeout_expected()
def test_proxy_default_timeout(timeout, expected):
    t = Timeouts()
    assert_proxy_default_timeout(3600)
    t.set_proxy_default_timeout(timeout)
    assert_proxy_default_timeout(expected)
    t.reset_proxy_default_timeout()
    assert_proxy_default_timeout(3600)


def assert_proxy_default_timeout(timeout):
    c = CustomRemoteProxy(session=None, remote_name=None)
    assert c.get_remote_proxy_timeout() == timeout


class CustomRemoteProxy(_RemoteProxy):
    def get_remote_proxy_timeout(self):
        return self._get_remote_proxy_timeout()
