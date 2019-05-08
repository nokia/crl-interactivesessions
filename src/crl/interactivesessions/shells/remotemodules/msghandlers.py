# pylint: disable=arguments-differ
if 'msgs' not in globals():
    from . import (
        msgs,
        exceptions)


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [msgs, exceptions]


class MsgHandlerBase(object):

    def __init__(self):
        self._send_reply = None
        self._server_id = None

    def handle_msg(self, msg):
        """Override this and do message handling in this method"""

    def set_send_reply(self, send_reply):
        self._send_reply = send_reply

    def set_server_id(self, server_id):
        self._server_id = server_id


class CommandHandlerBase(MsgHandlerBase):
    def __init__(self):
        super(CommandHandlerBase, self).__init__()
        self._pythoncmdline = None

    def handle_msg(self, msg):
        raise NotImplementedError()

    def _exec_cmdrequest(self, commandrequest):
        return self._pythoncmdline.exec_command(commandrequest.cmd)

    def set_pythoncmdline(self, pythoncmdline):
        self._pythoncmdline = pythoncmdline


class ExecCommandHandler(CommandHandlerBase):

    def handle_msg(self, execcommandrequest):
        out_obj = self._exec_and_get_outobj(execcommandrequest)
        self._send_reply(msgs.ExecCommandReply.create_reply(execcommandrequest,
                                                            out_obj))

    def _exec_and_get_outobj(self, execcommandrequest):
        try:
            return self._exec_cmdrequest(execcommandrequest)
        except Exception as e:  # pylint: disable=broad-except
            return msgs.ExecCommandErrorObj(e, self._pythoncmdline.current_cmd)


class ServeExitRequestHandler(MsgHandlerBase):
    def handle_msg(self, _):
        raise exceptions.ExitFromServe()


class ServerIdRequestHandler(MsgHandlerBase):
    def handle_msg(self, request):
        self._send_reply(msgs.ServerIdReply.create_reply(request, self._server_id))


class SendCommandHandler(CommandHandlerBase):
    def handle_msg(self, sendcommandrequest):
        self._exec_cmdrequest(sendcommandrequest)
