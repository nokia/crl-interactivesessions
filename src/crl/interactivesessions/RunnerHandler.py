try:
    import tty
    import termios
except ImportError:
    # in Windows only path to the module is needed
    pass
import os
import sys
import pickle
import base64
import StringIO  # pylint: disable=import-error
import traceback
import logging
import threading
from contextlib import contextmanager
from functools import wraps


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


def get_python_file_path():
    return os.path.abspath(__file__
                           if __file__.endswith('y') else
                           __file__[:-1])


class _Container(object):
    pass


_PROXY_CONTAINER = _Container()


def exec_in_module(code, module):
    exec(code, module.__dict__)


class FileHandle(object):

    def __init__(self, handle):
        self.logger = logging.getLogger()
        self.handle = handle
        self.olds = dict()
        self.infile = sys.stdin
        self.outfile = None

    def set_io_outfile(self, outfile):
        self.outfile = outfile

    def write(self, size):
        self._setraw_if_needed(self.infile.fileno())
        self._write_stdout_with_flush('reading start')
        self.handle.write(base64.b64decode(self.infile.read(size)))
        self._write_stdout_with_flush('reading stop')

    def _write_stdout_with_flush(self, buf):
        self.outfile.write(buf)
        self.outfile.flush()

    def read(self, size):
        self._setraw_if_needed(self.outfile.fileno())
        buf = self.handle.read(size)
        self._write_stdout_with_flush(b'{lenbuf:011d}{buf}'.format(
            lenbuf=len(buf),
            buf=buf))

    def _setraw_if_needed(self, fd):
        if fd not in self.olds:
            self._set_rawmode(fd)

    def _set_rawmode(self, fd):
        self.olds[fd] = termios.tcgetattr(fd)
        tty.setraw(fd)

    def set_originalmode(self):
        for fd, old in self.olds.items():
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        self._write_stdout_with_flush('originalmode set')


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
        if timeout >= 0 or timeout is None:
            self.thread.join(timeout)
        return self._get_response_from_thread(timeout)

    def _get_response_from_thread(self, timeout):
        if ((timeout is not None and timeout < 0) or
                self.thread.isAlive()):
            return self._store_and_return_response()
        self.runnerhandler.remove_response(self.response_id)
        return self._serialize(*self.response)

    def _store_and_return_response(self):
        self.runnerhandler.add_response(self.response_id, self)
        return self._serialize('timeout', self.response_id)

    def _serialize(self, steeringstring, obj):
        return base64.b64encode(self.runnerhandler.pickler.dumps(
            (steeringstring, self.runnerhandler.pickler.dumps(obj))))


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
        self._handled_types = [] if handled_types is None else handled_types

    def add_response(self, response_id, response):
        self._responses[response_id] = response

    def _get_response(self, response_id):
        return self._responses[response_id]

    def remove_response(self, response_id):
        try:
            del self._responses[response_id]
        except KeyError:
            pass

    @staticmethod
    def _deserialize(content, unpickler=pickle.Unpickler):
        outputstream = StringIO.StringIO(base64.b64decode(content))
        return unpickler(outputstream).load()

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
            response.set_response(('exception', e))

    @responsethread
    def run(self, code, locals_):
        return ('run', self._get_object(code, locals_))

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
        steeringstring = 'handled' if is_handled else 'nothandled'
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
