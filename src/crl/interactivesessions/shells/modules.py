"""This is a helper module for importing modules in remote end.

Note:
    - This module itself should not be transfered to the remote end.

    - This module provides command generators but no means to
      run actual commands in the remote end.
"""

import hashlib
import os
import itertools
from .termserialization import b64_pickled_source_from_file


__copyright__ = 'Copyright (C) 2019, Nokia'


def _path_bytes_for_fingerprint(path):
    """Bytes form of *path* for hashing; works on Python 2 and 3."""
    if isinstance(path, bytes):
        return path
    try:
        return os.fsencode(path)
    except AttributeError:
        if hasattr(path, 'encode'):
            return path.encode('utf-8', 'replace')
        return path


class MainModule(object):
    """MainModule generates commands for running exec for *children*
    (:class:`.ChildModule`) instances.  It assumes that globals() contains
    all the child modules after child command generation. Finally, it generates
    command for exec itself.
    """
    _cmd_treshold_len = 5000
    #: Max characters per ``+=`` fragment when building the pickled source on the
    #: remote side (limits single terminal lines; 0 or negative means no limit).
    _compile_cmd_chunk_size = 1024

    def __init__(self, module, compile_cmd_chunk_size=None):
        self.module = module
        self._module_vars = {}
        if compile_cmd_chunk_size is not None:
            self._compile_cmd_chunk_size = compile_cmd_chunk_size

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
        for cmd in self._reconstruct_pickled_source_cmds_gen():
            yield cmd
        compile_expr = (
            "compile(pickle.loads(base64.b64decode({var})), filename={fname!r}, "
            "mode='exec')").format(
                var=self._compile_src_temp_var,
                fname=os.path.basename(self.path))
        yield 'exec({compile_expr}, {module_var}.__dict__)'.format(
            compile_expr=compile_expr,
            module_var=self.module_var)

    @property
    def _compile_src_temp_var(self):
        """Stable remote name for the reconstructed base64 pickle payload."""
        digest = hashlib.md5(_path_bytes_for_fingerprint(self.path)).hexdigest()[:16]
        return '__crl_isess_src_{}'.format(digest)

    def _reconstruct_pickled_source_cmds_gen(self):
        """Emit ``temp = ''`` and ``temp += '...'`` lines bounded by chunk size."""
        b64_payload = b64_pickled_source_from_file(self.path)
        chunk_size = self._compile_cmd_chunk_size
        var = self._compile_src_temp_var
        if chunk_size is None or chunk_size <= 0:
            yield "{} = {}".format(var, repr(b64_payload))
            return
        yield "{} = ''".format(var)
        for i in range(0, len(b64_payload), chunk_size):
            piece = b64_payload[i:i + chunk_size]
            yield "{} += {}".format(var, repr(piece))


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
