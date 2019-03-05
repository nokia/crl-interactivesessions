if 'msgmanager' not in globals():
    from . import msgmanager


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [msgmanager]


class Client(msgmanager.MsgManagerBase):
    def send_and_receive(self, msg):
        self.send(msg)
        return self.receive()

    def send(self, msg):
        self._strcomm.write_str(self.serialize(msg))

    def receive(self):
        return self.deserialize(self._strcomm.read_str())
