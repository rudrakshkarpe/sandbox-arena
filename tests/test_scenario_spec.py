import pytest
from pydantic import ValidationError

from sandbox_arena.playground_models import RunSpec


def test_scenario_policy_is_catalog_owned():
    spec = RunSpec(mode='scenario', scenario_id='fixture-permission', iterations=2)
    assert not spec.allow_fixture
    assert spec.warmups == 0
    assert RunSpec.model_validate(spec.model_dump()) == spec
    for overrides in [{'allow_fixture': True}, {'warmups': 1}, {'code': '42'}, {'iterations': 11}, {'timeout_ms': 500}]:
        with pytest.raises(ValidationError):
            RunSpec(mode='scenario', scenario_id='fixture-permission', **overrides)


def test_unknown_and_mixed_mode_scenarios_are_rejected():
    with pytest.raises(ValidationError):
        RunSpec(mode='scenario', scenario_id='../unknown')
    with pytest.raises(ValidationError):
        RunSpec(code='42', scenario_id='fixture-permission')
