.. Copyright (C) 2019, Nokia

CHANGES
=======

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
