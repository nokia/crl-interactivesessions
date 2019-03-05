from crl.interactivesessions._terminalpoolkey import _TerminalPoolKey


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_poolkey_with_sets():
    s = set()
    for i in range(2):
        s.add(_TerminalPoolKey([{'s': i}]))


def test_poolkey_str():
    assert str(_TerminalPoolKey([{'n': 'v'}])) == '[[(\'n\', \'v\')]]'
