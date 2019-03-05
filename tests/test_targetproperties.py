import pytest
from crl.interactivesessions._targetproperties import _TargetProperties


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.mark.parametrize('property_name, expected_default', [
    ('termination_timeout', 10),
    ('prompt_timeout', 30),
    ('default_executable', '/bin/bash'),
    ('max_processes_in_target', 100),
    ('update_env_dict', {})])
def test_defaultproperties(property_name, expected_default):
    assert _TargetProperties().get_property(property_name) == expected_default
