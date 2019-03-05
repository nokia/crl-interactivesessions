.. Copyright (C) 2019, Nokia

.. _examples:

Examples of  *crl.interactivesessions* usage
=================================================

.. _backgroundrunner:

Running Commands In Background
------------------------------

This example demonstrates simple background execution of *Linux Shell*
commands. The implementation uses the transparent proxies which
are created by
:class:`crl.interactivesessions.autorunnerterminal.AutoRunnerTerminal`.
Please see the code from :ref:`backgroundrunnercode`.

By the default :ref:`remoteproxies` proxies are blocking until the timeout expires.
However, in this example the proxy of :meth:`subprocess.Popen.communicate` is
set to asynchronous mode:

.. literalinclude:: ../robottests/BackgroundRunner.py
    :pyobject: BackgroundRunner._communicate

The example usage of the :ref:`backgroundrunnercode` class *BackgroundRunner*
is here:

    >>> from crl.interactivesessions.InteractiveSession import SshShell
    >>> runner = BackgroundRunner(SshShell(
    ... '10.7.20.22', username='ncioadmin', password='admin_pass'))
    >>> handle = runner.run_in_background('echo Hello World!;sleep 100')
    >>> runner.terminate_and_get_response(handle)
    RunResponse(ret=-15, out='Hello World!\n', err='')


Copying Files To/From Remote Targets
------------------------------------

This example demonstrates binary file copying to and from the remote targets
using
:mod:`crl.interactivesessions.autorunnerterminal`
provided proxies.

In more detail a simple file handle like contextmanager is created which opens
the remote file is created. This is done in the following fashion.

.. literalinclude:: ../robottests/FileCopier.py
    :pyobject: _RemoteFile

The call *self.terminal.initialize_if_needed* will open a new terminal session
in case it is either never opened or for some reason broken.

A simple roundtrip example is here:

    >>> with open('hello.txt', 'w') as f:
    ...     f.write('Hello World!')
    ...
    >>> from crl.interactivesessions.InteractiveSession import SshShell
    >>> copier = FileCopier(SshShell(
    ... '10.7.20.22', username='ncioadmin', password='admin_pass'))
    >>> copier.copy_file_to_remote('hello.txt', 'hello_remote.txt')
    >>> copier.copy_file_from_remote('hello_remote.txt', 'hello_local.txt')
    >>> with open('hello_local.txt') as f:
    ...     f.read()
    ...
    'Hello World!'
    >>>

Please see the full source from :ref:`filecopiercode`.


Lazy Initialization of Remote Proxies
-------------------------------------

There is no need to initialize the session for the
:class:`crl.interactivesessions.remoteproxies._RemoteProxy` proxies
before the actual usage of the proxy. This can be achieved by calling
either
:meth:`crl.interactivesessions.autorunnerterminal.RunnerTerminal.create_empty_remote_proxy`
or
:meth:`crl.interactivesessions.autorunnerterminal.RunnerTerminal.create_empty_recursive_proxy`.
The access to proxies of this type will automatically tricker the initialization
process. In this case, it is recommended that the prepare method copies the
new proxy content over the old proxies so that the references to the proxies
can be still used. This can be achieved by using the
:meth:`crl.interactivesessions.remoteproxies._RemoteProxy.set_remote_proxy_from_proxy`.

Please see the details from :ref:`backgroundrunnercode`.

.. _backgroundrunnercode:

BackgroundRunner Code
---------------------

.. literalinclude:: ../robottests/BackgroundRunner.py
    :linenos:


.. _filecopiercode:

FileCopier Code
---------------

.. literalinclude:: ../robottests/FileCopier.py
    :linenos:
