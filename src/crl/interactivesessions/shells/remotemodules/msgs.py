# pylint: disable=arguments-differ
import sys
import traceback
import itertools
import base64
import logging
from collections import namedtuple
if 'exceptions' not in globals():
    from . import exceptions
    from . import compatibility


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [exceptions, compatibility]
LOGGER = logging.getLogger(__name__)


class MsgclsMsgid(namedtuple('MsgclsMgsid', ['msgcls', 'msgid'])):
    pass


class MsgMap(object):

    def __init__(self):
        self._msgclses = {}
        self._msgclsmsgids = {}
        self._count = itertools.count()

    def add_msgcls(self, msgcls):
        msgid = next(self._count)
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
        return b''


NOARG = NoArg()


class MsgBase(object):

    _msgmap = MsgMap()
    _uid_iter = itertools.count()

    def __init__(self):
        self._uid = None
        self._arg = None

    def __str__(self):
        return '{cls}(uid={uid}, arg={arg})'.format(
            cls=self.__class__.__name__, uid=self._uid, arg=self._arg)

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
        LOGGER.debug('==== MsgBase serialize starting')
        return b''.join(self._serialize_strings())

    def _serialize_strings(self):
        yield compatibility.string_conversion_to_bytes(self.msgid)
        yield b':'
        yield compatibility.string_conversion_to_bytes(self.uid)
        yield b':'
        yield self.serialize_arg()

    @classmethod
    def deserialize(cls, s):
        msgid, uid, serialized_args = s.split(b':', 2)
        msgcls = cls._msgmap.get_msgcls(int(msgid))
        args = msgcls.deserialize_arg(serialized_args)
        return msgcls.create_with_uid_and_args(int(uid), args)

    def serialize_arg(self):
        """Returns serialization of *_arg*.
        The default serialization expects bytes or string."""
        return (self._arg.serialize()
                if isinstance(self._arg, Serializable) else
                self._serialize_string_or_bytes_arg())

    def _serialize_string_or_bytes_arg(self):
        return self._serialize_string_or_bytes(self._arg)

    @staticmethod
    def _serialize_string_or_bytes(s):
        return base64.b64encode(
            b's' + s.encode('utf-8')
            if compatibility.PY3 and isinstance(s, str) else
            b'b' + s)

    @classmethod
    def deserialize_arg(cls, serialized_arg):
        """Returns arg from serialized *serialized_arg*"""
        if not serialized_arg:
            return NOARG
        decoded_arg = base64.b64decode(serialized_arg)
        return (decoded_arg[1:].decode('utf-8')
                if decoded_arg[0] == ord(b's') else
                decoded_arg[1:])

    @classmethod
    def create_reply(cls, msg, arg=NOARG):
        return cls.create_with_uid_and_args(uid=msg.uid, arg=arg)

    @classmethod
    def create(cls, arg=NOARG):
        return cls.create_with_uid_and_args(uid=next(cls._uid_iter),
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
        return compatibility.to_string(self._arg)


class ExecCommandRequest(CommandMsgBase):
    pass


class ExecCommandReply(MsgBase):

    @property
    def out(self):
        return self._arg

    def serialize_arg(self):
        outobj = self._arg

        return self._serialize_string_or_bytes(self._get_string_or_bytes(outobj))

    @staticmethod
    def _get_string_or_bytes(s):
        if isinstance(s, (bytes, str)):
            return s
        if s is None:
            return b''
        return repr(s)


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
                'size={lead}\n{fulltbstr}\nExecuted command block:\n{cmd}'.format(
                    fulltbstr=self._error.fulltbstr,
                    cmd=self._cmd_lines,
                    name_and_msg=self._error.name_and_msg,
                    lead=len(self._cmd)))

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
        raise exceptions.FatalPythonError(
            super(FatalPythonErrorReply, cls).deserialize_arg(s))


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
