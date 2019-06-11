from io import BytesIO
import logging


if 'compatibility' not in globals():
    from . import compatibility


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [compatibility]
LOGGER = logging.getLogger(__name__)


class MemoizeSingleArg(object):
    def __init__(self, f):
        self._f = f
        self._saved = {}

    def __call__(self, arg):
        if arg not in self._saved:
            self._saved[arg] = self._f(arg)

        return self._saved[arg]


class TokenReader(object):
    def __init__(self, token, read_until_size, matcher_factory):
        self._token = token
        self._read_until_size = read_until_size
        self._matcher = matcher_factory(token)
        self._io = BytesIO()
        self._remaining = 0

    def read_until_token(self):
        self._reset()
        while self._remaining > 0:
            already_handled = self._io.tell()
            s = self._buffered_read()
            self._matcher.find(s, already_handled=already_handled)
            self._remaining = len(self._token) - self._matcher.max_pass
        ret = self._io.getvalue()[:self._matcher.match_start]
        return ret

    def _reset(self):
        self._remaining = len(self._token)
        self._io = BytesIO()
        self._matcher.reset()

    def _buffered_read(self):
        s = self._read_until_size(self._remaining)
        self._io.write(compatibility.to_bytes(s))
        return s

    @property
    def _remaining_token(self):
        return self._token[-self._remaining:]


class MatcherBase(object):
    """Base class for matchers. The idea of the matcher is to :meth:`.find`
    whether strings matches *token*. Different matchers are needed because
    there are multiple ways to define whether or not string matches token. For
    example with *token* = 'token' one matcher matches 'tok000en' while another
    matcher does match with 't000oken' but not with 'tok000en'. Then the third
    matcher could match in both cases.
    """
    def __init__(self, token):
        self._token = token
        self._already_handled = None
        self._s = None

    def find(self, s, already_handled):
        """Find match for *s*. The argument *already_handled* is used for
        correctly indicating location in :meth:`.match_star`.

        Args:
            *s*: string of bytes from where the token is searched
            *already_handled*: the number of bytes already handled after reset
        """
        self._already_handled = already_handled
        self._s = s
        self._find()

    def _find(self):
        """Find match for attribute *_s*.
        """
        raise NotImplementedError()

    def reset(self):
        """Reset state of the mathcer appart of token.
        """
        raise NotImplementedError()

    @property
    def max_pass(self):
        """Maximum matched string length.
        """
        raise NotImplementedError()

    @property
    def full_match(self):
        """If full match, then True.
        """
        raise NotImplementedError()

    @property
    def match_start(self):
        """Start of the best match.
        """
        raise NotImplementedError()


class SingleGapMatcher(MatcherBase):
    """Token matcher for strings of type token_fist + gap + token_last
    where token = token_first + token_last.

    .. warning:

       This matcher works only for tokens which all characters are unique.
       For example this matcher *fails* for token 'x0110' if
       token_first = 'x0', gap = '01' and token_last = '110'.
    """
    def __init__(self, token):
        super(SingleGapMatcher, self).__init__(token)
        self._matchers = self._create_matchers(token)

    @property
    def max_pass(self):
        return max(self._max_passes())

    @property
    def full_match(self):
        for m in reversed(self._matchers):
            if m.full_match:
                return True

        return False

    @property
    def match_start(self):
        for m in reversed(self._matchers):
            if m.full_match:
                return m.match_start

        assert 0, 'match_start called even though, no full match'

    def _max_passes(self):
        for m in self._matchers:
            yield m.max_pass

    @staticmethod
    @MemoizeSingleArg
    def _create_matchers(token):
        return [FixedGapMatcher(token, gap_start=g)
                for g in compatibility.RANGE(1, len(token) + 1)]

    def _find(self):
        for m in reversed(self._matchers):
            m.find(self._s, already_handled=self._already_handled)
            if m.full_match:
                break

    def reset(self):
        for m in self._matchers:
            m.reset()


class FixedGapMatcher(MatcherBase):
    """This matcher matches (token[:gap_start]).*(token[gap_start:]) pattern.
    In the middle there is a single gap which starts at *gap_start*.
    """
    def __init__(self, token, gap_start):
        super(FixedGapMatcher, self).__init__(token)
        self._gap_start = gap_start
        self._first_group_idx = 0
        self._last_group_idx = self._gap_start
        self._match_start = None

    def reset(self):
        self._first_group_idx = 0
        self._last_group_idx = self._gap_start
        self._match_start = None
        self._already_handled = None

    @property
    def match_start(self):
        return self._match_start

    @property
    def max_pass(self):
        return self._first_group_idx + self._last_group_idx - self._gap_start

    def _find(self):
        for idx in compatibility.RANGE(len(self._s)):
            self._find_idx(idx)

    def _find_idx(self, idx):
        self._update_last(idx)
        self._update_first(idx)

    def _update_last(self, idx):
        if self._first_group_found and not self.full_match:
            if self._token[self._last_group_idx] == self._s[idx]:
                self._last_group_idx += 1
            else:
                self._last_group_idx = self._gap_start + int(
                    self._token[self._gap_start] == self._s[idx])

    def _update_first(self, idx):
        if not self._first_group_found:
            if self._token[self._first_group_idx] == self._s[idx]:
                self._first_group_idx += 1
                if self._match_start is None:
                    self._match_start = self._already_handled + idx

            else:
                first_group_idx_old = self._first_group_idx
                self._first_group_idx = 0
                self._match_start = None
                if first_group_idx_old:
                    self._update_first(idx)

    @property
    def _first_group_found(self):
        return self._first_group_idx >= self._gap_start

    @property
    def full_match(self):
        return self._first_group_found and self._last_group_idx >= len(self._token)
