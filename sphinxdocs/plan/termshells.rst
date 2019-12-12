.. Copyright (C) 2019, Nokia
.. _termshells:

termshells
----------

The repository termshell contains the core part of the crl.interactivesessions:

- shellstack f.k.a. InteractiveSession

- Shells including all registered shells and base shell but excluding e.g.
  *msgpythonshell* and associated *remotemodules*

The terminal, f.k.a. *pexpect.spawn* class shall be extended. The terminal
should contain the controlling terminal state. The attributes associated with
the controlling terminal state such as *tty_echo* are transfered to this new
class. The shells may contain still desired terminal state or initial terminal
states. However, the most part of the terminal helper methods should be
transferred implemented in shell should be transfered to this terminal.
Moreover, a new base class for the terminal should be written in order to make
unit testing of the shells easier.

The shellstack should be merely a simple stack manager for the shells, nothing
else. The idea is to try to keep the *push* and *pop* methods simple and
transfer the special implementation to the shells and to the terminal. The
tight coupling to *pecpect* should be removed and instead *shellstack* should
be given the terminal factory or spawner in the *__init__* or in the separate
method.
