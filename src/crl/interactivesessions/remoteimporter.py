import os
import sys
import types
import logging
from crl.interactivesessions.RunnerHandler import exec_in_module


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


class ModuleImporter(object):
    def __init__(self, importer):
        self.importer = importer

    def importmodule(self, modulename, content):
        module = self.importer.moduletype(modulename)
        self.importer.exec_in_module(content, module)
        self.importer.sys_modules[modulename] = module


class LocalImporter(object):
    def __init__(self):
        self.sys_modules = sys.modules
        self.moduletype = types.ModuleType
        self.exec_in_module = exec_in_module


class RemoteImporter(object):
    def __init__(self, terminal, timeout):
        self.terminal = terminal
        self.timeout = timeout
        self.sys_modules = self.terminal.create_empty_remote_proxy()
        self.moduletype = self.terminal.create_empty_recursive_proxy()
        self.exec_in_module = self.terminal.create_empty_remote_proxy()
        self._moduleimporters = [ModuleImporter(self),
                                 ModuleImporter(LocalImporter())]

    def prepare(self):
        self._import_libraries()
        self._setup_proxies()

    def _import_libraries(self):
        self.terminal.import_libraries('sys', 'types')

    def _setup_proxies(self):
        self.sys_modules.set_from_remote_proxy(
            self.terminal.get_proxy_object('sys.modules', None))
        self.moduletype.set_from_remote_proxy(
            self.terminal.get_recursive_proxy(
                self.get_remote_obj('create_module')))
        self.exec_in_module.set_from_remote_proxy(
            self.terminal.get_proxy_object(
                self.get_remote_obj('exec_in_module'), None))

    @staticmethod
    def get_remote_obj(objname):
        return "runnerhandlerns['{}']".format(objname)

    def importfile(self, filepath):
        modulename = os.path.splitext(os.path.basename(filepath))[0]
        content = self._get_filecontent(filepath)
        logger.debug('content: %s', repr(content))
        for importer in self._moduleimporters:
            importer.importmodule(modulename, content)

        self.terminal.import_libraries(modulename)

    def importmodule(self, module):
        """
        Import module in remote end and add to local and remote sys.modules.

        .. note::

            Assumed that the source code path can be found by changing the
            *module.__file__* extension to *py*.
        """
        self.importfile('.'.join([os.path.splitext(module.__file__)[0], 'py']))

    @staticmethod
    def _get_filecontent(filepath):
        with open(filepath) as f:
            return f.read()
