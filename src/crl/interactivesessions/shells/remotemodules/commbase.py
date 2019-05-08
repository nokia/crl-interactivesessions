__copyright__ = 'Copyright (C) 2019, Nokia'


class CommReaderBase(object):

    @property
    def readerror(self):
        """Return reading error class."""
        raise NotImplementedError()

    def read(self, n):
        """Read at most *n* bytes."""
        raise NotImplementedError()

    def read_until_size(self, n):
        """Read until exactly *n* bytes is read."""
        raise NotImplementedError()


class CommWriterBase(object):
    def write(self, s):
        """Write string s"""
        raise NotImplementedError()
