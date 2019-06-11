import os
import filecmp
from builtins import range

__copyright__ = 'Copyright (C) 2019, Nokia'


class FilesDiffers(Exception):
    pass


def create_random_file(filename, filesize, buffersize=32768):
    with open(filename, 'wb') as f:
        numberofchunks = int(filesize) // int(buffersize)
        lastchunksize = int(filesize) % int(buffersize)
        for _ in range(numberofchunks):
            f.write(os.urandom(buffersize))
        if lastchunksize:
            f.write(os.urandom(lastchunksize))


def diff_files(a, b):
    if not filecmp.cmp(a, b):
        raise FilesDiffers('File {a} differs from {b}'.format(a=a, b=b))


def remove_files(filenames):
    for filename in filenames:
        os.remove(filename)
