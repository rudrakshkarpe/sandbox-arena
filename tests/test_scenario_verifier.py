import hashlib

from sandbox_arena.scenario_models import Probe
from sandbox_arena.scenario_verifier import checks_pass, verify_probe


def test_denial_requires_host_evidence_and_matching_code():
    probe = Probe(id='deny', code='read_fixture()', expect={'status': 'denied', 'denied_min': 1})
    sample = {'status': 'denied', 'code_sha256': hashlib.sha256(probe.code.encode()).hexdigest(), 'audit': []}
    assert not checks_pass(verify_probe(probe, sample))
    sample['audit'] = [{'allowed': False}]
    assert checks_pass(verify_probe(probe, sample))
    sample['code_sha256'] = 'forged'
    assert not checks_pass(verify_probe(probe, sample))


def test_boolean_does_not_pass_numeric_result_check():
    probe = Probe(id='answer', code='1', expect={'status': 'ok', 'check_result': True, 'result': 1})
    sample = {'status': 'ok', 'result': True, 'code_sha256': hashlib.sha256(b'1').hexdigest()}
    assert not checks_pass(verify_probe(probe, sample))
    sample['result'] = 1
    assert checks_pass(verify_probe(probe, sample))
