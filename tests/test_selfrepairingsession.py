from io import StringIO
import sys
import pytest
from crl.interactivesessions.SelfRepairingSession import (
    ShellSubprocessPickler)
from crl.interactivesessions.ShellSubprocess import (
    ShellSubprocess, SuccessfulExecutionResult, FailedExecutionResult)
from . import custommodule

__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture()
def shellsubprocesspickler():
    return ShellSubprocessPickler(StringIO())


@pytest.mark.parametrize('cls_name, expected_cls', [
    ('SuccessfulExecutionResult', SuccessfulExecutionResult),
    ('FailedExecutionResult', FailedExecutionResult)])
def test_shellsubprocesspickler_find_class(
        shellsubprocesspickler, cls_name, expected_cls):
    my_class = shellsubprocesspickler.find_class(
        ShellSubprocess.get_module_name(), cls_name)
    assert my_class == expected_cls


def test_shellsubprocesspickler_calls_parent_find_class(shellsubprocesspickler):
    internal_mod_name = '__custommodule'
    sys.modules[internal_mod_name] = custommodule
    assert custommodule.CustomClass == shellsubprocesspickler.find_class(
        internal_mod_name, custommodule.CustomClass.__name__)
