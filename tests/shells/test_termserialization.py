import os
import pickle  # pylint: disable=unused-import; # noqa: F401
import base64  # pylint: disable=unused-import; # noqa: F401
import pytest
from crl.interactivesessions.shells.termserialization import (
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


def test_serialize():
    assert eval(serialize('c')) == 'c'
