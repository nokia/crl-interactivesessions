import logging
import time
import sys
import os
import select
import fcntl
if 'chunkcomm' not in globals():
    from . import chunkcomm
    from . import compatibility


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [chunkcomm, compatibility]
LOGGER = logging.getLogger(__name__)


class ServerComm(chunkcomm.ChunkWriterBase, chunkcomm.ChunkReaderBase):

    _sleep_in_broken_systems = 0.00005

    def __init__(self, infd, outfile):
        chunkcomm.ChunkReaderBase.__init__(self)
        self.infd = infd
        self.outfile = outfile
        self._msgcaches = None
        self._sleep_before_read = 0
        self._set_nonblocking_infd()
        self._write_meth = (self.outfile.buffer.write
                            if compatibility.PY3 else
                            self.outfile.write)

    def _set_nonblocking_infd(self):
        fl = fcntl.fcntl(self.infd, fcntl.F_GETFL)
        fcntl.fcntl(self.infd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def set_msgcaches(self, msgcaches):
        self._msgcaches = msgcaches

    def _read(self, n):
        while True:
            r, _, _ = select.select([self.infd], [], [], *self._msgcaches.timeout_args)
            self._msgcaches.send_expired()
            if r:
                try:
                    return self._read_sleep_if_needed(n)
                except (OSError, IOError):
                    self._sleep_before_read = self._sleep_in_broken_systems

    def _read_sleep_if_needed(self, n):
        if self._sleep_before_read:
            time.sleep(self._sleep_before_read)
        return os.read(self.infd, n)

    def _write(self, s):
        self._write_meth(s)

    def _flush(self):
        self.outfile.flush()

    @classmethod
    def create(cls, outfile):
        return cls(sys.stdin.fileno(), outfile)
