import threading

import pytest

from monty_incident_lab.benchmarks import WORKLOADS
from monty_incident_lab.playground_models import RunSpec
from monty_incident_lab.playground_runner import MontyProvider, Runner, RunStore, summarize


@pytest.mark.parametrize('key', list(WORKLOADS))
def test_real_benchmark_contract(pool, key):
    workload = WORKLOADS[key]
    sample = MontyProvider(pool).execute(RunSpec(code=workload.code), workload.code, key, 1, False)
    assert sample.verdict == 'pass', sample.model_dump()
    assert sample.total_ms >= sample.execution_ms >= 0


def test_permissions_isolation_limits_and_recovery(pool):
    adapter = MontyProvider(pool)

    def execute(code, **options):
        return adapter.execute(RunSpec(code=code, **options), code, 'custom', 1, False)

    denied = execute('try:\n    read_fixture()\nexcept Exception:\n    pass\n42', allow_fixture=False)
    assert denied.status == 'denied'
    assert denied.result == 42
    assert denied.audit[0]['allowed'] is False
    assert execute('secret = 123\nsecret').result == 123
    assert execute('secret').status == 'error'
    assert execute('x = [0] * 20_000_000\nlen(x)').status == 'limited'
    assert execute('6 * 7').result == 42
    assert execute("'x' * 20000").result_truncated
    assert execute('float("nan")').status == 'error'
    assert execute('21 * 2').result == 42


def test_queue_admission_cancellation_and_restart(tmp_path):
    started, release = threading.Event(), threading.Event()

    class SlowProvider:
        def execute(self, *args):
            started.set()
            release.wait(5)
            raise RuntimeError('Synthetic worker failure')

    store = RunStore(tmp_path / 'runs.db')
    runner = Runner(SlowProvider(), store)
    try:
        first = runner.submit(RunSpec(code='1'))
        assert started.wait(2)
        queued = [runner.submit(RunSpec(code='1')) for _ in range(7)]
        with pytest.raises(OverflowError):
            runner.submit(RunSpec(code='1'))
        for key in queued:
            runner.cancel(key)
        release.set()
        runner.executor.shutdown(wait=True)
        assert store.get(first)['status'] == 'failed'
        assert all(store.get(key)['status'] == 'cancelled' for key in queued)
        store.save({'id': 'restart', 'status': 'running', 'events': []})
    finally:
        release.set()
        runner.close()
    reopened = RunStore(tmp_path / 'runs.db')
    assert reopened.get('restart')['status'] == 'interrupted'
    reopened.close()


def test_statistics_exclude_warmups_and_failed_trials():
    samples = [
        {'workload_id': 'x', 'warmup': False, 'verdict': 'pass', 'execution_ms': value} for value in range(1, 21)
    ]
    samples += [
        {'workload_id': 'x', 'warmup': True, 'verdict': 'pass', 'execution_ms': 999},
        {'workload_id': 'x', 'warmup': False, 'verdict': 'fail', 'execution_ms': 999},
    ]
    result = summarize(samples)[0]
    assert result['samples'] == 21 and result['passed'] == 20 and result['failed'] == 1
    assert result['median_ms'] == 10.5 and result['p95_ms'] == 19
