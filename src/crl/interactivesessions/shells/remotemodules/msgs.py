# pylint: disable=arguments-differ
import sys
import traceback
import itertools
from collections import namedtuple

if 'exceptions' not in globals():
    from . import exceptions


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [exceptions]


class MsgclsMsgid(namedtuple('MsgclsMgsid', ['msgcls', 'msgid'])):
    pass


class MsgMap(object):

    def __init__(self):
        self._msgclses = {}
        self._msgclsmsgids = {}
        self._count = itertools.count()

    def add_msgcls(self, msgcls):
        msgid = self._count.next()
        self._msgclses[msgid] = msgcls
        self._msgclsmsgids[msgcls.__name__] = MsgclsMsgid(msgcls, msgid)

    def get_msgid(self, msg):
        return self._msgclsmsgids[msg.__class__.__name__].msgid

    def get_msgcls(self, msgid):
        return self._msgclses[msgid]


class Serializable(object):
    def serialize(self):
        """Return serialization of the object"""
        raise NotImplementedError()


class NoArg(Serializable):
    def serialize(self):
        return ''


NOARG = NoArg()


class MsgBase(object):

    _msgmap = MsgMap()
    _uid_iter = itertools.count()
    _serialization_tmpl = '{msgid}:{uid}:{serialized_arg}'

    def __init__(self):
        self._uid = None
        self._arg = None

    def set_arg(self, arg):
        self._arg = arg

    @classmethod
    def set_msgclses(cls, *msgclses):
        cls._msgmap = MsgMap()
        for msgcls in msgclses:
            cls._msgmap.add_msgcls(msgcls)

    def set_uid(self, uid):
        self._uid = uid

    @property
    def uid(self):
        return self._uid

    @property
    def msgid(self):
        return self._msgmap.get_msgid(self)

    @property
    def is_response_expected(self):
        return True

    def serialize(self):
        return self._serialization_tmpl.format(msgid=self.msgid,
                                               uid=self.uid,
                                               serialized_arg=self.serialize_arg())

    @classmethod
    def deserialize(cls, s):
        msgid, uid, serialized_args = s.split(':', 2)
        msgcls = cls._msgmap.get_msgcls(int(msgid))
        args = msgcls.deserialize_arg(serialized_args)
        return msgcls.create_with_uid_and_args(int(uid), args)

    def serialize_arg(self):
        """Returns serialization of *_arg*."""
        return (self._arg.serialize()
                if isinstance(self._arg, Serializable) else
                self._arg)

    @classmethod
    def deserialize_arg(cls, serialized_arg):
        """Returns arg from serialized *serialized_arg*"""
        return serialized_arg

    @classmethod
    def create_reply(cls, msg, arg=NOARG):
        return cls.create_with_uid_and_args(uid=msg.uid, arg=arg)

    @classmethod
    def create(cls, arg=NOARG):
        return cls.create_with_uid_and_args(uid=cls._uid_iter.next(),
                                            arg=arg)

    @classmethod
    def create_with_uid_and_args(cls, uid, arg):
        msg = cls()
        msg.set_uid(uid)
        msg.set_arg(arg)
        return msg


class CommandMsgBase(MsgBase):

    @property
    def cmd(self):
        return self._arg


class ExecCommandRequest(CommandMsgBase):
    pass


class ExecCommandReply(MsgBase):

    @property
    def out(self):
        return self._arg

    def serialize_arg(self):
        outobj = self._arg
        return '' if outobj is None else repr(outobj)


class ErrorObj(object):
    def __init__(self, error):
        self._error = error
        self._tbobj = traceback.extract_tb(sys.exc_info()[2])

    @property
    def tbstr(self):
        return ''.join(traceback.format_list(self._tbobj))

    @property
    def fulltbstr(self):
        return 'Traceback (most recent call last):\n{}'.format(self.tbstr)

    @property
    def name_and_msg(self):
        return '{name}: {msg}'.format(name=self.name, msg=str(self._error))

    @property
    def name(self):
        return self._error.__class__.__name__

    def __repr__(self):
        return '{fulltbstr}\n{name_and_msg}'.format(
            fulltbstr=self.fulltbstr,
            name_and_msg=self.name_and_msg)


class ExecCommandErrorObj(Serializable):
    def __init__(self, error, cmd):
        self._error = ErrorObj(error)
        self._cmd = cmd
        self._traceback = ''.join(traceback.format_list(
            traceback.extract_tb(sys.exc_info()[2])))

    def __str__(self):
        return ('{name_and_msg} '
                'size={l}\n{fulltbstr}\nExecuted command block:\n{cmd}'.format(
                    fulltbstr=self._error.fulltbstr,
                    cmd=self._cmd_lines,
                    name_and_msg=self._error.name_and_msg,
                    l=len(self._cmd)))

    def serialize(self):
        return str(self)

    def __repr__(self):
        return str(self)

    @property
    def _cmd_lines(self):
        return '\n'.join(
            ['    block line {i}: {c}'.format(i=i, c=c) for i, c in enumerate(
                self._cmd.splitlines(), start=1)])


class ExitRequest(MsgBase):
    pass


class FatalPythonErrorReply(MsgBase):

    @classmethod
    def deserialize_arg(cls, s):
        raise exceptions.FatalPythonError(s)


class ServerIdRequest(MsgBase):
    pass


class ServerIdReply(MsgBase):

    @property
    def server_id(self):
        return self._arg


class SendCommandRequest(CommandMsgBase):
    @property
    def is_response_expected(self):
        return False


class Ack(MsgBase):
    pass


def set_msgclses():
    MsgBase.set_msgclses(ExecCommandRequest,
                         ExecCommandReply,
                         ExitRequest,
                         FatalPythonErrorReply,
                         ServerIdRequest,
                         ServerIdReply,
                         SendCommandRequest,
                         Ack)
