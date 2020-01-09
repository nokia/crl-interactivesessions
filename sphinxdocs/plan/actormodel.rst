.. Copyright (C) 2019, Nokia
.. _actormodel:

Actor Model
-----------

Actors in this case are concurrently executing Python objects with a mailbox.
They handle messages in the mailbox one by one.  Moreover, they do not provide
any other interfaces than this mail system. The main principles are described
in `Actor model`_. When the message arrives the actor can:

  1. Send messages to actors

  2. Change the state

  3. Create new actors

Essentially, as the actor can send messages only to those actors which address
it has received earlier, there is no need for the hard coded messaging protocol
between the actors. It is enough that the actor knows the protocol of those
actors it is aware of.

Actor model in testing
^^^^^^^^^^^^^^^^^^^^^^

For example Testing and Test Control Notation (TTCN_) follows the ideas of the
`Actor model`_. In this case the reasoning to use Actor model like system are
rather similar to TTCN_: concurrency is needed for simultaneous testing
multiple nodes of the system under test (SUT).  Moreover, as in TTCN_, there is
a need for concurrent logging actor like capability.

Python implementations
^^^^^^^^^^^^^^^^^^^^^^

There are at least two good actor system Python implementations: Pykka_ and
Thespian_. However, both of them are created for production level actors while
testing actors are needed. This makes the direct usage of these implementations
difficult.

While it is not easy to use these implementation directly, some parts of them
can be used. Essentially Pykka_ provides very nice interface to the actor
system. It introduces proxy interface with some built-in methods (e.g. *on_exit*).
Moreover, the public methods of the actor are directly callable via proxy
objects. The return values of the proxy calls are futures.

In the other hand, Thespian_ is tailored for larger systems where the actors
can run in multiple hosts. The interface is not so nice as in Pykka_ but it has
some additional nice features like dead letters which are sent in case the
message cannot be delivered.  This is also important in this case as in the
testing, common problem is lack of connectivity to the system under test SUT
(for example due to SUT reboot). It is not possible to take fully Thespian_
implementation as here the actors are meant to be transient while in Thespian_
the actors are meant to be persistent.

.. include:: references.rst
