import abc
import logging
import os
import mock
import six
from .terminalmockos import (
    AttrContextBase,
    AttrMockOsBase)


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class RubbishContextBase(AttrContextBase):

    @property
    def client_attr(self):
        return ''

    @property
    def server_attr(self):
        return ''

    @abc.abstractproperty
    def expected_rubbish(self):
        """Return expected 'rubbish' (i.e. an added string) in IO.
        """

    @staticmethod
    def _mock_os_factory():
        return RubbishMockOs()

    def _os_patcher(self):
        return mock.patch('os.write', side_effect=self._mock_os.write)


class ClientRubbishContext(RubbishContextBase):

    @property
    def expected_rubbish(self):
        return self.client_attr[:10]

    @property
    def client_attr(self):
        return 'rubbish in client write'


class ServerRubbishContext(RubbishContextBase):

    @property
    def expected_rubbish(self):
        return self.server_attr[:10]

    @property
    def server_attr(self):
        return 'rubbish in server write'


class RubbishMockOs(AttrMockOsBase):
    def __init__(self):
        super(RubbishMockOs, self).__init__()
        self._write = os.write

    @property
    def _default_value(self):
        return ''

    def write(self, fd, s):
        LOGGER.debug('RubbishMockOs: write (%s) + (%s) to %d', self._attr, s, fd)
        out = '{rubbish}{s}'.format(rubbish=self._attr, s=s)
        self._write(fd, out)
