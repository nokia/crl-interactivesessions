# pylint: disable=unused-argument
import logging
from collections import namedtuple
import itertools
import pytest
import mock
from fixtureresources.fixtures import create_patch

from crl.interactivesessions._terminalpools import (
    _TerminalPools,
    TerminalPoolsBusy,
    PoolNotFoundError,
    InteractiveSessionError)


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def mock_autorunnerterminal(request):
    return create_patch(
        mock.patch('crl.interactivesessions._terminalpools'
                   '.AutoRunnerTerminal'), request)


@pytest.fixture(scope='function')
def terminalpools(request):
    p = _TerminalPools()
    p.close()
    request.addfinalizer(p.close)
    return p


class PropertiesArgs(object):
    def __init__(self, max_processes_in_target):
        self.properties = mock.Mock()
        self.properties.max_processes_in_target = max_processes_in_target

    def get_args(self, i):
        return ([{'n': i}], self.properties)


@pytest.mark.parametrize('maxsize, expected_size_at_end, expected_reuse', [
    (1, 1, False),
    (3, 3, True),
    (5, 4, True),
    (7, 5, True)])
def test_pool_cleaning(mock_autorunnerterminal,
                       terminalpools,
                       maxsize,
                       expected_size_at_end,
                       expected_reuse):
    pargs = PropertiesArgs(maxsize + 1)
    terminalpools.set_maxsize(maxsize)
    assert terminalpools.size == 0
    t = []
    terminallists = []
    for op in [lambda: t.append(terminalpools.get(*pargs.get_args(0))),
               lambda: terminalpools.put(t.pop())]:
        for _ in range(maxsize):
            op()
        terminallists.append(t[:])

    terminalpools.put(terminalpools.get(*pargs.get_args(1)))
    assert terminalpools.size == expected_size_at_end

    assert (terminalpools.get(
        *pargs.get_args(0)) in terminallists[0]) == expected_reuse


@pytest.mark.parametrize('maxsize', [1, 3, 5])
def test_pool_cleaning_raises(mock_autorunnerterminal,
                              terminalpools,
                              maxsize):
    pargs = PropertiesArgs(maxsize + 1)
    terminalpools.set_maxsize(maxsize)
    with pytest.raises(TerminalPoolsBusy):
        for _ in range(maxsize + 1):
            terminalpools.get(*pargs.get_args(0))


class ExampleException(Exception):
    pass


def test_terminal_close_raises(mock_autorunnerterminal,
                               terminalpools,
                               intcaplog):

    def raise_test_exception():
        raise ExampleException('message')

    mock_autorunnerterminal.return_value.close.side_effect = (
        raise_test_exception)
    term = terminalpools.get(*PropertiesArgs(1).get_args(0))
    term.set_is_persistent(lambda: False)
    terminalpools.put(term)
    assert 'Failed to close' in intcaplog.text


class TermZone(object):
    def __init__(self, name=None):
        self.name = name
        self.terms = set()

    @property
    def zone_kwarg(self):
        return {} if self.name is None else {'zone': self.name}


def test_terminalpools_zones(mock_autorunnerterminal, terminalpools):
    maxsize = 20
    pargs = PropertiesArgs(maxsize + 1)
    terminalpools.set_maxsize(maxsize)
    termzones = [TermZone('zone1'), TermZone('zone2'), TermZone()]
    zonesize = int(maxsize / len(termzones))

    for z in termzones:
        for _ in range(zonesize):
            t = terminalpools.get(*pargs.get_args(0), **z.zone_kwarg)
            z.terms.add(t)
            terminalpools.put(t)

    for x, y in itertools.combinations(termzones, 2):
        assert not x.terms.intersection(y.terms)

    for z in termzones:
        assert len(z.terms) == 1


class FakeShuffle(object):
    def __init__(self, shuffle_max):
        self.shuffle_max = shuffle_max
        self.count = 0

    def shuffle(self, l):
        tofront = l.pop(self.count % self.shuffle_max)
        l.insert(0, tofront)
        self.count += 1


@pytest.fixture
def mock_random_shuffle():
    s = FakeShuffle(shuffle_max=3)

    with mock.patch('random.shuffle', side_effect=s.shuffle) as p:
        yield p


class PoolsReuse(namedtuple('PoolsReuse', ['pools', 'reuse', 'remove_idx'])):
    pass


EXP_ROUND0 = {0: PoolsReuse(pools=[0], reuse=False, remove_idx=0),
              1: PoolsReuse(pools=[0, 1], reuse=False, remove_idx=0),
              2: PoolsReuse(pools=[0, 1, 2], reuse=False, remove_idx=0),
              3: PoolsReuse(pools=[1, 2, 3], reuse=False, remove_idx=0),
              4: PoolsReuse(pools=[1, 3, 4], reuse=False, remove_idx=1)}


EXP_ROUND1 = {0: PoolsReuse(pools=[1, 3, 0], reuse=False, remove_idx=2),
              1: PoolsReuse(pools=[1, 3, 0], reuse=True, remove_idx=2),
              2: PoolsReuse(pools=[3, 0, 2], reuse=False, remove_idx=0),
              3: PoolsReuse(pools=[3, 0, 2], reuse=True, remove_idx=0),
              4: PoolsReuse(pools=[3, 2, 4], reuse=False, remove_idx=1)}


EXPECTED_ROUNDS = {0: EXP_ROUND0,
                   1: EXP_ROUND1}


def get_expected_poolsreuse(exec_round, pool_idx):
    return EXPECTED_ROUNDS[exec_round][pool_idx]


class PoolsMan(object):

    def __init__(self, terminalpools):
        self.terminalpools = terminalpools
        self.maxsize = 3
        self.nofpools = 5
        self.pargs = PropertiesArgs(self.nofpools)
        self.terminalpools.set_maxsize(self.maxsize)

    def get_terms(self, n):
        for pool_idx in range(n):
            yield self.terminalpools.get(*self.pargs.get_args(pool_idx))

    def get_terms_and_put(self, n):
        for t in self.get_terms_and_op(n, self.terminalpools.put):
            yield t

    def get_terms_and_put_incr_shared(self, n):
        for t in self.get_terms_and_op(n, self.terminalpools.put_incr_shared):
            yield t

    def get_terms_and_op(self, n, op):
        for t in self.get_terms(n):
            yield t
            op(t)

    def shared_and_decr_shared(self, shared_gen):
        for t in shared_gen:
            yield t
            self.terminalpools.decr_shared(t)

    def assert_new_not_intersecting_shared(self, shared):
        terms = set()
        for t in self.get_terms_and_put(self.nofpools):
            terms.add(t)

        assert not shared.intersection(terms)


@pytest.fixture
def poolsman(terminalpools):
    return PoolsMan(terminalpools)


@pytest.mark.usefixtures('mock_autorunnerterminal', 'mock_random_shuffle')
def test_terminalpools_randomized_reuse(poolsman):

    terms = set()
    for exec_round in range(2):
        for pool_idx, t in enumerate(poolsman.get_terms_and_put(poolsman.nofpools)):
            exp_poolsreuse = get_expected_poolsreuse(exec_round=exec_round,
                                                     pool_idx=pool_idx)
            assert (t in terms) == exp_poolsreuse.reuse, exp_poolsreuse
            terms.add(t)


@pytest.mark.parametrize('error', [TerminalPoolsBusy, InteractiveSessionError])
@pytest.mark.usefixtures('mock_autorunnerterminal')
def test_terminalpools_shared(poolsman, error):
    terms = set()

    with pytest.raises(error):
        for t in poolsman.get_terms_and_put_incr_shared(poolsman.nofpools):
            terms.add(t)

    for t in poolsman.shared_and_decr_shared(terms):
        pass

    for t in poolsman.get_terms_and_put(poolsman.nofpools):
        pass


@pytest.mark.usefixtures('mock_autorunnerterminal')
def test_terminalpools_shared_nonpercistent_incr(poolsman):

    shared = set()

    for t in poolsman.get_terms_and_put_incr_shared(2 * poolsman.maxsize):
        t.set_is_persistent(lambda: False)

    poolsman.assert_new_not_intersecting_shared(shared)


@pytest.mark.usefixtures('mock_autorunnerterminal')
def test_terminalpools_shared_nonpercistent_decr(poolsman):

    shared = set()

    for t in poolsman.get_terms_and_put_incr_shared(poolsman.maxsize):
        shared.add(t)

    for t in poolsman.shared_and_decr_shared(shared):
        t.set_is_persistent(lambda: False)

    poolsman.assert_new_not_intersecting_shared(shared)


@pytest.mark.usefixtures('mock_autorunnerterminal')
@pytest.mark.parametrize('error', [PoolNotFoundError, InteractiveSessionError])
def test_nonpool_terminal_put(terminalpools, error):
    t = mock.Mock()
    with pytest.raises(error) as excinfo:
        terminalpools.put(t)

    assert t.key == excinfo.value.args[0]
