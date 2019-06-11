import logging
from functools import wraps
from crl.interactivesessions.runnerexceptions import (
    responsehandler, asyncresponsehandler, InvalidProxySession)


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


def autoinitialize(f):

    @wraps(f)
    def inner_function(proxy, *args, **kwargs):
        proxy.remote_proxy_autoprepare()
        return f(proxy, *args, **kwargs)

    return inner_function


def verify(f):

    @wraps(f)
    def inner_function(proxy, *args, **kwargs):
        proxy.remote_proxy_verify()
        return f(proxy, *args, **kwargs)

    return inner_function


class _RemoteProxy(object):
    """Wrapper exposing a remote object as a local one.

    Any attribute requests/assignments and method calls are
    transparently done on a remote object.

    A new proxy object for *remote_name* is created.

    **Args:**

    *session*:  a :class:`.runnerterminal.RunnerTerminal` instance.

    *remote_name*: The name of the remote object to proxy.

    *local_spec*: a local class object, used to determine which methods are
    available on the remote object. If None, the available methods are
    determined dynamically.

    *parent*: a reference to parent proxy object of this proxy.

    *is_remote_owned*:  If *True*, then remote object is deleted as well when
    the proxy is removed from the *Python* interpreter.

    """

    _SETATTR_TEMPLATE = "{handle}.{name} = RunnerHandler._deserialize({val!r})"
    _SETATTR_PROXY_TEMPLATE = "{handle}.{name} = {proxy}"

    def __init__(self, session, remote_name, local_spec=None,
                 parent=None, is_remote_owned=True):

        self.__dict__['_session'] = session
        self.__dict__['_handle'] = remote_name
        self.__dict__['_spec'] = None
        self.__dict__['__parent'] = parent
        self.__dict__['_is_remote_owned'] = is_remote_owned
        self.__dict__['_remote_proxy_default_timeout'] = 3600
        self.__dict__['_remote_proxy_session_id'] = (
            self._get_remote_proxy_session_id_from_remote_name(session,
                                                               remote_name))

        if local_spec:
            self.set_proxy_spec(local_spec)

        self._set_remote_proxy_timeout_from_parent()
        self.remote_proxy_use_synchronous_response()

    @staticmethod
    def _get_remote_proxy_session_id_from_remote_name(session,
                                                      remote_name):
        if remote_name is None:
            return None
        if session.session_id is None:
            return 'uninitialized'
        return session.session_id

    def set_from_remote_proxy(self, proxy):
        """Set proxy content from *proxy*.

        .. warning::

            This method nulifies the *proxy* given as an argument. The
            reasoning is that it would be really dangerous to keep two proxies
            with the same handles simultaneously.
            The :class:`.runnerexceptions.InvalidProxySession` is raised when
            *proxy* is accessed after this call.
        """
        proxy_dict = proxy.get_remote_proxy_dict()
        for n in ['_session',
                  '_handle',
                  '_spec',
                  '__parent',
                  '_is_remote_owned',
                  '_remote_proxy_session_id',
                  '_remote_proxy_response']:
            try:
                self.set_remote_proxy_dict_name(n, proxy_dict[n])
            except KeyError:
                pass
        proxy.set_remote_proxy_dict_name('is_remote_owned', False)
        proxy.set_remote_proxy_dict_name('_handle', None)

    def get_remote_proxy_dict(self):
        return self.__dict__

    def set_remote_proxy_dict_name(self, name, value):
        self.__dict__[name] = value

    @autoinitialize
    def as_local_value(self):
        """Returns a local copy of the proxied object."""
        return self._session.run_python(
            self._handle,
            timeout=self._get_remote_proxy_timeout())

    @autoinitialize
    def as_recursive_proxy(self):
        """Returns a :class:`._RecursiveProxy` for the proxied object."""
        return _RecursiveProxy(self._session, self._handle, parent=self)

    @autoinitialize
    def get_proxy_handle(self):
        """Returns the remote name for the proxied object."""
        return self._handle

    def remote_proxy_autoprepare(self):
        """Initialize the proxy session."""
        self._session.initialize_if_needed()
        self.remote_proxy_verify()

    def remote_proxy_verify(self):
        proxy_id_not_session = self._remote_proxy_session_id != self._session.session_id
        if (self._remote_proxy_session_id != 'uninitialized' and (
                self._remote_proxy_session_id is None or proxy_id_not_session)):
            raise InvalidProxySession(
                'Local session_id: {lid}, '
                'remote session_id: {rid}'.format(
                    lid=self._remote_proxy_session_id,
                    rid=self._session.session_id))

    def set_proxy_spec(self, local_spec):
        """Assigns a spec for this proxy object."""
        if self.__dict__['_spec']:
            raise RuntimeError("")  # FIXME

        self.__dict__['_spec'] = local_spec
        for method in self.__get_methods(local_spec):
            self.__add_remote_method(method)

    @verify
    def get_remote_proxy_response(self, remotetimeout, timeout=None):
        """Get remote respose when the call have been timed out.  Blocks
        forever if no *timeout* in seconds is  given. The *remotetimeout*
        is a handle which must be an instance of
        the exception :class:`.runnerexceptions.RemoteTimeout`.
        """
        return self._session.get_response(remotetimeout, timeout)

    def _set_remote_proxy_timeout_from_parent(self):
        parent = self.__dict__['__parent']
        self.set_remote_proxy_timeout(
            self._get_remote_proxy_default_timeout()
            if parent is None else
            parent._remote_proxy_timeout)  # pylint: disable=protected-access

    def set_remote_proxy_timeout(self, timeout):
        """Set timeout for remote command execution. The negative *timeout*
        causes proxy to raise always :class:`.runnerexceptions.RemoteTimeout`.
        If *None* is set as *timeout* value, then the default timeout is used.
        The default timeout is 3600 seconds.

        .. note::

            The *prompt_timeout* of
            :class:`.runnerterminal.RunnerTerminal` is added automatically
            to *timeout* in case *timeout* is positive. If *timeout* is
            negative then the terminal uses *prompt_timeout* only.
        """
        self.__dict__['_remote_proxy_timeout'] = (
            self._get_remote_proxy_default_timeout()
            if timeout is None else timeout)

    def _get_remote_proxy_default_timeout(self):
        return self.__dict__['_remote_proxy_default_timeout']

    def _get_remote_proxy_timeout(self):
        return (-1
                if self._remote_proxy_response is asyncresponsehandler else
                self._remote_proxy_timeout)

    def remote_proxy_use_synchronous_response(self):
        """Set proxy to use synchronous response and timeout"""
        self._set_remote_proxy_response(responsehandler)

    def remote_proxy_use_asynchronous_response(self):
        """Set proxy to use asynchronous response without any timeout. In this
        mode, the proxy returns handle (
        :class:`.runnerexceptions.RemoteTimeout` instance) which then should be
        passed to :meth:`.get_remote_proxy_response` to retrieve the actual
        value of the proxy call. Please see a complete example of
        the asynchronous mode usage from :ref:`backgroundrunner`.
        """
        self._set_remote_proxy_response(asyncresponsehandler)

    def _set_remote_proxy_response(self, response):
        self.__dict__['_remote_proxy_response'] = response

    @autoinitialize
    def __getattr__(self, name):
        # we use __setattr__, so manually check __dict__
        if name in self.__dict__:
            return self.__dict__[name]

        handle = self.__attr_handle(name)

        # if spec is dynamic, add callables to spec
        if not self._spec and self._session.iscallable(handle):
            self.__add_remote_method(name)
            return self.__dict__[name]

        return self._session.run_python(
            handle,
            timeout=self._get_remote_proxy_timeout())

    @autoinitialize
    def __setattr__(self, name, val):
        self.__call_remote_method('setattr', args=(self, name, val),
                                  kwargs={})

    @autoinitialize
    def __call__(self, *args, **kwargs):
        return self.__call_remote_method(self._handle, args=args,
                                         kwargs=kwargs)

    def __del__(self):
        """Add remote references to dynamic proxy objects to remote garbage
        collection.

        This is done to prevent leaking references on the remote end.
        """
        if self._is_remote_owned:
            self._session.add_handle_to_garbage(session_id=self._remote_proxy_session_id,
                                                handle=self._handle)

    @autoinitialize
    def __getitem__(self, key):
        return self.__call_remote_method(
            '{handle}.__getitem__'.format(handle=self._handle),
            args=[key],
            kwargs={})

    @autoinitialize
    def __setitem__(self, key, value):
        return self.__call_remote_method(
            '{handle}.__setitem__'.format(handle=self._handle),
            args=[key, value],
            kwargs={})

    def __add_remote_method(self, method_name):
        self.__dict__[method_name] = self.__build_wrapper(method_name)

    def __call_remote_method(self, callable_, args, kwargs):
        return self._remote_proxy_run_python_call(callable_, args, kwargs)

    def _remote_proxy_run_python_call(self, function, args, kwargs):
        return self._remote_proxy_response(
            lambda: self._session.run_python_call_with_timeout(
                self._get_remote_proxy_timeout(), function,
                args=args, kwargs=kwargs))

    def __build_wrapper(self, method_name):
        def wrap(*args, **kwargs):
            return self.__call_remote_method(
                '.'.join([self._handle, method_name]),
                args, kwargs)
        return wrap

    def __attr_handle(self, name):
        return '.'.join([self._handle, name])

    @staticmethod
    def __get_methods(obj):
        for name in dir(obj):
            if callable(getattr(obj, name)):
                yield name


class _RecursiveProxy(_RemoteProxy):
    """Wrapper exposing a remote object as a local one.

    Any attributes, methods and return values produced by a recursive proxy
    will be recursive proxy objects wrapping that value. The exceptions are the
    basic types which are defined in :class:`.runnerterminal.RunnerTerminal` in
    *HANDLED_TYPES* attribute. The *HANDLED_TYPES* are returned as local
    value always. The proxied object can be retrieved by calling
    :meth:`._RemoteProxy.as_local_value` on a remote proxy object.
    """
    def __init__(self, session, remote_name,
                 parent=None, is_remote_owned=None):
        super(_RecursiveProxy, self).__init__(session,
                                              remote_name,
                                              parent=parent,
                                              is_remote_owned=is_remote_owned)

    @autoinitialize
    def __iter__(self):
        return self.__get_recursive_proxy_or_basic_from_call(
            '.'.join([self._handle, '__iter__']), args=(), kwargs={})

    def __get_recursive_proxy_or_basic_from_call(self,
                                                 handle,
                                                 args, kwargs):
        return self._remote_proxy_response(
            function=lambda: (
                self._session.get_proxy_or_basic_from_call_with_timeout(
                    self._get_remote_proxy_timeout(),
                    handle, args=args, kwargs=kwargs)),
            response_wrap=self.__get_recursive_proxy_from_response)

    @staticmethod
    def __get_recursive_proxy_from_response(response):
        if isinstance(response, _RemoteProxy):
            response = response.as_recursive_proxy()
        return response

    @verify
    def next(self):
        return self.__get_recursive_proxy_or_basic_from_call(
            'next', args=(self,), kwargs={})

    __next__ = next

    @autoinitialize
    def __str__(self):
        return self._remote_proxy_run_python_call(
            '.'.join([self._handle, '__str__']), args=(), kwargs={})

    @autoinitialize
    def __getattr__(self, name):
        if not self._session.run_python(
                "hasattr({0}, {1!r})".format(self._handle, name),
                timeout=self._get_remote_proxy_timeout()):
            raise AttributeError("'{0}' has no attribute '{1}'".format(
                self._handle, name))
        remotename = '.'.join([self._handle, name])
        return self._remote_proxy_response(
            function=lambda: self._session.run_and_return_handled_python(
                remotename),
            response_wrap=(
                lambda response: self.__get_recursive_proxy_for_remotename(
                    response, remotename)))

    def __get_recursive_proxy_for_remotename(self, response, remotename):
        return response.obj if response.isobj else _RecursiveProxy(
            self._session,
            remotename,
            parent=self)

    @autoinitialize
    def __call__(self, *args, **kwargs):
        return self.__get_recursive_proxy_or_basic_from_call(self._handle,
                                                             args, kwargs)
