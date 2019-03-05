from .shell import Shell


__copyright__ = 'Copyright (C) 2019, Nokia'


class AutoCompletableShell(Shell):
    """
    Several shells support *tab autocompletion*. Any custom shell
    implementation can inherit from this class in order to provide such
    functionality.

    Args:
        cmd: part of a command.

        autocompletion_trigger: characters that the user would press to trigger
        autocompletion (for example ``'\\t'`` for bash)

        timeout: how much time to wait (in seconds) for the shell prompt to
        reappear after the tab completion


    Autocompletion works in different ways for different shells. Furthermore in
    some cases the autocompleted content just appears in the same line that the
    user was typing the command while in other cases it is printed below this
    line followed by a new prompt.  The default implementation that can be
    reused by Shell derivatives works by expecting the new prompt for a finite
    amount of time. If the prompt does not appear then the implementation
    assumes that autocompletion occured on the same line and returns as a
    result any bytes printed to the terminal until the timeout occured.
    """

    def get_command_auto_completion(self,
                                    cmd,
                                    timeout,
                                    autocompletion_trigger):
        self._send_input(cmd + autocompletion_trigger)
        retval = self._read_until_prompt(timeout, suppress_timeout=True)

        self._send_interrupt()
        self._read_until_prompt(-1)

        # Strip away terminal BEL (bell/alarm) if present
        # Occasionally, BEL is printed if command can not be completed
        return retval.strip('\x07')
