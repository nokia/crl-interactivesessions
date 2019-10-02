from crl.interactivesessions.shells.shell import DEFAULT_STATUS_TIMEOUT
from crl.interactivesessions.shells.msgreader import MsgReader
from crl.interactivesessions.shells.pythonshellbase import PythonShellBase
from crl.interactivesessions.remoteproxies import _RemoteProxy


__copyright__ = 'Copyright (C) 2019, Nokia'


class Timeouts(object):
    """Set common timeout for reading login banner and status code.
    """

    _original_short_timeout = 10

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

    @staticmethod
    def set_python_short_timeout(timeout):
        """Set timeout for short Python shell operations.
        """
        PythonShellBase.set_short_timeout(float(timeout))

    def reset_python_short_timeout(self):
        """Reset to default the timeout for short Python shell operations.
        """
        PythonShellBase.set_short_timeout(self._original_short_timeout)

    @staticmethod
    def set_proxy_default_timeout(timeout):
        """Set *_RemoteProxy* and *_RecursiveProxy* default timeouts
        """
        _RemoteProxy.set_remote_proxy_default_timeout(float(timeout))

    @staticmethod
    def reset_proxy_default_timeout():
        """Set *_RemoteProxy* and *_RecursiveProxy* default timeouts
        """
        _RemoteProxy.reset_remote_proxy_default_timeout()
