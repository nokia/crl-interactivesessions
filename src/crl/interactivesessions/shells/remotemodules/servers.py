import sys
import uuid
from collections import namedtuple
from contextlib import contextmanager

if 'msgs' not in globals():
    from . import (
        msgs,
        msghandlers,
        msgmanager,
        servercomm,
        pythoncmdline,
        exceptions)


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [msgs,
                 msghandlers,
                 msgmanager,
                 servercomm,
                 pythoncmdline,
                 exceptions]


class HandlerMap(namedtuple('HandlerMap', ['requestcls', 'handler_factory'])):

    @property
    def request_name(self):
        return self.requestcls.__name__


class ServerBase(msgmanager.MsgManagerBase):
    def __init__(self):
        super(ServerBase, self).__init__()
        self._server_id = str(uuid.uuid4().hex)

    def _update_handler_maps(self):
        self._handler_maps += [
            HandlerMap(msgs.ExitRequest, msghandlers.ServeExitRequestHandler),
            HandlerMap(msgs.ServerIdRequest, msghandlers.ServerIdRequestHandler)]

    def serve(self):
        self._send_server_id_reply()
        try:
            while True:
                self.handle_next_msg()
        except exceptions.ExitFromServe:
            pass

    def _send_server_id_reply(self):
        self._send_reply(msgs.ServerIdReply.create(self._server_id))

    def handle_next_msg(self):
        try:
            self.handle_serialized(self._strcomm.read_str())
        except Exception as e:  # pylint: disable=broad-except
            self._send_reply(msgs.FatalPythonErrorReply.create(e))
            raise exceptions.ExitFromServe()

    def handle_serialized(self, s):
        self._handle_msg(self.deserialize(s))

    def _handle_msg(self, msg):
        msghandler = self._msghandler_factories[msg.__class__.__name__]()
        msghandler.set_server_id(self._server_id)
        msghandler.set_send_reply(self._send_reply)

        msghandler.handle_msg(msg)

    def _send_reply(self, msg):
        self._strcomm.write_str(self.serialize(msg))


class PythonServer(ServerBase):
    stdout_handle = '__stdout'
    stderr_handle = '__stderr'

    def __init__(self):
        super(PythonServer, self).__init__()
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self._pythoncmdline_factory = None
        self._pythoncmdline = None
        self._iohandlemap = {self.stdout_handle: self.stdout,
                             self.stderr_handle: self.stderr}

    def _update_handler_maps(self):
        super(PythonServer, self)._update_handler_maps()
        self._handler_maps += [
            HandlerMap(requestcls=msgs.ExecCommandRequest,
                       handler_factory=self._execcmdhandler_factory),
            HandlerMap(requestcls=msgs.SendCommandRequest,
                       handler_factory=self._sendcmdhandler_factory)]

    def set_comm_factory(self, comm_factory):
        def comm_factory_with_stdout():
            return comm_factory(self.stdout)

        self._strcomm = msgmanager.StrComm(comm_factory_with_stdout)

    def set_pythoncmdline_factory(self, pythoncmdline_factory):
        self._pythoncmdline_factory = pythoncmdline_factory

    def _execcmdhandler_factory(self):
        return self._create_handler(msghandlers.ExecCommandHandler)

    def _sendcmdhandler_factory(self):
        return self._create_handler(msghandlers.SendCommandHandler)

    def _create_handler(self, handlercls):
        handler = handlercls()
        handler.set_pythoncmdline(self.pythoncmdline)
        return handler

    @property
    def pythoncmdline(self):
        if self._pythoncmdline is None:
            self._pythoncmdline = self._pythoncmdline_factory()
        return self._pythoncmdline

    def serve(self):
        with self._outerrtonull():
            super(PythonServer, self).serve()

    @contextmanager
    def _outerrtonull(self):
        self._setup_iohandles()

        self.pythoncmdline.exec_command('import os, sys')
        self.pythoncmdline.exec_command("f = open(os.devnull, 'w')")
        self.pythoncmdline.exec_command('sys.stdout = f')
        self.pythoncmdline.exec_command('sys.stderr = f')
        try:
            yield None
        finally:
            self.pythoncmdline.exec_command('sys.stdout = {stdout}'.format(
                stdout=self.stdout_handle))
            self.pythoncmdline.exec_command('sys.stderr = {stderr}'.format(
                stderr=self.stderr_handle))

    def _setup_iohandles(self):
        for handle, iofile in self._iohandlemap.items():
            self.pythoncmdline.namespace[handle] = iofile

    @classmethod
    def create_and_serve(cls):
        s = cls()
        s.set_comm_factory(servercomm.ServerComm.create)
        s.set_pythoncmdline_factory(pythoncmdline.PythonCmdline)
        s.serve()
