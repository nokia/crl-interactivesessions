# pylint: disable=arguments-differ
import sys
import traceback
import pickle
import logging
import uuid
from io import BytesIO
from collections import namedtuple
from contextlib import contextmanager
from six import iteritems
from crl.interactivesessions import RunnerHandler
from crl.interactivesessions.shells import MsgPythonShell
from crl.interactivesessions.shells.remotemodules.compatibility import (
    to_string, to_bytes)
from crl.interactivesessions.remoteproxies import (
    _RemoteProxy, _RecursiveProxy)
from crl.interactivesessions.runnerexceptions import (
    RunnerTerminalSessionClosed,
    RunnerTerminalSessionBroken,
    RunnerTerminalUnableToDeserialize,
    RemoteTimeout,
    remotetimeouthandler)
from .garbagemanager import GarbageManager
from .shells.remotemodules.compatibility import PY3

__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


_HandledReturnValue = namedtuple('_HandledReturnValue', [
    'isobj', 'obj'])

_RemoteReturnValue = namedtuple('_RemoteReturnValue', [
    'steeringstring', 'obj'])


class _RemoteRunner(object):
    def __init__(self,
                 runnerterminal,
                 description,
                 template,
                 timeout=None,
                 **kwargs):
        self.runnerterminal = runnerterminal
        self.description = description
        self.timeout = None
        self.run_timeout = None
        self._set_timeouts(timeout)
        self.template = template
        self.kwargs = kwargs
        self.cmd = self.template.format(
            timeout=self.timeout,
            contextmgr=self.runnerterminal.TARGET_CONTEXTMANAGER,
            pickler=self.runnerterminal.TARGET_PICKLER,
            **self.kwargs)

    def _set_timeouts(self, timeout):
        # None timeout means infinite timeout
        self.timeout = self._get_timeout(timeout)
        if self.timeout is None or self.runnerterminal.prompt_timeout is None:
            self.run_timeout = None
        else:
            self.run_timeout = (
                float(self.runnerterminal.prompt_timeout)
                if self.timeout < 0 else
                self.timeout + float(self.runnerterminal.prompt_timeout))

    def _get_timeout(self, timeout):
        return (float(self.runnerterminal.default_timeout)
                if timeout is None else
                float(timeout))

    def run(self):
        with remotetimeouthandler(self._response):
            with self.runnerterminal.error_handling():
                return self._response(
                    self.runnerterminal.get_response_or_raise(
                        self.runnerterminal.run(
                            self.cmd, timeout=self.run_timeout),
                        self.description))

    @staticmethod
    def _response(response):
        return response.obj


class _HandledRemoteRunner(_RemoteRunner):

    def _response(self, ret):
        return _HandledReturnValue(isobj=(ret.steeringstring == b'handled'), obj=ret.obj)


class _TimeoutRemoteRunner(_RemoteRunner):

    def _response(self, response):
        return response


class RunnerTerminal(object):
    """ This is the *Python* terminal session wrapper for
    the transparent proxy instances: :class:`.remoteproxies._RemoteProxy`
    and :class:`.remoteproxies._RecursiveProxy`.

    .. note::
        This class has *Python 2* dependencies.
    """
    # templates for execution on the remote end
    _RUNNERCALL = ("runnerhandlerns['_RUNNERHANDLER'].{method}({args})")

    _RUNNERLOCALS = _RUNNERCALL.format(
        method='{method}',
        args='{args}, locals_=locals()')

    _RUN_TEMPLATE = _RUNNERLOCALS.format(
        method='run',
        args="{cmd!r}, timeout={timeout}")

    _ASSIGN_AND_RUN_TEMPLATE = _RUNNERLOCALS.format(
        method='assign_and_run',
        args="{handle!r}, {cmd!r}, timeout={timeout}")

    _RUN_AND_RETURN_HANDLED_TEMPLATE = _RUNNERLOCALS.format(
        method='run_and_return_handled',
        args="{handle!r}, timeout={timeout}")

    _DESERIALIZE_TEMPLATE = _RUNNERCALL.format(method='deserialize',
                                               args='{obj!r}, {unpickler}')

    _GET_RESPONSE_TEMPLATE = _RUNNERCALL.format(
        method='get_response',
        args='{response_id}, timeout={timeout}')

    # list of libraries to be imported on the remote end during setup phase
    _IMPORTS = ['pickle', 'imp', 'base64', 'os']

    # OPTIONS FOR CONFIGURING SUBCLASS BEHAVIOR
    # path to retrieve the remote handler module from
    HANDLER_SOURCE_PATH = None
    # path where the handler module is to be written to on the remote end
    HANDLER_TARGET_PATH = None
    # Types of objects which are passed back to calller in case of
    # _RecursiveProxy instead of the proxy object. NoneType cannot
    # be pickled and thus we use here singleton instance 'None' instead.
    HANDLED_TYPES = None
    # unpickler to be used when deserializing data returned by remote calls
    UNPICKLER = pickle.Unpickler

    # context manager for handling exception serialization on the remote end
    TARGET_CONTEXTMANAGER = "runnerhandlerns['_RUNNERHANDLER'].pickle_errors"
    # pickler to be used for serializing outgoing data on the remote end
    TARGET_PICKLER = 'pickle'
    # unpickler to be used when deserializing incoming data on the remote end
    TARGET_UNPICKLER = 'pickle.Unpickler'
    # maximum number of remote proxies before garbage cleaning
    MAX_GARBAGE = 100

    def __init__(self):
        self.session = None
        self._initialized_session = None
        self._session_id = None
        self._saved_delaybeforesend = None
        self.default_timeout = 3600
        self.prompt_timeout = 30
        self._garbage_manager = GarbageManager(clean=self._clean_garbage,
                                               max_garbage=self.MAX_GARBAGE)

    def set_default_timeout(self, default_timeout):
        self.default_timeout = default_timeout

    def initialize(self, session):
        """Initializes the terminal with *session*. The *session* has to be a
        wrapper to :class:`.InteractiveSession.InteractiveSession` which
        implements at least *get_session* method which returns the
        :class:`.InteractiveSession.InteractiveSession` instance.
        """

        self.session = session
        self.setup_session()

    def setup_session(self):
        if self.session != self._initialized_session:
            self._prepare_terminal_session()
            self._setup_handler()
            self._set_session_metadata()
            # subclass callback:
            self._setup()

    @property
    def session_id(self):
        return self._session_id

    def initialize_if_needed(self):
        pass

    def _prepare_terminal_session(self):
        self.get_session().push(MsgPythonShell())

    def _setup_handler(self):
        self.import_libraries(*self._IMPORTS)
        self.__setup_handler_module(RunnerHandler.get_python_file_path())

    def _set_session_metadata(self):
        self._initialized_session = self.session
        self._session_id = id(self.get_session())

    def get_session(self):
        return self.session.get_session()

    def run(self, cmd, timeout=-1, _rerun=False):
        """Run with error handling *run* of the session.

        .. note ::

            It is recommended to use :meth:`.run_python` instead
            of this method.
        """
        if self.session is None:
            raise RunnerTerminalSessionClosed(
                'Trying to run command (cmd: {cmd}, timeout: {timeout})'
                ' in the closed session. Command has no effect.'.format(
                    cmd=cmd, timeout=timeout))
        try:
            self._garbage_manager.clean_if_needed(session_id=self._session_id)
            return self._run_in_session(cmd, timeout)
        except Exception as e:  # pylint: disable=broad-except
            self._raise_session_broken_exception(e)

    def add_handle_to_garbage(self, session_id, handle):
        """Adds :class:`crl.interactivesessions.remoteproxies._RemoteProxy`
        handles (or the derivates of it) into garbage collection. The garbage
        is cleaned during executions when the treshold *MAX_GARBAGE* is
        exceeded.
        """
        if session_id == self._session_id:
            self._garbage_manager.add(session_id=session_id, garbage=handle)

    def _clean_garbage(self, garbage):
        self._run_in_session('del {garbage}'.format(garbage=', '.join(garbage)),
                             timeout=(2 * self.prompt_timeout))

    def _run_in_session(self, cmd, timeout):
        return self._run_full_output(cmd, timeout=timeout)

    def _run_full_output(self, cmd, timeout):
        return self.get_session().current_shell().exec_command(
            cmd, timeout=timeout)

    @staticmethod
    def _raise_session_broken_exception(exception):
        LOGGER.debug('%s: %s\nBacktrace: \n%s',
                     exception.__class__.__name__,
                     exception,
                     ''.join(traceback.format_list(traceback.extract_tb(
                         sys.exc_info()[2]))))
        raise RunnerTerminalSessionBroken(exception)

    @contextmanager
    def _session_error_handling(self):
        try:
            yield None
        except Exception as e:  # pylint: disable=broad-except
            self._raise_session_broken_exception(e)

    def close_session(self):
        if self.session is not None and self.get_session() is not None:
            self.get_session().close_terminal()
        self.session = None

    def _setup(self):
        """Subclass callback, called at the end of executor creation.

        Any setup actions for the executor or handler should be done here.
        """

    def _close(self):
        """Subclass callback, called before the executor is closed.

        Any cleanup actions for the executor or handler should be done here.
        """

    def run_python(self, cmd, timeout=None):
        """Runs a python expression on the remote node.

        The return value of the remote call is returned as a python object.

        If an exception is raised on the remote end, the traceback is
        logged, and the exception object is raised by this method.
        """
        return _RemoteRunner(runnerterminal=self,
                             template=self._RUN_TEMPLATE,
                             description=cmd,
                             timeout=timeout,
                             cmd=cmd).run()

    @staticmethod
    @contextmanager
    def error_handling():
        yield None

    def assign_and_run_python(self, handle, cmd, timeout=None):
        """Runs a python expression *cmd* on the remote node and assigns then
        value to *handle*. If the value of the expression is an instance of any
        of the  *HANDLED_TYPES*, then also the value is returned.

        .. note::

            The *HANDLED_TYPES* instances must be serializable and
            deserializable by picklers and unpicklers.

        The return value of the remote call is returned as a python object with
        two attributes:

        *isobj*: True if the value of the object is returned.

        *obj*: The value of the expression.

        If an exception is raised on the remote end, the traceback is logged,
        and the exception object is raised by this method.
        """
        return _HandledRemoteRunner(
            runnerterminal=self,
            description=cmd,
            template=self._ASSIGN_AND_RUN_TEMPLATE,
            timeout=timeout,
            handle=handle,
            cmd=cmd,
            handled_types=self._get_python_arg(self.HANDLED_TYPES)).run()

    def run_and_return_handled_python(self, handle):
        """Get handle object associated with *handle* from the remote end
        in case the handle object is in *HANDLED_TYPES*

        .. note::

            The *HANDLED_TYPES* instances must be serializable and
            deserializable by picklers and unpicklers.

        The return value of the remote call is returned as a python object with
        two attributes:

        *isobj*: True if the value of the object is returned.

        *obj*: The value of the expression.

        If an exception is raised on the remote end, the traceback is logged,
        and the exception object is raised by this method.
        """
        return _HandledRemoteRunner(
            runnerterminal=self,
            description=handle,
            template=self._RUN_AND_RETURN_HANDLED_TEMPLATE,
            handle=handle,
            handled_types=self._get_python_arg(self.HANDLED_TYPES)).run()

    def get_response(self, remotetimeout, timeout=None):
        with remotetimeouthandler(remotetimeout.response_wrap):
            return remotetimeout.response_wrap(self._get_response(
                remotetimeout, timeout))

    def _get_response(self, remotetimeout, timeout):
        return _TimeoutRemoteRunner(
            runnerterminal=self,
            template=self._GET_RESPONSE_TEMPLATE,
            description='Get response with id {}'.format(
                remotetimeout.response_id),
            timeout=timeout,
            response_id=remotetimeout.response_id).run()

    def get_response_or_raise(self, out, cmd):
        return self.__identity_or_raise(self._try_to_deserialize(out, cmd))

    def _try_to_deserialize(self, output, cmd):
        try:
            return self.__deserialize(output, cmd)
        except Exception as e:
            exc = RunnerTerminalSessionBroken(
                "Unexpected output in terminal ('{output}'): "
                "unable to deserialize "
                "when running command '{cmd}' ({cls}: {msg})".format(
                    output=output,
                    cmd=cmd,
                    cls=e.__class__.__name__,
                    msg=str(e)))
            LOGGER.info('RunnerTerminalSessionBroken: %s', exc)
            raise exc

    def __deserialize(self, output, cmd):
        LOGGER.debug("__deserialize(cmd=%s) - pickled output: '%s'", repr(cmd), output)
        out = self.__unpickle(output)
        return out

    def __unpickle(self, output):
        outputstream = BytesIO(output)
        out = self.UNPICKLER(outputstream).load() if output else None
        return out

    def __identity_or_raise(self, out):
        LOGGER.debug('__identity_or_raise: %s, type=%s', out, type(out))
        if out is None:
            raise RunnerTerminalSessionBroken('No output in terminal')
        steeringstring, pickled = out
        steeringstring = to_bytes(steeringstring)
        outobj = self.__try_to_unpickle(to_bytes(pickled), steeringstring)
        if steeringstring == b'exception':
            if hasattr(outobj, 'trace'):
                LOGGER.debug("Remote Traceback: \n%s", ''.join(outobj.trace))
            raise outobj
        if steeringstring == b'timeout':
            raise RemoteTimeout(response_id=outobj)

        return _RemoteReturnValue(steeringstring=steeringstring, obj=outobj)

    def __try_to_unpickle(self, output, steeringstring):
        try:
            out = self.__unpickle(output)
            LOGGER.debug('Unpickled output: %s', out)
            return out
        except Exception as e:
            raise RunnerTerminalUnableToDeserialize(
                '{steeringstring}: {output} ({cls}: {msg})'.format(
                    steeringstring=to_string(steeringstring),
                    output=repr(output),
                    cls=e.__class__.__name__,
                    msg=str(e)))

    def run_python_call(self, function_name, *args, **kwargs):
        """Calls a python function on the remote end.

        function_name: a string, describing what function to call.

        Any additional arguments given will be passed as arguments
        to the function on the remote end.

        The return value and any exceptions are handled as in
        :meth:`.run_python`.
        """
        return self.run_python_call_with_timeout(
            self.default_timeout,
            function_name,
            args=args,
            kwargs=kwargs)

    def run_python_call_with_timeout(self, timeout, function_name,
                                     args, kwargs):

        return self.run_python(self._get_python_call(function_name,
                                                     args, kwargs),
                               timeout=timeout)

    def import_libraries(self, *imports):
        """Import the libraries given as arguments on the remote end."""
        self.run("import {0}".format(', '.join(imports)))

    def get_proxy_object(self, remote_object, local_spec):
        """Creates a proxy object for remote_object.

        **Args:**

        *remote_object*:  the name of the remote object to proxy.

        *local_spec*: a local class object, used to determine which methods
                      are available on the remote object. If None, the spec
                      is determined dynamically.

        Any method calls and attribute requests for the proxy object
        will be executed remotely on remote_object.

        Calling as_recursive_proxy on the proxy object creates a new
        :class:`.remoteproxies._RecursiveProxy` for the proxied object.

        Example:

            >>> RunnerSession.run_python("a = open('test')")
            >>> proxy = RunnerTerminal.get_proxy_object('a', file)
            >>> proxy.readlines() # same as run_python("a.readlines()")
        """
        return _RemoteProxy(self,
                            remote_object,
                            local_spec,
                            is_remote_owned=False)

    def get_proxy_object_from_call(self, function_name, *args, **kwargs):
        """Calls a remote function, and proxies the return value.

        The call is done as in :meth:`.run_python`, but the return value
        is a :class:`.remoteproxies._RemoteProxy` for the remote return value.
        """
        handle = self._get_random_handle_name()

        python_call = self._get_python_call(function_name, args, kwargs)

        self.run_python("{handle} = {call}".format(handle=handle,
                                                   call=python_call))

        return _RemoteProxy(self, handle)

    def get_proxy_or_basic_from_call(self, function_name, *args, **kwargs):
        """Calls a remote function, and proxies the return value.

        The call is done as in :meth:`.run_python`, but the return value is a
        :class:`.remoteproxies._RemoteProxy` for the remote return value in
        case of complex types. But in case the return value is of type *int*,
        *float* or is a string or *None* then the local copy is created and
        returned.
        """

        return self.get_proxy_or_basic_from_call_with_timeout(
            self.default_timeout,
            function_name,
            args=args,
            kwargs=kwargs)

    def get_proxy_or_basic_from_call_with_timeout(
            self, timeout, function_name, args, kwargs):
        handle = self._get_random_handle_name()

        python_call = self._get_python_call(function_name, args, kwargs)

        with remotetimeouthandler(lambda response: self._get_proxy_or_basic(
                handle, response)):  # pylint: disable=bad-continuation
            return self._get_proxy_or_basic(handle,
                                            self.assign_and_run_python(
                                                handle, python_call,
                                                timeout=timeout))

    def _get_proxy_or_basic(self, handle, response):
        return response.obj if response.isobj else _RemoteProxy(self, handle)

    def _get_random_handle_name(self):
        return self._get_handle_for_name(self._get_random_name())

    @staticmethod
    def _get_handle_for_name(name):
        return "runnerhandlerns['_PROXY_CONTAINER.handle_{name}']".format(
            name=name)

    @staticmethod
    def _get_random_name():
        return str(uuid.uuid4().hex)

    def get_recursive_proxy(self, remote_object):
        """Creates a recursive proxy object for remote_object.

        **Args:**

        *remote_object*:  the name of the remote object to proxy.

        Any attributes, methods and return values produced by a
        recursive proxy will be recursive proxy objects wrapping
        that value. The proxied object can be retrieved by calling
        :meth:`.remoteproxies._RemoteProxy.as_local_value` on a remote proxy
        object. For more details, see :class:`.remoteproxies._RecursiveProxy`.
        """
        return _RecursiveProxy(self,
                               remote_object,
                               is_remote_owned=False)

    @staticmethod
    def serialize(content):
        return pickle.dumps(content, protocol=0)

    @staticmethod
    def isproxy(obj):
        """Returns *True* if *obj* is a remote proxy, else *False*."""
        return isinstance(obj, _RemoteProxy)

    def iscallable(self, remote_object):
        """Determines whether *remote_object* is callable or not."""
        return self.run_python("callable({0})".format(remote_object))

    def close(self):
        """Close the terminal session.

        Removes any handler modules from the remote end if necessary,
        and restores the terminal to the original state.
        """
        # subclass callback:
        if self.session is not None:
            self._close()
            self.close_session()

    def _get_python_call(self, function_name, args, kwargs):
        """Generates the code for a function call on the remote end."""
        LOGGER.debug("preparing call - %s(*%s, **%s)",
                     function_name, args, kwargs)

        arg_list = [self._get_python_arg(arg) for arg in args]
        for name, arg in iteritems(kwargs):
            arg_list.append("{0}={1}".format(name, self._get_python_arg(arg)))

        return "{fn}({args})".format(
            fn=function_name, args=', '.join(arg_list))

    def _get_python_arg(self, arg):
        """Handle serialization and possible proxy values in arguments.

        If *arg* is a :class:`remoteproxies._RemoteProxy` or
        :class:`.remoteproxies._RecursiveProxy` instance, the handle is
        returned, otherwise the argument is returned serialized and wrapped in
        a deserialize-call.

        Used mainly for :meth:`.run_python_call`.
        """
        if self.isproxy(arg):
            return arg.get_proxy_handle()
        return self._DESERIALIZE_TEMPLATE.format(
            obj=self.serialize(arg), unpickler=self.TARGET_UNPICKLER)

    def __setup_handler_module(self, handler_source):
        """Setup a remote module to target node.

        The path from where the module is retrieved is given as
        *handler_source*.
        """
        handler_content = self.__get_content(handler_source)
        self.__exec_handler_content_in_remote(handler_content)
        self.__initialize_runnerhandler()

    @staticmethod
    def __get_content(source_path):
        with open(source_path, 'r') as _f:
            return _f.read()

    def __exec_handler_content_in_remote(self, handler_content):
        self.run("_handlercode = compile({handler_content}, "
                 "'RunnerHandler', 'exec')".format(
                     handler_content=(
                         "pickle.loads({b}{dumps!r})".format(
                             b='' if PY3 else 'b',
                             dumps=pickle.dumps(
                                 handler_content, protocol=0)))))
        self.run('runnerhandlerns = {}')
        self.run("exec(_handlercode, runnerhandlerns)")

    def __initialize_runnerhandler(self):
        self.run(self._RUNNERCALL.format(
            method='initialize',
            args=(
                'contextmgr={contextmgr},'
                ' pickler={pickler},'
                ' handled_types={handled_types}'.format(
                    contextmgr=self.TARGET_CONTEXTMANAGER,
                    pickler=self.TARGET_PICKLER,
                    handled_types=self._get_python_arg(self.HANDLED_TYPES)))))

    def create_empty_recursive_proxy(self):
        """Creates :class:`.remoteproxies._RecursiveProxy` without handle or
        any other content.  This proxy cannot be used but the content of it
        should be changed by calling
        :meth:`.remoteproxies._RemoteProxy.set_from_remote_proxy`.
        """
        return _RecursiveProxy(session=self,
                               remote_name=None,
                               is_remote_owned=False)

    def create_empty_remote_proxy(self):
        """Creates empty :class:`.remoteproxies._RemoteProxy`. See
        :meth:`.create_empty_recursive_proxy`.
        """
        return _RemoteProxy(session=self,
                            remote_name=None,
                            is_remote_owned=False)
