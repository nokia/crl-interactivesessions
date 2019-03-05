.. Copyright (C) 2019, Nokia

Stability test execution
------------------------

Stability tests are created for memory leak checking. Currently this is semi-manual.

Please start the robot test case first with::

# tox -e stability

Then, in other terminal, check what is the pid of the python process::

# pidof python

Alternatively, you can use::

# pstree -al | less

Please note that there are at least two python processes: one for running
the robot test case and the other running the hello command in a loop in python
So, you likely want to check the pid of latter one::

# watch cat /proc/<pid>/status

If you like to check memory leaks, please verify that VmSize does not increase
(It may well go up a bit before the garbage collector is activated so
please verify that the maximum does not increase over the time).
