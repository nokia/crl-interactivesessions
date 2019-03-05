import pytest
from crl.interactivesessions.shells.registershell import (
    RegisteredShells)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.mark.parametrize('shellname', [
    'BashShell',
    'NamespaceShell',
    'PythonShell',
    'SftpShell',
    'SshShell'])
def test_builtin_shell_registration(shellname):
    assert RegisteredShells().get_shellcls(shellname).__name__ == shellname
