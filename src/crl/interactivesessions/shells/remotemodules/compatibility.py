import sys
import codecs

__copyright__ = 'Copyright (C) 2019, Nokia'


try:
    RANGE = xrange
except NameError:
    RANGE = range


PY3 = (sys.version_info.major == 3)
UNICODE_TYPE = str if PY3 else unicode  # pylint:disable=E0602; # noqa: F821


def string_conversion_to_bytes(value):
    return to_bytes(str(value))


def to_bytes(s):
    return s.encode('utf-8') if PY3 and isinstance(s, str) else s


def to_string(b):
    if PY3 and isinstance(b, bytes):
        return b.decode('utf-8', 'compatibilityreplace')
    return b


def encode_error_char(c):
    i = ord(c)
    return '\\U{:08x}'.format(i) if i >= 0x10000 else '\\u{:04x}'.format(i)


def decode_error_char(c):
    return '\\x{:02x}'.format(compatibility_ord(c))


def py23_unic(s):
    return (s.decode('utf-8', 'compatibilityreplace')
            if PY3 and isinstance(s, bytes) or (not PY3 and isinstance(s, str)) else s)


def unic_to_string(s):
    if PY3 or not isinstance(s, UNICODE_TYPE):
        return s
    return s.encode('utf-8', 'compatibilityreplace')


def compatibilityreplace(e):
    error_char = (encode_error_char
                  if isinstance(e, UnicodeEncodeError)
                  else decode_error_char)
    return u''.join(error_char(c) for c in e.object[e.start:e.end]), e.end


def compatibility_ord(c):
    # Assuming char is from byte string,
    # will return appropriate int in python 3
    # and ASCII order number in python 2
    return c if PY3 else ord(c)


codecs.register_error('compatibilityreplace', compatibilityreplace)
