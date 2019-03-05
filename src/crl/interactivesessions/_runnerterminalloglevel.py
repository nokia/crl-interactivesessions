import logging
from functools import wraps
from collections import OrderedDict


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


class _RunnerTerminalLogLevel(object):
    def __init__(self, level):
        self.level = level
        self.base = 'crl.interactivesessions'
        self.modules = [
            'runnerterminal',
            'autorunnerterminal',
            'shells.pythonshell',
            'shells.shell']
        self.loggers = OrderedDict()
        self.backuplevels = {}
        self._setup_loggers()

    def _setup_loggers(self):
        for module in self.modules:
            self.loggers[module] = logging.getLogger(
                self._get_logger_name(module))

    def __call__(self, f):

        @wraps(f)
        def inner_function(*args, **kwargs):
            self._backup_levels()
            self._setlevel_for_loggers()
            try:
                return f(*args, **kwargs)
            finally:
                self._restore_levels()
        return inner_function

    def _setlevel_for_loggers(self):
        for _, logger_ in self.loggers.items():
            logger_.setLevel(self.level)
        logger.debug('Set log level to %s in modules %s',
                     self.level, self.modules)

    def _backup_levels(self):
        for module, logger_ in self.loggers.items():
            self.backuplevels[module] = logger_.getEffectiveLevel()

    def _restore_levels(self):
        for module, logger_ in self.loggers.items():
            logger.debug("Restoring log levels to %s in module '%s'",
                         self.backuplevels[module],
                         module)
            logger_.setLevel(self.backuplevels[module])

    def _get_logger_name(self, module):
        return '.'.join([self.base, module])


class _QuietRunnerTerminalLogLevel(_RunnerTerminalLogLevel):
    def __init__(self, level):
        super(_QuietRunnerTerminalLogLevel, self).__init__(level)
        self.loggers[__name__] = logger
