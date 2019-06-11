import uuid
import logging
import re
from crl.interactivesessions.interactivesessionexceptions import (
    InteractiveSessionError)
from .autocompletableshell import AutoCompletableShell
from .shell import (
    TimeoutError,
    DEFAULT_STATUS_TIMEOUT)
from .sshoptions import scpoptions
from .registershell import RegisterShell


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)
_LOGLEVEL = 7


class ScpError(InteractiveSessionError):
    pass


class BashError(InteractiveSessionError):
    """Raised by BashShell errors"""


class FailedToStartApplication(InteractiveSessionError):
    pass


class FailedToTerminateProcess(InteractiveSessionError):
    pass


class SourceInitFileFailed(InteractiveSessionError):
    pass


class CdToWorkdirFailed(InteractiveSessionError):
    pass


@RegisterShell()
class BashShell(AutoCompletableShell):
    """InteractiveSession Shell interface for bash."""

    def __init__(self,
                 cmd="bash",
                 confirmation_msg=None,
                 confirmation_rsp="Y",
                 tty_echo=False,
                 set_rand_promt=True,
                 init_env=None,
                 workdir=None):
        super(BashShell, self).__init__(tty_echo=tty_echo)
        self._prompt = str(uuid.uuid4()) if set_rand_promt else 'NOPROMT'
        self._start_cmd = cmd
        self._confirmation_msg = confirmation_msg
        self._confirmation_rsp = confirmation_rsp
        self.set_rand_promt = set_rand_promt
        self.init_env = init_env
        self.workdir = workdir

    def _set_bash_environment(self):
        """Set bash settings for shell session.

        TTY echo is set in accordance with the value of self._tty_echo.

        The terminal buffer size size is increased, to ease reading and
        writing to the terminal.

        The PS1 environment variable is set to a known value
        (:class::`.BashShell`._prompt) so as to allow for accurate prompt
        detection during command execution.
        """
        logger.log(_LOGLEVEL, "Preparing bash session")
        output = self._read_until_end()

        self._send_input_line('unset HISTFILE')
        stty_cmd = "stty cols 400 rows 400 {0}".format(
            'echo' if self.tty_echo else '-echo')
        self._send_input_line(stty_cmd)
        self.set_prompt()
        try:
            self._read_until_end(timeout=1)
        except TimeoutError:
            pass

        self._prompt = self._detect_bash_prompt()
        output = self._init_env_if_needed(output)
        output = self._cd_to_workdir_if_needed(output)

        return output

    def set_prompt(self):
        if self.set_rand_promt:
            self._send_input_line("unset PROMPT_COMMAND")
            self._send_input_line("export PS1={0}".format(self._prompt))

    def _detect_bash_prompt(self):
        """Detect current bash prompt and make sure terminal
        input & output are synchronized
        """
        logging.log(7, "Trying to detect bash prompt...")
        self._terminal.sendline('echo PROMPT=')
        self._terminal.sendline('echo -n 123456789;echo 987654321')
        res = self._read_until('123456789987654321', timeout=60)
        logging.log(7, '_read_until returned: "%s"', res)
        res = res.replace('echo PROMPT=', '')
        res = res.replace('echo -n 123456789;echo 987654321', '')

        res = ''.join(res.split())
        m = re.search('PROMPT=(.*)$', res)
        if not m:
            raise BashError('Could not detect prompt')
        detected_prompt = m.group(1)
        self._read_until(detected_prompt, timeout=60)
        logging.log(7, "Detected prompt '%s'", detected_prompt)
        return detected_prompt

    def _init_env_if_needed(self, output):
        if self.init_env is not None:
            out = self.exec_command('. {}'.format(self.init_env))
            ret = self.get_status_code()
            if ret != 0:
                raise SourceInitFileFailed(out)
            output += str(out)
        return output

    def _cd_to_workdir_if_needed(self, output):
        if self.workdir is not None:
            out = self.exec_command('cd {}'.format(self.workdir))
            ret = self.get_status_code()
            if ret != 0:
                raise CdToWorkdirFailed(str(out))
            output += str(out)
        return output

    def get_start_cmd(self):
        return self._start_cmd

    def start(self):
        retval = ""

        if self._confirmation_msg:
            logger.log(_LOGLEVEL, "Awaiting prompt '%s'",
                       self._confirmation_msg)
            retval = self._read_until(self._confirmation_msg, -1)
            self._terminal.sendline(self._confirmation_rsp)

        retval += self._set_bash_environment()
        return retval

    def exit(self):
        logger.log(_LOGLEVEL, "Exit from BashShell")
        self._exec_cmd("exit")

    def get_status_code(self, timeout=DEFAULT_STATUS_TIMEOUT):
        """
        Returns the status code of the last executed command using 'echo $?'

        The default status timeout is globally adjustable. The setting

        >>> from crl.interactivesessions.shells.shell import DefaultStatusTimeout
        >>> DefaultStatusTimeout.set(20)

        sets default status timeout to 20 seconds.
        """
        return int(self.exec_command("echo $?", timeout=float(timeout)))

    def get_pid(self):
        """
        Returns the pid of the last crated process using 'echo $!'
        """
        return int(self.exec_command("echo $!"))

    def start_application(self, cmd, expect, timeout=60):
        self.start_application_without_confirmation(cmd)
        return self.confirm_application_was_started(expect, timeout)

    def start_application_without_confirmation(self, cmd):
        self._verify_bash_terminal()
        self._exec_cmd(cmd)

    def confirm_application_was_started(self, expect, timeout=60):
        logger.log(_LOGLEVEL, "Run subscriber expect: %s, timeout: %s",
                   expect, timeout)
        if self._terminal.expect_exact([expect, self.get_prompt()],
                                       timeout=timeout) > 0:
            output = self._terminal.before.decode("utf-8")
            raise FailedToStartApplication(self.get_status_code(), output)

        return self._terminal.before.decode("utf-8")

    def stop_application(self, timeout=30):
        self._send_interrupt()
        return self._read_until_prompt(timeout)

    def scp_copy_file(
            self, source_file, dest_ip, dest_user, dest_pass, dest_file):
        """
        Copy a file from localhost to a destination. This method is just a
        convenience wrapper around scp command line tool. Same results could be
        achieved using exec_command.

        Args:
            source_file: name of the local file to be transfered

            dest_ip: ip of the host that should receive the file

            dest_user: username for host login

            dest_pass: password for host login

            dest_file: where to put the file on the destination host
        """
        cmd = "scp -q {0} {1} {2}@{3}:{4}".format(
            scpoptions,
            source_file, dest_user, dest_ip, dest_file)

        self._exec_cmd(cmd)
        self._read_until("word:")
        self._terminal.sendline(dest_pass)

        n = self._terminal.expect_exact([self.get_prompt(), "word:"])
        if n == 1:
            try:
                self._send_interrupt()
                self._read_until_prompt()
            finally:
                raise ScpError("Bad password; user '{0}',"
                               " password '{1}'".format(
                                   dest_user, dest_pass))

        res = self._terminal.before.decode("utf-8")

        if self.get_status_code() != 0:
            raise ScpError("Failed to transfer file (" + res + ")")

        return res

    def scp_download_file(self,
                          source_file,
                          source_ip,
                          source_user,
                          source_pass,
                          dest_file):
        """
        Download a file from a remote machine to local. This method is just a
        convenience wrapper around scp command line tool. Same results could be
        achieved using exec_command.

        Args:
            source_file: name of the remote file to be transfered

            source_ip: ip of the host that contains the file

            source_user: username for host login

            source_pass: password for host login

            dest_file: where to put the file on the local machine
        """

        cmd = "scp -q {0} {1}@{2}:{3} {4}".format(
            scpoptions,
            source_user, source_ip, source_file, dest_file)

        self._send_input_line(cmd)
        self._read_until("word:")
        self._send_input_line(source_pass)

        n = self._terminal.expect_exact([self.get_prompt(), "word:"])
        if n == 1:
            self._send_interrupt()
            self._read_until_prompt()
            raise ScpError("Bad password")

        res = self._terminal.before.decode("utf-8")

        if self.get_status_code() != 0:
            raise ScpError("Failed to transfer file (" + res + ")")

        return res

    def terminate_process_forced(self, pid):
        """
        This method send signal -9 to a process forcing its termination.

        .. note::

            Consider using *exec_command("kill -9 my_pid")*

            After executing *kill -9 ...* in a bash shell, the shell
            itself prints output notifying the user that some process was
            killed.  This output is not guaranteed to be printed before the
            prompt that appears once the user hits Enter and can confuse
            *exec_command*.
        """
        cmd = "kill -9 " + str(pid)
        self._exec_cmd(cmd)

        n = self._terminal.expect(["illed", "Exit 9", self.get_prompt(),
                                   "No such process"])
        if n in (0, 1):
            self._read_until_prompt()
        elif n == 2:
            self._send_input_line("")
            self._read_until(["illed", "Exit 9"])
            self._read_until_prompt()
        else:
            raise FailedToTerminateProcess("No process with pid " + str(pid))

    def _verify_bash_terminal(self):
        self.exec_command("", timeout=2)
