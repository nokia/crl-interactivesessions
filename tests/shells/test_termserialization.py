import os
import pickle
import base64
import pytest
from crl.interactivesessions.shells.termserialization import (
    b64_pickled_source_from_file,
    serialize_from_file,
    serialize)

__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def tmpfile_factory(tmpdir):
    def fact(content):
        t = tmpdir.join('tmpfile')
        t.write(content)
        return os.path.join(t.dirname, t.basename)

    return fact


def test_serialize_from_file(tmpfile_factory):
    content = 'content'
    assert eval(serialize_from_file(tmpfile_factory(content))) == content


def test_b64_pickled_source_from_file(tmpfile_factory):
    content = 'content'
    path = tmpfile_factory(content)
    assert pickle.loads(base64.b64decode(
        b64_pickled_source_from_file(path))) == content


def test_serialize():
    assert eval(serialize('c')) == 'c'
