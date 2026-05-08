import pickle
import base64


__copyright__ = 'Copyright (C) 2019, Nokia'


def serialize_from_file(path):
    return serialize(_read_content(path))


def b64_pickled_source_from_file(path):
    """Return ASCII base64 of pickled file text (same payload as :func:`serialize`)."""
    raw = base64.b64encode(pickle.dumps(_read_content(path), protocol=0))
    if isinstance(raw, bytes):
        return raw.decode('ascii')
    return raw


def serialize(s):
    return "pickle.loads(base64.b64decode({!r}))".format(
        base64.b64encode(pickle.dumps(s, protocol=0)))


def _read_content(path):
    with open(path) as f:
        return f.read()
