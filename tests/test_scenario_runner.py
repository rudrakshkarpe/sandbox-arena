import time

from sandbox_arena.playground_models import RunSpec
from sandbox_arena.playground_runner import TERMINAL, MontyProvider, Runner, RunStore


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
    finally:
        runner.close()
