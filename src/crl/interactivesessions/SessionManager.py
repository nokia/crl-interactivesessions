from six import iteritems


__copyright__ = 'Copyright (C) 2019, Nokia'


class SessionManager(object):

    def __init__(self, create_runner_session):
        self._sessions = {}
        self._create_runner_session = create_runner_session

    @property
    def subclass_name(self):
        return None

    def run(self, session, node, cmd):
        return self.get_or_create(session, node).run(cmd)

    def get_or_create(self, session, node):
        if (session, node) not in self._sessions:
            self._create_session(session, node)
        return self._sessions[(session, node)]

    def _create_session(self, session, node):
        self._sessions[(session, node)] = self._create_runner_session(
            node,
            subclass_name=self.subclass_name)

    def close(self):
        for _, session in iteritems(self._sessions):
            session.close()
        self._sessions = {}

    def get_status_code(self, session, node):
        return self._sessions[(node, session)].get_status_code()

    def __str__(self):
        return "Session Manager"
