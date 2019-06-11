from collections import namedtuple
from contextlib import contextmanager
import mock
import pytest

from crl.interactivesessions._runnerintarget import _RunnerInTarget


__copyright__ = 'Copyright (C) 2019, Nokia'


class RunnerInTargetBackground(object):
    def __init__(self, method_processcls):
        self.shelldicts = [{'shellname': 'ExampleShell'}]
        self.runner_in_target = _RunnerInTarget(self.shelldicts)
        self.method_processcls = method_processcls
        self.process_cls = None

    @contextmanager
    def patch(self):
        with mock.patch('crl.interactivesessions.'
                        '_runnerintarget.{}'.format(self.method_processcls.cls)) as p:
            self.process_cls = p
            yield self

    @property
    def method(self):
        return getattr(self.runner_in_target, self.method_processcls.method)


class MethodProcessCls(namedtuple('MethodProcessCls', ['method', 'cls'])):
    pass


@pytest.fixture(params=[
    MethodProcessCls('run_in_background', '_BackgroundProcessWithoutPty'),
    MethodProcessCls('run_in_nocomm_background', '_NoCommBackgroudProcess')])
def runner_in_target_background(request):
    with RunnerInTargetBackground(request.param).patch() as r:
        yield r


def test_run_in_nocomm_background(executable_kwargs,
                                  runner_in_target_background):

    background_method = runner_in_target_background.method('cmd', **executable_kwargs)
    bground_rtr = runner_in_target_background.process_cls.return_value.run.return_value
    assert background_method == bground_rtr

    r = runner_in_target_background.runner_in_target
    runner_in_target_background.process_cls.assert_called_once_with(
        cmd='cmd',
        executable=(
            executable_kwargs['executable']
            if executable_kwargs else
            r.properties.default_executable),
        shelldicts=runner_in_target_background.shelldicts,
        properties=r.properties)
