.. Copyright (C) 2019, Nokia

.. _implementation-plan:

Implementation Plan
-------------------

Obviously first can be independently implemented :ref:`stagecrew` and
:ref:`termshells`. In :ref:`stagecrew` independent parts are the *importer* and
*transport-concurrency* pair. After this, the actual actor system can be
implemented with a single actor (e.g. command executor). Then the rest of the
:ref:`stagecrew` can be implemented. Finally, :ref:`termactors` and
:ref:`remoterunner` can be implemented.
