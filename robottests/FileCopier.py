from crl.interactivesessions.InteractiveSession import BashShell
from crl.interactivesessions.autorunnerterminal import AutoRunnerTerminal
from crl.interactivesessions.autorecoveringterminal import (
    AutoRecoveringTerminal)


__copyright__ = 'Copyright (C) 2019, Nokia'


class _RemoteFile(object):
    def __init__(self, terminal, filename, options='r'):
        self.terminal = terminal
        self.filename = filename
        self.options = options
        self.handle = None

    def __enter__(self):
        self.terminal.initialize_if_needed()
        self.handle = self.terminal.get_proxy_object_from_call(
            'open', self.filename, self.options)
        self.handle.set_proxy_spec(file)
        return self.handle

    def __exit__(self, *args, **kwargs):
        if self.handle is not None:
            self.handle.close()
            self.handle = None


class FileCopier(object):
    def __init__(self, shells=None):
        self.terminal = None
        self.buffersize = 32768
        self._initialize(BashShell() if shells is None else shells)
        self._buf = None

    def set_buffersize(self, buffersize):
        self.buffersize = buffersize

    def _initialize(self, shells):
        self.terminal = AutoRunnerTerminal()
        self.terminal.initialize_with_shells(shells=shells)

    def copy_file_to_remote(self, source, dest):
        self._copy_file_from_ropen_to_wopen(
            lambda: open(source, 'rb'),
            lambda: _RemoteFile(self.terminal, dest, 'wb'))

    def copy_file_from_remote(self, source, dest):
        self._copy_file_from_ropen_to_wopen(
            lambda: _RemoteFile(self.terminal, source, 'rb'),
            lambda: open(dest, 'wb'))

    def _copy_file_from_ropen_to_wopen(self, ropen, wopen):
        with ropen() as readf:
            with wopen() as writef:
                self._copy_file_from_readf_to_writef(readf, writef)

    def _copy_file_from_readf_to_writef(self, readf, writef):
        while self._read(readf):
            writef.write(self._buf)

    def _read(self, readf):
        self._buf = readf.read(self.buffersize)
        return self._buf
