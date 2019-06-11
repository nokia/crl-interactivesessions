import logging
from crl.interactivesessions.shells import Shell
from crl.interactivesessions.shells.registershell import RegisterShell


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


@RegisterShell()
class SpawningShell(Shell):
    def __init__(self, terminal_factory):
        super(SpawningShell, self).__init__()
        self._terminal_factory = terminal_factory

    def spawn(self, timeout):  # pylint: disable=unused-argument
        LOGGER.debug('======\n\n Calling SpawningShell.spawn() ===')
        self._terminal = self._terminal_factory()
        return self._terminal

    def get_start_cmd(self):
        pass

    def start(self):
        pass

    def exit(self):
        pass

    def _exec_cmd(self, cmd):
        LOGGER.info('Command (%s) has no effect', cmd)
        return ''

    def get_prompt_from_terminal(self, empty_command="", timeout=-1):
        pass

    def get_prompt(self):
        pass

    def is_terminal_prompt_matching(self, terminal_prompt):
        return True
