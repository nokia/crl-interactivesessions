# pylint: disable=arguments-differ
import logging
from contextlib import contextmanager
from crl.interactivesessions.autorecoveringterminal import (
    AutoRecoveringTerminal)
from crl.interactivesessions.runnerterminal import (
    RunnerTerminal, RunnerTerminalSessionBroken, RunnerTerminalSessionClosed)
from crl.interactivesessions._runnerterminalloglevel import (
    _QuietRunnerTerminalLogLevel)
from .shells.shellstack import ShellStack


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class AutoRunnerTerminal(RunnerTerminal):
    """*Python* terminal session wrapper with the automated recovery feature
    for the session. This wrapper expects that the session is an instance of
    :class:`.autorecoveringterminal.AutoRecoveringTerminal`.
    """
    default_verification_timeout = 10

    def __init__(self):
        super(AutoRunnerTerminal, self).__init__()
        self.prepare = None
        self.finalize = None
        self._verify_proxy = None

    def initialize_with_shelldicts(self,
                                   shelldicts,
                                   prepare=lambda: None,
                                   finalize=lambda: None):
        """This method initializes the terminal in the same fashion than
        :meth:`initialize_with_shells` but instead of *shells* the dictionary
        of shells accepted by :meth:`.shells.shellstack.ShellStack.initialize`
        has to be to be given.
        """

        ss = ShellStack()
        ss.initialize(shelldicts=shelldicts)
        self.initialize_with_shells(ss.shells,
                                    prepare=prepare,
                                    finalize=finalize)

    def initialize_with_shells(self, shells,
                               prepare=lambda: None, finalize=lambda: None):
        """
        Initialize the terminal with the :class:`.InteractiveSession.Shell`
        based *shells* stack or a single shell.

        .. note::
            The terminal session is not opened by this call. Either
            call :meth:`initialize_if_needed` directly or
            use initially empty proxies. The empty proxies
            can be created via methods
            :meth:`.runnerterminal.RunnerTerminal.create_empty_remote_proxy`
            and
            :meth:`.runnerterminal.RunnerTerminal.create_empty_recursive_proxy`

        The *prepare* callable should import any required modules and set the
        proxies. If the empty proxies are used in the initial setup then use
        :meth:`remoteproxies._RemoteProxy.set_from_remote_proxy` to replace the
        content.

        The *finalize* callable should do any special finalization
        of the proxies which are set in *prepare*. For example, if the
        proxy is managing a temporary file in the remote end, that could
        be removed in the *finalize*.

        .. note::

            Proxies are automatically invalidated after finalization
            without any need to do special operations in *finalize* method.
            After finalization :class:`.runnerexceptions.InvalidProxySession`
            will be raised in case the remote object is accessed via proxies.

            The session is not guaranteed to be open when the *finalize*
            is called. That is why all possible exceptions are only
            logged.
        """
        session = AutoRecoveringTerminal()
        session.initialize(shells=shells)
        self.initialize(session, prepare=prepare, finalize=finalize)

    def initialize(self, session,
                   prepare=lambda: None, finalize=lambda: None):
        """This method initializes the terminal in the same fashion than
        :meth:`initialize_with_shells` but instead of *shells* the underlying
        :class:.autorecoveringterminal.AutoRecoveringTerminal` instance should
        be given as a *session*.

        .. note::

            The
            :meth:`.autorecoveringterminal.AutoRecoveringTerminal.set_verify`
            must be called after this method as the *verify* is overridden by
            the default *verify*.
        """
        self.session = session
        self.prepare = prepare
        self.finalize = finalize
        self._set_session_callbacks()

    def _set_session_callbacks(self):
        self.session.set_prepare(self.setup_session)
        self.session.set_finalize(self._close_in_auto_close)
        self.session.set_broken_exceptions(RunnerTerminalSessionBroken)
        self.session.set_verify(self._verify)

    def _setup(self):
        self._verify_proxy = self.get_proxy_object('None', None)
        self._verify_proxy.set_remote_proxy_timeout(
            self.default_verification_timeout)
        self.prepare()

    @_QuietRunnerTerminalLogLevel(logging.INFO)
    def _verify(self):
        if self._verify_proxy is None:
            raise RunnerTerminalSessionBroken()

        self._verify_proxy.as_local_value()

    def initialize_if_needed(self):
        """Initialize the terminal if necessary."""
        if self.session is None:
            raise RunnerTerminalSessionClosed()
        self.session.initialize_if_needed()

    @contextmanager
    def error_handling(self):
        if self.session is None:
            with super(AutoRunnerTerminal, self).error_handling():
                yield None
        else:
            with self.session.auto_close():
                yield None

    def _close(self):
        self.finalize()

    def _close_in_auto_close(self):
        try:
            self._close()
        finally:
            self._initialized_session = None
            self._session_id = None
