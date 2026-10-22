import hashlib

from sandbox_arena.evidence_integrity import seal
from sandbox_arena.playground_models import RunSpec
from sandbox_arena.scenario_catalog import PACKS, pack_digest
from sandbox_arena.scenario_reports import assess_scenario, verify_report


def record():
    pack = PACKS['fixture-permission']
    samples = []
    for probe in pack.probes:
        samples.append(
            dict(
                workload_id=probe.id,
                iteration=1,
                warmup=False,
                status=probe.expect.status,
                verdict='pass',
                result=probe.expect.result,
                audit=[{'allowed': False}] if probe.role == 'challenge' else [],
                setup_ms=0,
                execution_ms=1,
                cleanup_ms=0,
                total_ms=1,
                code_sha256=hashlib.sha256(probe.code.encode()).hexdigest(),
            )
        )
    return dict(
        schema_version='1.0',
        status='completed',
        scenario=pack.model_dump(mode='json'),
        scenario_sha256=pack_digest(pack),
        spec=RunSpec(mode='scenario', scenario_id=pack.id, iterations=1).model_dump(),
        samples=samples,
    )


def test_complete_evidence_and_checksum_are_both_required():
    data = record()
    assert verify_report(seal(data))['verified']
    data['samples'][1]['audit'] = []
    assert assess_scenario(data)['outcome'] == 'unexpected_observed'
    data['samples'][0]['result'] = 0
    assert assess_scenario(data)['outcome'] == 'inconclusive'


def test_missing_duplicate_and_changed_pack_evidence_fail_closed():
    data = record()
    data['samples'].append(data['samples'][0])
    assert assess_scenario(data)['outcome'] == 'inconclusive'
    data = record()
    data['status'] = 'cancelled'
    assert assess_scenario(data)['outcome'] == 'inconclusive'
    data['scenario']['version'] = '9.0.0'
    assert assess_scenario(data)['outcome'] == 'unsupported'


def test_policy_mismatch_and_out_of_order_evidence_are_inconclusive():
    data = record()
    data['spec']['allow_fixture'] = True
    assert assess_scenario(data)['outcome'] == 'inconclusive'
    data = record()
    data['samples'].reverse()
    assert assess_scenario(data)['outcome'] == 'inconclusive'
    data['scenario'] = None
    assert assess_scenario(data)['outcome'] == 'unsupported'


def test_unknown_report_schema_is_not_verified():
    data = record()
    data['schema_version'] = '999.0'
    assert verify_report(seal(data))['assessment']['outcome'] == 'unsupported'
