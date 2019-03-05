import StringIO
import mock
import pytest
from crl.interactivesessions.SelfRepairingSession import (
    Unpickler, ShellSubprocessPickler)
from crl.interactivesessions.ShellSubprocess import (
    ShellSubprocess, SuccessfulExecutionResult, FailedExecutionResult)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture()
def shellsubprocesspickler():
    return ShellSubprocessPickler(StringIO.StringIO())


@pytest.fixture()
def mock_unpickler_find_class():
    with mock.patch.object(Unpickler, 'find_class') as p:
        yield p


@pytest.mark.parametrize('cls_name, expected_cls', [
    ('SuccessfulExecutionResult', SuccessfulExecutionResult),
    ('FailedExecutionResult', FailedExecutionResult)])
def test_shellsubprocesspickler_find_class(
        shellsubprocesspickler, cls_name, expected_cls):
    my_class = shellsubprocesspickler.find_class(
        ShellSubprocess.get_module_name(), cls_name)
    assert my_class == expected_cls


def test_shellsubprocesspickler_calls_parent_find_class(
        shellsubprocesspickler, mock_unpickler_find_class):
    shellsubprocesspickler.find_class(
        'some_module', 'some_class')
    mock_unpickler_find_class.assert_called_once_with(
        shellsubprocesspickler, 'some_module', 'some_class')
