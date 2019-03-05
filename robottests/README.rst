.. Copyright (C) 2019, Nokia

Running and developing Robot framework tests
============================================

To run tests, please first create variable as described in
*examplehosts.py*. Then, execute::

   # tox -e robottests -- -V myhosts.py

For development, use *HOST1* and *HOST2* hosts and make sure
that your change work at least in some Linux systems.
