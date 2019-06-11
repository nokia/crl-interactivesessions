__copyright__ = 'Copyright (C) 2019, Nokia'


class GarbageManager(object):
    def __init__(self, clean, max_garbage):
        self._clean = clean
        self._max_garbage = max_garbage
        self._session_id = None
        self._garbage = []

    def add(self, session_id, garbage):
        if session_id != self._session_id:
            self._session_id = session_id
            self._garbage = []

        self._garbage.append(garbage)

    def clean_if_needed(self, session_id):
        if session_id == self._session_id and len(self._garbage) > self._max_garbage:
            self._clean(self._garbage)
            self._garbage = []

    def __len__(self):
        return len(self._garbage)
