import logging
import signal
import errno
from collections import namedtuple
from crl.interactivesessions.InteractiveSession import BashShell
from crl.interactivesessions.autorunnerterminal import AutoRunnerTerminal
from crl.interactivesessions.autorecoveringterminal import (
    AutoRecoveringTerminal)


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


class _OsProxies(object):
    def __init__(self, terminal):
        self.killpg = terminal.create_empty_remote_proxy()
        self.getpgid = terminal.create_empty_remote_proxy()
        self.setsid = terminal.create_empty_remote_proxy()


ResponseHandle = namedtuple('ResponseHandle', ['pro', 'handle'])


RunResponse = namedtuple('RunResponse', ['ret', 'out', 'err'])


class BackgroundRunner(object):
    def __init__(self, shells=None):
        self.terminal = None
        self.popen = None
        self.pipe = None
        self.os = None
        self._initialize(BashShell() if shells is None else shells)

    def _initialize(self, shells):
        self.terminal = AutoRunnerTerminal()
        self.terminal.initialize_with_shells(shells=shells,
                                             prepare=self._prepare)
        self._setup_with_empty_proxies()

    def _setup_with_empty_proxies(self):
        self.os = _OsProxies(self.terminal)
        self.popen = self.terminal.create_empty_recursive_proxy()
        self.pipe = self.terminal.create_empty_remote_proxy()

    def _prepare(self):
        self._import_libraries()
        self._setup_proxies()

    def _import_libraries(self):
        self.terminal.import_libraries('os', 'subprocess')

    def _setup_proxies(self):
        self._setup_subprocess_proxies()
        self._setup_os_proxies()

    def _setup_subprocess_proxies(self):
        self.popen.set_from_remote_proxy(
            self.terminal.get_recursive_proxy('subprocess.Popen'))
        self.pipe.set_from_remote_proxy(
            self.terminal.get_proxy_object('subprocess.PIPE', None))

    def _setup_os_proxies(self):
        self.os.killpg.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.killpg', None))
        self.os.getpgid.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.getpgid', None))
        self.os.setsid.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.setsid', None))

    def run_in_background(self, cmd):
        pro = self.popen(cmd,
                         stdout=self.pipe,
                         stderr=self.pipe,
                         shell=True,
                         preexec_fn=self.os.setsid)
        return self._communicate(pro)

    @staticmethod
    def _communicate(pro):
        communicate = pro.communicate
        communicate.remote_proxy_use_asynchronous_response()
        return ResponseHandle(pro=pro, handle=communicate())

    def terminate_and_get_response(self, handle):
        self._terminate_if_needed(handle.pro)
        out, err = handle.pro.get_remote_proxy_response(handle.handle,
                                                        timeout=10)
        return RunResponse(ret=handle.pro.returncode, out=out, err=err)

    def _terminate_if_needed(self, pro):
        try:
            self.os.killpg(self.os.getpgid(pro.pid), signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                logger.debug('Not terminating: process already terminated')
            else:
                raise
