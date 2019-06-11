import logging
import base64
import pytest
from crl.interactivesessions.RunnerHandler import (
    _RunnerHandler, RunnerHandlerUnableToDeserialize)
from crl.interactivesessions.shells.remotemodules.compatibility import to_bytes, to_string
from crl.interactivesessions.shells.remotemodules.compatibility import PY3

__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)

FOOBAR = to_string(base64.b64encode(to_bytes('foobar')))


@pytest.fixture
def runnerhandler():
    return _RunnerHandler()


def serialize_params():
    foobar = to_string(base64.b64encode(to_bytes('foobar')))
    values = ([('foobar', 'S' + foobar + '', 'S'),
               (b'foobar', 'B' + foobar, 'B')]
              if PY3 else
              [('foobar', 'u' + foobar, 'u'),
               ('foobar', 's' + foobar, 's')])

    return pytest.mark.parametrize('given, expected, strtype', values)


@serialize_params()
def test_serialize_deserialize_string(given, expected, strtype, runnerhandler):
    serialized = runnerhandler.serialize_string(given, strtype)
    deserialized = runnerhandler.deserialize_string(serialized)
    LOGGER.debug("With %s as given and %s as strtype %s was serialized",
                 given,
                 strtype,
                 serialized)
    LOGGER.debug("With %s as serialized %s was deserialized",
                 serialized,
                 deserialized)
    assert len(given) == len(deserialized)
    assert len(expected) == len(serialized)
    assert serialized == expected
    assert deserialized == given


@pytest.mark.parametrize('given, strtype', [('foobar', 'x')])
def test_serialize_deserialize_string_fails(given, strtype, runnerhandler):

    serialized = runnerhandler.serialize_string(given, strtype)
    with pytest.raises(RunnerHandlerUnableToDeserialize):
        runnerhandler.deserialize_string(serialized)
