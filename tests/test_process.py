import mock
from crl.interactivesessions._process import _NoCommBackgroudProcess


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockNoCommBackgroundProcess(_NoCommBackgroudProcess):

    def _initialize_terminal(self):
        self.terminal = mock.Mock()
        self.terminalpools = mock.Mock()
        self.proxies = mock.Mock()
        self.proxies.daemon_popen.return_value = 'pid'

    @staticmethod
    def _nocall_comm():
        assert 0, 'Communicate called eventhough it should not'


def test_nocommbackgroundprocess():
    p = MockNoCommBackgroundProcess('cmd',
                                    executable='executable',
                                    shelldicts=[{'ExampleShell'}],
                                    properties={})
    assert p.run() == 'pid'
