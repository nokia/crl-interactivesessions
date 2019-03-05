import os
import subprocess
from collections import namedtuple
from contextlib import contextmanager


__copyright__ = 'Copyright (C) 2019, Nokia'


class PipeFiles(namedtuple('PipeFiles', ['read', 'write'])):
    pass


def daemon_popen(cmd, executable, env, outfile=None):
    pipefiles = PipeFiles(*os.pipe())

    pid = os.fork()
    if pid:
        return _read_cmd_pid(pipefiles)
    else:
        out = open(os.devnull, 'w') if outfile is None else open(outfile, 'w')
        pro = subprocess.Popen(cmd,
                               executable=executable,
                               bufsize=-1,
                               shell=True,
                               stdin=None,
                               stdout=out,
                               stderr=subprocess.STDOUT,
                               env=env,
                               close_fds=True,
                               preexec_fn=os.setsid)

        _write_cmd_pid(pipefiles, pro.pid)
        os._exit(0)  # pylint: disable=protected-access


def _read_cmd_pid(pipefiles):
    os.close(pipefiles.write)
    with _fdopen(pipefiles.read) as r:
        return int(r.read())


def _write_cmd_pid(pipefiles, pid):
    os.close(pipefiles.read)
    with _fdopen(pipefiles.write, 'w') as w:
        w.write(str(pid))
        w.flush()


@contextmanager
def _fdopen(fd, mode='r'):
    try:
        yield os.fdopen(fd, mode)
    finally:
        os.close(fd)
