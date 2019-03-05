from .pythonshellbase import (
    PythonShellBase,
    UnexpectedOutputInPython)


__copyright__ = 'Copyright (C) 2019, Nokia'


class RawPythonShell(PythonShellBase):

    _setup_cmds_before_echo_off = [
        'import sys, termios, tty',
        '_fdin = sys.stdin.fileno()',
        '_orig_inattrs = termios.tcgetattr(_fdin)',
        '_new_inattrs = termios.tcgetattr(_fdin)',
        '_new_inattrs[3] = _new_inattrs[3] & ~termios.ECHO',
        'termios.tcsetattr(_fdin, termios.TCSADRAIN, _new_inattrs)']

    setup_cmds = _setup_cmds_before_echo_off + [
        'tty.setraw(_fdin)',
        "'endofsetup'"]
    teardown_cmd = 'termios.tcsetattr(_fdin, termios.TCSADRAIN, _orig_inattrs)'

    def __init__(self, start_cmd='python -u'):
        super(RawPythonShell, self).__init__(start_cmd)
        self._orig_delaybeforesend = None

    def exit(self):
        self._sendline(self.teardown_cmd)
        self.delaybeforesend = self._orig_delaybeforesend
        super(RawPythonShell, self).exit()

    def start(self):
        super(RawPythonShell, self).start()
        self._terminal.setwinsize(400, 400)
        self._setup_echo_off_and_raw()
        self._verify_setup()
        self._setup_delaybeforesend()

    def _verify_setup(self):
        out = self._read_until_prompt_after_last_command()
        cmds = self._split_to_cmds(out)
        self._verify_cmds(cmds, exception=UnexpectedOutputInPython(
            'Unexpected out={out!r}, cmds={cmds}'.format(out=out, cmds=cmds)))

    def _read_until_prompt_after_last_command(self):
        last = self.setup_cmds[-1]
        out = self._read_until(last, timeout=self.short_timeout)
        out += self._read_until_prompt(timeout=self.short_timeout)
        return out

    @staticmethod
    def _split_to_cmds(out):
        return [
            cmd for cmd in [
                c.strip() for c in out.replace('>>>', '').splitlines()] if cmd]

    def _verify_cmds(self, cmds, exception):
        if cmds and cmds != self._setup_cmds_before_echo_off:
            raise exception

    def _setup_echo_off_and_raw(self):
        for cmd in self.setup_cmds:
            self._sendline(cmd)
        self.set_tty_echo(False)

    def _sendline(self, cmd):
        self._terminal.sendline(cmd)

    def _setup_delaybeforesend(self):
        self._orig_delaybeforesend = self.delaybeforesend
        self.delaybeforesend = 0
