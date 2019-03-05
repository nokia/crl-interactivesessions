# pylint: disable=too-many-instance-attributes,too-many-arguments
import logging
from .InteractiveSession import InteractiveSession, UnknownShellState
from .InteractiveSession import SshShell, PythonShell, NamespaceShell


__copyright__ = 'Copyright (C) 2019, Nokia'


class FailedToSetWorkingDirectory(Exception):
    pass


class FailedToRemoveWorkingDirectory(Exception):
    pass


class InteractiveSessionExecutor(object):

    invalidhosts = []

    def __init__(self,
                 node_name,
                 host_name,
                 host_user,
                 host_password,
                 node_ip=None,
                 node_user=None,
                 node_password=None,
                 node_namespace=None,
                 dhcpagenthost=None,
                 work_dir=None,
                 management_node_floating_ip=None):
        """

        node_name is the de to connect to, or None to connect to the
        controller.
        """
        self._management_node_floating_ip = management_node_floating_ip
        self.node_name = node_name
        self.host_name = host_name
        self.host_user = host_user
        self.host_password = host_password
        self.node_ip = node_ip
        self.node_user = node_user
        self.node_password = node_password
        self.node_namespace = node_namespace
        self.dhcpagenthost = dhcpagenthost
        self._controller_shell = None
        self._node_shell = None

        self._session = InteractiveSession()

        self._work_dir = work_dir
        self.initialize_host(self.host_name,
                             self.host_user,
                             self.host_password)
        if node_name is not None:
            self.initialize_node(self.node_ip,
                                 self.node_user,
                                 self.node_password,
                                 self.node_namespace)
        self.initialize_connection()

    def initialize_host(self,
                        host_name,
                        host_user,
                        host_password):
        self.host_name = host_name
        self.host_user = host_user
        self.host_password = host_password

    def initialize_node(self,
                        node_ip,
                        node_user,
                        node_password,
                        node_namespace):
        self.node_ip = node_ip
        self.node_user = node_user
        self.node_password = node_password
        self.node_namespace = node_namespace

    def setup_working_directory(self):
        output = self.run(
            "mkdir -p {0}; cd {0}".format(self._work_dir),
            timeout=10)
        status = self.get_status_code()
        if status:
            raise FailedToSetWorkingDirectory(status, output)

    def remove_working_directory(self):
        output = self.run(
            "cd; rm -rf {0}".format(self._work_dir),
            timeout=10)
        status = self.get_status_code()
        if status:
            raise FailedToRemoveWorkingDirectory(status, output)

    def transfer_text_file(self, textfile, destination_dir=''):
        self._session.push(PythonShell())
        self.get_current_shell().transfer_text_file(textfile,
                                                    destination_dir)
        self._session.pop()

    def reset_session(self):
        try:
            self._session.pop_until(self._node_shell)
        except UnknownShellState:
            self._session.pop_until(self._controller_shell)
            self._connect_to_node_via_dhcpagenthost()

    def run(self, cmd, timeout=-1):
        return self.run_full_output(cmd, timeout=timeout).rstrip('\r\n')

    def run_full_output(self, cmd, timeout=-1):
        return self._session.current_shell().exec_command(cmd, timeout=timeout)

    def get_current_shell(self):
        return self._session.current_shell()

    def get_session(self):
        return self._session

    def isalive(self):
        return self._session.isalive()

    def close(self):
        self._session.close_terminal()

    def get_status_code(self):
        return self._session.current_shell().get_status_code()

    def initialize_connection(self):
        if self._management_node_floating_ip:
            self._connect_to_node_via_floating_ip()
        else:
            self._connect_to_controller()
            if self.node_ip is not None:
                self._connect_to_node_via_dhcpagenthost()

    def _connect_to_node_via_dhcpagenthost(self):
        self._try_to_connect_dhcpagenthost()
        self._set_namespace()
        self._connect_to_node()

    def _connect_to_node_via_floating_ip(self):
        self._session.spawn(SshShell(self._management_node_floating_ip,
                                     self.node_user,
                                     self.node_password))
        if self.node_name != self._get_hostname():
            self._session.push(SshShell(self.node_name,
                                        self.node_user,
                                        self.node_password))

    def _connect_to_controller(self):
        self._session.spawn(SshShell(self.host_name,
                                     self.host_user,
                                     self.host_password))
        self._controller_shell = self._session.current_shell()

    def _try_to_connect_dhcpagenthost(self):
        try:
            if self.dhcpagenthost not in self.invalidhosts:
                self._connect_to_dhcpagenthost()
            else:
                logging.debug("Did not try to connect DHCP Agent host %s, "
                              " because earlier connection attempt failed. "
                              " Trying via controller to the namespace...",
                              self.dhcpagenthost)
        except Exception:  # pylint: disable=broad-except
            logging.debug("Could not connect to DHCP Agent host %s,"
                          " Trying via controller to the namespace...",
                          self.dhcpagenthost)
            self._add_to_invalid_hosts(self.dhcpagenthost)

    @classmethod
    def _add_to_invalid_hosts(cls, host):
        cls.invalidhosts.append(host)

    def _connect_to_dhcpagenthost(self):
        if self.dhcpagenthost != self._get_hostname():
            self._session.push(SshShell(self.dhcpagenthost,
                                        self.host_user,
                                        self.host_password))

    def _get_hostname(self):
        return self.run("hostname")

    def _set_namespace(self):
        self._session.push(NamespaceShell(self.node_namespace))

    def _connect_to_node(self):
        if self.node_ip is not None:
            self._session.push(SshShell(self.node_ip,
                                        self.node_user,
                                        self.node_password))
        self._get_hostname()
        self._node_shell = self._session.current_shell()

    def __str__(self):
        return "Interactive Session on {0}".format(self.node_ip)
