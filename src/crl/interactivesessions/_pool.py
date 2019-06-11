import logging
import itertools
from collections import Counter


__copyright__ = 'Copyright (C) 2019, Nokia'

LOGGER = logging.getLogger(__name__)


class SharedCounter(object):
    def __init__(self):
        self._shared = Counter()

    def incr(self, item):
        self._shared[id(item)] += 1

    def decr(self, item):
        self._shared[id(item)] -= 1

    def get_count(self, item):
        return self._shared[id(item)]

    def clear(self, item):
        self._shared[id(item)] = 0


class _Pool(object):
    """Pool of items which are created by *factory* and closed by callable
    *close* of the item. Pool items are either free or in-use. Free items can
    be either shared or unshared. By :meth:`.get' the item is transferred to
    in-use state. The item is put to free state via :meth:`.put`. The shared
    state can be managed via methods :meth:`.put_incr_shared` and
    :meth:`.decr_shared`.

    Note:
        This implementation is not thread-safe.

    Args:
        factory: callable for creating a new pool item.
        exception: Exception to be raised in case Pool operation failure.

    Attributes:
        free: set of free items
        inuse: set of items in use
    """

    def __init__(self, factory, exception=Exception):
        self.factory = factory
        self._maxsize = 0
        self.exception = exception
        self.inuse = set()
        self.free = set()
        self._sharedcounter = SharedCounter()

    def get(self):
        """Get free item from the pool. If there is no free items, create a new
        item by calling *factory*.
        """
        item = self._get_item()
        self.inuse.add(item)
        return item

    def set_maxsize(self, maxsize):
        """Set maximum size of the pool.

        Note:
            Pool maximum size cannot be set less than the size of shared
            or in-use items.

        Args:
            maxsize(int): New maximum size of the pool.
        """
        maxsize = int(maxsize)
        if maxsize < len(self.inuse) + self._get_shared_free_size():
            raise self.exception(
                'Pool cannot set the maximum size less than the number of the '
                'items already in use.')
        self.remove_n_free(len(self.free) - maxsize)
        self._maxsize = maxsize

    def _get_shared_free_size(self):
        shared_free_size = 0
        for i in self.free:
            if self._sharedcounter.get_count(i):
                shared_free_size += 1
        return shared_free_size

    @property
    def maxsize(self):
        """Maximum size of the pool."""
        return self._maxsize

    @property
    def size(self):
        """Pool size i.e. number of items in the pool."""
        return len(self.inuse) + len(self.free)

    @property
    def items(self):
        """Set of items in the pool"""
        return self.inuse.copy().union(self.free)

    def _get_item(self):
        try:
            return self.free.pop()
        except KeyError:
            if len(self.inuse) >= self.maxsize:
                raise self.exception(
                    'Cannot create a new item to the pool: '
                    'the maximum size of the pool exceeded.')
            return self.factory()

    def put(self, item):
        """Put item to the pool as free."""
        self.inuse.remove(item)
        self.free.add(item)

    def put_incr_shared(self, item):
        """Put item back to the pool as shared i.e. increment shared counter.
        """
        self.put(item)
        self._sharedcounter.incr(item)

    def decr_shared(self, item):
        """Decrement shared counter of the item.
        """
        self._sharedcounter.decr(item)

    def close(self):
        """Close pool. Try to call *close* of each item.
        """
        for i in self.items:
            self._try_to_close_item(i)
        self.inuse = set()
        self.free = set()
        self._sharedcounter = SharedCounter()

    @staticmethod
    def _try_to_close_item(item):
        try:
            item.close()
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.debug('Failed to close item %s: %s (%s)',
                         item, e.__class__.__name__, e)

    def remove(self, item):
        """Remove item and try to call item *close*.
        """
        self._try_to_close_item(item)
        self._sharedcounter.clear(item)
        for itemset in [self.inuse, self.free]:
            try:
                itemset.remove(item)
            except KeyError:
                pass

    def remove_every_nth_free(self, n):
        """Remove as many as possible but at most every *n*th unshared free
        items.

        Args:
            n(int): Divisor of free items.

        Return:
            Number of removed items.
        """
        return self.remove_n_free(len(self.free) // n)

    def remove_n_free(self, n):
        """Remove as many as possible but at most *n* free unshared items.

        Args:
            n(int): Number of items to be removed.

        Return:
            Number of removed items.
        """
        removed_count = 0
        for (removed_count, item) in self._n_size_slice_of_enumerated_unshared_free(n):
            self.remove(item)

        return removed_count

    def _n_size_slice_of_enumerated_unshared_free(self, n):
        return enumerate(itertools.islice(self._unshared_free(), max(0, n)), start=1)

    def _unshared_free(self):
        for i in self.free.copy():
            if not self._sharedcounter.get_count(i):
                yield i
