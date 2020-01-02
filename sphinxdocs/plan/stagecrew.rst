.. Copyright (C) 2019, Nokia
.. _stagecrew:

Stagecrew
---------

The library *stagecrew* provides actor system library, test support and tools for
creating actor systems for testing purposes. It contains also fully functional
*thread* and *process* based actor systems for unit testing purposes.

The actor system of the *stagecrew* is managed via *stageman* built-in top
level actor. The implementation of the *stageman* actor is an actor system
specific. A simple implementation for unit testing is provided.

The actor system tools and libraries contain at least the following building
blocks:

 - abstract transport

 - abstract concurrency

 - implementation for importer

 - abstract actor

 - the following actors:

     - stageman

     - file manager

     - command executor

     - Python object proxy

     - logging

     - reminder

Transport and concurrency
^^^^^^^^^^^^^^^^^^^^^^^^^

Abstraction for *concurrency* is just a class which implements *run* method so
that the code block associated with *start* is executed concurrently. This is
similar to *multiprocessing.Process* and *threading.Thread*.

The abstraction for the *transport* is defined so that if the code block of the
*start* of the *concurrency* contains *transport* implementation, then the
*transport* can send bytes to any address given in *start* (or later on
*receive*). It can also receive bytes from any *concurrency* execution which has
the address of the *transport* object.

Transport implementation
^^^^^^^^^^^^^^^^^^^^^^^^

One implementation for transport is provided by *stagecrew*. This
implementation is Unix Domain Socket (UDS) based. Each execution unit with
transport has unique file name (in e.g. current working directory) for UDS.
For more detail implementation there are many Python examples using sockets and
especially UDS (e.g.  `UDS socket example`_, `Python sockets`_ and
`TCP sockets`_).

The listening of the socket is done in a separate thread (listener thread).
This thread may also manage all connections which it passes to the *select* (or
*poll*) call. Actual receiving of the message is done in the single worker
thread or in the main thread. Alternatively first on listener thread, then on
receiver thread and only after that on the worker thread. The receiver thread
is possibly better as in that case the sending would not block even if the
capacity of the UDS is exceeded.  The socket on receiving side should be made
non-blocking. However, the sockets for sending messages should probably be
blocking: one thread per address. The sending part may block (e.g. if the other
end is slow in receive) It would be better to use internally *dequeue* and
*memoryview* as there is no need to pass Python objects in transport but just
bytes.

.. _`UDS socket example`: https://pymotw.com/3/socket/uds.html
.. _`Python sockets`:  https://docs.python.org/3/library/socket.html
.. _`TCP sockets`: https://steelkiwi.com/blog/working-tcp-sockets/

Concurrency implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^

Two implementations are provided: *threading.Thread* and
*multiprocessing.Process* based. These both are meant mainly for the testing
purposes, but can be used as building blocks for useful implementations in
:ref:`termactors`.

Implementation for importer
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The basic idea is that the modules are stored *sys.modules* according to their
paths in the local file system. This ensures good enough uniqueness even though
it cannot be extended to *setuptools* like package management.  Partial
implementation for this importer is in issue-13_.

Another way is to write a completely new importer similarly than described in
`importer protocol`_ and in `python imports`_.

The basic idea is to re-import the required module with the new name created
from the full file path of the module. The modules which should be imported
along with the given module are informed via *IMPORTS* global variable in the
module.  In more detail, *IMPORTS* contains list of the functions, classes or
modules imported via import statements. After creating the module from the
source, this *IMPORTS* is checked and the associated modules are imported
recursively.  The associated modules can be found directly if the import is a
module otherwise *__module__* attribute is looked and the associated module is
either imported or looked from *sys.modules*. The latter is used e.g.
in *pickle.whichmodule* function.

Finally, the attributes in the module listed in *IMPORTS* are replaced with the
attributes from the importer imported modules instead of built-in.

This induced bundle of the modules can then be transferred anywhere and
re-imported using tailored *sys.meta_path* finder and loader. This
process is a bit more tricky because the meaning for especially non-package
relative imports is very specific to the original location of the module.
Therefore, the imports should be done one-by-one in the reverse dependency order.
Essentially, the finder should have the context of the currently imported
module. Using that, it can then map imports to modules imported previous import
steps.

.. _`issue-13`: https://github.com/petrieh/crl-interactivesessions/tree/issue-13
.. _`python imports`: https://blog.ffledgling.com/python-imports-i.html
.. _`importer protocol`: https://www.python.org/dev/peps/pep-0302/#specification-part-1-the-importer-protocol

Abstract actor
^^^^^^^^^^^^^^

Similarly like in Pykka_, the following built-in methods could be
implemented:

 - on_start

 - on_stop

 - on_failure

From Thespian_ the special *DeadLetter* can be used in case the message cannot
be delivered.

Moreover, the actor could respond with acknowledgement when it receives the
message.  It is quite obvious that the message handling may block
indefinitely. It is important to be able to distinguish between the cases
where the actor never receives the actual message (which should cause
DeadLetter in configured timeout) and that the action itself hangs.

The transport layer may use also acknowledgements but it this is not
implemented in *stagecrew*. The reasoning is that it UDS rather robust.

As in Pykka_ actors are called via proxies which are returned in the actor
creation.  The proxy has the same public methods than the actual actor. The
actor system transforms the proxy calls to the messaging between the proxy and the
Actor. The return values of the calls are either *futures* or alternatively, in
the call the handler method for the response can be given. The latter is
obviously for the proxy calls from the actor. In the actor, the *futures*
cannot be used nicely as the *get* method expects message to be received. This
is a deadlock, because the receiving of the messages are done in the single
thread. However, the *futures* are useful from calls from the outside of the
actor system as there it is possible to receive the message independently
from the actor receive system.

In addition to the simple *get* method in the *future* like implemented in
Pykka_ it would be useful to implement iterator *future*. The reasoning is
simply that the actor may send multiple messages in the tell fashion. The
receiving of such stream of the messages would be rather clumsy with *get*
only.


Stageman
^^^^^^^^

Simple implementation for the *stageman* actor is provided. The duty of the
*stageman* is to manage actor system. It can for example modify transport on
need bases. It can also kill malfunctioning actors and stop the actor system on
need bases. All actor creations and closings are reported to *stageman* so that
it has up to date information about the actor system.

File manager
^^^^^^^^^^^^

The file manager actor is for file and directory copying between actors.

Command Executor
^^^^^^^^^^^^^^^^

The command executor is for executing shell commands via *subprocess*.

Python object proxy
^^^^^^^^^^^^^^^^^^^

Python object proxy actor creates Python objects and stores them into the state
of it. The methods of the proxies can be called similarly like in
*crl.interactivesessions.remoteproxies* proxies. The basic idea is to implement
replacement for the current global store for the proxies.

Logging
^^^^^^^

Logging should be built-in functionality in the actor base. In addition, it is
useful to write simple implementation as an actor for the logging.  Basically,
this means that the actor base should should get the address of the logging
actor (of course configurable). In *stagecrew* the implementation could be
simply writing the received logs to the specified file.

Reminder
^^^^^^^^

Reminder actor implements timeouts. This could be built-in functionality. For
example in case the actor asks other actor, then the handler could create
reminder actor and ask. If the reminder returns before the asking response,
then the timeout handler is called otherwise the actual response handler.

Actor system messaging
^^^^^^^^^^^^^^^^^^^^^^

The messages are basically sequentially numbered Python objects serialized by
*pickle*.  The messages contains also the header: the sender and the target
address. The actor system may request again messages if it notices gaps. The
actor creation message may contain meta-data which can be used for deciding
e.g. how and where the new actor should be launched. For example, in meta-data
can be given the instruction to start the actor in the daemon mode.

In more detail, the actor messages are tuples containing method names
and proprietary serialization of the arguments. Basically, all Python objects
are serialized with *pickle*. The exceptions are the proxy objects, string and
bytes like objects. String and bytes have special serialization because they
have to work still on cross Python 2 and Python 3 platforms.

.. include:: references.rst
