import os
import subprocess
from contextlib import contextmanager
import pytest
import signal
import time

from crl.interactivesessions.daemonizer import daemon_popen
from . utils import verify_kill


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def outfile(tmpdir):
    return os.path.join(tmpdir.dirname, 'outfile')


@pytest.fixture
def popen_hello_sleep_pid(outfile, sleeptime):
    with popen_hello_sleep_context(outfile, sleeptime) as pid:
        yield pid


@contextmanager
def popen_hello_sleep_context(outfile, sleeptime):
    pid = daemon_popen('echo hello; sleep {}'.format(sleeptime),
                       executable='/bin/bash', env=os.environ.copy(),
                       outfile=outfile)
    for _ in range(5):
        try:
            with open(outfile) as f:
                assert f.read() == 'hello\n'
        except AssertionError:
            time.sleep(0.1)
    with verify_kill(pid):
        yield pid


def test_daemon_popen_with_killpg(popen_hello_sleep_pid):
    os.killpg(popen_hello_sleep_pid, signal.SIGTERM)


@pytest.mark.usefixtures('popen_hello_sleep_pid')
def test_daemon_popen_with_pkill(outfile, sleeptime):
    subprocess.check_call(['pkill', '-f', 'sleep {}'.format(sleeptime)])
