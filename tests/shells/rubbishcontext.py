import abc
import logging
import os
import six
from .terminalmockos import (
    WriteContextBase,
    AttrMockOsBase)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class RubbishContextBase(WriteContextBase):

    @property
    def client_attr(self):
        return b''

    @property
    def server_attr(self):
        return b''

    @abc.abstractproperty
    def expected_rubbish(self):
        """Return expected 'rubbish' (i.e. an added string) in IO.
        """

    @staticmethod
    def _mock_os_factory():
        return RubbishMockOs()


class ClientRubbishContext(RubbishContextBase):

    @property
    def expected_rubbish(self):
        return self.client_attr[:10]

    @property
    def client_attr(self):
        return b'rubbish in client write'


class ServerRubbishContext(RubbishContextBase):

    @property
    def expected_rubbish(self):
        return self.server_attr[:10]

    @property
    def server_attr(self):
        return b'rubbish in server write'


class RubbishMockOs(AttrMockOsBase):
    def __init__(self):
        super(RubbishMockOs, self).__init__()
        self._write = os.write

    @property
    def _default_value(self):
        return b''

    def write(self, fd, s):
        LOGGER.debug('RubbishMockOs: write (%s) + (%s) to %d', self._attr, s, fd)
        out = self._attr + s
        self._write(fd, out)
