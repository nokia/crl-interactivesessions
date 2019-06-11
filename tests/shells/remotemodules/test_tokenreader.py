import random
import string
import itertools
import pytest
from crl.interactivesessions.shells.remotemodules.tokenreader import (
    TokenReader,
    SingleGapMatcher)
from crl.interactivesessions.shells.remotemodules.compatibility import (
    RANGE,
    to_bytes,
    string_conversion_to_bytes)


__copyright__ = 'Copyright (C) 2019, Nokia'

CHARS = bytearray(to_bytes(string.ascii_letters + string.digits))


@pytest.fixture
def token_with_single_gaps(token_with_fixed_gaps, token_with_random_gap):
    return itertools.chain(token_with_fixed_gaps(), token_with_random_gap())


@pytest.fixture
def token_with_fixed_gaps(simple_single_gaps):
    def gaps():
        for prefix in [b'', b'aa']:
            for t in simple_single_gaps():
                yield prefix + t

    return gaps


@pytest.fixture
def simple_single_gaps(token):
    def gaps():
        for i in RANGE(len(token)):
            yield token[:i] + token
            yield token[:i] + token[i:i + 1] + token[i:]
            yield token[:i] + token[i:i + 1] + b'aa' + token[i:]
            if i > 1:
                yield token[:i] + token[i - 1:i] + token[i:]
                yield token[:i] + b'aa' + token[i - 1:i] + token[i:]
                yield token[:i] + token[i - 1:i + 1] + token[i:]

    return gaps


@pytest.fixture
def token_with_random_gap(token_with_random_single_gap_factory):
    def gaps():
        for gap_lens_sum in [0, 1, 80, 400]:
            for _ in RANGE(900 // (gap_lens_sum + 10)):
                yield token_with_random_single_gap_factory(gap_lens_sum)
    return gaps


@pytest.fixture
def token_with_random_single_gap_factory(token):
    def fact(sum_gap_lens):
        r = RandomCreator(sum_gap_lens)
        r.initialize(token, max_nbr_gaps=1)
        return r.create()

    return fact


class RandomCreator(object):
    def __init__(self, sum_gap_lens):
        self._sum_gap_lens = sum_gap_lens
        self._max_nbr_gaps = None
        self._token = None

    def initialize(self, token, max_nbr_gaps=None):
        self._token = token
        self._max_nbr_gaps = max_nbr_gaps or len(token)

    def create(self):
        gap_chars = [GapChar(c) for c in self._token]
        gap_chars_with_gaps = random.sample(gap_chars, self._max_nbr_gaps)
        for _ in RANGE(self._sum_gap_lens):
            random.choice(gap_chars_with_gaps).add_char_to_gap()
        return b''.join(g.bytes for g in gap_chars)


class GapChar(object):
    def __init__(self, c):
        self._c = ascii_char_to_bytes(c)
        self._gap = b''

    def add_char_to_gap(self):
        self._gap += ascii_char_to_bytes(random.choice(CHARS))

    @property
    def bytes(self):
        return self._gap + self._c


def ascii_char_to_bytes(c):
    return string_conversion_to_bytes(bytearray([c]).decode('utf-8'))


@pytest.fixture
def token():
    return b''.join([to_bytes(chr(c)) for c in random.sample(CHARS, 20)])


class ReaderError(Exception):
    pass


@pytest.fixture
def tokenreader_factory(token):
    def fact(s):
        r = Reader(s)
        t = TokenReader(token, read_until_size=r.read_until_size,
                        matcher_factory=SingleGapMatcher)
        return t

    return fact


class Reader(object):
    def __init__(self, s):
        self._s = s
        self._idx = 0

    def getvalue(self):
        return self._s

    def read_until_size(self, n):
        assert n > 0
        if n + self._idx > len(self._s):
            raise ReaderError('number of bytes remaining exceeded: {}'.format(n))
        ret = self._s[self._idx:self._idx + n]
        self._idx += n
        return ret


def test_singlegapreader(tokenreader_factory, token_with_single_gaps):
    for s in token_with_single_gaps:
        t = tokenreader_factory(s)
        before_token = t.read_until_token()

        with pytest.raises(ReaderError):
            tokenreader_factory(before_token).read_until_token()

        from_token = s[len(before_token):]
        assert s == before_token + from_token
        assert not tokenreader_factory(from_token).read_until_token()

        with pytest.raises(ReaderError):
            t.read_until_token()
