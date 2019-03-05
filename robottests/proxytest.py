__copyright__ = 'Copyright (C) 2019, Nokia'


class TestResponse(object):
    def __init__(self, testid, status):
        self.testid = testid
        self.status = status


class ProxyTest(object):
    def __init__(self, testid):
        self.testid = testid

    def test(self, status):
        return TestResponse(self.testid, status)
