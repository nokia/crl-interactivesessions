# pylint: disable=unused-argument
import paramiko
import mock


__copyright__ = 'Copyright (C) 2019, Nokia'


class EchoChannel(object):
    def __init__(self, recvlist=None):
        self.recvlist = recvlist
        self.mock = None
        self.active = True
        self.create_mock()
        self.recv_side_effect = None

    def create_mock(self):
        self.mock = mock.create_autospec(paramiko.channel.Channel,
                                         spec_set=True)
        self.mock.recv.side_effect = self.recv
        self.mock.send.side_effect = self.send
        self.mock.close.side_effect = self.close

    def send(self, s):
        self.recvlist.append(s)
        return len(s)

    def recv(self, size):
        if self.recv_side_effect is not None:
            self.recv_side_effect()  # pylint: disable=not-callable
        while self.active:
            try:
                return self.recvlist.pop(0)
            except IndexError:
                pass
        return b''

    def close(self):
        self.recvlist = list()
        self.active = False

    def wait_until_all_recv(self):
        while self.recvlist:
            # Receiving data
            pass
