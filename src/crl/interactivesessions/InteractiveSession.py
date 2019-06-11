"""
This class is intended to be a wrapper around *pexpect*.  The reason for
implementing such a wrapper is to avoid having several testcases repeating the
same sequences of calls to be *pexpect.sendline()* / *pexpect.spawn()* /
*pexpect.read()* e.t.c.  Furthermore the intention is to protect users from
sequences of calls to these methods that could lead to erroneous results (for
example executing two successive commands and not being able to properly
distinguish/split the results printed to the terminal from each one).

Major functionality provided by the class is the ability to execute commands in
a pseudo-terminals and getting back any bytes sent to it from the command.

This requires sending the command to the terminal, consuming any 'waste'
printed on it and waiting for the shell prompt in order to be able to execute
the next command. Since its type of shell (like bash) provides its own prompt,
in order to keep track of prompt changes (for example invoking python shell
from bash shell) a stack of objects is used (top object represents the
currently active shell).

Each such object in the stack describes allowed actions and way of working of
the currently active shell.

Recommended reading: basic knowledge of pexpect would help in understanding and
using this library properly.


Bash Shell
----------

This example describes how to start a bash shell and execute some commands:

.. code-block:: python

    s = InteractiveSession()
    s.spawn(BashShell())
    print s.current_shell().exec_command("ls -l")
    print s.current_shell().exec_command("echo Hello")
    print s.current_shell().exec_command("ls -l /some/non/existing/dir")
    if s.current_shell().get_status_code() != 0:
        print "Command failed!!"

SSH Connection
--------------

This example describes how to start an SSH connection and execute command on
remote machine:

.. code-block:: python

    s = InteractiveSession()
    s.spwan(SshShell("1.2.3.4", "username", "password"))
    print s.current_shell().exec_command("ls -l")
    print s.current_shell().get_status_code()

Stacking of Shells
------------------

This example describes how stacking of different shells work:

.. code-block:: python

    s = InteractiveSession()
    s.spawn(BashShell())
    print s.current_shell().exec_command("ls -l")
    s.push(SshShell("1.2.3.4", "username", "password"))
    s.push(PythonShell())
    print s.current_shell().exec_command(
        "print 'I am python on the remote host...'")
    s.pop()
    print s._current_shell().exec_command(
        "echo 'I am bash on the remote host...'")
    s.pop()
    print s._current_shell().exec_command("echo 'I am back...'")

User Input
----------

Executing commands that require user input:

.. code-block:: python

    s = InteractiveSession()
    s.spawn(BashShell())
    s.current_shell().exec_command("rm my_important_file",
                                   confirmation_msg="Are you sure (Y/n):",
                                   confirmation_rsp="y')
    s.current_shell().exec_command("rm my_other_file1 my_other_file2",
                                   confirmation_msg=[
                                   "Are you sure (Y/n):",
                                   "Are you sure (Y/n):"], ["y", "y"])
"""

import logging
import sys
import traceback
import pexpect
from crl.interactivesessions.runnerterminal import RunnerTerminalSessionBroken
from .interactivesessionexceptions import InteractiveSessionError
from .shells.keyauthenticatedsshshell import ShellStartError
# pylint: disable=protected-access,unused-import
from .shells.bashshell import BashShell  # noqa: F401
from .shells.namespaceshell import NamespaceShell  # noqa: F401
from .shells.pythonshell import PythonShell  # noqa: F401
from .shells.shell import Shell  # noqa: F401
from .shells.sshshell import SshShell  # noqa: F401
# pylint: enable=unused-import


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7  # less than DEBUG


class UnexpectedPrompt(InteractiveSessionError):
    """
    Prompt received from terminal does not match with expected prompt.
    """
    def __init__(self, received, expected):
        super(UnexpectedPrompt, self).__init__(received, expected)
        self.received_prompt = received
        self.expected_prompt = expected


class UnknownShellState(InteractiveSessionError):
    """Raised when pop_until() results in an unexpected shell stack state."""


class InteractiveSession(object):
    """
    InteractiveSession is a wrapper class of *pexpect*.

    Two arguments for storing the sent and the received data to files are
    provided.  By default, nothing is stored.  If *dump_received* is given,
    then all the bytes received from the pseudo-terminal are stored to the file
    with full path *dump_received*.  Similarly *dump_outgoing* is a path
    to a file to where all the sent data is stored.
    """

    def __init__(self, dump_received=None, dump_outgoing=None):
        self.terminal = None
        self.shells = []
        self.dump_received = dump_received
        self.dump_outgoing = dump_outgoing
        self.terminal_spawn_timeout = 30
        self.terminal_expect_timeout = 60

    def spawn(self, shell):
        """
        Thin wrapper around pexpect.spawn. This method is the first one that
        should be called in order to create a new terminal.

        Args:
            shell: any class implementing the Shell interface

        Example:

        .. code-block:: python

            s = InteractiveSession()
            s.spawn(BashShell())
        """

        cmd = shell.get_start_cmd()
        logger.debug("Spawning shell '%s(%s)' with cmd '%s'",
                     shell.__class__.__name__, shell, cmd)
        terminal = self._spawn(shell, cmd)

        if self.dump_outgoing is not None:
            open(self.dump_outgoing, "a").write(
                "*" * 30 + "NEW TERMINAL" + "*" * 30 + "\n")
            terminal.logfile_send = open(self.dump_outgoing, "a")

        if self.dump_received is not None:
            open(self.dump_received, "a").write(
                "*" * 30 + "NEW TERMINAL" + "*" * 30 + "\n")
            terminal.logfile_read = open(self.dump_received, "a")

        self.terminal = terminal
        self.terminal.timeout = self.terminal_expect_timeout
        shell.set_terminal(self.terminal)

        retval = shell.start()
        self.shells.append(shell)

        return retval

    def _spawn(self, shell, cmd):
        try:
            return shell.spawn(self.terminal_spawn_timeout)
        except AttributeError as e:
            if "has no attribute 'spawn'" in str(e):
                logger.debug('Spawning shell using pexpect.spawn')
                return pexpect.spawn(cmd,
                                     env={"TERM": "dumb"},
                                     timeout=self.terminal_spawn_timeout,
                                     ignore_sighup=False)
            raise

    def push(self, shell, timeout=30):
        """
        Should be called for any action that would change the command prompt.
        Failing to keep this rule will result in unpredictable results from
        Shell.exec_command
        set the last shell's prompt back in case of ShellStartError
        (hostname is wrong in the started shell)

        Args:
            shell: any class implementing the Shell interface

        Example:

        .. code-block:: python

            s = InteractiveSession()
            s.spawn(BashShell()
            s.push(SshShell("1.2.3.4", "username", "password"))
        """

        cmd = shell.get_start_cmd()
        logger.debug("Pushing shell '%s(%s)' with cmd '%s'",
                     shell.__class__.__name__, shell, cmd)
        self.current_shell()._exec_cmd(cmd)
        shell.set_terminal(self.terminal)
        shell.set_tty_echo(self.current_shell().tty_echo)

        try:
            retval = shell.start()
            self.shells.append(shell)
            return retval
        except ShellStartError:
            self.current_shell().set_prompt()
            raise
        except Exception as ex:
            logger.info("Failed to push shell - %s", ex)
            logger.debug("Traceback:\n%s",
                         ''.join(traceback.format_tb(sys.exc_info()[2])))
            self.terminal.expect_exact(self.current_shell().get_prompt(),
                                       timeout=timeout)
            raise ex

    def pop(self):
        """
        Should be called in order to terminate currently active shell and
        return to the previous one.

        .. note::

            The originally spawned shell is not part of the shell stack.

        Example:

        .. code-block:: python

            s = InteractiveSession()
            s.spawn(BashShell())
            s.push(SshShell("1.2.3.4", "username", "password"))
            s.current_shell().exec_command("remote host command here")
            s.pop()
            s.current_shell().exec_command("local host command here")
        """
        self._pop()

        retval = None
        if self.shells:
            retval = self.current_shell()._read_until_prompt()
            logger.log(_LOGLEVEL, "InteractiveSession _pop returns: %s",
                       retval)

        return retval

    def pop_until(self, shell):
        """
        Pop shells from the stack, until the received prompt matches
        the one of 'shell'.

        Should be used to ensure the shell stack is in a known state
        (e.g. at the beginning of each test case reusing the same
        :class:`InteractiveSession`.)
        """
        logger.log(_LOGLEVEL, "Popping shells until prompt matches '%s'",
                   shell.get_prompt())

        while shell in self.shells:
            try:
                self._prompt_should_match(shell)
            except UnexpectedPrompt:
                self._pop()
            else:
                return

        raise UnknownShellState("Shell not in stack, or prompt not detected")

    def _pop(self):
        try:
            self._prompt_should_match()
            self.current_shell().exit()
        except UnexpectedPrompt as e:
            logger.info("Prompt '%s' does not match expected prompt '%s',"
                        " popping shell without calling exit()",
                        e.received_prompt, e.expected_prompt)
            raise e
        finally:
            self.shells.pop()

    def current_shell(self):
        """
        Return the currently active shell or raise exception
        if there is no shell
        """
        try:
            return self.shells[-1]
        except Exception:
            raise RunnerTerminalSessionBroken(
                "InteractiveSession is already closed."
            )

    def get_parent_shell(self):
        """
        Returns the shell below currently active shell
        """
        return self.shells[-2]

    def get_nbr_of_shells(self):
        return len(self.shells)

    def _prompt_should_match(self, shell_to_match=None):
        if not shell_to_match:
            shell_to_match = self.current_shell()

        t_prompt = self.current_shell().get_prompt_from_terminal(timeout=3)
        if not shell_to_match.is_terminal_prompt_matching(t_prompt):
            raise UnexpectedPrompt(t_prompt, self.current_shell().get_prompt())

    def isalive(self):
        return self.terminal.isalive()

    def close_terminal(self):
        while self.shells:
            try:
                self._pop()
            except UnexpectedPrompt as e:
                logger.info("Failed to pop() shell: %s", e)
                logger.debug("Traceback:\n%s",
                             traceback.format_tb(sys.exc_info()[2]))
        self.terminal.close(force=True)

        self.shells = []
        self.terminal = None
        self.dump_received = None
        self.dump_outgoing = None
