import os
import mock


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockKillpg(object):
    def __init__(self, ignoresignals=None, side_effect=lambda: None):
        self.ignoresignals = ignoresignals or []
        self.originalkillpg = None
        self.killpgpatcher = None
        self.side_effect = side_effect
        self._setup_patcher()

    def _setup_patcher(self):
        self.originalkillpg = os.killpg
        self._define_killpgpatcher()

    def mock_killpg(self, pid, sig):
        if sig not in self.ignoresignals:
            self.originalkillpg(pid, sig)
        self.side_effect()

    def _define_killpgpatcher(self):
        self.killpgpatcher = mock.patch.object(os, 'killpg',
                                               side_effect=self.mock_killpg)

    def __enter__(self):
        self.killpgpatcher.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.killpgpatcher.stop()
