import pytest
from pydantic import ValidationError

from sandbox_arena.scenario_models import Expectation, Probe, ScenarioPack


def test_expectations_require_specific_evidence():
    for value in [{'status': 'denied'}, {'status': 'error'}, {'status': 'limited'}, {'status': 'ok'}]:
        with pytest.raises(ValidationError):
            Expectation(**value)
    assert Expectation(status='denied', denied_min=1).denied_min == 1
    assert Expectation(status='ok', check_result=True, result=None).check_result


def test_pack_requires_control_and_unique_ids():
    probe = Probe(id='attempt', code='42', expect=Expectation(status='ok', check_result=True, result=42))
    values = dict(
        id='test',
        version='1.0.0',
        title='Test',
        category='Evidence',
        objective='Verify',
        boundary='Host',
        limitation='Synthetic',
    )
    with pytest.raises(ValidationError):
        ScenarioPack(**values, probes=[probe, probe])
    control = probe.model_copy(update={'id': 'control', 'role': 'control'})
    assert len(ScenarioPack(**values, probes=[control, probe]).probes) == 2
    with pytest.raises(ValidationError):
        Probe(id='../path', code='1', expect=probe.expect)
