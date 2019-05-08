from crl.interactivesessions.shells.remotemodules.msgmanager import MsgManagerBase
from crl.interactivesessions.shells.remotemodules.msgs import Ack

__copyright__ = 'Copyright (C) 2019, Nokia'


class Client(MsgManagerBase):
    def send_and_receive(self, msg):
        self.send(msg)
        while True:
            reply = self.receive()
            if not isinstance(reply, Ack) and msg.uid == reply.uid:
                return reply

    def send(self, msg):
        self._strcomm.write_str(self.serialize(msg))

    def receive(self):
        return self.deserialize(self._strcomm.read_str())
