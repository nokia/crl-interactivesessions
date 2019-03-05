import os
from random import randint
from contextlib import contextmanager
import pytest

from crl.interactivesessions.remoterunner import RemoteRunner
from crl.interactivesessions.InteractiveSession import InteractiveSession
from crl.interactivesessions.shells import (
    RawPythonShell,
    MsgPythonShell,
    BashShell,
    PythonShell)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def bash_remoterunner_initializer(bash_init):
    def initializer(runner):
        runner.set_target([{'shellname': 'BashShell',
                            'init_env': bash_init.init_env}])
        ret = runner.execute_command_in_target('echo hello')
        assert not int(ret.status)
        return runner

    bash_init.set_initializer(initializer)
    return bash_init


class BashInit(object):

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.init_env_local_path = None
        self.initializer = None
        self._initialize()

    def set_initializer(self, initializer):
        self.initializer = initializer

    @property
    def pid_file(self):
        return os.path.join(self.tmpdir.dirname, 'bashshell.pid')

    @property
    def init_env(self):
        return os.path.join(self.init_env_local_path.dirname,
                            self.init_env_local_path.basename)

    def _initialize(self):
        self.init_env_local_path = self.tmpdir.join('bash_init.sh')
        self.init_env_local_path.write('echo $$ > {}'.format(self.pid_file))


@pytest.fixture
def bash_init(tmpdir):
    return BashInit(tmpdir)


@pytest.fixture
def bash_remoterunner(bash_remoterunner_initializer):
    with bash_remoterunner_context(bash_remoterunner_initializer.initializer) as r:
        yield r


@contextmanager
def bash_remoterunner_context(initializer):
    r = RemoteRunner()
    try:
        yield initializer(r)
    finally:
        r.close()


@pytest.fixture
def sleeptime():
    return randint(100000000, 10000000000)


@pytest.fixture
def interactivesession():
    i = InteractiveSession()
    try:
        yield i
    finally:
        i.close_terminal()


@pytest.fixture(params=[
    [BashShell, PythonShell],
    [RawPythonShell],
    [MsgPythonShell],
    [BashShell, MsgPythonShell]])
def anypythonshell(request, interactivesession):
    interactivesession.spawn(request.param[0]())
    for cls in request.param[1:]:
        interactivesession.push(cls())
    return interactivesession.current_shell()
