__copyright__ = 'Copyright (C) 2019, Nokia'


class _TerminalPoolKey(object):

    def __init__(self, shelldicts):
        self._key = self._get_string_from_list_of_dicts(shelldicts)

    @staticmethod
    def _get_string_from_list_of_dicts(dicts):
        return str([sorted(s.items()) for s in dicts])

    def get(self):
        return self._key

    def __str__(self):
        return self.get()

    def __eq__(self, other):
        return self.get() == other.get()

    def __hash__(self):
        return hash(self.get())
