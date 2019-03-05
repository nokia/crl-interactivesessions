# pylint: disable=arguments-differ
import sys
import traceback
from collections import namedtuple

if 'exceptions' not in globals():
    from . import exceptions


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [exceptions]


class MsgclsMsgid(namedtuple('MsgclsMgsid', ['msgcls', 'msgid'])):
    pass


class MsgMap(object):

    def __init__(self, *msgclses):
        self.msgclses = dict(enumerate(msgclses))
        self.msgclsmsgids = dict((msgcls.__name__, MsgclsMsgid(msgcls, msgid))
                                 for msgid, msgcls in self.msgclses.items())


class MsgBase(object):

    def serialize(self):
        pass

    def deserialize(self, s):
        pass

    @classmethod
    def create(cls, *args, **kwargs):
        msg = cls()
        msg.initialize(*args, **kwargs)
        return msg

    def initialize(self, *args, **kwargs):
        """Initialization with args in the implementation of this method.
        """


class StrMsgBase(MsgBase):
    def __init__(self):
        self._s = None

    def serialize(self):
        return self._s

    def deserialize(self, s):
        self._s = s

    def initialize(self, s):
        self._s = s


class CommandMsgBase(StrMsgBase):

    @property
    def cmd(self):
        return self._s


class ExecCommandRequest(CommandMsgBase):
    pass


class ExecCommandReply(MsgBase):
    def __init__(self):
        self.out_obj = None
        self.out = None

    def serialize(self):
        return '' if self.out_obj is None else repr(self.out_obj)

    def deserialize(self, s):
        self.out = s

    def initialize(self, out_obj):
        self.out_obj = out_obj


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


class ExecCommandErrorObj(object):
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

    def __init__(self):
        self._errorobj = None

    def serialize(self):
        return repr(self._errorobj)

    def deserialize(self, s):
        raise exceptions.FatalPythonError(s)

    def initialize(self, errorobj):
        self._errorobj = ErrorObj(errorobj)


class ServerIdRequest(MsgBase):
    pass


class ServerIdReply(StrMsgBase):

    @property
    def server_id(self):
        return self._s


class SendCommandRequest(CommandMsgBase):
    pass


MSGMAP = MsgMap(ExecCommandRequest,
                ExecCommandReply,
                ExitRequest,
                FatalPythonErrorReply,
                ServerIdRequest,
                ServerIdReply,
                SendCommandRequest)
