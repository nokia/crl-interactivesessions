import logging
from crl.interactivesessions.SelfRepairingSession import SelfRepairingSession
from crl.interactivesessions.InteractiveExecutor import InteractiveExecutor
from crl.interactivesessions.InteractiveSessionExecutor import InteractiveSessionExecutor


__copyright__ = 'Copyright (C) 2019, Nokia'


class ClusterExec(object):

    def __init__(self):
        self.nodes = {}
        self.interactiveexecutor = None

    def set_host(self, host_as_dict):
        self.host_name = host_as_dict['host']
        self.host_user = host_as_dict['user']
        self.host_password = host_as_dict['password']

    def add_node(self, name, host_as_dict):
        self.nodes[name] = host_as_dict

    def initialize_executor(self):
        self.interactiveexecutor = InteractiveExecutor(self._create_selfrepairingsession)

    def _create_selfrepairingsession(self, node_name):
        return SelfRepairingSession(node_name=node_name,
                                    create_runner_session=self._create_runnersession,
                                    max_retries=3,
                                    sleep_between_retries=1)

    def _create_runnersession(self, node_name, work_dir):
        ise = InteractiveSessionExecutor(host_name=self.host_name,
                                         host_user=self.host_user,
                                         host_password=self.host_password,
                                         node_name=node_name,
                                         node_ip=self.nodes[node_name]['host'],
                                         node_user=self.nodes[node_name]['user'],
                                         node_password=self.nodes[node_name]['password'],
                                         node_namespace=None,
                                         dhcpagenthost=None,
                                         work_dir=work_dir,
                                         management_node_floating_ip=self.host_name)
        return ise

    def run_cmd_in_node(self, node, cmd, timeout=120, validate_return_status=False):
        """
        Run command in target node

        Example:
        | ${status} |  ${stdout} |  ${stderr}= | Run Cmd In Node |  CLA-0 | "echo Hello" |
        """
        return self.interactiveexecutor.run(
            node,
            cmd,
            timeout=timeout,
            validate_return_status=validate_return_status)

    def close(self):
        self.interactiveexecutor.close()


