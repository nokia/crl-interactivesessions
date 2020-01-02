.. Copyright (C) 2019, Nokia

Solution
--------

The first idea to solve the problem was to improve client-server model already
created between terminal driver and the controlling terminal. However, this
would then quite clearly make unecessary tight coupling between the messages
and the client-server implementation. In the other hand, for retrieving logs
during execution from background commands, it would be better to run clients
also concurrently. Moreover, gathering logs (for diagnostics) should be
possible concurrently.

The terminal is used for many different purposes in *RemoteRunner* and each of
these would require different solution. It would be good that the solution
could be created, maintained and extended without any need to touch the
framework. This would not be possible with the current client-server solution
where the messaging is fixed.

One option, instead of client-sever model, the :ref:`actormodel` could be used.
In the :ref:`actormodel` the transport and concurrency are fully separated from
the business logic of the actors. This would fit nicely for *RemoteRunner* case
as then the command execution, the file mangement and the proxy calls can be
implemented as actors. This would have the following benefits:

 - Actors are by their nature always concurrent, so the background execution
   would be very easy to implement as well as background file copying.

 - The transport and the concurrency can be implemented in simplified manner
   for unit testing purposes, which would simplify unit testing of the
   components of *RemoteRunner*

 - For diagnostics a logging actor could be created.

 - New feature development and maintanence of the *RemoteRunner* does not need
   to touch the :ref:`actormodel` framework.

 - Actors could be used more easily programmatically without a need to fixed
   RemoteRunner API made for Robot Framework.

As a downside, quite much new code is needed. Unfortunately, there is no good
known :ref:`actormodel` implementation for Python suitable for this purpose and
therefore there is currently not known any other way than writing the actor
system from scratch. Luckily, it is possible to use some of the ideas of the
existing Python actor system libraries.

Because of layers and complex structure of the current *RemoteRunner* solution,
it would be better to create new libraries for implementing the solution. The
solution libraries are described in:

 - :ref:`stagecrew`,

 - :ref:`termshells`,

 - :ref:`termactors` and

 - :ref:`remoterunner`
