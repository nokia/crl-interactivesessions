from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from crl.interactivesessions.shells.msgreader import MsgReader


__copyright__ = 'Copyright (C) 2019, Nokia'


class Timeouts(object):
    """Set common timeout for reading login banner and status code.
    """

    @staticmethod
    def set(timeout):
        """Set timeout to *timeout* for reading login banner and getting
        status code.
        """
        DEFAULT_STATUS_TIMEOUT.set(timeout)
        MsgReader.set_timeout(timeout)

    @staticmethod
    def reset():
        """Reset to default timeouts of reading login banner and getting
        status code.
        """
        DEFAULT_STATUS_TIMEOUT.reset()
        MsgReader.reset_timeout()
