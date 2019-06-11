from contextlib import contextmanager


__copyright__ = 'Copyright (C) 2019, Nokia'


class RunnerException(Exception):
    pass


class RunnerTerminalSessionClosed(RunnerException):
    """Internal exception raised by :class:`.RunnerTerminal` in case
    :meth:`.RunnerTerminal.run_python` is called while the
    :meth:`.RunnerTerminal.close` is already called or alternatively if the
    session is not initialized.
    """


class RunnerTerminalSessionBroken(RunnerException):
    """Exception raised in case the :meth:`.RunnerTerminal.run` raises
    an exception. The original exception is embedded into the first
    argument of the new exception.
    """


class RunnerTerminalUnableToDeserialize(RunnerException):
    """Exception raised in case remote object returned is not
    deserialiazable by the local deserialization methods.
    """


class RemoteTimeout(RunnerException):
    """Exception raised in case remote timeout occurs.

    **Args:**

    *response_id*: The response id to be used in
    :meth:`.remoteproxies._RemoteProxy.get_remote_proxy_response`
    call for retrieving the response later. The

    *response_wrap(callable)*: is called with the response and the return value
    of *response_wrap* is returned back to the
    :meth:`.remoteproxies._RemoteProxy.get_remote_proxy_response`.
    """
    def __init__(self, response_id):
        super(RemoteTimeout, self).__init__(response_id)
        self.response_id = response_id
        self.response_wrap = lambda response: response

    def add_response_wrap(self, response_wrap):
        orig_response_wrap = self.response_wrap
        self.response_wrap = lambda response: response_wrap(
            orig_response_wrap(response))

    def __str__(self):
        return 'Remote response not got yet from response {}'.format(
            self.response_id)


@contextmanager
def remotetimeouthandler(response_wrap):
    try:
        yield None

    except RemoteTimeout as e:
        e.add_response_wrap(response_wrap)
        raise


def responsehandler(function,
                    response_wrap=lambda x: x):
    with remotetimeouthandler(response_wrap):
        return response_wrap(function())


def asyncresponsehandler(function,
                         response_wrap=lambda x: x):
    try:
        responsehandler(function, response_wrap)
    except RemoteTimeout as e:
        return e


class InvalidProxySession(RunnerException):
    """This exception is raised by :class:`.remoteproxies._RemoteProxy` methods
    in case the session identifier has been changed. This occurs for example in
    case the session is recovered but the proxy is not recovered.
    """


class SessionInitializationFailed(RunnerException):
    """ This exception is raised by
    :class:`.autorecoveringterminal.AutoRecoveringTerminal`
    when the initialization of the terminal fails during
    :meth:`.autorecoveringterminal.AutoRecoveringTerminal.initialize_terminal`.
    The original exception is stored into the first argument of the
    exception.
    """
