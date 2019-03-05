import logging
import os
import mock
from .terminalmockos import (
    AttrContextBase,
    AttrMockOsBase)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class ChunkContext(AttrContextBase):

    @property
    def client_attr(self):
        return 10

    @property
    def server_attr(self):
        return 10

    @staticmethod
    def _mock_os_factory():
        return ChunkMockOs()

    def _os_patcher(self):
        return mock.patch('os.read', side_effect=self._mock_os.read)


class ChunkMockOs(AttrMockOsBase):
    def __init__(self):
        super(ChunkMockOs, self).__init__()
        self._read = os.read

    @property
    def _default_value(self):
        return 10000000

    def read(self, fd, n):
        LOGGER.debug('ChunkMockOs: reading chunk min(%d, %d) from %d',
                     self._attr, n, fd)
        return self._read(fd, min(self._attr, n))
