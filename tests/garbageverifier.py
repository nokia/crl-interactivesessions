import pytest


__copyright__ = 'Copyright (C) 2019, Nokia'


class GarbageVerifier(object):
    def __init__(self, runnerterminal, proxy_factory):
        self._runnerterminal = runnerterminal
        self._proxy_factory = proxy_factory

    def reset_session(self, session):
        self._runnerterminal.initialize(session)

    def verify_garbage_cleaning(self, number_of_times):
        for _ in range(number_of_times):
            self._create_max_proxies_and_trigger_cleaning()

    def _create_max_proxies_and_trigger_cleaning(self):
        handles = self.create_max_proxies()
        self._trigger_garbage_cleaning(handles)

    def create_max_proxies(self):
        handles = [h for h in self._generate_handles()]
        self._assert_all_proxies_exists(handles)
        return handles

    def _generate_handles(self):
        for _ in range(self._runnerterminal.MAX_GARBAGE):
            p = self._proxy_factory(self._runnerterminal)
            handle = p.get_proxy_handle()
            self._runnerterminal.session.mock_run_cmdline(handle)
            yield handle

    def _trigger_garbage_cleaning(self, handles):
        """Trigger garbage cleaning in case garbage length is already maximum.
        """
        self._proxy_factory(self._runnerterminal)
        self._runnerterminal.run('None')
        self.assert_all_proxies_cleaned(handles)

    def _assert_all_proxies_exists(self, handles):
        for h in handles:
            self._runnerterminal.session.mock_run_cmdline(h)

    def assert_all_proxies_cleaned(self, handles):
        for h in handles:
            with pytest.raises(KeyError):
                self._runnerterminal.session.mock_run_cmdline(h)
