"""Example Robot framework variable file for robottests.

This is an example how to create
:class:`crl.interactivesessions.remoterunner.RemoteRunner` shell dictionaries
HOST1 and HOST2. Moreover, in order to run all tests, two hop targets are
needed. For two hop targets, please define GW, HOST1_VIA_GW and
HOST<nbr>_VIA_GW. HOST<nbr>_VIA_GW can be the same host as HOST<nbr>. The
requirement is that HOST<nbr>_VIA_GW is accessible via GW. It also defines
SUDOSHELL, so that if appended to HOST1 shell, the commands are executed as
root.

..note::

    Hosts HOST1 and HOST2 shall not share the filesystem.
"""
__copyright__ = 'Copyright (C) 2019, Nokia'

HOST1 = {'host': 'example1', 'user': 'user1', 'password': 'anypassword'}
HOST2 = {'host': 'example2', 'user': 'user2', 'password': 'anypassword'}
SUDOSHELL = {'shellname': 'BashShell', 'cmd': 'sudo /bin/bash'}
GW = {'host': 'examplegw', 'user': 'gwuser', 'password': 'anypassword'}
HOST1_VIA_GW = {'host': 'example1-via-gw', 'user': 'user1', 'password': 'anypassword'}
HOST2_VIA_GW = {'host': 'example2-via-gw', 'user': 'user2', 'password': 'anypassword'}
