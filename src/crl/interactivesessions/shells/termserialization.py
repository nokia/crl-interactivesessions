import pickle
import base64


__copyright__ = 'Copyright (C) 2019, Nokia'


def serialize_from_file(path):
    return serialize(_read_content(path))


def serialize(s):
    return "pickle.loads(base64.b64decode({!r}))".format(
        base64.b64encode(pickle.dumps(s, protocol=0)))


def _read_content(path):
    with open(path) as f:
        return f.read()
