.. Copyright (C) 2019-2020, Nokia

CHANGES
=======

1.4.0b6
-------

- Fix Python 2 incompatibilities.

1.4.0b5
-------

- Fix overflow in Python server write by sending ACK messages for each chunk if
  more than one chunk in the message.  Moreover, reduce the chunk size to 2 KB
  from 4 KB and remove the imp module from default modules of the terminal as
  it is removed from Python 3.12.

1.4.0b4
-------

- Fix RawPythonShell problem with Python 3.12 by removing superfluous output
  from the terminal caused the new return values from termios.tcsetattr and/or
  tty.setraw.

1.4.0b3
-------

- Fix the hanging problem in RemoteShell by removing extra
  ANSI CSI escape sequences in bash terminal prompt texts
  of different OS

1.4.0b2
-------

- Fix Windows compatibility
- Add option for custom proxies to TerminalPools

1.4.0b1
-------

- Add remote shell that uses paramiko in both linux and windows to setup remote
  ssh connection

- Add kubernetes shell that access the pods bash terminal by exec



1.3.2
-----

- Change prompt setting in BashShell so that the prompt is not literally
  shown in command history, otherwise listing command history could lead
  to incorrect match when reading command output until prompt is found.

1.3.1
-----

- Fix pexpect TypeErrError when terminal has logfile defined.

- Fix pexpect can't find prompt when KeyauthenticatedSshShell initial_prompt
  attribute is string.

1.3.0
-----

- Refactor BashShell init_env parameter, alias python command executing
  is added as option

- Add new parameter python_command to SelfRepairingSession and
  InteractiveSessionExecutor classes' constructor.

1.2.9
-----

- Use Alpine Linux in docker-robottests instead of Debian

1.2.8
-----

- Fix BashShell banner reading error in slow shells by adding banner_timeout
  keyword argument

- Fix hanging of the start in case in case BashShell value of tty_echo is True
  while in reality the terminal echo is off

1.2.7
-----

- Add stability tests documentation back

- Improve logging by moving and requiring all logging to be under
  'crl.interactivesessions' logger.

- Make _RemoteProxy and _RecursiveProxy default timeouts configurable

1.2.6
-----

- Raise FatalPythonError in MsgPythonShell.exec_command in case the remote
  server has failed

1.2.5
-----

- Fix python 2 & 3 compatibility for SelfRepairingSession

1.2.4
-----

- Acknowledge server ID reply in start of MsgPythonShell

1.2.3
-----

- Set sys.stdout.fileno() blocking in remote

1.2.2
-----

- Fix remote PythonServer failure in case stdout is not writable

1.2.1
-----

- Stop using terminal after fatal failure from MsgPythonShell

1.2.0
-----

- Improved test coverage and added python 3 to setup

1.1.7
-----

 - Stop using terminal after fatal failure from MsgPythonShell

1.1.6
-----

- Implement python 3 compatibility

1.1.5
-----

 - Make MsgPythonShell more robust

1.1.4
-----

 - Convert string to float in set_python_short_timeout

1.1.3
-----

 - Correct terminal leak in RemoteRunner

1.1.2
-----

 - Make Python shell short_timeout configurable

1.1.1
-----

 - Add contribution links to README

1.1
---

 - Add initial content
