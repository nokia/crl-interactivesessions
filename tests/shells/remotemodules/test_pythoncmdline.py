from crl.interactivesessions.shells.remotemodules.pythoncmdline import PythonCmdline


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_pythoncmdline_assign():
    p = PythonCmdline()
    p.exec_command('a = 1')
    assert p.exec_command('a') == 1


def test_pythoncmdline_function():
    p = PythonCmdline()
    p.exec_command('def f():')
    p.exec_command('    return 1')
    assert p.exec_command('f()') == 1


def test_pythoncmdline_none():
    p = PythonCmdline()
    assert p.exec_command('None') is None
