from crl.interactivesessions.shells.remotemodules.servercomm import ServerComm
from .commutils import (
    EchoCommThread,
    ClientComm)


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_servercomm():
    e = EchoCommThread()

    def servercomm_fact():
        return ServerComm(infd=e.thread_in_fd, outfile=e.thread_out_file)

    e.set_servercomm_factory(servercomm_fact)

    e.start()
    f = ClientComm(*e.mainfds)
    f.write(EchoCommThread.echomessage)

    assert f.read_until_size(
        len(EchoCommThread.echomessage)) == EchoCommThread.echomessage
