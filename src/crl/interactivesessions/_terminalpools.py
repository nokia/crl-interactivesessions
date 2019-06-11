import logging
import random
from copy import deepcopy
from collections import OrderedDict
from contextlib import contextmanager
import six
from crl.interactivesessions._metasingleton import MetaSingleton
from crl.interactivesessions._pool import _Pool
from crl.interactivesessions._terminalpoolkey import _TerminalPoolKey
from crl.interactivesessions.autorunnerterminal import AutoRunnerTerminal
from crl.interactivesessions._remoterunnerproxies import (
    _RemoteRunnerProxies)
from .interactivesessionexceptions import InteractiveSessionError


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


class TerminalPoolsBusy(InteractiveSessionError):
    pass


class PoolNotFoundError(InteractiveSessionError):
    pass


class _Terminal(object):

    def __init__(self, key, shelldicts, properties):
        self.key = key
        self.shelldicts = shelldicts
        self.properties = properties
        self.terminal = None
        self.proxies = None
        self._initialize(shelldicts)
        self.terminal_cleanup = lambda: None
        self.is_persistent = lambda: True

    def set_terminal_cleanup(self, terminal_cleanup):
        self.terminal_cleanup = terminal_cleanup

    def set_is_persistent(self, is_persistent):
        self.is_persistent = is_persistent

    def shall_be_stored(self):
        return self.is_persistent() and self.terminal is not None

    def _initialize(self, shelldicts):
        self.terminal = AutoRunnerTerminal()
        self.proxies = _RemoteRunnerProxies(self.terminal)
        self.terminal.initialize_with_shelldicts(
            shelldicts=deepcopy(shelldicts),
            prepare=self._prepare)
        self._initialize_terminal()

    def _prepare(self):
        self.proxies.prepare()

    def initialize_with_properties(self, properties):
        self.properties = properties
        self._initialize_terminal()

    def _initialize_terminal(self):
        self.terminal.prompt_timeout = self.properties.prompt_timeout

    def close(self):
        if self.terminal is not None:
            try:
                self.terminal_cleanup()
                self.terminal.close()
            finally:
                self.terminal = None


@six.add_metaclass(MetaSingleton)
class _TerminalPools(object):
    def __init__(self):
        self._pools = OrderedDict()
        self._maxsize = 256

    def set_maxsize(self, maxsize):
        self._maxsize = maxsize

    @property
    def maxsize(self):
        return int(self._maxsize)

    @property
    def size(self):
        size = 0
        for _, pool in self._pools.items():
            size += pool.size
        return size

    def get(self, shelldicts, properties, zone=None):
        pool = self._get_pool(_TerminalPoolKey(shelldicts + [{'zone': zone}]),
                              shelldicts,
                              properties)
        self._clean_if_needed(pool)
        return self._get_terminal(pool, properties)

    @contextmanager
    def active_terminal(self, shelldicts, properties):
        terminal = self.get(shelldicts, properties)
        try:
            yield terminal
        finally:
            self.put(terminal)

    def _get_pool(self, key, shelldicts, properties):
        if key not in self._pools:
            self._pools[key] = _Pool(
                factory=lambda: _Terminal(key, shelldicts, properties),
                exception=TerminalPoolsBusy)
        pool = self._pools[key]
        pool.set_maxsize(properties.max_processes_in_target)
        return pool

    def _get_pool_from_key(self, key):
        try:
            return self._pools[key]
        except KeyError:
            raise PoolNotFoundError(key)

    def _clean_if_needed(self, pool):
        if not pool.free and self.size >= self.maxsize:
            self._try_to_clean()

    def _try_to_clean(self):
        if not self._clean_free():
            self._clean_free_in_random_order_or_raise()

    def _clean_free(self):
        removed = 0
        for _, pool in self._pools.items():
            removed += pool.remove_every_nth_free(2)
        return removed

    def _clean_free_in_random_order_or_raise(self):
        for key, pool in self._get_pools_items_in_random_order():
            if pool.remove_every_nth_free(1):
                if not pool.size:
                    del self._pools[key]
                return
        raise TerminalPoolsBusy()

    def _get_pools_items_in_random_order(self):
        items = list(self._pools.items())
        random.shuffle(items)
        return items

    def put_incr_shared(self, terminal):
        self._put_op(self._put_incr_shared, terminal)

    def put(self, terminal):
        self._put_op(self._put, terminal)

    def decr_shared(self, terminal):
        self._put_op(self._decr_shared, terminal)

    @staticmethod
    def _put_incr_shared(pool, terminal):
        pool.put_incr_shared(terminal)

    @staticmethod
    def _put(pool, terminal):
        pool.put(terminal)

    @staticmethod
    def _decr_shared(pool, terminal):
        pool.decr_shared(terminal)

    def _put_op(self, op, terminal):
        pool = self._get_pool_from_key(terminal.key)
        if terminal.shall_be_stored():
            op(pool=pool, terminal=terminal)
        else:
            pool.remove(terminal)

    def remove(self, terminal):
        if terminal.key in self._pools:
            self._pools[terminal.key].remove(terminal)

    @staticmethod
    def _get_terminal(pool, properties):
        terminal = pool.get()
        terminal.initialize_with_properties(properties)
        return terminal

    def close(self):
        for _, pool in self._pools.items():
            pool.close()
        self._pools = OrderedDict()
