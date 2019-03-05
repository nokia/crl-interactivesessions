from .bashshell import BashShell
from .registershell import RegisterShell


__copyright__ = 'Copyright (C) 2019, Nokia'


@RegisterShell()
class NamespaceShell(BashShell):
    """
    This class can be used in order to start a bash shell inside a given
    namespace

    Example:

    .. code-block:: python

        s = InteractiveSession()
        s.spawn(SshShell("open_stack_controller", "username", "password"))
        s.push(NamespaceShell("qdhcp-1234...")
        s.push(SshShell("virtual_machine", "username", "password"))
        s.current_shell().exec_command("ls -l")
    """

    def __init__(self, namespace, *args, **kwargs):
        super(NamespaceShell, self).__init__(*args, **kwargs)
        self.namespace = namespace

    def get_start_cmd(self):
        cmd = "ip netns exec {0} bash".format(self.namespace)
        return cmd

    def start(self):
        return self._set_bash_environment()
