import pytest
import mock
from crl.interactivesessions.garbagemanager import GarbageManager


@pytest.fixture
def garbage():
    return Garbage(10)


class Garbage(object):
    def __init__(self, max_garbage):
        self._max_garbage = max_garbage
        self._clean = mock.Mock()
        self._manager = GarbageManager(clean=self._clean, max_garbage=self._max_garbage)

    @property
    def clean(self):
        return self._clean

    @property
    def max_garbage(self):
        return self._max_garbage

    @property
    def manager(self):
        return self._manager


def test_garbage_manager(garbage):
    for i in range(garbage.max_garbage):
        garbage.manager.add(session_id=1, garbage=i)
        garbage.manager.clean_if_needed(session_id=1)

    assert not garbage.clean.mock_calls

    for i in range(garbage.max_garbage, 2 * garbage.max_garbage):
        garbage.manager.add(session_id=1, garbage=i)
        garbage.manager.clean_if_needed(session_id=1)
        if i == garbage.max_garbage:
            _, args, _ = garbage.clean.mock_calls[0]
            assert list(args[0]) == list(range(garbage.max_garbage + 1))

    assert garbage.clean.call_count == 1


def test_garbage_manager_session_id(garbage):
    for i in range(3 * garbage.max_garbage):
        garbage.manager.add(session_id=i, garbage=i)
        garbage.manager.clean_if_needed(session_id=i)

    assert not garbage.clean.call_count
    assert len(garbage.manager) == 1
