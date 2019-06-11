import os
import sys
import types
import pickle
import base64
import traceback
import threading
import fcntl
import struct
from io import BytesIO
from contextlib import contextmanager
from functools import wraps


__copyright__ = 'Copyright (C) 2019, Nokia'

TOKEN = b'+7_<sf80UBtd%umz'
SIZE_PACKER = struct.Struct('!I')
PY3 = (sys.version_info.major == 3)
UNICODE_TYPE = str if PY3 else unicode  # pylint: disable=undefined-variable; # noqa F821


def get_python_file_path():
    return os.path.abspath(__file__
                           if __file__.endswith('y') else
                           __file__[:-1])


class _Container(object):
    pass


class RunnerHandlerUnableToDeserialize(Exception):
    pass


_PROXY_CONTAINER = _Container()


def create_module(modulename):
    n = (modulename.encode('utf-8')
         if not PY3 and isinstance(modulename, UNICODE_TYPE) else
         modulename)
    return types.ModuleType(n)


def exec_in_module(code, module):
    exec(code, module.__dict__)


def iter_until_empty(readline):
    return iter(readline, b'')


class FileHandle(object):
    _size_packer = struct.Struct('!I')

    def __init__(self, handle):
        self.handle = handle
        self.infile = sys.stdin
        self.outfile = None
        self._outfile_write = None

    def set_io_outfile(self, outfile):
        self.outfile = outfile
        self._outfile_write = self.outfile.buffer.write if PY3 else self.outfile.write

    def write(self, size):
        self._write_stdout_with_flush(b'reading start')
        with self._blocking_context():
            self.handle.write(base64.b64decode(self.infile.read(size)))
        self._write_stdout_with_flush(b'reading stop')

    @contextmanager
    def _blocking_context(self):
        infd = self.infile.fileno()
        fl = fcntl.fcntl(infd, fcntl.F_GETFL)
        fcntl.fcntl(infd, fcntl.F_SETFL, fl & ~os.O_NONBLOCK)
        try:
            yield None
        finally:
            fcntl.fcntl(infd, fcntl.F_SETFL, fl)

    def _write_stdout_with_flush(self, buf):
        self._outfile_write(buf)
        self.outfile.flush()

    def read(self, size):
        buf = self.handle.read(size)
        to_be_flushed = TOKEN + SIZE_PACKER.pack(len(buf)) + buf
        self._write_stdout_with_flush(to_be_flushed)


class _Response(object):
    def __init__(self, function, runnerhandler, *args, **kwargs):
        self.response = None
        self.function = function
        self.runnerhandler = runnerhandler
        self.args = args
        self.kwargs = kwargs.copy()
        self.timeout = None
        self._handle_timeout_kwarg()
        self.thread = None
        self.response_id = id(self)

    def _handle_timeout_kwarg(self):
        try:
            self.timeout = self.kwargs['timeout']
            del self.kwargs['timeout']
        except KeyError:
            pass

    def set_response(self, response):
        self.response = response

    def run(self):
        with self.runnerhandler.contextmgr(self):
            self.set_response(
                self.function(self.runnerhandler, *self.args, **self.kwargs))

    def run_in_thread(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.get_response_with_timeout(self.timeout)

    def get_response_with_timeout(self, timeout):
        if timeout is None or timeout >= 0:
            self.thread.join(timeout)
        return self._get_response_from_thread(timeout)

    def _get_response_from_thread(self, timeout):
        if (timeout is not None and timeout < 0) or self.thread.is_alive():
            return self._store_and_return_response()
        self.runnerhandler.remove_response(self.response_id)
        return self._serialize(*self.response)

    def _store_and_return_response(self):
        self.runnerhandler.add_response(self.response_id, self)
        return self._serialize(b'timeout', self.response_id)

    def _serialize(self, steeringstring, obj):
        return self.runnerhandler.pickler.dumps(
            (steeringstring, self.runnerhandler.pickler.dumps(obj, protocol=0)),
            protocol=0)


def responsethread(function, *args, **kwargs):
    # pylint: disable=unused-argument
    @wraps(function)
    def inner_function(runnerhandler, *args, **kwargs):
        return _Response(
            function, runnerhandler, *args, **kwargs).run_in_thread()

    return inner_function


class _RunnerHandler(object):

    def __init__(self):
        self.contextmgr = None
        self.pickler = None
        self._handled_types = None
        self._responses = dict()

    def initialize(self,
                   contextmgr=None,
                   pickler=pickle,
                   handled_types=None):
        self.contextmgr = contextmgr or self.pickle_errors
        self.pickler = pickler
        self._handled_types = (self._default_handled_types
                               if handled_types is None else
                               handled_types)

    @property
    def _default_handled_types(self):
        common = [None, int, float, str]
        pydep = ([bytes]
                 if PY3 else
                 [long, unicode])  # pylint: disable=undefined-variable; # noqa: F821
        return common + pydep

    def add_response(self, response_id, response):
        self._responses[response_id] = response

    def _get_response(self, response_id):
        return self._responses[response_id]

    def remove_response(self, response_id):
        try:
            del self._responses[response_id]
        except KeyError:
            pass

    @classmethod
    def deserialize(cls, content, unpickler=pickle.Unpickler):
        outputstream = BytesIO(cls._to_bytes(content))
        return unpickler(outputstream).load()

    @staticmethod
    def _unicode(s):
        try:
            return unicode(s)
        except NameError:
            return str(s)

    @staticmethod
    def _to_bytes(s):
        return s.encode('utf-8') if PY3 and isinstance(s, str) else s

    @staticmethod
    def _extract_tb():
        return traceback.format_list(traceback.extract_tb(
            sys.exc_info()[2])[3:])

    @contextmanager
    def pickle_errors(self, response):
        try:
            yield None

        except Exception as e:  # pylint: disable=broad-except
            e.trace = self._extract_tb()
            response.set_response((b'exception', e))

    @responsethread
    def run(self, code, locals_):
        return (b'run', self._get_object(code, locals_))

    @responsethread
    def assign_and_run(self, handle, code, locals_):
        self._get_object('{handle} = {code}'.format(
            handle=handle, code=code), locals_)
        return self._get_handled(handle, locals_)

    @responsethread
    def run_and_return_handled(self, code, locals_):
        return self._get_handled(code, locals_)

    def get_response(self, response_id, timeout):
        return self._get_response(
            response_id).get_response_with_timeout(timeout)

    def _get_handled(self, code, locals_):
        obj = self._get_object(code, locals_)
        is_handled = self._is_in_handled_types(obj)
        steeringstring = b'handled' if is_handled else b'nothandled'
        return (steeringstring, obj if is_handled else None)

    def _is_in_handled_types(self, obj):
        for t in self._handled_types:
            if t is None:
                if obj is None:
                    return True
            elif isinstance(obj, t):
                return True
        return False

    @staticmethod
    def _get_object(code, locals_):
        try:
            code_obj = compile(code, '', 'eval')
        except SyntaxError:
            code_obj = compile(code, '', 'single')
        return eval(code_obj, locals_)


_RUNNERHANDLER = _RunnerHandler()
