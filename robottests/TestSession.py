""" This is a test session for testing in local *Linux* host.
"""

__copyright__ = 'Copyright (C) 2019, Nokia'


from crl.interactivesessions.InteractiveSession import (
    InteractiveSession,
    BashShell,
    PythonShell)


class TestSession(object):

    def __init__(self):
        self.session = InteractiveSession(dump_received='dump_received.txt', dump_outgoing='dump_outgoing.txt')
        self.session.spawn(BashShell())

    def get_session(self):
        return self.session

    def close(self):
        self.session.close()
