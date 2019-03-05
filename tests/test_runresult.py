# -*- coding: utf-8 -*-
from crl.interactivesessions.remoterunner import RunResult


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_run_result_str():
    assert str(RunResult(0, 'stdout', 'stderr')) == (
        '\n exit status:   0\n stdout:\n stdout\n stderr:\n stderr\n')


def test_run_result_str_unic_raises():
    assert str(RunResult(0, 1, 2)) == (
        '\n exit status:   0\n stdout:\n 1\n stderr:\n 2\n')


def test_unicodedecodeerror_handling():
    assert str(RunResult(0, 'out', u'err\xff\xe4')) == (
        '\n exit status:   0\n stdout:\n out\n stderr:\n err\xc3\xbf\xc3\xa4\n')
