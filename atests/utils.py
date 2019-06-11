import time
from contextlib import contextmanager
import psutil


__copyright__ = 'Copyright (C) 2019, Nokia'


@contextmanager
def verify_kill(pid):
    assert pid is not None and is_active(pid)
    yield None
    process_should_not_be_active_after_iterations(pid, iterations=1000)


def process_should_not_be_active_after_iterations(pid, iterations):
    for _ in range(iterations):
        if not is_active(pid):
            return

        time.sleep(0.001)

    assert 0, '{} is still active'.format(psutil.Process(pid))


def is_active(pid):
    return is_condition(
        pid, lambda p: p.is_running() and p.status() != psutil.STATUS_ZOMBIE)


def is_condition(pid, condition):
    try:
        return condition(psutil.Process(pid))
    except psutil.NoSuchProcess:
        return False


def cmdline_should_not_be_running_or_zompie(cmdline):
    def msg_fact(p):
        return '{}: {}'.format(cmdline, p.status())
    for p in psutil.process_iter():
        if p.cmdline() == cmdline:
            assert (not p.is_running and p.status() != psutil.STATUS_ZOMBIE), msg_fact(p)
