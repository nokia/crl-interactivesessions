import os
import signal

import pytest

from crl.interactivesessions.pexpectplatform import is_windows
from .utils import verify_kill, cmdline_should_not_be_running_or_zompie


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.mark.xfail(is_windows(), reason='Windows pexpect cannot spawn BashShell')
def test_background_nohup(bash_remoterunner,
                          bash_remoterunner_initializer,
                          sleeptime,
                          caplog):
    caplog.set_level(7)
    bash_pid = get_bashshell_pid(bash_remoterunner)
    cmd = 'sleep {}'.format(sleeptime)

    background_pid = bash_remoterunner.execute_nohup_background_in_target(cmd)

    with verify_kill(bash_pid):
        os.kill(bash_pid, signal.SIGHUP)
    bash_remoterunner.close()
    bash_remoterunner_initializer.initializer(bash_remoterunner)
    with verify_kill(background_pid):
        bash_remoterunner.execute_command_in_target("pkill -f '{}'".format(cmd))

    cmdline_should_not_be_running_or_zompie(cmd.split())


def get_bashshell_pid(runner):
    term = runner.get_terminal()
    return int(term.runnerterminal.run('os.getppid()'))


@pytest.mark.xfail(is_windows(), reason='Windows pexpect cannot spawn BashShell')
@pytest.mark.usefixtures('bash_remoterunner')
def test_initialization():
    pass
