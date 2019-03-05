if 'msgs' not in globals():
    from . import msgs


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [msgs]


class StrComm(object):

    len_width = 11
    str_tmpl = '{{s_len:0{len_width}}}{{s}}'.format(len_width=len_width)

    def __init__(self, comm_factory):
        self._comm_factory = comm_factory
        self._comm = None

    @property
    def comm(self):
        if self._comm is None:
            self._comm = self._comm_factory()
        return self._comm

    def write_str(self, s):
        self.comm.write(self.str_tmpl.format(s_len=len(s), s=s))

    def read_str(self):
        return self.comm.read_until_size(int(self.comm.read_until_size(self.len_width)))


class MsgManagerBase(object):

    messages = msgs.MSGMAP
    msgid_len = 3
    msg_tmpl = '{{msgid:0{msgid_len}}}{{serialized_msg}}'.format(msgid_len=msgid_len)

    def __init__(self):
        self._msghandler_factories = dict()
        self._strcomm = None
        self._handler_maps = []
        self._update_handler_maps()
        self._setup_handlers()

    def _update_handler_maps(self):
        """Add :class:`.HandlerMap` instance
        (request class, handler factory pairs) to *_handler_maps*.
        """

    @property
    def strcomm(self):
        return self._strcomm

    def _setup_handlers(self):
        for m in self._handler_maps:
            self.set_msghandler_factory(m.request_name, m.handler_factory)

    def set_msghandler_factory(self, cls_name, msghandler_factory):
        self._msghandler_factories[cls_name] = msghandler_factory

    def set_comm_factory(self, comm_factory):
        self._strcomm = StrComm(comm_factory)

    def serialize(self, msg):
        return self.msg_tmpl.format(
            msgid=self.messages.msgclsmsgids[msg.__class__.__name__].msgid,
            serialized_msg=msg.serialize())

    def deserialize(self, s):
        msgid = int(s[:self.msgid_len])
        msg = self.messages.msgclses[msgid]()
        msg.deserialize(s[self.msgid_len:])
        return msg
