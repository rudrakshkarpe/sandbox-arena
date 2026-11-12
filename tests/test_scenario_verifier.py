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


def test_checks_are_labelled_by_evidence_class():
    from sandbox_arena.scenario_verifier import HOST_OBSERVED, PROBE_REPORTED, evidence_summary

    probe = Probe(id='deny', code='read_fixture()', expect={'status': 'denied', 'denied_min': 1})
    sample = {
        'status': 'denied',
        'code_sha256': hashlib.sha256(probe.code.encode()).hexdigest(),
        'audit': [{'allowed': False}],
    }
    labels = {check['name']: check['evidence'] for check in verify_probe(probe, sample)}
    assert labels == {'code digest': HOST_OBSERVED, 'status': HOST_OBSERVED, 'host denial evidence': HOST_OBSERVED}

    probe = Probe(id='answer', code='1', expect={'status': 'ok', 'check_result': True, 'result': 1})
    checks = verify_probe(probe, {'status': 'ok', 'result': 1, 'code_sha256': hashlib.sha256(b'1').hexdigest()})
    assert {check['name']: check['evidence'] for check in checks}['result'] == PROBE_REPORTED
    assert evidence_summary(checks) == {HOST_OBSERVED: 1, PROBE_REPORTED: 2}


def test_every_catalog_check_has_an_evidence_class():
    from sandbox_arena.scenario_catalog import PACKS
    from sandbox_arena.scenario_verifier import EVIDENCE_CLASSES

    for pack in PACKS.values():
        for probe in pack.probes:
            for check in verify_probe(probe, {}):
                assert check['evidence'] in EVIDENCE_CLASSES, (pack.id, check['name'])
