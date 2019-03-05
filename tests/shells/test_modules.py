from crl.interactivesessions.shells.modules import MainModule
from crl.interactivesessions.shells.remotemodules.pythoncmdline import (
    PythonCmdline)

from .exampleremotemodules import mainexample


__copyright__ = 'Copyright (C) 2019, Nokia'


def test_mainmodule():
    m = MainModule(mainexample)
    assert m.module_var == '__mainexample'
    assert_module(m, expected_name='mainexample')


def assert_module(module, expected_name):
    assert module.name == expected_name
    with open(module.path) as f:
        assert 'Example module' in f.read()


def test_module_descendants():
    main = MainModule(mainexample)
    p = PythonCmdline()
    for cmd in main.cmds_gen():
        p.exec_command(cmd)
    assert p.exec_command("{mod}.call_descendants()".format(
        mod=main.module_var)) == mainexample.call_descendants()
