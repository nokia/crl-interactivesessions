.. Copyright (C) 2019, Nokia

Remote Proxies
==============

Remote proxies provide a Pythonic way to communicate with the
targets connected via :ref:`interactivesession`.

Basically the only requirement is that the remote end is capable
of starting :ref:`pythonshell` in the interactive mode.

In this section the proxy management associated interfaces are
described. Examples of proxies can be found from :ref:`examples`.


AutoRecoveringTerminal
----------------------

.. automodule:: crl.interactivesessions.autorecoveringterminal
    :members:

RunnerTerminal
--------------

.. automodule:: crl.interactivesessions.runnerterminal
    :members:

AutoRunnerTerminal
------------------

.. automodule:: crl.interactivesessions.autorunnerterminal
    :members:
    :show-inheritance:


RunnerTerminal Exceptions
-------------------------

.. automodule:: crl.interactivesessions.runnerexceptions
    :members:

.. _remoteproxies:

Remoteproxies
-------------
.. automodule:: crl.interactivesessions.remoteproxies
    :members: _RemoteProxy, _RecursiveProxy
    :show-inheritance:
