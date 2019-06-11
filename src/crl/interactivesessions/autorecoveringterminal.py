"""This module implements pseudo terminal based autorecovering terminal.
"""
# pylint: disable=too-many-arguments
import time
import logging
import traceback
import sys
from contextlib import contextmanager
from crl.interactivesessions.InteractiveSession import (
    InteractiveSession)
from crl.interactivesessions.runnerexceptions import (
    SessionInitializationFailed)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class AutoRecoveringTerminal(object):
    """Automatically recovering terminal in case of listed exception occurs in
    :meth:`.run` or in :meth:`.initialize`.

    For running commands in the terminal of SSH host *example.com* just use:

        >>> from crl.interactivesessions import (
        ...     AutorecoveringTerminal)
        >>> from crl.interactivesessions import (
        ...     SshShell)
        >>> term = AutoRecoveringTerminal()
        >>> term.initialize(SshShell(
        ...     'example.com', 'username', 'password'))
        >>> term.run('echo hello world!')
    """

    def __init__(self):
        self._shells = None
        self._broken_exceptions = None
        self._init_broken_exceptions = None
        self._session = None
        self._max_tries = None
        self._sleep_between_tries = None
        self._prepare = None
        self._finalize = None
        self._verify = None
        self._in_verify = False

    def initialize(self,
                   shells,
                   broken_exceptions=Exception,
                   init_broken_exceptions=Exception,
                   sleep_between_tries=3,
                   max_tries=3,
                   prepare=lambda: None,
                   finalize=lambda: None,
                   verify=lambda: None):
        """
        Initialize terminal topology information.

        .. note::

            This method does not open the connections. The connections
            are opened by :meth:`.initialize_terminal`. It is up to
            the use-case when to open the connection and thus connection
            opening is purposly separated from the topology setting.

            The connection opening can be also left to :meth:`.retry_run`.
            It opens the connection in the first call. In this fashion
            the connection opening is not done without a real reason.

        Args:
            *shells* (Shell or list of Shells): List of objects derived from
            :class:`.InteractiveSession.Shell` which defines the desired
            state of the terminal.

            *broken_exceptions* (Exception class or list of Exception classes):
            The exceptions which determines the broken session. If any of these
            exceptions occurs, the session is automatically recovered.
            By default, the occurence of any exception triggers the recovery
            process.

            *init_broken_exceptions* (Eception class or list of exceptions):
            The exceptions which determines the broken session during init.  By
            default all the exceptions are in this category.

            *sleep_between_tries* (int): seconds to sleep between tries if the
            exception marking broken session/connection occurs.

            *max_tries* (positive int): maximum number of tries for
            initialization or for run. If *max_tries* is 1, then initialization
            or run is tried only once even if the connection is broken.

            *prepare* (callable): function to be called once initialization
            of the shell stack is ready.

            *finalize* (callable): function to be called prior the terminal
            close.
            *verify* (callable): function to be called from :meth:`.auto_setup`
            for verifying session. Must raise an exception in
            *broken_exceptions* in case the session is broken.
        """
        self._set_shells(shells)
        self.set_broken_exceptions(broken_exceptions)
        self._set_init_broken_exceptions(init_broken_exceptions)
        self._sleep_between_tries = sleep_between_tries
        self._max_tries = max_tries
        self.set_prepare(prepare)
        self.set_finalize(finalize)
        self.set_verify(verify)

    def _set_shells(self, shells):
        self._shells = (shells
                        if isinstance(shells, list) else
                        [shells])

    def set_broken_exceptions(self, broken_exceptions):
        self._broken_exceptions = (tuple(broken_exceptions)
                                   if isinstance(broken_exceptions, list) else
                                   broken_exceptions)

    def _set_init_broken_exceptions(self, init_broken_exceptions):
        self._init_broken_exceptions = (
            tuple(init_broken_exceptions)
            if isinstance(init_broken_exceptions, list) else
            init_broken_exceptions)

    def set_prepare(self, prepare):
        self._prepare = prepare

    def set_finalize(self, finalize):
        self._finalize = finalize

    def set_verify(self, verify):
        """Set verify callable. If *verify* raises any *broken_exceptions*, the
        old session will be closed and the new session will be prepared in
        :meth:`.initialize_if_needed`.
        """
        self._verify = verify

    def initialize_terminal(self):
        """ Initialize terminal connections."""
        self._retry(self._initialize_terminal,
                    broken_exceptions=self._init_broken_exceptions)

    def _initialize_terminal(self):
        self._init_session()
        self._session.spawn(self._shells[0])
        for shell in self._shells[1:]:
            self._session.push(shell)
        self._prepare()

    def _retry(self, function, broken_exceptions):
        for _ in range(self._max_tries):
            try:
                return function()
            except broken_exceptions as e:
                exc = e
                LOGGER.debug('%s: %s\nBacktrace: \n%s',
                             e.__class__.__name__, e,
                             ''.join(traceback.format_list(
                                 traceback.extract_tb(sys.exc_info()[2]))))
                time.sleep(self._sleep_between_tries)

        raise SessionInitializationFailed(exc)

    def _init_session(self):
        self.close()
        self._session = InteractiveSession()

    def get_session(self):
        return self._session

    @contextmanager
    def auto_close(self):
        try:
            yield None
        except self._broken_exceptions:
            self.close()
            raise

    def initialize_if_needed(self):
        """Initialize the session in case *verify* fails or if the terminal is
        not initialized already.
        """
        if self._session is None:
            self.initialize_terminal()
        else:
            self._recover_if_needed()

    def _recover_if_needed(self):
        try:
            self._verify_only_once()
        except self._broken_exceptions:
            self.close()
            self.initialize_terminal()

    def _verify_only_once(self):
        if not self._in_verify:
            self._in_verify = True
            try:
                self._verify()
            finally:
                self._in_verify = False

    def close(self):
        """Close terminal.

        .. note::

            Please remember to call :meth:`.initialize_terminal` after
            :meth:`.close`. in order to make the object usable again.
        """
        if self._session is not None:
            try:
                self._try_to_finalize()
                self._session.close_terminal()
            except Exception as e:  # pylint: disable=broad-except
                LOGGER.info('Failed to close terminal: %s', e)
            self._session = None

    def _try_to_finalize(self):
        try:
            self._finalize()
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.info('Failed to finalize the terminal: %s', e)
