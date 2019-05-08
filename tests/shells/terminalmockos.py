import abc
import multiprocessing
from contextlib import contextmanager
import six
import mock


__copyright__ = 'Copyright (C) 2019, Nokia'


@six.add_metaclass(abc.ABCMeta)
class TerminalMockOsBase(object):
    def __init__(self):
        self._serverprocess_factory = None
        self._manager = multiprocessing.Manager()
        self._namespace = self._manager.Namespace()
        self._mock_os = self._create_mock_os()
        self._pythonterminal = None
        self._pythonterminal_factory = None

    def _create_mock_os(self):
        m = self._mock_os_factory()
        m.set_namespace(self._namespace)
        return m

    def set_serverprocess_factory(self, serverprocess_factory):
        self._serverprocess_factory = serverprocess_factory

    @contextmanager
    def in_mock_os(self):
        with self._os_patcher():
            yield self._mock_os

    def set_pythonterminal_factory(self, pythonterminal_factory):
        self._pythonterminal_factory = pythonterminal_factory

    @property
    def pythonterminal(self):
        if self._pythonterminal is None:
            self._pythonterminal = self._pythonterminal_factory(
                self._updated_serverprocess_factory)
        return self._pythonterminal

    def _updated_serverprocess_factory(self):
        st = self._serverprocess_factory()
        st.set_process_factory(self._process_factory)
        return st

    @abc.abstractmethod
    def _process_factory(self, target):
        """Abstract method. Create :class:`multiprocessing.Process` derivative.
        """

    @abc.abstractmethod
    def _mock_os_factory(self):
        """Return mock *os* with some functions implemented (e.g. *os.write*)
        """

    @abc.abstractmethod
    def _os_patcher(self):
        """Return patcher instance (e.g. *mock.patch(..)*)
        """


@six.add_metaclass(abc.ABCMeta)
class AttrContextBase(TerminalMockOsBase):

    @abc.abstractproperty
    def client_attr(self):
        """Return client attribute value.
        """

    @abc.abstractproperty
    def server_attr(self):
        """Return server attribute value.
        """

    @contextmanager
    def in_context(self):
        self._set_client_attr()
        with self._mock_os.in_attr_context():
            yield None

    def _process_factory(self, target):
        t = AttrProcess(target=target, namespace=self._namespace)
        t.set_attr_factory(self._create_server_attr)
        return t

    def _create_server_attr(self):
        self._set_mock_os_attr(self.server_attr)
        return self._mock_os

    def _set_client_attr(self):
        self._set_mock_os_attr(self.client_attr)

    def _set_mock_os_attr(self, value):
        self._mock_os.set_attr(value)

    @abc.abstractmethod
    def _mock_os_factory(self):
        """Return :class:`.AttrMockOsBase derivative instance.
        """


class WriteContextBase(AttrContextBase):
    def _os_patcher(self):
        return mock.patch('os.write', side_effect=self._mock_os.write)


class AttrProcess(multiprocessing.Process):
    def __init__(self, target, namespace):
        super(AttrProcess, self).__init__(target=self._target_wrapper,
                                          args=(namespace,))
        self._attr_factory = None
        self._attr_namespace = namespace
        self._attr_target = target

    def _target_wrapper(self, namespace):
        a = self._attr_factory()
        a.set_namespace(namespace)
        self._attr_target()

    def set_attr_factory(self, attr_factory):
        self._attr_factory = attr_factory


@six.add_metaclass(abc.ABCMeta)
class AttrMockOsBase(object):

    def __init__(self):
        self._local_attr = None
        self._namespace = None

    def set_namespace(self, namespace):
        self._namespace = namespace

    @abc.abstractproperty
    def _default_value(self):
        """Return the default value for the attribute when not in the attribute
        context.
        """

    @property
    def _attr_ctx(self):
        try:
            return self._namespace.attr_ctx
        except AttributeError:
            self._set_attr_ctx(False)
            return False

    def _set_attr_ctx(self, attr_ctx):
        self._namespace.attr_ctx = attr_ctx

    @property
    def _attr(self):
        return self._local_attr if self._attr_ctx else self._default_value

    def set_attr(self, value):
        self._local_attr = value

    @contextmanager
    def in_attr_context(self):
        self._set_attr_ctx(True)
        try:
            yield None
        finally:
            self._set_attr_ctx(False)
