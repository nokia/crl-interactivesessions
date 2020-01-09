import mock
from crl.interactivesessions.InteractiveSession import InteractiveSession
from crl.interactivesessions.SelfRepairingSession import SelfRepairingSession
from crl.interactivesessions.InteractiveExecutor import InteractiveExecutor
from crl.interactivesessions.InteractiveSessionExecutor import InteractiveSessionExecutor


__copyright__ = 'Copyright (C) 2019-2020, Nokia'


class CustomInteractiveSession(InteractiveSession):

    _spawn_port = None

    @classmethod
    def set_spawn_port(cls, spawn_port):
        cls._spawn_port = spawn_port

    def spawn(self, shell):
        shell.port = self._spawn_port
        return super(CustomInteractiveSession, self).spawn(shell)


class ClusterExec(object):

    def __init__(self):
        self.nodes = {}
        self.interactiveexecutor = None
        self.host_robot_dict = None
        self.host = None

    def set_host(self, host):
        self.host = host

    def add_node(self, host):
        self.nodes[host.host] = host

    def initialize_executor(self):
        self.interactiveexecutor = InteractiveExecutor(self._create_selfrepairingsession)

    def _create_selfrepairingsession(self, node_name):
        kwargs = dict()
        if 'python_command' in self.nodes[node_name]:
            kwargs = {'python_command': self.nodes[node_name].python_command}
        return SelfRepairingSession(node_name=node_name,
                                    create_runner_session=self._create_runnersession,
                                    max_retries=3,
                                    sleep_between_retries=1,
                                    **kwargs)

    def _create_runnersession(self, node_name, work_dir, python_command='python'):
        CustomInteractiveSession.set_spawn_port(self.host.port)
        with mock.patch('crl.interactivesessions.'
                        'InteractiveSessionExecutor.InteractiveSession',
                        side_effect=CustomInteractiveSession):
            ise = InteractiveSessionExecutor(host_name=self.host.host,
                                             host_user=self.host.user,
                                             host_password=self.host.password,
                                             node_name=node_name,
                                             node_ip=self.nodes[node_name].host,
                                             node_user=self.nodes[node_name].user,
                                             node_password=self.nodes[node_name].password,
                                             python_command=python_command,
                                             node_namespace=None,
                                             dhcpagenthost=None,
                                             work_dir=work_dir,
                                             management_node_floating_ip=self.host.host)
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
