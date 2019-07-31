"""Robot Framework variable file for robottests.

This is an example how to create
:class:`crl.interactivesessions.remoterunner.RemoteRunner` shell dicts HOST1
and HOST2 so that HOST1 and HOST2 can be accessed via RemoteRunner. Moreover,
it defines SUDOSHELL, so that if appended to HOST1 shell, the commands are
executed as root.

..note::

    Hosts HOST1 and HOST2 shall not share the same home directory.
"""

__copyright__ = 'Copyright (C) 2019, Nokia'

DICT__HOST1 = {'host': 'localhost', 'user': 'python2user', 'password': 'python2testing'}
DICT__HOST2 = {'host': 'localhost', 'user': 'python3user', 'password': 'python3testing'}
SUDOSHELL = {'shellname': 'BashShell', 'cmd': 'sudo /bin/bash'}
