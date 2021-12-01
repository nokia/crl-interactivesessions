import logging
from .bashshell import BashShell
from .registershell import RegisterShell


__copyright__ = 'Copyright (C) 2019-2020, Nokia'

LOGGER = logging.getLogger(__name__)
_LOGLEVEL = 7


@RegisterShell()
class KubernetesShell(BashShell):
    """InteractiveSession Shell interface for bash in kubernetes pod.

    Args:
        pod_name (str): name of pod

        container (str): ame of container to open the shell if multiple exists

        namespace (str): the namespace scope for the pod

        cmd (str): command to start bash shell, default: bash

        confirmation_msg (str): string to expect for confirmation to start bash shell

        confirmation_rsp (str): expected response to confirmation

        tty_echo (bool): terminal echo value to be set when started in spawn

        init_env (str): path to the file to be sourced in init or
                        bash command to be executed if starts with 'content:'.
                        example: 'content: alias python=python3'
                        default: None

        workdir (bool): change to this directory in start

        cli (str): The command line interface to use
                   default: kubectl

    """

    def __init__(self,
                 pod_name,
                 container=None,
                 namespace=None,
                 cmd="bash",
                 init_env=None,
                 workdir=None,
                 cli="kubectl"):
        super(KubernetesShell, self).__init__(workdir=workdir, init_env=init_env)
        self._pod_name = pod_name
        self._container = container
        self._namespace = namespace
        self._start_cmd = cmd
        self._cli = cli

    def get_start_cmd(self):
        kube_exec = "{0} exec {1} -it{2}{3} {4}".format(
            self._cli,
            self._pod_name,
            " -c " + self._container if self._container else "",
            " -n " + self._namespace if self._namespace else "",
            self._start_cmd
        )
        return kube_exec
