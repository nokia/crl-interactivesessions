.. Copyright (C) 2019, Nokia

CHANGES
=======
1.1.6
-----
- Convert relative paths of src/crl/interactivesessions/shells/__init__.py to
  python 3 compatible
- Change the python 2 import StringIO to from io import StringIO in the following modules in /interactivesessoins: runnerterminal.py, RunnerHandler.py.
- Changed runnerterminal.py basestring in HANDLED_TYPES to string_types from module six
- Changed the relative import of daemonize in /interactivesessions/_remoterunnerproxies.py to python 3 compatible
- Changed the relative import of patch_subprocess in /tests/conftest.py to python 3 compatible
- Changed self.pterm.before.decode('utf-8') to self.pter.before in method _get_terminal_output in Object _remoteFileProxy in module _filecopier.py
- Added python2to3compatibility.py module to remotemodules directory.

- In AutoRecoveringTerminal, at method _retry, changed error variable e to broken_exceptions
- In interactivesessions/runnerexceptions.py added missing pass statement to Ses  sionInitializationFailed exception
- Added exception variable exc to /interactivesessions/autorecoveringterminal.py since python 3 cleares variable after raise as
- Changed next call in shells/terminalclient method send_and_receive to support python 3
- Added itertools from six to /interactivesessions/runnerterminal.py
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
