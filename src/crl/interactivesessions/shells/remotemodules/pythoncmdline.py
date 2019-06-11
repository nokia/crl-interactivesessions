__copyright__ = 'Copyright (C) 2019, Nokia'
import logging

LOGGER = logging.getLogger(__name__)


class PythonCmdline(object):
    """Emulates Python interactive shell. The major difference of
    *exec_command* from executing the same command in the interactive shell is
    the return value which is Python object instead of string representation.
    If the string representation is needed, then please use *repr*. Similarly
    any exceptions are not returned as string but raised.

    Moreover, multiple commands separated by semi-colon do not return anything
    while in normal interactive command line, the last expression value is
    forwarded  to the standard output.

    Example:

    >>> from crl.interactivesessions.shells.remotemodules.pythoncmdline import (
    ...     PythonCmdline)
    >>>
    >>> p = PythonCmdline()
    >>> p.exec_command('a = 1')
    >>> p.exec_command('a')
    1
    >>> repr(p.exec_command('a'))
    '1'
    >>> p.exec_command('b = 2; b')
    >>> p.exec_command('b')
    2
    """

    def __init__(self):
        self._multilinecmd = ''
        self._namespace = {}
        self._current_cmd = None

    @property
    def current_cmd(self):
        return self._current_cmd

    @property
    def namespace(self):
        return self._namespace

    def exec_command(self, cmd):
        try:
            self._current_cmd = self._multilinecmd + cmd
            code_obj = get_code_object(self.current_cmd)
            self._multilinecmd = ''
        except (IndentationError, SyntaxError) as e:
            indent_error = isinstance(e, IndentationError)
            if (e.args[0].startswith('unexpected EOF') or indent_error):
                self._multilinecmd += cmd + '\n'
                # FIXME: raise specific expection instead
                return None

            self._multilinecmd = ''
            raise

        return self._get_response(code_obj)

    def _get_response(self, code_obj):
        return eval(code_obj, self._namespace)


def get_code_object(cmd, mode='exec'):
    LOGGER.debug("===== get_code_object: cmd == %s", cmd)
    try:
        return compile(cmd, '', 'eval')
    except SyntaxError:
        return compile(cmd, '', mode)
