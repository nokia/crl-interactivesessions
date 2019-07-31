from contextlib import contextmanager
import logging
import os
import stat
import errno
import base64
import pexpect
from .shells.remotemodules.tokenreader import (
    TokenReader,
    SingleGapMatcher)
from .RunnerHandler import (
    TOKEN,
    SIZE_PACKER)

__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)
BUFFER_SIZE = 4092


class CompatibilityFile(object):
    """Class which
    h callable dir attributes are like Python2 dir(file) callables"""
    @staticmethod
    def __noop__():
        return None
    close = __noop__
    fileno = __noop__
    flush = __noop__
    isatty = __noop__
    next = __noop__
    read = __noop__
    readinto = __noop__
    readline = __noop__
    readlines = __noop__
    seek = __noop__
    tell = __noop__
    truncate = __noop__
    write = __noop__
    writelines = __noop__
    xreadlines = __noop__


class RemoteFileReadingFailed(Exception):
    pass


class RemoteFileOperationTimeout(Exception):
    pass


class _RemoteFileProxy(object):
    """Optimized file proxy which uses raw terminal mode.  The implementation
    bypasses most of the pexpect and terminal input and output buffer handling.

    TODO: Still some decoding and encoding is done by pexpect for send. With
    further optimization the writing could be done about 30 - 50% faster.  This
    could be done by pty_pexpect case by writing directly to pty.child_fd. In
    the Windows case direct reading and writing to Paramiko channel would do
    the trick without encodings.
    """
    def __init__(self, fileproxy, terminal, timeout):
        self.fileproxy = fileproxy
        self.terminal = terminal
        self.timeout = timeout
        self._filehandle = None
        self._proxy_handle = None
        self._tokenreader = TokenReader(
            TOKEN,
            read_until_size=self._read_until_size,
            matcher_factory=SingleGapMatcher)

    @property
    def filehandle(self):
        if self._filehandle is None:
            self._set_filehandle()
        return self._filehandle

    def _set_filehandle(self):
        self._filehandle = self.terminal.get_proxy_object_from_call(
            self._get_remote_obj('FileHandle'), self.fileproxy)
        stdout_proxy = self.terminal.get_proxy_object(
            self.shell.get_stdout_str(), None)
        self._filehandle.set_io_outfile(stdout_proxy)

    @staticmethod
    def _get_remote_obj(objname):
        return "runnerhandlerns['{}']".format(objname)

    @property
    def shell(self):
        return self.terminal.get_session().current_shell()

    @property
    def pterm(self):
        return self.terminal.get_session().terminal

    @property
    def proxy_handle(self):
        if self._proxy_handle is None:
            self._proxy_handle = self.filehandle.get_proxy_handle()
        return self._proxy_handle

    def read(self, size):
        self.shell.send_command('{proxy_handle}.read({size})'.format(
            proxy_handle=self.proxy_handle,
            size=size))
        with self.timeouthandling():
            return self._read_until_size(self._read_buffer_size(size))

    def _read_buffer_size(self, maxsize):
        self._tokenreader.read_until_token()
        size = SIZE_PACKER.unpack(self._read_until_size(4))[0]
        if size > maxsize:
            raise RemoteFileReadingFailed(
                "Unpacked size {s} exceeded given maximum size {m}".format(
                    s=size,
                    m=maxsize))
        return size

    @contextmanager
    def timeouthandling(self):
        try:
            yield None
        except pexpect.TIMEOUT:
            raise RemoteFileOperationTimeout(self._get_terminal_output())

    def _get_terminal_output(self):
        return b'' if self.pterm.before is None else self.pterm.before

    def _read_until_size(self, size):
        buf = b''
        toread = size
        while toread > 0:
            ret = self.pterm.read_nonblocking(toread, timeout=self.timeout)
            buf += ret
            toread -= len(ret)
        return buf

    def write(self, buf):
        encoded_buf = base64.b64encode(buf)
        with self.timeouthandling():
            self._write(encoded_buf)

    def _write(self, buf):

        self.shell.send_command('{proxy_handle}.write({lenbuf})'.format(
            proxy_handle=self.proxy_handle,
            lenbuf=len(buf)))
        self.pterm.expect('reading start')
        self.pterm.send(buf)
        self.pterm.expect('reading stop')

    def close(self):
        self._clean_shell()
        self.fileproxy.close()

    def _clean_shell(self):
        self.shell.get_prompt_from_terminal(timeout=20)


class _LocalFile(object):
    def __init__(self, destination, source_file=None):
        self.destination = destination
        self.source_file = source_file
        self.handle = None
        self._filename = None

    @property
    def _chmod(self):
        return os.chmod

    @property
    def _makedirs(self):
        return os.makedirs

    @property
    def _path(self):
        return os.path

    def makedirs_with_mode(self, path, mode=None):
        # os.makedirs follows umask of the shell => forcing with chmod.
        self._makedirs(path)
        if mode is not None:
            self._chmod(path, mode)

    @contextmanager
    def open(self, options):
        try:
            self.handle = self._open(options)
            yield self.handle
        finally:
            self.close()

    def _open(self, options):
        return open(self.filename, options)

    def chmod(self, mode):
        self._chmod(self.filename, int(mode, 8))

    def makedirs_if_needed(self, mode):
        try:
            self.makedirs(mode)
        except OSError as e:
            if e.errno == errno.EEXIST:
                return
            raise

    def makedirs(self, mode=None):
        d = self._path.dirname(self.filename)
        if d:
            self.makedirs_with_mode(d, **self._get_mode_kwargs(mode))

    @staticmethod
    def _get_mode_kwargs(mode):
        return {} if mode is None else {'mode': int(mode, 8)}

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    @property
    def filename(self):
        if self._filename is None:
            self._set_filename()
        return self._filename

    def _set_filename(self):
        if self.source_file is not None:
            self._set_filename_with_source_file()
        else:
            self._filename = self.destination

    def _set_filename_with_source_file(self):
        destination_file = (
            self._path.join('.', '')
            if self.destination is None or self.destination == '' else
            self.destination)
        self._filename = (
            self._path.join(destination_file, self._path.basename(
                self.source_file))
            if self._is_directory(destination_file) else
            destination_file)

    def _is_directory(self, path):
        return self._path.basename(path) == '' or self._is_existing_directory(path)

    @staticmethod
    def _is_existing_directory(path):
        try:
            return stat.S_ISDIR(os.stat(path).st_mode)
        except OSError as e:
            if e.errno == errno.ENOENT:
                return False
            raise


class _OsProxiesForRemoteFile(object):
    def __init__(self, terminal, timeout):
        self.terminal = terminal
        self.timeout = timeout
        self._proxynames = ['chmod',
                            'makedirs',
                            'path']
        self._proxies = {}
        self._set_proxies()

    def __getattr__(self, name):
        try:
            return self._proxies[name]
        except KeyError:
            raise AttributeError()

    def _set_proxies(self):
        for n in self._proxynames:
            self._proxies[n] = self.terminal.get_proxy_object(
                'os.{}'.format(n), None)
            self._proxies[n].set_remote_proxy_timeout(self.timeout)


class _RemoteFile(_LocalFile):
    def __init__(self, filename, terminal, timeout, source_file=None):
        super(_RemoteFile, self).__init__(filename, source_file)
        self.terminal = terminal
        self.terminal.initialize_if_needed()
        self.timeout = timeout
        self._osproxies = _OsProxiesForRemoteFile(self.terminal, self.timeout)

    @property
    def _chmod(self):
        return self._osproxies.chmod

    @property
    def _makedirs(self):
        return self._osproxies.makedirs

    @property
    def _path(self):
        return self._osproxies.path

    def _open(self, options):
        handle = self.terminal.get_proxy_object_from_call(
            'open', self.filename, options)
        handle.set_proxy_spec(CompatibilityFile())
        handle.set_remote_proxy_timeout(self.timeout)
        return _RemoteFileProxy(handle,
                                terminal=self.terminal,
                                timeout=self.timeout)


class _RemoteScriptRemoteFile(_RemoteFile):
    def __init__(self, filename, terminal, timeout, source_file=None):
        super(_RemoteScriptRemoteFile, self).__init__(
            '' if filename is None else filename,
            terminal,
            timeout,
            source_file)

    def _set_filename(self):
        self._filename = self._path.join(self.destination, self.source_file)


class _DirRemoteFile(_RemoteFile):

    def makedirs(self, mode=None):
        self.makedirs_with_mode(self.destination,
                                **self._get_mode_kwargs(mode))


class _CopyDirRemoteFile(_RemoteFile):
    def __init__(self, targetdir, terminal, timeout, parts=None):
        super(_CopyDirRemoteFile, self).__init__(targetdir, terminal, timeout)
        self.parts = None
        self._set_parts(parts)

    def _set_parts(self, parts):
        self.parts = list() if parts is None else list(parts)

    def _set_filename(self):
        self._filename = self._path.join(self.destination, *self.parts)

    def makedirs(self, mode=None):
        self.makedirs_with_mode(self.filename, **self._get_mode_kwargs(mode))

    def create_with_append(self, part):
        return self._create(targetdir=self.destination,
                            terminal=self.terminal,
                            timeout=self.timeout,
                            parts=self.parts + [part])

    @classmethod
    def _create(cls, **kwargs):
        return cls(**kwargs)


class _FileCopier(object):
    def __init__(self):
        self.buffersize = BUFFER_SIZE
        self._buf = None

    def copy_file(self, sourcefile, targetfile, mode=None):
        targetfile.makedirs_if_needed(mode)
        self.copy_file_no_dir_create(sourcefile, targetfile, mode)

    def copy_file_no_dir_create(self, sourcefile, targetfile, mode):
        with sourcefile.open('rb') as readf:
            with targetfile.open('wb') as writef:
                self._copy_file_from_readf_to_writef(readf, writef)
        if mode is not None:
            targetfile.chmod(mode)

    def _copy_file_from_readf_to_writef(self, readf, writef):
        while self._read(readf):
            writef.write(self._buf)

    def _read(self, readf):
        self._buf = readf.read(self.buffersize)
        return self._buf


class _LocalDirCopier(_FileCopier):
    def __init__(self, source_dir, target_dir, mode, terminal, timeout):
        super(_LocalDirCopier, self).__init__()
        self.source_dir = source_dir
        self.mode = mode
        self.copydirremotefile = _CopyDirRemoteFile(
            target_dir,
            terminal=terminal,
            timeout=timeout)

    def copy_directory_to_target(self):
        self.copydirremotefile.makedirs_if_needed(oct(0o777))
        self._copy_directory(self.source_dir, self.copydirremotefile)

    def _copy_directory(self, source_dir, target):
        try:
            oswalktuple = next(os.walk(source_dir))
            self._copy_directory_from_oswalktuple(oswalktuple, target)
        except StopIteration:
            pass

    def _copy_directory_from_oswalktuple(self, oswalktuple, target):
        root, dirnames, filenames = oswalktuple
        for f in filenames:
            self.copy_file_no_dir_create(
                sourcefile=_LocalFile(os.path.join(root, f)),
                targetfile=target.create_with_append(f),
                mode=self.mode)
        for d in dirnames:
            nexttarget = target.create_with_append(d)
            nexttarget.makedirs_if_needed(oct(0o777))
            self._copy_directory(os.path.join(root, d), nexttarget)

        target.chmod(self.mode)
