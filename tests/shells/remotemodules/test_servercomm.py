import fcntl
import os
import pytest
from crl.interactivesessions.shells.remotemodules.servercomm import ServerComm


@pytest.fixture
def infd(tmpdir):
    infile = tmpdir.join('infile')
    infile.write('content-of-infile')
    with open(str(infile)) as f:
        yield f.fileno()


@pytest.fixture
def outfile(tmpdir):
    outfile = tmpdir.join('outfile')
    with open(str(outfile), 'w') as f:
        yield f


def test_servercomm_blocking_states(infd, outfile):
    s = ServerComm(infd, outfile)
    infl = fcntl.fcntl(s.infd, fcntl.F_GETFL)
    assert infl & os.O_NONBLOCK
    outfl = fcntl.fcntl(s.outfile.fileno(), fcntl.F_GETFL)
    assert not outfl & os.O_NONBLOCK
