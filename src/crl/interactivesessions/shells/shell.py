import re
import logging
import abc
from contextlib import contextmanager
import six
import pexpect
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .remotemodules.compatibility import to_string


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)
_LOGLEVEL = 7  # less than DEBUG


class TimeoutError(InteractiveSessionError):
    """Raised when remote command execution times out."""
    def __init__(self, output):
        super(TimeoutError, self).__init__(output)
        self.output = output.encode('ascii', 'xmlcharrefreplace')
        self.message = "TIMEOUT, console log:\n{0}".format(self.output)

    def __str__(self):
        return self.message


class DefaultStatusTimeout(object):
    _orig = 5
    _timeout = _orig

    @classmethod
    def __float__(cls):
        return float(cls._timeout)

    @classmethod
    def __repr__(cls):
        return repr(cls.get())

    @classmethod
    def get(cls):
        return cls._timeout

    @classmethod
    def set(cls, timeout):
        LOGGER.info('Set timeout for reading status code to %s seconds', timeout)
        cls._timeout = timeout

    @classmethod
    def reset(cls):
        LOGGER.info('Reset timeout for reading status code to %s seconds', cls._orig)
        cls._timeout = cls._orig


DEFAULT_STATUS_TIMEOUT = DefaultStatusTimeout()


@six.add_metaclass(abc.ABCMeta)
class Shell(object):
    """This is the basic interface that any new shell should implement."""
    def __init__(self, tty_echo=False):
        self._terminal = None
        self._prompt = None
        self._tty_echo = tty_echo

    def set_terminal(self, terminal):
        self._terminal = terminal

    @property
    def tty_echo(self):
        return self._tty_echo

    def set_tty_echo(self, tty_echo):
        self._tty_echo = tty_echo

    @property
    def delaybeforesend(self):
        return self._terminal.delaybeforesend

    @delaybeforesend.setter
    def delaybeforesend(self, delaybeforesend):
        self._terminal.delaybeforesend = delaybeforesend

    @abc.abstractmethod
    def get_start_cmd(self):
        """Return the command to be run in order to start this shell.

        This method will be called by InteractiveSession.spawn() and
        InteractiveSession.push().
        """

    @abc.abstractmethod
    def start(self):
        """Initialize the new shell.

        This method will be called after running the command provided by
        get_start_cmd() and provides ability for the new shell
        to initialize itself.
        """

    @abc.abstractmethod
    def exit(self):
        """Close this shell."""

    def get_prompt_from_terminal(self, empty_command="", timeout=-1):
        """
        Send terminal an empty command which should cause
        terminal to send back the prompt. First, expected prompt is
        waited for timeout. If succesful, the expected prompt is returned
        but if timeout occurs, then output read so far
        is returned.
        """
        terminal_prompt = self._get_prompt_from_terminal(empty_command,
                                                         timeout=timeout)
        if terminal_prompt == '':
            self._send_interrupt()
            terminal_prompt = self._get_prompt_from_terminal(empty_command,
                                                             timeout=timeout)
        return terminal_prompt

    def _get_prompt_from_terminal(self, empty_command="", timeout=-1):
        terminal_prompt = None
        self._read_until_end()
        self._send_input_line(empty_command)
        try:
            self._read_until_prompt(timeout=timeout)
            terminal_prompt = self._terminal.after.decode('utf-8')
        except TimeoutError:
            terminal_prompt = self._terminal.before.decode('utf-8')
        return terminal_prompt

    def is_terminal_hung(self, empty_command="", timeout=-1):
        is_hung = False
        self._send_input_line(empty_command)
        try:
            self._read_until_prompt(timeout=timeout)
        except TimeoutError:
            is_hung = True
        return is_hung

    def is_terminal_prompt_matching(self,
                                    terminal_prompt):
        """
        Return True if and only if prompt is matching with the terminal output.

        Args:

            terminal_prompt(str): expected terminal prompt
        """
        if isinstance(self.get_prompt(), six.string_types):
            return terminal_prompt == self.get_prompt()
        return terminal_prompt in self.get_prompt()

    def exec_command(self, cmd, timeout=-1):
        """Execute a command and return and text printed to the terminal.

        Args:
            cmd: string containing the command to be executed

            timeout: how many seconds to wait for command completion

        Returns:
            The terminal output of the command execution.
        """
        self._read_until_end(
            chunk_timeout=0)  # default:  timeout=0, chunk_timeout=0.1

        self._exec_cmd(cmd)
        output = self._read_until_prompt(timeout)

        return output

    def exec_command_expecting_more(self, cmd, more_prompt="--More--"):
        """
        This method is a variation of :meth:`exec_command` that can be used
        when the command generates paged output. The method returns a tuple
        *(more_counter, output)*, where more_counter is an integer representing
        the number of occurences of the more_prompt and output contains any
        text directed to the terminal (including *more_prompt*).
        """
        self._exec_cmd(cmd)

        output = ""
        more_counter = 0

        while self._terminal.expect_exact(
                [more_prompt, self.get_prompt()]) != 1:
            more_counter += 1
            output += self._terminal.before.decode("utf-8")
            self._send_input(" ")
        output += self._terminal.before.decode("utf-8")

        return (more_counter, output)

    def exec_prompting_command(self, cmd, responses, timeout=-1):
        """Execute a command that prompts for additional input.

        responses should be a list of tuples, each tuple specifying the
        prompt(s) expected, and the response to be sent.

        Args:
            cmd(str): Command to be executed.

            responses(list of tuples): Expected prompts.

            timeout(number): Timeout for receiving each prompt.

        Returns:
            Terminal output.
        """
        self._exec_cmd(cmd)

        output = ""
        for (msg, rsp) in responses:
            output += self._read_until(msg, timeout)
            LOGGER.log(_LOGLEVEL,
                       "Received prompt '%s', sending response '%s'",
                       msg, rsp)
            self._terminal.sendline(rsp)

        output += self._read_until_prompt(timeout)

        return output

    @staticmethod
    def create_responses_list(*args):
        if len(args) % 2 != 0:
            raise ValueError(
                "Responses list must have exactly one reponse per prompt")

        return zip(args[0::2], args[1::2])

    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        """Abstract method.
        Implementation must return the status of the last command executed.

        Returned value should be an integer indicating success/failure of the
        last command executed.

        The default timeout *DEFAULT_STATUS_TIMEOUT* is globally adjustable:

        >>> from crl.interactivesessions.shells.shell import (
        ...     DefaultStatusTimeout,
        ...     DEFAULT_STATUS_TIMEOUT,
        ...     Shell)
        >>>
        >>> class ExampleShell(Shell):
        ...    def get_start_cmd(self):
        ...        pass
        ...    def start(self):
        ...        pass
        ...    def exit(self):
        ...        pass
        ...    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        ...        return float(timeout)
        >>>
        >>> DefaultStatusTimeout.set(20)
        >>> ExampleShell().get_status_code()
        20.0
        """
        raise NotImplementedError(
            "Attempt to call abstract method get_status_code")

    def get_prompt(self):
        """Get the expected prompt for this shell."""
        return self._prompt

    def _exec_cmd(self, cmd):
        """Run a command."""
        LOGGER.log(_LOGLEVEL, "(%s) Running command: '%s'",
                   self.__class__.__name__, cmd)
        self._terminal.sendline(cmd)

        if self._tty_echo:
            self._read(len(cmd) + 2)  # cmd + '\r\n'

    def _send_input(self, _input):
        """Send input to the terminal."""
        self._terminal.send(_input)

        if self._tty_echo:
            self._read(len(_input))

    def _send_input_line(self, _input):
        """Send a line of input to the terminal."""
        self._terminal.sendline(_input)

        if self._tty_echo:
            self._read(len(_input) + 2)  # line + '\r\n'

    def _send_interrupt(self):
        """Send ctrl + c to the terminal."""
        self._terminal.sendcontrol('c')

    def _detect_prompt(self):
        self._exec_cmd("")
        self._read_until_end(timeout=1.0)

        self._exec_cmd("")
        prompt = self._read_until_end(timeout=0.25)

        LOGGER.log(_LOGLEVEL, "Detected prompt '%s'", prompt)
        return prompt

    def _read(self, count, timeout=-1):
        output = ''

        with self._wrap_timeout_exception():
            while count > 0:
                out = self._read_str_nonblocking(size=count,
                                                 timeout=timeout)
                self._terminal.buffer = b''

                count -= len(out)
                output += out

        return output

    def _read_until_end(self, timeout=0, chunk_timeout=0.1):
        """Read to the end of the terminal output buffer.

        If timeout is set, call will block for at most *timeout* seconds, and
        timeout exception is raised if no output was received.

        If chunk_timeout is set, return only once no new input has been
        received within the last *chunk_timeout* seconds. (defaults to 0.1)
        """
        output = ''

        if timeout:
            with self._wrap_timeout_exception():
                output += self._read_str_nonblocking(size=1024,
                                                     timeout=timeout)

        with self._suppress_timeout_exception(silent=True):
            while True:
                output += self._read_str_nonblocking(size=1024, timeout=chunk_timeout)
        self._terminal.buffer = b''

        if output:
            LOGGER.log(_LOGLEVEL, "Read until end output:\n%s", output)

        return output

    def _read_str_nonblocking(self, size, timeout):
        ret = self._terminal.read_nonblocking(size=size, timeout=timeout)
        return to_string(ret)

    def _read_until_prompt(self, timeout=-1, suppress_timeout=False):
        """Read the output of the previous command."""
        return self._read_until(self.get_prompt(), timeout, suppress_timeout)

    def _read_until(self, trigger, timeout=-1, suppress_timeout=False):
        """Read output until a specified string is encountered.

        *trigger* specifies the string to be matched. The argument *trigger*
        can be a plain string, a compiled regex object, a list of strings,
        or a list of compiled regex objects.

        .. note::

            Strings and regex objects cannot be mixed within
            the provided list (i.e. if a list is given, it must be either a
            list of only strings, or a list of only regex objects).

        If *suppress_timeout* is set to *True*, no :class:`.TimeoutError` will
        be raised, and the command output will always be returned,
        even when a timeout occurs.
        """
        if suppress_timeout:
            with self._suppress_timeout_exception():
                self.__read_until(trigger, timeout=timeout)
        else:
            with self._wrap_timeout_exception():
                self.__read_until(trigger, timeout=timeout)

        return self._terminal.before.decode('utf-8')

    __RegexType = type(re.compile(''))

    def __read_until(self, trigger, timeout):
        # Single regex object
        if isinstance(trigger, self.__RegexType):
            return self._terminal.expect_list([trigger], timeout)

        # List of regex objects
        try:
            if isinstance(trigger[0], self.__RegexType):
                return self._terminal.expect_list(trigger, timeout)
        except (IndexError, TypeError):
            pass

        # String, or list of strings
        return self._terminal.expect_exact(trigger, timeout)

    @staticmethod
    @contextmanager
    def _suppress_timeout_exception(silent=False):
        """Hide a possible timeout exception."""
        try:
            yield
        except pexpect.TIMEOUT:
            if not silent:
                LOGGER.debug("Terminal read timed out (Supressed)")

    @contextmanager
    def _wrap_timeout_exception(self):
        """Produce a more useful timeout exception."""
        try:
            yield
        except pexpect.TIMEOUT:
            raise TimeoutError('' if self._terminal.before is None else
                               self._terminal.before.decode('utf-8'))
