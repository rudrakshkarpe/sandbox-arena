"""Recompute observations without executing code or trusting saved verdicts."""

from pydantic import ValidationError

from .evidence_integrity import checksum_valid
from .playground_models import RunSpec, Sample
from .scenario_catalog import PACKS, pack_digest
from .scenario_verifier import checks_pass, verify_probe


def assess_scenario(record: dict) -> dict:
    if record.get('schema_version') != '1.0':
        return {'outcome': 'unsupported', 'reason': 'Unsupported report schema.', 'probes': []}
    snapshot = record.get('scenario', {})
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('id'), str):
        return {'outcome': 'unsupported', 'reason': 'Missing scenario identity.', 'probes': []}
    pack = PACKS.get(snapshot.get('id'))
    if pack is None or snapshot != pack.model_dump(mode='json') or record.get('scenario_sha256') != pack_digest(pack):
        return {
            'outcome': 'unsupported',
            'reason': 'The installed catalog does not match the recorded pack.',
            'probes': [],
        }
    try:
        spec = RunSpec.model_validate(record.get('spec'))
        if spec.mode != 'scenario' or spec.scenario_id != pack.id:
            raise ValueError('Scenario identity differs from run policy')
    except ValueError, TypeError:
        return {'outcome': 'inconclusive', 'reason': 'Invalid or mismatched run policy.', 'probes': []}
    iterations = spec.iterations
    if not isinstance(record.get('samples'), list) or len(record['samples']) > 40:
        return {'outcome': 'inconclusive', 'reason': 'Invalid sample collection.', 'probes': []}
    rows = []
    try:
        samples = [Sample.model_validate(value).model_dump() for value in record.get('samples', [])]
    except ValidationError, TypeError:
        return {'outcome': 'inconclusive', 'reason': 'Invalid sample evidence.', 'probes': []}
    expected_ids = {probe.id for probe in pack.probes}
    sequence = [(probe.id, index) for index in range(1, iterations + 1) for probe in pack.probes]
    observed = [(sample['workload_id'], sample['iteration']) for sample in samples]
    complete = record.get('status') == 'completed' and observed == sequence
    complete = complete and all(sample['workload_id'] in expected_ids and not sample['warmup'] for sample in samples)
    for probe in pack.probes:
        matching = [sample for sample in samples if sample['workload_id'] == probe.id]
        coverage = sorted(sample['iteration'] for sample in matching) == list(range(1, iterations + 1))
        checks = [{'iteration': sample['iteration'], 'checks': verify_probe(probe, sample)} for sample in matching]
        passed = coverage and all(checks_pass(row['checks']) for row in checks)
        rows.append({'id': probe.id, 'role': probe.role, 'coverage': coverage, 'passed': passed, 'trials': checks})
        complete = complete and coverage
    controls = all(row['passed'] for row in rows if row['role'] == 'control')
    outcome = 'inconclusive'
    if complete and controls:
        outcome = 'expected_observed' if all(row['passed'] for row in rows) else 'unexpected_observed'
    return {
        'outcome': outcome,
        'complete': complete,
        'controls_passed': controls,
        'probes': rows,
        'limitation': pack.limitation,
    }


def verify_report(record: dict) -> dict:
    assessment = assess_scenario(record)
    valid = checksum_valid(record)
    return {
        'checksum_valid': valid,
        'assessment': assessment,
        'verified': valid and assessment['outcome'] == 'expected_observed',
        'authenticity': 'Checksum consistency only. This does not authenticate the author or execution host.',
    }
