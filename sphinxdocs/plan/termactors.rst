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
