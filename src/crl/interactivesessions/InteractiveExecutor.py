import logging
from six import iteritems

__copyright__ = 'Copyright (C) 2019, Nokia'


class InteractiveExecutor(object):

    run_number = 0

    def __init__(self, create_node_runner):
        self._create_node_runner = create_node_runner
        self._sessions = {}

    def run(self, node, command, timeout=60, validate_return_status=False):
        self.run_number += 1
        logging.log(7, "Running command %d in %s: "
                    "'%s', "
                    "timeout: %s, "
                    "validate_return_status: %s",
                    self.run_number,
                    node,
                    command,
                    str(timeout),
                    str(validate_return_status))
        session = self._get_or_create_session_for_node(node)
        result = self._get_run_function(
            session, validate_return_status)(
                command,
                timeout=self._unify_timeout(timeout))
        logging.log(7, "Run %d returned %s",
                    self.run_number, result)
        return result

    @staticmethod
    def _unify_timeout(timeout):
        try:
            timeout = float(timeout)
            if 0 <= timeout < 0.0001:
                timeout = 0
            elif timeout < 0:
                timeout = -1
        except (ValueError, TypeError):
            timeout = 60
        return timeout

    @staticmethod
    def _get_run_function(session, is_validate):
        return session.run if is_validate else session.run_no_validate

    def _get_or_create_session_for_node(self, node):
        if node not in self._sessions:
            self._sessions[node] = self._create_node_runner(node)
        return self._sessions[node]

    def close(self):
        for _, session in iteritems(self._sessions):
            session.close()
        self._sessions = {}

    def reset(self):
        for _, session in iteritems(self._sessions):
            session.reset()
