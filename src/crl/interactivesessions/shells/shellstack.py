from .sshshell import SshShell
from .registershell import RegisterShell, RegisteredShells


__copyright__ = 'Copyright (C) 2019, Nokia'


@RegisterShell()
class DefaultSshShell(SshShell):
    """Alias for :class:`.InteractiveSession.SshShell` which
    converts the *__init__* arguments in the following fashion:

    +---------------------------+--------------------------------------+
    |:class:`.DefaultSshShell`  | :class:`.sshshell.SshShell`          |
    | Argument                  | Argument                             |
    +===========================+======================================+
    | *host*                    | *ip*                                 |
    +---------------------------+--------------------------------------+
    | *username* or *user*      | *username*                           |
    +---------------------------+--------------------------------------+

    Other keyword arguments are passsed without any conversion to
    :class:`.sshshell.SshShell`.

    """
    def __init__(self, **kwargs):
        super(DefaultSshShell, self).__init__(
            **self._get_sshkwargs(kwargs))
        self.kwargs = kwargs

    @staticmethod
    def _get_sshkwargs(kwargs):
        sshkwargs = kwargs.copy()
        if 'username' not in sshkwargs:
            try:
                del sshkwargs['user']
                sshkwargs['username'] = kwargs['user']
            except KeyError:
                pass
        del sshkwargs['host']
        sshkwargs['ip'] = kwargs['host']
        return sshkwargs

    def __str__(self):
        return '**{}'.format(self.kwargs)


class ShellStack(object):
    """ This class is a stack of the
    :class:`.shell.Shell` based shells.
    """
    def __init__(self):
        self._shelldicts = []
        self._shells = []
        self._registeredshells = RegisteredShells()

    def initialize(self, shelldicts):
        """Initialize shells with list of dictionaries, *shelldicts*, where
        each dictionary is mapped to registered :class:`.shell.Shell` based
        shells in the order of the list. The dictionary can contain the class
        name (*shellname*) of the registered shell. The rest of the name-value
        pairs are passed as keyword arguments to the associated shell class. If
        no *shellname* is given, then :class:`DefaultSshShell` is created
        from the dictionary.
        """
        self._shelldicts = shelldicts

    @property
    def shells(self):
        """Shell stack created from *shelldicts*."""
        if not self._shells:
            for shelldict in self._shelldicts:
                self._shells.append(self._create_shell(shelldict))
        return self._shells

    def _create_shell(self, shelldict):
        return self._registeredshells.create_shell(
            **self._get_shelldict_with_shellname(shelldict))

    @staticmethod
    def _get_shelldict_with_shellname(shelldict):
        if 'shellname' not in shelldict:
            shelldict['shellname'] = 'DefaultSshShell'
        return shelldict
