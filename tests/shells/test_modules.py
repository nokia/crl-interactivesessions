import ast

from crl.interactivesessions.shells.modules import MainModule
from crl.interactivesessions.shells.remotemodules.pythoncmdline import (
    PythonCmdline)
from crl.interactivesessions.shells.termserialization import (
    b64_pickled_source_from_file)

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


def test_module_descendants_tiny_compile_chunks():
    """Chunked source reconstruction must match single-shot behavior."""
    main = MainModule(mainexample, compile_cmd_chunk_size=24)
    p = PythonCmdline()
    for cmd in main.cmds_gen():
        p.exec_command(cmd)
    assert p.exec_command("{mod}.call_descendants()".format(
        mod=main.module_var)) == mainexample.call_descendants()


def test_compile_reconstruct_commands_respect_chunk_size():
    """Each ``+=`` fragment must be at most *compile_cmd_chunk_size* characters."""
    chunk_size = 37
    main = MainModule(mainexample, compile_cmd_chunk_size=chunk_size)
    var = main._compile_src_temp_var
    expected_b64 = b64_pickled_source_from_file(main.path)
    lines = list(main._reconstruct_pickled_source_cmds_gen())
    assert lines[0] == "{} = ''".format(var)
    rebuilt = ''
    for line in lines[1:]:
        prefix = '{} += '.format(var)
        assert line.startswith(prefix)
        piece = ast.literal_eval(line[len(prefix):])
        assert len(piece) <= chunk_size
        rebuilt += piece
    assert rebuilt == expected_b64


def test_compile_reconstruct_unlimited_uses_single_assignment():
    """``compile_cmd_chunk_size <= 0`` must emit one assignment with the full payload."""
    main = MainModule(mainexample, compile_cmd_chunk_size=0)
    var = main._compile_src_temp_var
    expected_b64 = b64_pickled_source_from_file(main.path)
    lines = list(main._reconstruct_pickled_source_cmds_gen())
    assert len(lines) == 1
    assert lines[0] == '{} = {}'.format(var, repr(expected_b64))
