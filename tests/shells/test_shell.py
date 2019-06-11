import pytest
from crl.interactivesessions.shells.shell import (
    Shell,
    DefaultStatusTimeout,
    DEFAULT_STATUS_TIMEOUT)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def preserve_default_timeout():
    try:
        yield None
    finally:
        DefaultStatusTimeout.reset()


class CustomShellA(Shell):

    def get_start_cmd(self):
        """Not needed
        """

    def start(self):
        """Not needed
        """

    def exit(self):
        """Not needed
        """

    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        return float(timeout)


class CustomShellB(CustomShellA):
    pass


@pytest.mark.usefixtures('preserve_default_timeout')
def test_default_status_timeout():

    a = CustomShellA()
    b = CustomShellB()
    assert b.get_status_code() == DEFAULT_STATUS_TIMEOUT.get()
    assert repr(DEFAULT_STATUS_TIMEOUT) == repr(DEFAULT_STATUS_TIMEOUT.get())
    expected = float(20)
    DefaultStatusTimeout.set(expected)
    for actual in [a.get_status_code(),
                   b.get_status_code(),
                   DEFAULT_STATUS_TIMEOUT.get(),
                   DefaultStatusTimeout.get()]:
        assert actual == expected


def test_status_timeout_logs(caplog):
    default = DEFAULT_STATUS_TIMEOUT.get()
    try:
        DEFAULT_STATUS_TIMEOUT.set(20)
    finally:
        DEFAULT_STATUS_TIMEOUT.reset()
    s = set(['Set timeout for reading status code to 20 seconds',
             'Reset timeout for reading status code to {} seconds'.format(default)])
    assert s.issubset({r.message for r in caplog.records})
