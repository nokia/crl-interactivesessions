.. Copyright (C) 2019, Nokia

.. _interactivesession:

InteractiveSession
==================

.. automodule:: crl.interactivesessions.InteractiveSession
    :members:
    :show-inheritance:
    :special-members:
    :exclude-members: __dict__,__weakref__, __metaclass__

InteractiveSession Shells
-------------------------

Shells serve as front-ends for the pseudo terminal by providing initialization
and finalization methods of a new shell in the pseudo terminal as well as
the pseudo terminal shell specific functionality.

In this section available shells as well as the base classes for them are
documented.

Shell Abstract Bases
^^^^^^^^^^^^^^^^^^^^

AutoCompletableShell
""""""""""""""""""""
.. automodule:: crl.interactivesessions.shells.autocompletableshell
    :members:
    :show-inheritance:


.. _shell:

Shell
"""""
.. automodule:: crl.interactivesessions.shells.shell
    :members:

Built-In Shells
^^^^^^^^^^^^^^^

BashShell
"""""""""
.. automodule:: crl.interactivesessions.shells.bashshell
    :members:
    :show-inheritance:

NamespaceShell
""""""""""""""

.. automodule:: crl.interactivesessions.shells.namespaceshell
    :members:
    :show-inheritance:


.. _pythonshell:

PythonShell
"""""""""""
.. automodule:: crl.interactivesessions.shells.pythonshell
    :members:
    :show-inheritance:

SshShell
""""""""
.. automodule:: crl.interactivesessions.shells.sshshell
    :members:
    :show-inheritance:

SftpShell
"""""""""

.. automodule:: crl.interactivesessions.shells.sftpshell
    :members:
    :show-inheritance:

KeyAuthenticatedSshShell
""""""""""""""""""""""""

.. automodule:: crl.interactivesessions.shells.keyauthenticatedsshshell
    :members:
    :show-inheritance:

SudoShell
"""""""""

.. automodule:: crl.interactivesessions.shells.sudoshell
    :members:
    :show-inheritance:

Shell Tools
^^^^^^^^^^^

The shells based on :ref:`shell` can be registered via
:ref:`registershell`. The registered shells can be used in the
shell stack container described in :ref:`shellstack`.

.. _registershell:

Registering Shells
""""""""""""""""""

.. automodule:: crl.interactivesessions.shells.registershell
    :members:

.. _shellstack:

Shell Stack Container
"""""""""""""""""""""

.. automodule:: crl.interactivesessions.shells.shellstack
    :members:


MsgReader
"""""""""

.. automodule:: crl.interactivesessions.shells.msgreader
    :members:
