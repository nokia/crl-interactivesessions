from collections import namedtuple
import pytest
import mock
from crl.interactivesessions._pool import _Pool


__copyright__ = 'Copyright (C) 2019, Nokia'


class Factory(object):

    def __init__(self):
        self.count = 0
        self.items = []

    def create(self):
        self.count += 1
        self.items.append(mock.Mock())
        return self.items[-1]


class ReusingFactory(Factory):

    def create(self):
        try:
            return self.items[self.count]
        except IndexError:
            return super(ReusingFactory, self).create()

    def clear_count(self):
        self.count = 0


@pytest.fixture(scope='function')
def factory():
    return ReusingFactory()


def test_get(factory):
    p = _Pool(factory=factory.create)
    p.set_maxsize(1)
    assert p.get() == factory.items[0]


class ExampleException(Exception):
    pass


@pytest.mark.parametrize('maxsize', [1, 2, 3])
def test_get_too_many(factory, maxsize):
    with pytest.raises(ExampleException):
        p = _Pool(factory=factory.create, exception=ExampleException)
        p.set_maxsize(maxsize)
        p.exception = ExampleException
        for _ in range(maxsize + 1):
            p.get()


@pytest.mark.parametrize('shared', [True, False])
@pytest.mark.parametrize('maxsize', [1, 2, 3])
def test_set_maxsize_too_small(factory, maxsize, shared):
    with pytest.raises(ExampleException) as excinfo:
        p = _Pool(factory=factory.create, exception=ExampleException)
        p.set_maxsize(maxsize)
        items = []
        for _ in range(maxsize):
            items.append(p.get())

        if shared:
            for i in items:
                p.put_incr_shared(i)

        p.set_maxsize(maxsize - 1)
    assert 'Pool cannot set the maximum size less than' in str(excinfo.value)


def iterations():
    return pytest.mark.parametrize('iterations', [1, 2, 3])


@iterations()
def test_get_and_put(factory, iterations):
    p = _Pool(factory=factory.create)
    p.set_maxsize(1)
    for _ in range(iterations):
        ret = p.get()
        assert ret == factory.items[0]
        p.put(ret)


def verify_items_closed(factory, iterations, pool):
    for i in range(iterations):
        factory.items[i].close.assert_called_once_with()
    assert not pool.inuse
    assert not pool.free


@iterations()
def test_close(factory, iterations):
    p = _Pool(factory=factory.create)
    p.set_maxsize(6)
    for _ in range(iterations):
        p.get()
    items = []
    for _ in range(iterations):
        items.append(p.get())

    for item in items:
        p.put(item)

    p.close()
    for item in factory.items:
        item.close.assert_called_once_with()
    assert not p.inuse
    assert not p.free


@iterations()
def test_remove(factory, iterations):
    p = _Pool(factory=factory.create)
    p.set_maxsize(1)

    for _ in range(iterations):
        item = p.get()
        p.remove(item)

    verify_items_closed(factory, iterations, p)


@iterations()
def test_close_raises(factory,
                      iterations,  # pylint:disable=unused-argument
                      intcaplog):
    def raise_exception():
        raise Exception('message')

    p = _Pool(factory=factory.create)
    p.set_maxsize(1)
    p.get()
    factory.items[0].close.side_effect = raise_exception
    p.close()

    assert 'Failed to close item {}: Exception (message)'.format(
        str(factory.items[0])) in intcaplog.text


@pytest.mark.parametrize('sizeoffree,n,expected_size_after_free', [
    (1, 1, 0),
    (1, 2, 1),
    (2, 1, 0),
    (2, 2, 1),
    (4, 2, 2)])
def test_remove_every_nth_free(factory,
                               sizeoffree,
                               n,
                               expected_size_after_free):
    p = _Pool(factory=factory.create)
    p.set_maxsize(sizeoffree)
    items = []
    for op in [lambda: items.append(p.get()), lambda: p.put(items.pop())]:
        for _ in range(sizeoffree):
            op()
    p.remove_every_nth_free(n)
    assert len(p.free) == expected_size_after_free


@pytest.fixture
def factories(factory):
    def pfact(maxsize):
        p = _Pool(factory=factory.create)
        p.set_maxsize(maxsize)
        return p

    return Factories(pool_factory=pfact, factory=factory)


class Factories(namedtuple('Factories', ['pool_factory', 'factory'])):
    pass


@pytest.fixture
def shareditems(factories):
    return SharedItems(factories.pool_factory, factory=factories.factory)


class SharedItems(object):
    def __init__(self, pool_factory, factory):
        self.maxsize = 8
        self._factory = factory
        self.pool = pool_factory(self.maxsize)
        self.shared = 4
        self.inuse = 2
        self.inuse_items = []
        self.shared_items = []
        self.get_shared_and_assert_size(1)

    @property
    def inuse_set(self):
        return set(self.inuse_items)

    @property
    def shared_set(self):
        return set(self.shared_items)

    def get_shared_and_assert_size(self, expected_size):
        for _ in range(self.shared):
            self.shared_items.append(self.pool.get())
            self.pool.put_incr_shared(self.shared_items[-1])

        assert self.pool.size == expected_size

    def get_inuse_and_assert_size(self, expected_size):
        for _ in range(self.inuse):
            self.inuse_items.append(self.pool.get())

        assert self.pool.size == expected_size
        assert self.shared_set.issubset(self.inuse_set)

    def put_inuse_and_assert_size(self):
        for i in self.inuse_items:
            self.pool.put(i)
        assert self.pool.size == self.inuse

    def decr_shared(self):
        for i in self.shared_items:
            self.pool.decr_shared(i)

    def remove_every_free_and_assert_size(self, expected_size):
        orig_size = self.pool.size
        ret = self.pool.remove_every_nth_free(1)
        assert self.pool.size == expected_size
        assert ret == orig_size - expected_size

    def clear_factory_object_count(self):
        self._factory.clear_count()

    def remove_shared(self):
        for i in self.shared_items:
            self.pool.remove(i)
        self.shared_items = []

    def assert_empty_after_clear_count_get_shared_remove(self):
        self.clear_factory_object_count()
        self.get_shared_and_assert_size(1)
        self.decr_shared()
        self.remove_every_free_and_assert_size(0)

    def close(self):
        self.pool.close()
        self.inuse_items = []
        self.shared_items = []


def test_pool_shared_items(shareditems):
    shareditems.get_inuse_and_assert_size(shareditems.inuse)

    shareditems.remove_every_free_and_assert_size(shareditems.inuse)

    shareditems.put_inuse_and_assert_size()

    shareditems.remove_every_free_and_assert_size(1)

    shareditems.decr_shared()

    shareditems.remove_every_free_and_assert_size(0)


def test_pool_shared_items_remove(shareditems):
    shareditems.remove_shared()

    shareditems.assert_empty_after_clear_count_get_shared_remove()


def test_pool_shared_items_close(shareditems):
    shareditems.close()

    shareditems.assert_empty_after_clear_count_get_shared_remove()
