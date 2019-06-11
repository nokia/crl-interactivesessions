from crl.interactivesessions.shells.remotemodules.compatibility import to_string

__copyright__ = 'Copyright (C) 2019, Nokia'


def test_anypythonshell(anypythonshell):
    anypythonshell.exec_command('a = 1')
    assert to_string(anypythonshell.exec_command('a').rstrip()) == '1'


def test_anypythonshell_syntaxerror(anypythonshell):
    out = to_string(anypythonshell.exec_command('incorrect syntax'))
    assert 'SyntaxError: invalid syntax' in out, out
    assert 'incorrect syntax' in out, out


def test_anypythonshell_exception(anypythonshell):
    pre_cmds = [
        'class A(object):',
        '    def raise_exception(self):',
        '        raise Exception("msg")',
        '',
        'a = A()']

    for c in pre_cmds:
        out = anypythonshell.exec_command(c)
        assert not out, out

    out = to_string(anypythonshell.exec_command('a.raise_exception()'))
    assert 'Exception: msg' in out, out
