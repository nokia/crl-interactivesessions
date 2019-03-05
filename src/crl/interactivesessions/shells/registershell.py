from __future__ import print_function
import six
from crl.interactivesessions._metasingleton import MetaSingleton
from .shell import Shell


__copyright__ = 'Copyright (C) 2019, Nokia'


class UnregisteredShell(Exception):
    """ Raised when the shell name is not registered with
    :class:`.RegisterShell`.
    """


class ShellAlreadyRegistered(Exception):
    """Raised when the shell is already registerd with
    :class:`RegisterShell`.
    """


@six.add_metaclass(MetaSingleton)
class RegisteredShells(object):
    """Dictionary for :class:`.shell.Shell` based shell classes registered via
    :class:`.RegisterShell`.
    """
    def __init__(self):
        self._shells = {}

    def add_shellcls(self, shellcls):
        if shellcls.__name__ in self._shells:
            raise ShellAlreadyRegistered(shellcls)
        self._shells[shellcls.__name__] = shellcls

    def get_shellcls(self, shellclsname):
        """ Return shell class for the name *shellcls*.  Raises
        :class:`UnregisteredShell` if not found.
        """
        try:
            return self._shells[shellclsname]
        except KeyError:
            raise UnregisteredShell(shellclsname)

    def create_shell(self, shellname, **kwargs):
        """Create shell instance with class name *shellname* and with keyword
        arguments *kwargs*."""
        return self.get_shellcls(shellname)(**kwargs)


class RegisterShell(object):
    """
    Registration decorator for the :class:`.shell.Shell` based shells.

    **Usage example:**

    .. code-block:: python

        @RegisterShell()
        class AliasBashShell(BashShell):
            pass

    """
    def __call__(self, shellcls):
        if issubclass(shellcls, Shell):
            RegisteredShells().add_shellcls(shellcls)
        return shellcls
