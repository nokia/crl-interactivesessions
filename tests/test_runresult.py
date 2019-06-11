# -*- coding: utf-8 -*-
from collections import namedtuple
import pytest
from crl.interactivesessions.remoterunner import RunResult


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_run_result_str():
    assert str(RunResult(0, 'stdout', 'stderr')) == (
        '\n exit status:   0\n stdout:\n stdout\n stderr:\n stderr\n')


def test_run_result_str_unic_raises():
    assert str(RunResult(0, 1, 2)) == (
        '\n exit status:   0\n stdout:\n 1\n stderr:\n 2\n')


class StrOut(namedtuple('StrOut', ['out', 'err'])):
    @property
    def expected_str(self):
        return '\n exit status:   0\n stdout:\n {out}\n stderr:\n {err}\n'.format(
            out=self.out,
            err=self.err)


@pytest.mark.parametrize('out, err, strout',
                         [(u'out', u'stderr', StrOut(out='out', err='stderr')),
                          ('out', 'stderr', StrOut(out='out', err='stderr')),
                          (b'out', b'stderr', StrOut(out='out', err='stderr')),
                          (b'\xef\xef', b'\x84\x84', StrOut(out='\\xef\\xef',
                                                            err='\\x84\\x84')),
                          (b'\xef\xeffoobar', b'\x84\x84foobar',
                           StrOut(out='\\xef\\xeffoobar', err='\\x84\\x84foobar')),
                          (b'\xeffoobar\xff', b'\xa9barfoo\xff',
                           StrOut(out='\\xeffoobar\\xff', err='\\xa9barfoo\\xff'))])
def test_unicodedecodeerror_handling(out, err, strout):
    assert str(RunResult(0, out, err)) == strout.expected_str
