"""Local job runner with durable evidence, bounded admission and fresh sessions."""

import hashlib
import json
import platform
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from statistics import median
from typing import Protocol
from uuid import uuid4

from pydantic_monty import CollectString, MontyCrashedError, MontyError, MontyRuntimeError

from .benchmarks import WORKLOADS
from .playground_models import RunSpec, Sample
from .scenario_catalog import PACKS, pack_digest
from .scenario_reports import assess_scenario
from .scenario_verifier import checks_pass, verify_probe

TERMINAL = {'completed', 'cancelled', 'failed', 'interrupted'}
CAPABILITIES = ['python-subset', 'host-callbacks', 'os-policy', 'resource-limits', 'fresh-sessions']


class Provider(Protocol):
    """Adapters must contain execution and release resources before returning."""

    def execute(self, spec: RunSpec, code: str, workload_id: str, iteration: int, warmup: bool) -> Sample: ...


class MontyProvider:
    def __init__(self, pool):
        self.pool = pool

    def execute(self, spec, code, workload_id, iteration, warmup):
        started = time.perf_counter()
        setup_end = execution_end = started
        audit = []
        output = CollectString(max_bytes=4096)
        status, error, raw = 'ok', None, None

        def read_fixture():
            allowed = spec.allow_fixture and len(audit) < 8
            audit.append({'operation': 'read_fixture', 'allowed': allowed, 'layer': 'host policy'})
            if not allowed:
                raise PermissionError('Fixture access is disabled or its call budget is exhausted')
            return [{'name': 'alpha', 'value': 10}, {'name': 'beta', 'value': 20}, {'name': 'gamma', 'value': 30}]

        def deny_os(*, name, args, kwargs, is_async, **future_kwargs):
            if len(audit) < 32:
                audit.append({'operation': str(name)[:120], 'allowed': False, 'layer': 'OS policy'})
            raise PermissionError('This playground does not grant filesystem or network access')

        try:
            with self.pool.checkout(
                limits={
                    'max_memory': spec.memory_mb * 1_000_000,
                    'max_feed_duration_secs': spec.timeout_ms / 1000,
                    'max_turn_duration_secs': spec.timeout_ms / 1000,
                    'max_recursion_depth': 100,
                    'max_suspensions': 32,
                    'max_total_sleep_secs': 0.01,
                },
                os_policy={'datetime': datetime(2026, 1, 1), 'sleep': 'call_host', 'random_start': {'seed': 0}},
            ) as session:
                setup_end = time.perf_counter()
                try:
                    raw = session.feed_run(
                        code,
                        external_lookup={'read_fixture': read_fixture},
                        os=deny_os,
                        print_callback=output,
                    )
                finally:
                    execution_end = time.perf_counter()
        except MontyRuntimeError as exc:
            error = exc.display(format='type-msg')[:2048]
            status = 'limited' if error.split(':', 1)[0] in {'MemoryError', 'TimeoutError'} else 'error'
        except MontyCrashedError as exc:
            status = 'limited' if exc.timed_out else 'error'
            error = 'Worker deadline reached' if exc.timed_out else 'Monty worker stopped unexpectedly'
        except (MontyError, TimeoutError) as exc:
            status, error = 'error', f'{type(exc).__name__}: {str(exc)[:1024]}'
        ended = time.perf_counter()
        if any(not event['allowed'] for event in audit):
            status = 'denied'  # Catching a guest exception does not erase a denied host operation.
        # Guest return values can be cyclic or contain non-JSON numbers.
        try:
            serialized = json.dumps(
                raw,
                default=lambda value: f'<{type(value).__name__}>',
                ensure_ascii=True,
                allow_nan=False,
            )
        except TypeError, ValueError, RecursionError, OverflowError:
            serialized = 'null'
            error = 'Return value cannot be represented as JSON. Return a finite, acyclic JSON-compatible value.'
            if status == 'ok':
                status = 'error'
        workload = WORKLOADS.get(workload_id)
        verdict = 'unverified'
        if workload:
            passed = status == workload.expected_status and (status != 'ok' or raw == workload.expected)
            verdict = 'pass' if passed else 'fail'
        # Export JSON-compatible, bounded evidence, never render guest values as HTML.
        truncated = len(serialized) > 16_384
        result = serialized[:16_384] + '… [truncated]' if truncated else json.loads(serialized)
        return Sample(
            workload_id=workload_id,
            iteration=iteration,
            warmup=warmup,
            status=status,
            verdict=verdict,
            result=result,
            result_truncated=truncated,
            stdout=output.output,
            error=error,
            audit=audit,
            setup_ms=(setup_end - started) * 1000,
            execution_ms=(execution_end - setup_end) * 1000,
            cleanup_ms=(ended - execution_end) * 1000,
            total_ms=(ended - started) * 1000,
            code_sha256=hashlib.sha256(code.encode()).hexdigest(),
        )


def summarize(samples):
    summaries = []
    for key in dict.fromkeys(s['workload_id'] for s in samples):
        measured = [s for s in samples if s['workload_id'] == key and not s['warmup']]
        valid = [s for s in measured if s['verdict'] == 'pass']
        timings = sorted(s['execution_ms'] for s in valid)
        summaries.append(
            {
                'workload_id': key,
                'samples': len(measured),
                'passed': len(valid),
                'failed': sum(s['verdict'] == 'fail' for s in measured),
                'median_ms': median(timings) if timings else None,
                'min_ms': min(timings) if timings else None,
                'max_ms': max(timings) if timings else None,
                # Small interactive runs cannot support a useful tail estimate.
                'p95_ms': timings[max(0, (95 * len(timings) + 99) // 100 - 1)] if len(timings) >= 20 else None,
            }
        )
    return summaries


class RunStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute("CREATE INDEX IF NOT EXISTS runs_created ON runs(json_extract(data, '$.created_at'))")
        self.db.commit()
        # A restarted server must not leave jobs falsely reported as running forever.
        rows = self.db.execute(
            "SELECT data FROM runs WHERE json_extract(data, '$.status') IN ('queued', 'running')"
        ).fetchall()
        for row in rows:
            record = json.loads(row[0])
            if record['status'] not in TERMINAL:
                record['status'] = 'interrupted'
                record['events'].append(
                    {'id': len(record['events']) + 1, 'type': 'interrupted', 'message': 'Server restarted'}
                )
                self.save(record)

    def save(self, record):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO runs VALUES (?, ?)', (record['id'], json.dumps(record)))
            self.db.commit()

    def get(self, run_id):
        with self.lock:
            row = self.db.execute('SELECT data FROM runs WHERE id = ?', (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit=100, offset=0):
        """Read compact metadata without materializing the history's raw samples."""
        with self.lock:
            rows = self.db.execute(
                """SELECT json_object(
                    'id', id, 'created_at', json_extract(data, '$.created_at'),
                    'status', json_extract(data, '$.status'), 'spec', json_extract(data, '$.spec'),
                    'summaries', json_extract(data, '$.summaries')
                ) FROM runs ORDER BY json_extract(data, '$.created_at') DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def close(self):
        self.db.close()


class Runner:
    def __init__(self, provider: Provider, store: RunStore):
        self.provider, self.store = provider, store
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='sandbox-runner')
        self.lock = threading.Lock()
        self.pending: dict[str, threading.Event] = {}

    def submit(self, spec: RunSpec):
        with self.lock:
            if len(self.pending) >= 8:
                raise OverflowError('Run queue is full. Wait for a run to finish.')
            run_id = uuid4().hex
            cancel = threading.Event()
            self.pending[run_id] = cancel
        record = {
            'schema_version': '1.0',
            'id': run_id,
            'created_at': datetime.now(UTC).isoformat(),
            'status': 'queued',
            'spec': spec.model_dump(),
            'samples': [],
            'summaries': [],
            'events': [],
            'environment': {
                'provider': 'monty',
                'monty_version': version('pydantic-monty'),
                'python': platform.python_version(),
                'os': platform.system(),
                'architecture': platform.machine(),
                'runner_concurrency': 1,
                'session_mode': 'fresh session on existing worker pool',
                'timing': 'Host wall clock; execution includes IPC and callbacks. Process cold start is excluded.',
                'memory': 'Monty allocator budget; not process RSS.',
            },
            'workloads': [WORKLOADS[key].model_dump() for key in spec.benchmark_ids]
            if spec.mode == 'benchmark'
            else [],
        }
        if spec.mode == 'scenario':
            pack = PACKS[spec.scenario_id]
            record['scenario'] = pack.model_dump(mode='json')
            record['scenario_sha256'] = pack_digest(pack)
        try:
            self.event(record, 'queued', 'Accepted by the local runner')
            self.executor.submit(self.run, record, spec, cancel)
        except Exception:
            with self.lock:
                self.pending.pop(run_id, None)
            raise
        return run_id

    def event(self, record, kind, message, **extra):
        record['events'].append(
            {
                'id': len(record['events']) + 1,
                'type': kind,
                'at': datetime.now(UTC).isoformat(),
                'message': message,
                **extra,
            }
        )
        self.store.save(record)

    def cancel(self, run_id):
        with self.lock:
            event = self.pending.get(run_id)
            if event:
                event.set()

    def run(self, record, spec, cancel):
        try:
            record['status'] = 'running'
            self.event(record, 'started', 'Runner acquired; every trial uses a fresh session')
            pack = PACKS.get(spec.scenario_id) if spec.mode == 'scenario' else None
            if pack:
                tasks = [
                    (probe.id, probe.code, index, False, probe)
                    for index in range(1, spec.iterations + 1)
                    for probe in pack.probes
                ]
            elif spec.mode == 'benchmark':
                tasks = [
                    (key, WORKLOADS[key].code, index + 1, index < spec.warmups, None)
                    for key in spec.benchmark_ids
                    for index in range(spec.warmups + spec.iterations)
                ]
            else:
                tasks = [('custom', spec.code, 1, False, None)]
            for key, code, index, warmup, probe in tasks:
                if cancel.is_set():
                    break
                self.event(record, 'trial_started', f'{key} · {"warmup" if warmup else "measurement"} {index}')
                sample = self.provider.execute(spec, code, key, index, warmup)
                data = sample.model_dump()
                if probe:
                    data['checks'] = verify_probe(probe, data)
                    data['verdict'] = 'pass' if checks_pass(data['checks']) else 'fail'
                record['samples'].append(data)
                record['summaries'] = summarize(record['samples'])
                self.event(
                    record, 'trial_finished', f'{key} · {sample.status}', sample_index=len(record['samples']) - 1
                )
            record['status'] = 'cancelled' if cancel.is_set() else 'completed'
            if pack:
                record['assessment'] = assess_scenario(record)
            self.event(record, record['status'], 'Session resources released; evidence saved')
        except Exception as exc:
            record['status'] = 'failed'
            self.event(record, 'failed', f'Runner error: {type(exc).__name__}')
        finally:
            with self.lock:
                self.pending.pop(record['id'], None)

    def close(self):
        with self.lock:
            for event in self.pending.values():
                event.set()
        self.executor.shutdown(wait=True)
        self.store.close()
