import time

from sandbox_arena.playground_models import RunSpec
from sandbox_arena.playground_runner import TERMINAL, MontyProvider, Runner, RunStore
from sandbox_arena.scenario_reports import verify_report


def wait_done(runner, run_id):
    for _ in range(300):
        record = runner.store.get(run_id)
        if record['status'] in TERMINAL:
            return record
        time.sleep(0.01)
    raise AssertionError('Run did not finish')


def test_runner_preserves_probe_order_and_fresh_sessions(pool, tmp_path):
    runner = Runner(MontyProvider(pool), RunStore(tmp_path / 'runs.db'))
    try:
        run_id = runner.submit(RunSpec(mode='scenario', scenario_id='fresh-session-state', iterations=2))
        record = wait_done(runner, run_id)
        assert record['status'] == 'completed'
        assert record['assessment']['outcome'] == 'expected_observed'
        assert [(s['workload_id'], s['iteration']) for s in record['samples']] == [
            ('control', 1),
            ('next-session', 1),
            ('control', 2),
            ('next-session', 2),
        ]
        assert all(sample['checks'] for sample in record['samples'])
        assert record['scenario']['version'] == '1.0.0'
        assert verify_report(record)['verified']
    finally:
        runner.close()


def test_interrupted_runs_are_sealed_as_inconclusive(tmp_path):
    from sandbox_arena.evidence_integrity import checksum_valid
    from sandbox_arena.scenario_catalog import PACKS, pack_digest

    path = tmp_path / 'restart.db'
    pack = PACKS['fixture-permission']
    store = RunStore(path)
    store.save(
        dict(
            id='unfinished',
            status='running',
            events=[],
            samples=[],
            spec={'iterations': 1},
            scenario=pack.model_dump(mode='json'),
            scenario_sha256=pack_digest(pack),
        )
    )
    store.close()
    recovered = RunStore(path)
    try:
        record = recovered.get('unfinished')
        assert record['status'] == 'interrupted'
        assert record['assessment']['outcome'] == 'inconclusive'
        assert checksum_valid(record)
    finally:
        recovered.close()


def test_replay_preserves_configuration_and_parent_digest(pool, tmp_path):
    import pytest

    runner = Runner(MontyProvider(pool), RunStore(tmp_path / 'replay.db'))
    try:
        source = wait_done(runner, runner.submit(RunSpec(mode='scenario', scenario_id='caught-denial', iterations=1)))
        replay = wait_done(runner, runner.replay(source))
        assert replay['id'] != source['id']
        assert replay['spec'] == source['spec']
        assert replay['replay_of']['report_sha256'] == source['integrity']['digest']
        assert verify_report(replay)['verified']
        source['samples'][0]['result'] = 'edited'
        with pytest.raises(ValueError, match='checksum'):
            runner.replay(source)
    finally:
        runner.close()
