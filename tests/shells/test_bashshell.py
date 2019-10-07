import logging
import os
import pytest
from crl.interactivesessions.InteractiveSession import InteractiveSession
from crl.interactivesessions.shells.bashshell import (
    BashShell,
    BashShellTypeError)
from crl.interactivesessions.shells.remotemodules.compatibility import to_bytes
from .mockspawn import MockSpawn
from .interpreter import (
    HandlerBase,
    HandlerNotMatching,
    Response)


__copyright__ = 'Copyright (C) 2019, Nokia'


LOGGER = logging.getLogger(__name__)


class SlowBannerHandler(HandlerBase):

    _initial_prompt = b'initial-prompt'
    _responses = [Response.create(b'Banner line 1\n'),
                  Response.create(b'Banner line 2\n', latency=1),
                  Response.create(_initial_prompt)]

    def get_responses(self, line):
        path = line.split()[0]
        if os.path.split(path)[-1] != b'bash':
            raise HandlerNotMatching

        self._state.prompt = self.initial_prompt
        return self._responses

    @property
    def initial_prompt(self):
        return self._initial_prompt

    @property
    def expected_banner(self):
        return b''.join([r.response for r in self._responses])


class EmptyResponseHandler(HandlerBase):
    def get_responses(self, line):
        for r in self._get_responses(line):
            p = Response.create(
                self._echo_line(line) + r.response + self._state.prompt)
            LOGGER.debug('Response: %s', p.response)
            yield p

    def _echo_line(self, line):
        return line if self._state.tty_echo else b''

    @staticmethod
    def _get_responses(line):  # pylint: disable=unused-argument
        LOGGER.debug('Creating empty response')
        return [Response.create(b'')]


class EchoHandler(EmptyResponseHandler):

    def _get_responses(self, line):
        response = b''
        for cmd in line.split(b';'):
            tokens = cmd.split()
            if tokens[0] != b'echo':
                raise HandlerNotMatching
            response += self._get_echo_from_tokens(tokens)
        LOGGER.debug('Creating echo response')
        yield Response.create(response)

    @staticmethod
    def _get_echo_from_tokens(tokens):
        return tokens[-1] if tokens[1] == b'-n' else tokens[-1] + b'\n'


class SttyEchoHandler(EmptyResponseHandler):

    _echo_map = {b'echo': True, b'-echo': False}

    def _get_responses(self, line):
        if not line.startswith(b'stty '):
            raise HandlerNotMatching
        for token in line.split():
            if token in self._echo_map:
                self._state.tty_echo = self._echo_map[token]
                LOGGER.debug('tty_echo set to %s', self._state.tty_echo)
                return [Response.create(b'')]

        raise HandlerNotMatching


@pytest.fixture(params=[True, False])
def echo_in_state(mockspawn_state, request):
    mockspawn_state.tty_echo = request.param


@pytest.fixture
def slowbanner_handler():
    slow = SlowBannerHandler()
    MockSpawn.set_handlers([slow,
                            EchoHandler(),
                            SttyEchoHandler(),
                            EmptyResponseHandler()])
    return slow


@pytest.mark.usefixtures('mockspawn', 'echo_in_state')
@pytest.mark.parametrize('echo_in_init', [True, False])
def test_bash_slow_banner(slowbanner_handler, echo_in_init):
    i = InteractiveSession()
    banner = i.spawn(BashShell(tty_echo=echo_in_init, banner_timeout=2))
    assert to_bytes(banner).startswith(slowbanner_handler.expected_banner)


@pytest.mark.parametrize('kwargs', [
    {'wrong': 1, 'banner_timeout': 2},
    {'banner_timeout': 1, 'wrong': 2}])
def test_bash_kwargs_not_accepted(kwargs):
    with pytest.raises(BashShellTypeError) as excinfo:
        BashShell(**kwargs)

    expected = "BashShell() got an unexpected keyword argument 'wrong'"
    assert str(excinfo.value) == expected


def test_get_status_code(statuscodeverifier):
    statuscodeverifier.verify()
