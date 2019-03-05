import logging


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class MsgReader(object):
    """MsgReader is for reading login banner e.g. 'lecture' or 'message-of-day'
    messages from the terminal in shells.

    Args:
        read_until_end: :meth:`.shell.Shell._read_until_end`
    """

    _default_timeout = 15
    _timeout = _default_timeout

    def __init__(self, read_until_end):
        self._read_until_end = read_until_end

    def read_until_end(self):
        """Reads message and returns it. Timeout *_timeout* is used for
        reading timeout.
        """
        return self._read_until_end(self._timeout)

    @classmethod
    def get_timeout(cls):
        """Get timeout.
        """
        return cls._timeout

    @classmethod
    def set_timeout(cls, timeout):
        """Set timeout.

        Args:
            timeout: timeout in seconds
        """
        LOGGER.info('Set timeout for reading post-login banner message to %s seconds',
                    timeout)
        cls._timeout = float(timeout)

    @classmethod
    def reset_timeout(cls):
        """Reset timeout to original default value.
        """
        LOGGER.info('Reset timeout for reading post-login banner message to %s seconds',
                    cls._default_timeout)
        cls._timeout = cls._default_timeout
