.. Copyright (C) 2019, Nokia
.. _termactors:

termactors
----------

The repository *termactors* contains actor implementation which uses
:ref:`stagecrew` and :ref:`termshells`. In this actor system *stageman* creates
for each terminal the following built-in actors:

 - terminal driver reader

 - terminal driver writer

 - controlling terminal reader

 - controlling terminal writer

 - controlling terminal manager

In principle, it would be possible to survive with two actors alone so that the
driver side and controlling terminal side actors are merged to single actor in
both cases. However, this may cause slowness as actor can handle only one
message a time. It would be of course possible to implement terminal driver and
the controlling terminal parts without actors involved but that would break the
all-actor idea.

Basically, *stageman* takes the role of the current *terminalpools*.  It
manages the terminal resources according to given boundary conditions.

.. _termactorterminal:

Terminal
^^^^^^^^

New terminal can be created in the controlling terminal. For that purpose
modified terminal driver reader and driver writer has to be created. A new
terminal class is needed as well. Using this type of the terminal, it is
possible to branch multiple new shells from remote hosts via single terminal.
This is possibly a bit slower solution in communication but the spawning can be
faster.  With this fashion it is also possible to limit number of the
connections required from the single host. Especially in case the SUT cluster
is large this is often a problem as the maximum number of SSH connections is
limited. This solution is separate from the :ref:`paramikospawn`.

Another independent terminal actor solution is to provide only the terminal
driver and writer without anything in the controlling terminal side.  In this
fashion, the pure terminal can be used for e.g. streaming test output of the
executed commands. This type of the solution is required e.g. by Moler_.

.. _`Moler`: https://github.com/nokia/moler
