import os
from contextlib import contextmanager
import logging
from ._terminalpools import _TerminalPools
from .pythonterminal import PythonTerminal
from ._targetproperties import _TargetProperties
from ._runnerintarget import _RunnerInTarget
from ._filecopier import (
    _FileCopier,
    _LocalFile,
    _RemoteFile,
    _RemoteScriptRemoteFile,
    _DirRemoteFile,
    _LocalDirCopier)
from ._process import RunResult, rstrip_runresult


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


class TargetIsNotSet(Exception):
    pass


class BackgroundExecIdAlreadyInUse(Exception):
    pass


class RemoteRunner(object):
    """
    Library for executing remote commands in the remote target shell.

    With this library the test targets are first defined with \`Set Target\`
    keyword and they are given optionally a name. More detailed target setup is
    possible with \`Set Target Property\` keyword. After the targets are
    defined
    the commands can be executed with `Execute Command In Target` keyword.

    The library is singleton so the targets can be defined whenever suitable.

    .. note::

        Targets must have *Python* installed. In more detail it must
        be possible to start an interactive *Python* shell from the
        topmost shell of the shell stack with the command *python*.

     **Example 1 for setting target:**

     *NamespaceShell* can be used in a middle for executing commands in the
     test targets where the connection requires setting of the
     *Linux* kernel namespace.

     +----------------------+--------------------------------------------+
     | &{CONTROLLER}=       | host=10.102.227.10                         |
     +----------------------+--------------------------------------------+
     | ...                  | user=root                                  |
     +----------------------+--------------------------------------------+
     | ...                  | password=root                              |
     +----------------------+--------------------------------------------+
     | &{NAMESPACE}=        | shellname=NamespaceShell                   |
     +----------------------+--------------------------------------------+
     | ...                  | namespace=\ |namespace|                    |
     +----------------------+--------------------------------------------+
     | &{VNFNODE}=          | host=192.168.57.124                        |
     +----------------------+--------------------------------------------+
     | ...                  | user=nodeuser                              |
     +----------------------+--------------------------------------------+
     | ...                  | password=nodepassword                      |
     +----------------------+--------------------------------------------+
     | @{SHELLDCITS}=       | ${CONTROLLER}                              |
     +----------------------+--------------------------------------------+
     | ...                  | ${NAMESPACE}                               |
     +----------------------+--------------------------------------------+
     | ...                  | ${VNFNODE}                                 |
     +----------------------+--------------------------------------------+
     | Set Target           | shelldicts=${SHELLDICTS}                   |
     +----------------------+--------------------------------------------+
     | ...                  | name=vnfnode                               |
     +----------------------+--------------------------------------------+

     .. |namespace| replace:: qdhcp-d5c44716-4d11-45a6-a658-8ed97502d26b


     **Creating new shells**

     If none of the built-in shells
     (*SshShell*, *BashShell* and *NamespaceShell*) is usable
     the new shell can be created.
     The shell code can be located e.g in any test library which is
     imported e.g. via *Library* in the Robot Framework suites.

     The new shells must inherit from *Shell* and must be registered
     via *RegisterShell* decorator from
     *crl.interactivesessions.shells.registershell*

     For further information, please refer to the documentation of
     *Shell* from *crl.interactivesessions.shells.shell*.

     **Example 2 of new shell**

     In this example is shown in the high level how the new
     *Shell* can he registered and used.

     Example code which has to be import e.g. by *Library*:

     .. code:: python

         @RegisterShell()
         NewShell(Shell):
             def __init__(self, newargument):
                ...

     Example usage of the code from Robot Framework test suites:

     +----------------------+--------------------------------------------+
     | &{CONTROLLER}=       | host=10.102.227.10                         |
     +----------------------+--------------------------------------------+
     | ...                  | user=root                                  |
     +----------------------+--------------------------------------------+
     | ...                  | password=root                              |
     +----------------------+--------------------------------------------+
     | &{NEWSHELL}=         | shellname=NewShell                         |
     +----------------------+--------------------------------------------+
     | ...                  | newargument=newvalue                       |
     +----------------------+--------------------------------------------+
     | @{SHELLDCITS}=       | ${CONTROLLER}                              |
     +----------------------+--------------------------------------------+
     | ...                  | ${NEWSHELL}                                |
     +----------------------+--------------------------------------------+
     | Set Target           | shelldicts=${SHELLDICTS}                   |
     +----------------------+--------------------------------------------+
     | ...                  | name=newtarget                             |
     +----------------------+--------------------------------------------+

     The real life example could be *SuShell* which would change the user to
     the required user. Another use-case could be to extend *BashShell* to
     execute source of the  required file in the shell start.

    **Setting timeouts for shell operations**

    For setting timeouts for *SudoShell* and *BashShell* operations to
    get status code and reading the loging banner, *Timeouts* library
    can be used when first setting library

    +-------------+------------------------------------------------------+
    | Library     | crl.interactivesessions.shells.timeouts.Timeouts     |
    +-------------+-----------+------------------------------------------+
    | ...         | WITH NAME | Timeouts                                 |
    +-------------+-----------+------------------------------------------+

    Then setting e.g. timeouts to 100 seconds

    +--------------+-----+
    | Timeouts.Set | 100 |
    +--------------+-----+

    In order to reset back to default timeouts, please use

    +----------------+
    | Timeouts.Reset |
    +----------------+
    """
    def __init__(self):
        self.filecopier = _FileCopier()
        self.targets = dict()
        self.terminalpools = _TerminalPools()
        self._backgrounds = dict()
        self._nohup_processes = None

    @staticmethod
    def _create_runner_in_target(shelldicts):
        return _RunnerInTarget(shelldicts)

    def set_target(self, shelldicts, name='default'):
        """
        Set connection path to target as dictionaries of *Shells*. The default
        shell is *DefaultSshShell* from
        *crl.interactivesessions.shells.shellstack*.  The shell *__init__*
        arguments have to be given as keyword argument dictionary with addition
        of the *shellname* keyword. If the *shellname* argument is not given,
        the *DefaultSshShell* is instantiated.

        In the *DefaultSshShell* the *host* is the only mandatory argument
        so it supports passwordless login. The arguments *user* and *username*
        are aliases for the *SshShell* argument *ip*.

        .. warning::

            If targets are set for each test case separately it causes sessions
            to the targets to be closed and opened again. This causes usually
            rather serious 1 - 2 seconds delay in the test execution.

        **Arguments:**

        *shelldicts*: Path to the target defined by the stack of *Shell*
        dictionaries.

        *name*: String identifier used to distinguish multiple targets.

        **Returns:**

        Nothing.

        **Example 1:**

        +----------------------+--------------------------------------------+
        | &{UNDERCLOUD}=       | host=10.102.227.10                         |
        +----------------------+--------------------------------------------+
        | ...                  | user=root                                  |
        +----------------------+--------------------------------------------+
        | ...                  | password=root                              |
        +----------------------+--------------------------------------------+
        | &{OVERCLOUD} =       | host=192.168.122.56                        |
        +----------------------+--------------------------------------------+
        | ...                  | user=nokiaovercloud                        |
        +----------------------+--------------------------------------------+
        | ...                  | password=overcloudpass                     |
        +----------------------+--------------------------------------------+
        | @{SHELLDCITS}=       | ${UNDERCLOUD}                              |
        +----------------------+--------------------------------------------+
        | ...                  | ${OVERCLOUD}                               |
        +----------------------+--------------------------------------------+
        | Set Target           | shelldicts=${SHELLDICTS}                   |
        +----------------------+--------------------------------------------+
        | ...                  | name=Overcloud                             |
        +----------------------+--------------------------------------------+
        """
        self.targets[name] = _RunnerInTarget(shelldicts)

    def set_target_property(self, target_name, property_name, property_value):
        """
        Sets property *property_name* for target *target_name*.

        **Arguments:**

        *target_name*: Name of the individual target, whose property to set.

        *property_name*: Name of the property.

        *property_value*: Value of the property.

        **Returns:**

        Nothing.

        **Supported properties:**

        +------------------------+-------------------------------+-----------+
        | Name                   | Description                   | Default   |
        |                        |                               | value     |
        +========================+===============================+===========+
        |default_executable      | The default shell             | /bin/bash |
        |                        | executable in which the       |           |
        |                        | commands are executed.        |           |
        +------------------------+-------------------------------+-----------+
        |max_processes_in_target | Maximum number of             | 100       |
        |                        | simultaneous command execution|           |
        |                        | processes in the              |           |
        |                        | single target.                |           |
        +------------------------+-------------------------------+-----------+
        |prompt_timeout          | Timeout in seconds            | 30        |
        |                        | for getting prompt            |           |
        |                        | in the pseudo terminal.       |           |
        |                        | This mainly depends on the    |           |
        |                        | connection latency to the     |           |
        |                        | target.                       |           |
        +------------------------+-------------------------------+-----------+
        |termination_timeout     | Timeout in seconds for waiting| 10        |
        |                        | the execution process to      |           |
        |                        | gracefully shutdown after     |           |
        |                        | it is signaled with *SIGTERM*.|           |
        +------------------------+-------------------------------+-----------+
        |update_env_dict         | Dictionary of *os.environ*    | {}        |
        |                        | style environmental variables |           |
        |                        | which updates the original    |           |
        |                        | environment for all the runs. |           |
        +------------------------+-------------------------------+-----------+
       """

        with self._targethandle(target_name) as handle:
            handle.properties.set_property(property_name, property_value)

    @staticmethod
    def set_default_target_property(property_name, property_value):
        """
        Sets default property for all future targets.

        Target specific properties override the default values. See
        \`Set Target Property\` for supported properties.
        Moreover, it is possible to also create new properties.

        **Arguments:**

        *property_name*: Name of the property.

        *property_value*: Value of the property.

        **Returns:**

        Nothing.
        """
        _TargetProperties.set_default_property(property_name, property_value)

    def get_target_properties(self, target):
        """
        Returns dictionary containing effective properties for *target*.
        """
        with self._targethandle(target) as handle:
            return handle.properties.properties

    def set_terminalpools_maxsize(self, maxsize):
        """
        Set terminal pools maximum size. Terminal pools maximum size defines
        the maximum number of terminals in pool. Execution of any command in
        the target creates a terminal which is put to this pool. So, if e.g.
        the maximum allowed number of SSH connections to the targets is e.g. 50
        and there is known to be more than 50 targets with SSH connections,
        then set *maxsize* to 50 prior executions.

        *RemoteRunner* takes care of removal of free terminals when the maximum
        number of terminals is about to exceed.

        The original default value for *maxsize* is 256.

        **Arguments:**

        *maxsize*: Maximum size of the terminal pools

        **Returns:**

        Nothing

        **Example:**

        +---------------------------+----+
        | Set Terminalpools Maxsize | 50 |
        +---------------------------+----+
        """
        self.terminalpools.set_maxsize(int(maxsize))

    def execute_command_in_target(self,
                                  command,
                                  target='default',
                                  timeout=3600,
                                  executable=None,
                                  progress_log=False):
        """
        Executes remote command in the target.

        This call will block until the command has been executed.

        **Arguments:**

        *commmand*: Shell command to execute in the target
                   (example: "uname -a;ls;sleep 5;date")

        *target*:  Name of the target where to execute the command.

        *timeout*: Timeout for command in seconds.

        *executable*: The path to executable shell where the
                      command is executed.

        *progress_log*: logs progress in the level *DEBUG* if *True*.
        In practice, the *stdout* of the execution is filed line by line
        to the log.

        *Returns:*

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        *Example:*

        +----------------+------------------+-----------------------+
        | ${result}=     | Execute          | echo foo; echo bar>&2 |
        |                | Command          |                       |
        |                | In Target        |                       |
        +----------------+------------------+-----------------------+
        | Should Be Equal| ${result.status} | 0                     |
        +----------------+------------------+-----------------------+
        | Should Be Equal| ${result.stdout} | foo                   |
        +----------------+------------------+-----------------------+
        | Should Be Equal| ${result.stderr} | bar                   |
        +----------------+------------------+-----------------------+

        """

        with self._targethandle(target) as handle:
            logger.debug(
                "execute_command_in_target(command='%s', target='%s')",
                command, target)
            return rstrip_runresult(
                handle.run(command,
                           timeout=timeout,
                           executable=executable,
                           progress_log=progress_log))

    def execute_background_command_in_target(self,
                                             command,
                                             target='default',
                                             exec_id='background',
                                             executable=None):
        """
        Starts to execute remote command in the target.

        This keyword returns immediately and the command is left
        running in the background. See \`Wait Background Execution\` on
        how to read command output and \`Kill Background Execution\` on
        how to interrupt the execution.

        **Arguments:**

        *commmand*: Shell command to execute in the target
                   (example: "uname -a;ls;sleep 5;date")

        *target*:  Name of the target where to execute the command.

        *exec_id*: The execution ID of the background job.

        *executable*: The path to executable shell where the
                      command is executed.

        **Returns:**

        Nothing.

        **Example:**

        +-------------+-------------+------------------+
        | Execute     | echo Hello1;| exec_id=hello1   |
        | Background  | sleep 10    |                  |
        | Command In  |             |                  |
        | Target      |             |                  |
        +-------------+-------------+------------------+
        | Execute     | echo Hello2;| exec_id=hello2   |
        | Background  | sleep 10    |                  |
        | Command In  |             |                  |
        | Target      |             |                  |
        +-------------+-------------+------------------+
        | Kill        | hello1      |                  |
        | Background  |             |                  |
        | Execution   |             |                  |
        +-------------+-------------+------------------+
        | Kill        | hello2      |                  |
        | Background  |             |                  |
        | Execution   |             |                  |
        +-------------+-------------+------------------+
        | ${result1}= | Wait        | hello1           |
        |             | Background  |                  |
        |             | Execution   |                  |
        +-------------+-------------+------------------+
        | ${result2}= | Wait        | hello2           |
        |             | Background  |                  |
        |             | Execution   |                  |
        +-------------+-------------+------------------+

        """
        if exec_id in self._backgrounds:
            raise BackgroundExecIdAlreadyInUse(exec_id)
        with self._targethandle(target) as handle:
            self._backgrounds[exec_id] = handle.run_in_background(
                command, executable)

    def execute_nohup_background_in_target(self,
                                           command,
                                           target='default',
                                           executable=None):
        """
        Starts to execute remote command in the target in nohup mode.

        This keyword returns immediately and the command is left
        running. The stopping of the process must be done
        via e.g. calling *pkill* with \`Execute Command In Target\`.

        The command is executed in a single command mode of the
        *executable* shell, so roughly equivalent with::

           # executable -c 'command'

        If executable is not defined, then the  *default_executable* of the
        target is used.

        **Arguments:**

        *command*: Shell command to execute in the target
                   (example: "uname -a;ls;sleep 5;date")

        *target*:  Name of the target where to execute the command.

        *executable*: The path to executable shell which executes the command.

        **Returns:**

        PID of the process started in the target. This is the process group
        leader PID which can be used for killing the whole process group
        containing all the processes started by the *executable* and *command*.

        **Note**

        The operating system of the target may reuse the PID in case the
        executable is terminated.

        **Example:**

        +-------------+-------------+
        | Execute     | echo Hello1 |
        | Nohup       |             |
        | Background  |             |
        | In Target   |             |
        +-------------+-------------+
        """

        with self._targethandle(target) as handle:
            return handle.run_in_nocomm_background(command, executable)

    @contextmanager
    def _targethandle(self, name):
        yield self._get_targethandle(name)

    def _get_targethandle(self, name):
        try:
            return self.targets[name]
        except KeyError:
            raise TargetIsNotSet(name)

    @contextmanager
    def _terminalhandle(self, name):
        with self._proxyterminalhandle(name) as terminal:
            yield terminal.terminal

    @contextmanager
    def _proxyterminalhandle(self, name):
        with self._targethandle(name) as handle:
            with handle.active_terminal() as terminal:
                yield terminal

    def wait_background_execution(self, exec_id, timeout=3600):
        """
        Waits for background command execution to finish.

        This keyword blocks until the background command with handle *handle*
        finishes or the timeout expires.

        **Arguments:**

        *exec_id*: The execution ID of the background job.

        *timeout*: Time to wait in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        **Example:** See \`Execute Background Command In Target\`
        """
        handle = self._backgrounds[exec_id]
        result = rstrip_runresult(handle.wait_background_execution(timeout))
        del self._backgrounds[exec_id]
        return result

    def kill_background_execution(self, exec_id):
        """
        Terminates the background execution.

        The command being executed is killed gracefully first with *SIGTERM*
        and, in case of failure, forcefully with *SIGKILL*.  Result is
        returned but still \`Wait Background Execution\` keyword
        returns the very same result.

        **Arguments:**

        *exec_id*: The execution ID of the background job.

        **Returns:**

        Nothing.

        *Example:* See \`Execute Background Command In Target\`
        """

        handle = self._backgrounds[exec_id]
        return rstrip_runresult(handle.kill_background_execution())

    def copy_file_between_targets(self,
                                  from_target,
                                  source_file,
                                  to_target,
                                  destination_dir='.',
                                  mode=oct(0o755),
                                  timeout=3600):
        """
        Copy file from one remote target to another.

        **Arguments:**

        *from_target*: Source target.

        *source_file*: Source file.

        *to_target*: Destination target.

        *destination*: Destination directory or file.

        *mode*: Access mode to set to the file in the destination target.

        *timeout*: Timeout in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        **Example:**

        +---------+---------+--------------+---------+---------------+
        | Copy    | default | /tmp/foo.tgz | target2 | /tmp/backups/ |
        | File    |         |              |         |               |
        | Between |         |              |         |               |
        | Targets |         |              |         |               |
        +---------+---------+--------------+---------+---------------+
        """

        with self._terminalhandle(from_target) as from_terminal:
            with self._terminalhandle(to_target) as to_terminal:

                self.filecopier.copy_file(
                    sourcefile=_RemoteFile(source_file,
                                           terminal=from_terminal,
                                           timeout=timeout),
                    targetfile=_RemoteScriptRemoteFile(
                        destination_dir,
                        terminal=to_terminal,
                        timeout=timeout,
                        source_file=os.path.basename(source_file)),
                    mode=mode)
        return RunResult(status='0', stdout='', stderr='')

    def copy_file_from_target(self,
                              source_file,
                              destination=None,
                              target='default',
                              timeout=3600):
        """
        Copy file from the target to local host.

        **Arguments:**

        *source_file*: Target source file.

        *destination*: Local destination directory or file.

        *target*: Target where to copy the file from.

        *timeout*: Timeout in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        **Example:**

        +----------------------------+-------------------------------+
        | Execute Command In Target  | mkdir /tmp/my-robot-tc &&     |
        |                            | touch /tmp/my-robot-tc/bar.sh |
        +----------------------------+-------------------------------+
        | Copy File From Target      | /tmp/my-robot-tc/bar.sh       |
        +----------------------------+-------------------------------+

        """

        with self._terminalhandle(target) as from_terminal:
            self.filecopier.copy_file(
                sourcefile=_RemoteFile(source_file,
                                       terminal=from_terminal,
                                       timeout=timeout),
                targetfile=_LocalFile(destination, source_file))
        return RunResult(status='0', stdout='', stderr='')

    def copy_file_to_target(self,
                            source_file,
                            destination_dir='.',
                            mode=oct(0o755),
                            target='default',
                            timeout=3600):
        """
        Copy file from local host to the target.

        **Arguments:**

        *source_file:*  Local source file.

        *destination*: Remote destination directory or file (files
        and directories are distinguished by *os.path.basename* which
        is an empty string in case of dirctory.) If directories do not
        exist, they are created.

        *mode*: Access mode to set to the file in the target.

        *target*: Target where to copy the file.

        *timeout*: Timeout in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        **Example:**

        +---------------------+--------+-----------------------+
        | Copy File To Target | foo.sh | /tmp/my-robot-tc/     |
        +--------------------+--------+------------------------+

        """
        with self._terminalhandle(target) as to_terminal:
            logger.debug('Destination_dir: %s', destination_dir)
            self.filecopier.copy_file(
                sourcefile=_LocalFile(source_file),
                targetfile=_RemoteScriptRemoteFile(
                    destination_dir,
                    terminal=to_terminal,
                    timeout=timeout,
                    source_file=os.path.basename(source_file)),
                mode=mode)
        return RunResult(status='0', stdout='', stderr='')

    def copy_directory_to_target(self,
                                 source_dir,
                                 target_dir='.',
                                 mode=oct(0o755),
                                 target='default',
                                 timeout=3600):
        """
        Copies contents of local source directory to remote destination
        directory.

        **Arguments:**

        *source_dir*: Local source directory whose contents are copied to the
        target.

        *target_dir*: Remote destination directory that will be created if
        missing.

        *mode*: Access mode to set to the files and directories copied
        to the target.

        *target*: Target where to copy the file.

        *timeout*: Timeout in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        **Example:**

        +----------------+---------+---------------------------+
        | Copy Directory | scripts | /tmp/my-robot-tc/scripts/ |
        | To Target      |         |                           |
        +----------------+---------+---------------------------+

        """

        with self._terminalhandle(target) as to_terminal:
            _LocalDirCopier(
                source_dir=source_dir,
                target_dir=target_dir,
                mode=mode,
                terminal=to_terminal,
                timeout=timeout).copy_directory_to_target()

        return RunResult(status='0', stdout='', stderr='')

    def create_directory_in_target(self,
                                   path,
                                   mode=oct(0o755),
                                   target='default',
                                   timeout=3600):
        """
        Create a directory including missing parent directories in the target.

        **Arguments:**

        *path*: Remote directory to create.

        *mode*: Access mode to set to the directory in the target.

        *target*: Target where to create the file.

        *timeout* Timeout in seconds.

        **Returns:**

        Python *namedtuple* with arguments *status*, *stdout* and *stderr*.

        """

        with self._terminalhandle(target) as to_terminal:
            _DirRemoteFile(path,
                           terminal=to_terminal,
                           timeout=timeout).makedirs_if_needed(mode)
        return RunResult(status='0', stdout='', stderr='')

    def get_terminal(self, target='default'):
        with self._targethandle(target) as t:
            return PythonTerminal(t)

    @staticmethod
    def import_local_path_module_in_terminal(terminal, path):
        terminal.remoteimporter.importfile(str(path))

    @staticmethod
    def get_proxy_from_call_in_terminal(terminal, remote_function,
                                        *args, **kwargs):
        return terminal.runnerterminal.get_proxy_object_from_call(
            remote_function, *args, **kwargs)

    @staticmethod
    def get_proxy_object_in_terminal(terminal, remote_object):
        return terminal.runnerterminal.get_proxy_object(remote_object,
                                                        None)

    def close(self):
        """
        Closes all targets and kills all the executions. Should be called in
        the very end of the suites using the same target topologies.
        """
        self.terminalpools.close()
        self.targets = dict()
        self._backgrounds = dict()
