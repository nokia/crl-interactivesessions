import sys
import pytest
from crl.interactivesessions.pexpectplatform import is_windows


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.mark.parametrize('platform,iswin', [
    ('win32', True),
    ('linux', False)])
def test_get_exe_suffix(monkeypatch, platform, iswin):
    monkeypatch.setattr(sys, 'platform', platform)
    assert is_windows() is iswin
