.. Copyright (C) 2019, Nokia

Current Problems
----------------

The current code is hard to read, buggy and difficult to maintain and extend.
The main root cause for current rather complex and layered code is that the
code has been extended to solve many separate problems different from the
original purpose.

Originally the code was created for testing proprietary
command line interface (CLI).  Essentially, the idea was to first open SSH
connection to the system under test (SUT) and then start CLI. This caused
rather clumsy code where the connection opening was mixed with the CLI start.
To solve this problem, terminal states in *pexpect* were named according to the
controlling terminal shell. Moreover, the state changes from the previous
terminal shell state to the next shell were implemented to this shell class.
For the management of these shells the *InteractiveSession* for stacking the
shells was created.

The next problem where the same solution was tried was the remote command
execution.  For that purpose *SelfRepairingSession* was created. It introduced
a mechanism for creating and recreating the stack of the shells using
*InteractiveSession*.  Recreation was needed as quite often the SUT was
rebooted during tests.

Then the library was extended so that it would be able to proxy Python objects
of SUT. Mainly this was used for testing REST API which was accessible only
from SUT.  In more detail, requests library methods were proxied transparently
so that instead of e.g. *requests.get* directly issuing REST request to host
the proxy system first transferred via SSH the request to SUT. Finally, the
actual *requests.get* object was called in the host. For that purpose,
remoteproxies, *autorecoveringterminal*, *runnerterminal* and *RunnerHandler*
modules were created.

Finally, *SelfRepairingSession* idea was replaced by the remoteproxies.  For
that purpose, an implementation for *RemoteRunner* was created. The basic
reasoning was that *crl.remotescript* did not provide good way to run commands
over multiple hops.

Some refactoring has been done for replacing mostly direct *pexpect* calls with
the client-server type of messaging.

As consequence, especially *RemoteRunner* is implemented using improper
building blocks. The suboptimal solution is the result of this. The users of
the *RemoteRunner* complain these problems rather frequently:

  - File management does work only for small files

     - copying directories with large number of files is very slow

     - large file (gigabytes) copying may hang

     - The main reason for file management problems is that
       direct terminal read and write is used without any proper
       error handling and recovery. This causes robustness problems.

  - Timeouts are difficult to manage (because of the layers and large number
    of proxies used)

  - Command execution requires around many different synchronous calls to SUT
    which causes unnecessary slowness.

  - Diagnostics is difficult as low level messaging is visible in logs. The
    main problem here is that the layers are not properly separated from each
    other.
