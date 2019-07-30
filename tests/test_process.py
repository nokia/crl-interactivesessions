import mock
import pytest
from crl.interactivesessions._process import _NoCommBackgroudProcess


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def mock_terminalpools():
    with mock.patch('crl.interactivesessions._process._TerminalPools',
                    spec_set=True) as p:
        proxies = mock.Mock()
        p.return_value.get.return_value.proxies = proxies
        proxies.daemon_popen.return_value = 'pid'
        yield p


class MockNoCommBackgroundProcess(_NoCommBackgroudProcess):
    pass


def test_nocommbackgroundprocess(mock_terminalpools):
    p = create_mock_process()

    assert p.run() == 'pid'

    assert_terminalpools(mock_terminalpools, mock_process=p)


class DaemonError(Exception):
    pass


def test_nocommbackgroundprocess_raises(mock_terminalpools):
    p = create_mock_process()
    proxies = mock_terminalpools.return_value.get.return_value.proxies
    proxies.daemon_popen.side_effect = DaemonError

    with pytest.raises(DaemonError):
        p.run()

    assert_terminalpools(mock_terminalpools, mock_process=p)


def create_mock_process():
    return MockNoCommBackgroundProcess('cmd',
                                       executable='executable',
                                       shelldicts=[{'ExampleShell'}],
                                       properties={})


def assert_terminalpools(mock_terminalpools, mock_process):
    tpools = mock_terminalpools.return_value
    tpools.get.assert_called_once_with([set(['ExampleShell'])], {}, zone='background')
    tpools.put.assert_called_once_with(mock_process.terminal)
