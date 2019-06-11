# noqa: W605
from . import InteractiveSession


__copyright__ = 'Copyright (C) 2019, Nokia'


class NoSuchTerminal(Exception):
    pass


class TerminalAlreadyExists(Exception):
    pass


class InteractiveSessionFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def allocate(dump_received=None, dump_outgoing=None):
        return InteractiveSession.InteractiveSession(dump_received,
                                                     dump_outgoing)


class InteractiveSessions(object):
    _default_terminal_name = "default_terminal"

    def __init__(self, session_factory):
        self._terminals = {}
        self._session_factory = session_factory
        self._default_terminal_name = (
            InteractiveSessions._default_terminal_name)

    def _find_terminal(self, terminal_name):
        if terminal_name is None:
            terminal_name = self._default_terminal_name

        term = self._terminals.get(terminal_name, None)

        if term is None:
            raise NoSuchTerminal("No terminal named " + terminal_name)

        return term

    def set_default_terminal_name(self, terminal_name):
        self._default_terminal_name = terminal_name

    def create_terminal(self, terminal_name=None, dump_received=None,
                        dump_outgoing=None):
        """ Creates a new terminal by initializing all the connection
        information provided by \`Set Openstack Controller\` and \`Set Vm
        Instance\` and adds it to the list of existing terminals.

        User must always use this keyword to create the terminal with which he
        will interact.

        If a terminal with the same name already exists, an Exception is
        thrown.

        Examples:

        +-----------------+---------------------------------+
        | Create Terminal |                                 |
        +-----------------+---------------------------------+
        | Create Terminal | terminal_name = second_terminal |
        +-----------------+---------------------------------+

        See also `Set Openstack Controller`, `Set Vm Instance`

        """
        if terminal_name is None:
            terminal_name = self._default_terminal_name

        if terminal_name in self._terminals:
            raise TerminalAlreadyExists(
                "Terminal name exists in terminals list: " + terminal_name)

        s = self._session_factory.allocate(dump_received, dump_outgoing)
        self._terminals[terminal_name] = s
        return terminal_name

    def spawn(self, shell, terminal_name=None):
        return self._find_terminal(terminal_name).spawn(shell)

    def push(self, shell, terminal_name=None):
        return self._find_terminal(terminal_name).push(shell)

    def get_current_prompt(self, terminal_name=None):
        """
         Returns the prompt of the current shell.

         If you have more than one terminals, use *terminal_name* to
         execute the keyword to the corresponding terminal.

         Examples:

         +-----------------+--------------------+-----------------------------+
         | ${result}=      | Get Current Prompt | terminal_name=scli_terminal |
         +-----------------+--------------------+-----------------------------+
         | Should Be Equal | ${result}          | root@CLA-0 [test]  >        |
         +-----------------+--------------------+-----------------------------+
         | ${result}=      | Get Current Prompt | terminal_name=bash_terminal |
         +-----------------+--------------------+-----------------------------+
         | Should Be Equal | ${result}          | BASH_PROMPT                 |
         +-----------------+--------------------+-----------------------------+

         Remember that specifically for bash shell, the prompt is set to
         'BASH_PROMPT' in \`Begin Bash Mode\` and in \`Begin Local Bash\`.
         """
        return self._find_terminal(terminal_name).current_shell().get_prompt()

    def get_status_code(self, terminal_name=None):
        """
        Returns the exit status of a command. Use this keyword after
        executing a command to get the command exit code.

        If you have more than one terminals, use *terminal_name* to execute
        the keyword to the corresponding terminal.

        Note that exit code is returned as int.

        Examples:

        +----------------------------+----------------------------+-----+
        | Exec Command               | rm -f my_existing_file     |     |
        +----------------------------+----------------------------+-----+
        | ${status}=                 | Get Status Code            |     |
        +----------------------------+----------------------------+-----+
        | Should Be Equal            | '$status'                  | '0' |
        +----------------------------+----------------------------+-----+
        | Exec Command               | rm -f my_non_existing_file |     |
        +----------------------------+----------------------------+-----+
        | ${status}=                 | Get Status Code            |     |
        +----------------------------+----------------------------+-----+
        | Should Be Equal As Numbers | ${status}                  |  1  |
        +----------------------------+----------------------------+-----+

        See also \`Exec Command\` and \`Exec Command Expecting More\`.
        """
        return self._find_terminal(
            terminal_name).current_shell().get_status_code()

    def get_pid(self, terminal_name=None):
        """
        Returns the pid of a created process. Use this keyword after
        creating a process to get the pid.  If you have more than one
        terminals, use *terminal_name* to execute the keyword to the
        corresponding terminal.

        Note that pid is returned as int.

        Examples:

        +----------------------------+----------------------------+------+
        | Exec Command               | python  dummyscript.py     |      |
        +----------------------------+----------------------------+------+
        | ${status}=                 | Get Pid                    |      |
        +----------------------------+----------------------------+------+
        | Should Be Equal            | '$pid'                     |'5778'|
        +----------------------------+----------------------------+------+

        See also `Exec Command`, `Exec Command Expecting More`
        """
        return self._find_terminal(terminal_name).current_shell().get_pid()

    def exec_command(self, cmd, terminal_name=None, timeout=-1):
        """
         Executes the specified command and expects the current shell
         prompt.

         If the execution was successful, the result of the command is
         returned, otherwise the error is returned.

         Change *terminal_name* if you want to excecute the command to the
         corresponding terminal.

         Simple example:

         +------------+--------------+--------+
         | ${result}= | Exec Command | ls -al |
         +------------+--------------+--------+

         The result ${result} contains *ls* output.

         You can use \`Get Status Code\` after executing a command to get the
         command exit code.

         See also \`Exec Prompting Command\`, `Exec Command Expecting More`,
         \`Get Status Code\`
        """
        return self._find_terminal(
            terminal_name).current_shell().exec_command(
                cmd, timeout=float(timeout)).strip()

    def exec_prompting_command(self,
                               cmd,
                               responses=None,
                               terminal_name=None,
                               timeout=-1):
        """
        Executes the specified command, answers specified prompts and expects
        the current shell prompt.

        If the execution was successful, the result of the command is returned,
        otherwise the error is returned.

        Change *terminal_name* if you want to excecute the command to the
        corresponding terminal.

        Use this keyword if the command to be executed will prompt the user
        with a confirmation message and requires a response to proceed.  The
        user must provide this information to this keyword by giving the exact
        confirmation message expected and the response to be given.  In case
        more than one messages is displayed by the command, multiple prompts
        and responses can be defined.  A robot list should be created with all
        confirmation messages expected, and given as the _responses_ argument.

        Example:

        +---------------+-----------+--------------+---+----------------+---+
        | ${responses}= | Create    | rm: remove   | y | rm: remove     | y |
        |               | Responses | regular file |   | regular file   |   |
        |               | List      | 'my_file3'?  |   | 'my_file4'?    |   |
        +---------------+-----------+--------------+---+----------------+---+
        | ${result}=    | Exec      | rm -i        | ${responses}           |
        |               | Prompting | my_file3     |                        |
        |               | Command   | my_file4     |                        |
        +---------------+-----------+--------------+------------------------+

        Answers yes to all file deletion questions. ${result} is a blank
        string.

        You can use `Get Status Code` after executing a command to get the
        command exit code.

        See also \`Exec Command\`, \`Exec Command Expecting More\`,
        \`Get Status Code\`
        """
        return self._find_terminal(
            terminal_name).current_shell().exec_prompting_command(
                cmd, responses, timeout=float(timeout)).strip()

    @staticmethod
    def create_responses_list(*args):
        """
        Helper keyword for creating the responses list for
        \`Exec Prompting Command\`

        Arguments should be given in pairs of expected prompt, and response to
        be given.

        Example: see \`Exec Prompting Command\`
        """
        return InteractiveSession.Shell.create_responses_list(*args)

    def exec_command_expecting_more(self,
                                    cmd,
                                    more_prompt="--More--",
                                    terminal_name=None):
        """
        Executes the specified command. Used for handling cases where the
        command output is too large and paging function is not disabled.

        If the execution was successful, the result of the command is returned
        together with the number of pages.  The result of the command exceeds
        maximum limit of lines, therefore the '--More--' prompt appears instead
        of the current prompt. In this case `Exec Command` will fail, use this
        function instead.  The keyword sends continually the _space_ character
        to the prompt, until end of input is reached and shell prompt appears.

        Return value of this keyword is a list which conains a counter of how
        many times *--More--* appeared and the whole output of the command in
        one string.

        The expected final prompt is the current prompt.

        If *more_prompt* is other than '--More--' it can be set accordingly by
        the user.

        Examples:

        +------------+--------------------+-----------------+
        | ${result}= | Exec Command       | cat my_file.txt |
        |            | Expecting More     |                 |
        +------------+--------------------+-----------------+

        ${result} contains the whole output of my_file.txt

        +------------+-----------+---------+--------------+-----------------+
        | ${result}= | Exec      | help    | more_prompt= | terminal_name = |
        |            | Command   | cmdtree | --More--     | scli_terminal   |
        |            | Expecting |         |              |                 |
        |            | More      |         |              |                 |
        +------------+-----------+---------+--------------+-----------------+

        ${result} contains the whole fsclish command tree

        See also \`Exec Command\`, \'Get Status Code\`.
        """
        return self._find_terminal(
            terminal_name).current_shell().exec_command_expecting_more(
                cmd, more_prompt)

    def exit_shell(self, terminal_name=None):
        """
        Exits the current shell using the corresponging exit command. The
        expected prompt changes to the prompt expected after entering this
        shell.

        This keyword is always pair to a *Begin (terminal_name) Mode*
        keyword of this library.

        Examples:

        +-----------------+--------------+------------------------------------+
        | Begin Bash Mode | bash         | #Executes *bash* command and       |
        |                 |              | initiates a new bash shell         |
        +-----------------+--------------+------------------------------------+
        | Exec Command    | ls           | #Executes *ls* command in the bash |
        |                 |              | shell                              |
        +-----------------+--------------+------------------------------------+
        | Begin Scli Mode | fsclish      | #Executes *fsclish* command in the |
        |                 |              | bash shell to initiate an scli     |
        |                 |              | shell                              |
        +-----------------+--------------+------------------------------------+
        | Exec Command    | show cli env | #Executes *show cli env* command   |
        |                 |              | in the SCLI shell                  |
        +-----------------+--------------+------------------------------------+
        | Exit Shell      | exit         | #Executes *exit* command in the    |
        |                 |              | scli shell, so user exits scli     |
        |                 |              | shell and returns to the previous  |
        |                 |              | bash shell                         |
        +-----------------+--------------+------------------------------------+
        | Exec Command    | pwd          | #Executes *pwd* command in the     |
        |                 |              | bash shell                         |
        +-----------------+--------------+------------------------------------+

        See also \`Begin Python Mode\`, \`Begin Scli Mode\`,
        \`Begin Local Bash\` and \`Begin Bash Mode\` .
        """
        return self._find_terminal(terminal_name).pop().strip()

    def close_terminal(self, terminal_name=None):
        if terminal_name is None:
            terminal_name = self._default_terminal_name

        self._find_terminal(terminal_name).close_terminal()
        del self._terminals[terminal_name]
