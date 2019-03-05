"""This is a helper module for importing modules in remote end.

Note:
    - This module itself should not be transfered to the remote end.

    - This module provides command generators but no means to
      run actual commands in the remote end.
"""

import os
import itertools
from .termserialization import serialize_from_file


__copyright__ = 'Copyright (C) 2019, Nokia'


class MainModule(object):
    """MainModule generates commands for running exec for *children*
    (:class:`.ChildModule`) instances.  It assumes that globals() contains
    all the child modules after child command generation. Finally, it generates
    command for exec itself.
    """
    _cmd_treshold_len = 5000

    def __init__(self, module):
        self.module = module
        self._module_vars = {}

    @property
    def module_var(self):
        """Entry variable to the module.
        """
        return '__{}'.format(self.name)

    @property
    def name(self):
        return self.module.__name__.split('.')[-1]

    @property
    def path(self):
        return '.'.join([os.path.splitext(self.module.__file__)[0], 'py'])

    def cmds_gen(self):
        self._module_vars = {}
        for c in self._grouped_cmds_gen():
            yield c

    def _grouped_cmds_gen(self):
        grouped_cmd = ''
        for c in self.raw_cmds_gen():
            grouped_cmd += '; {}'.format(c) if grouped_cmd else c
            if len(grouped_cmd) > self._cmd_treshold_len:
                yield grouped_cmd
                grouped_cmd = ''

        if grouped_cmd:
            yield grouped_cmd

    def raw_cmds_gen(self):
        cmds_gen = (self._assign_existing_cmds_gen
                    if self.name in self._module_vars else
                    self._import_module_cmds_gen)
        for cmd in cmds_gen():
            yield cmd

    def _assign_existing_cmds_gen(self):
        yield '{module_var} = {module_var_in_module_vars}'.format(
            module_var=self.module_var,
            module_var_in_module_vars=self._module_vars[self.name])

    def _import_module_cmds_gen(self):
        for cmd in itertools.chain(self._import_cmd_gen(),
                                   self._module_cmd_gen(),
                                   self._children_cmds_gen(),
                                   self._exec_cmd_gen()):
            yield cmd

        self._module_vars[self.name] = self.module_var

    @staticmethod
    def _import_cmd_gen():
        yield 'import pickle, base64, types'

    def _module_cmd_gen(self):
        yield '{module_var} = {module_cmd}'.format(
            module_var=self.module_var,
            module_cmd=self._module_cmd)

    @property
    def _module_cmd(self):
        return "types.ModuleType('{name}')".format(name=self.name)

    def _children_cmds_gen(self):
        for child in self._children_gen():
            for c in child.raw_cmds_gen():
                yield c

    def _children_gen(self):
        for c in self._child_modules_gen():
            yield ChildModule(module=c, parent=self)

    def _child_modules_gen(self):
        try:
            for m in self.module.CHILD_MODULES:
                yield m
        except AttributeError:
            pass

    def _exec_cmd_gen(self):
        yield 'exec({compile_cmd}, {module_var}.__dict__)'.format(
            compile_cmd=self._compile_cmd,
            module_var=self.module_var)

    @property
    def _compile_cmd(self):
        return ("compile({serialized}, filename='{basename}', "
                "mode='exec')".format(serialized=serialize_from_file(self.path),
                                      basename=os.path.basename(self.path)))


class ChildModule(MainModule):
    """Generate commands for adding child modules to the parent module
    dictionary.
    """
    def __init__(self, module, parent):
        super(ChildModule, self).__init__(module)
        self._parent = parent

    def _import_cmd_gen(self):
        return iter(())

    @property
    def module_var(self):
        return "{parent_module_var}.__dict__['{name}']".format(
            parent_module_var=self._parent.module_var,
            name=self.name)
