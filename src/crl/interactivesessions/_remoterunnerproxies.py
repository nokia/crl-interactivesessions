from crl.interactivesessions.remoteimporter import RemoteImporter
from . import daemonizer


__copyright__ = 'Copyright (C) 2019, Nokia'


class _RemoteRunnerProxies(object):
    def __init__(self, terminal):
        self.terminal = terminal
        self.killpg = terminal.create_empty_remote_proxy()
        self.getpgid = terminal.create_empty_remote_proxy()
        self.setsid = terminal.create_empty_remote_proxy()
        self.environ = terminal.create_empty_remote_proxy()
        self.popen = terminal.create_empty_recursive_proxy()
        self.pipe = terminal.create_empty_remote_proxy()
        self.iter_until_empty = terminal.create_empty_recursive_proxy()
        self.daemon_popen = terminal.create_empty_remote_proxy()
        self.proxies = [self.killpg,
                        self.getpgid,
                        self.setsid,
                        self.popen,
                        self.pipe,
                        self.iter_until_empty,
                        self.environ,
                        self.daemon_popen]
        self.proxy_timeout = 30  # for all non-blocking calls
        self.remoteimporter = RemoteImporter(self.terminal,
                                             self.proxy_timeout)
        self._setup_proxy_timeout()

    def prepare(self):
        self._import_libraries()
        self.remoteimporter.prepare()
        self._setup_proxies()

    def _import_libraries(self):
        self.terminal.import_libraries('os', 'subprocess')

    def _setup_proxies(self):
        self._setup_subprocess_proxies()
        self._setup_os_proxies()
        self.iter_until_empty.set_from_remote_proxy(
            self.terminal.get_recursive_proxy(
                RemoteImporter.get_remote_obj('iter_until_empty')))
        self._setup_daemonizer_proxy()

    def _setup_subprocess_proxies(self):
        self.popen.set_from_remote_proxy(
            self.terminal.get_recursive_proxy('subprocess.Popen'))
        self.pipe.set_from_remote_proxy(
            self.terminal.get_proxy_object('subprocess.PIPE', None))

    def _setup_os_proxies(self):
        self.killpg.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.killpg', None))
        self.getpgid.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.getpgid', None))
        self.setsid.set_from_remote_proxy(
            self.terminal.get_proxy_object('os.setsid', None))
        self.terminal.run_python('_dictenviron = dict(os.environ)')
        self.environ.set_from_remote_proxy(
            self.terminal.get_proxy_object('_dictenviron', None))

    def _setup_daemonizer_proxy(self):
        self.remoteimporter.importmodule(daemonizer)
        self.daemon_popen.set_from_remote_proxy(
            self.terminal.get_proxy_object('daemonizer.daemon_popen', None))

    def _setup_proxy_timeout(self):
        for proxy in self.proxies:
            proxy.set_remote_proxy_timeout(self.proxy_timeout)
