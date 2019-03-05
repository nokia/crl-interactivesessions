import sys
import os
if 'commbase' not in globals():
    from . import commbase
    from . import chunkcomm


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [commbase, chunkcomm]


class ServerComm(chunkcomm.ChunkWriterBase, commbase.CommReaderBase):

    def __init__(self, infd, outfile):
        self.infd = infd
        self.outfile = outfile

    def read(self, n):
        out = os.read(self.infd, n)
        return out

    def read_until_size(self, n):
        buf = ''
        toread = n
        while toread > 0:
            ret = self.read(toread)
            buf += ret
            toread -= len(ret)
        return buf

    def _write(self, s):
        self.outfile.write(s)

    def _flush(self):
        self.outfile.flush()

    @classmethod
    def create(cls, outfile):
        return cls(sys.stdin.fileno(), outfile)
