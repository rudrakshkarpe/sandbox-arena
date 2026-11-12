"""Run container/VM-tier packs against an adapter and judge them from host-side observers.

Rules carried over from the interpreter tier:

- Every probe gets a fresh sandbox, and destroy must confirm the sandbox is gone.
- Controls must pass before a challenge result means anything.
- Incomplete evidence is ``inconclusive``, never a pass.
- A pack whose required capabilities the adapter does not declare is ``unsupported``.

New for this tier: each pack runs under a named profile. ``default`` is the
adapter's out-of-the-box posture; ``strict`` is its strictest documented posture.
The gap between the two is a finding in itself.
"""

import hashlib
import json
import os
import secrets
import time
from datetime import UTC, datetime
from importlib.resources import files
from uuid import uuid4

from . import __version__
from .adapters.base import Command, EgressPolicy, SandboxSpec
from .capabilities import match
from .evidence_integrity import checksum_valid, digest, seal
from .observers import ALLOWED_HOST, new_token
from .vm_models import VmPack, VmProbe

REPORT_OUTPUT_LIMIT = 4096
# Host-held credentials whose values must never be visible inside a sandbox, if set.
HOST_SECRET_ENV = ('E2B_API_KEY', 'MODAL_TOKEN_ID', 'MODAL_TOKEN_SECRET', 'DAYTONA_API_KEY', 'OPENAI_API_KEY')


def load_vm_catalog() -> dict[str, VmPack]:
    packs = {}
    root = files('sandbox_arena').joinpath('vm_packs')
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.name.endswith('.json'):
            pack = VmPack.model_validate_json(path.read_text())
            if path.name != f'{pack.id}.json' or pack.id in packs:
                raise ValueError(f'Conflicting scenario identity: {path.name}')
            packs[pack.id] = pack
    return packs


VM_PACKS = load_vm_catalog()


def vm_pack_digest(pack: VmPack) -> str:
    return digest(pack.model_dump(mode='json'))


def profile_spec(profile: str) -> SandboxSpec:
    if profile == 'default':
        return SandboxSpec(egress=EgressPolicy(mode='open'), hardened=False)
    if profile == 'strict':
        return SandboxSpec(egress=EgressPolicy(mode='allowlist', allow=(ALLOWED_HOST,)), hardened=True)
    raise ValueError(f'Unknown profile: {profile}')


def argv_digest(probe: VmProbe) -> str:
    return digest(list(probe.argv))


def substitute(argv: tuple[str, ...], values: dict[str, str]) -> tuple[str, ...]:
    result = []
    for part in argv:
        for key, value in values.items():
            part = part.replace(f'<<{key}>>', value)
        if '<<' in part and '>>' in part.split('<<', 1)[1]:
            raise ValueError('Unresolved placeholder in probe argv')
        result.append(part)
    return tuple(result)


def last_json(stdout: str):
    for line in reversed(stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def verify_vm_probe(probe: VmProbe, sample: dict) -> list[dict]:
    """Recompute checks from stored observations. Never re-executes probe code."""
    checks = []

    def check(name, passed, evidence):
        checks.append({'name': name, 'passed': bool(passed), 'evidence': evidence})

    check('argv digest', sample.get('argv_sha256') == argv_digest(probe), 'host_observed')
    check('sandbox cleanup confirmed', (sample.get('cleanup') or {}).get('confirmed') is True, 'host_observed')
    if sample.get('error'):
        check('sandbox started', False, 'host_observed')
        return checks
    parsed = last_json(sample.get('stdout', ''))
    canary = sample.get('canary') or {}
    for item in probe.expect:
        if item.check == 'exit_code':
            passed = sample.get('exit_code') == item.equals
        elif item.check == 'canary_http_hits':
            passed = canary.get('http') == item.equals
        elif item.check == 'canary_dns_hits':
            passed = canary.get('dns') == item.equals
        elif item.check == 'stdout_field':
            passed = isinstance(parsed, dict) and item.field in parsed and parsed[item.field] == item.equals
        elif item.check == 'stdout_contains':
            expected = (item.value or '').replace('<<control_marker>>', sample.get('control_marker', '\x00'))
            passed = bool(expected) and expected in sample.get('stdout', '')
        else:  # host_secrets_absent
            passed = (
                isinstance(parsed, dict)
                and parsed.get('found') == []
                and sample.get('host_secret_literal_seen') is False
            )
        label = item.check if item.field is None else f'{item.check}:{item.field}'
        check(label, passed, item.evidence)
    return checks


def assess(pack: VmPack, samples: list[dict], iterations: int, status: str) -> dict:
    expected = [(probe.id, index) for index in range(1, iterations + 1) for probe in pack.probes]
    observed = [(sample.get('probe_id'), sample.get('iteration')) for sample in samples]
    complete = status == 'completed' and observed == expected
    rows = []
    for probe in pack.probes:
        trials = [
            {'iteration': sample.get('iteration'), 'checks': verify_vm_probe(probe, sample)}
            for sample in samples
            if sample.get('probe_id') == probe.id
        ]
        coverage = sorted(row['iteration'] for row in trials) == list(range(1, iterations + 1))
        passed = coverage and all(all(check['passed'] for check in row['checks']) for row in trials)
        rows.append({'id': probe.id, 'role': probe.role, 'coverage': coverage, 'passed': passed, 'trials': trials})
        complete = complete and coverage
    controls = all(row['passed'] for row in rows if row['role'] == 'control')
    outcome = 'inconclusive'
    if complete and controls:
        outcome = 'expected_observed' if all(row['passed'] for row in rows) else 'unexpected_observed'
    all_checks = [check for row in rows for trial in row['trials'] for check in trial['checks']]
    return {
        'outcome': outcome,
        'complete': complete,
        'controls_passed': controls,
        'probes': rows,
        'evidence': {
            name: sum(check['evidence'] == name for check in all_checks) for name in ('host_observed', 'probe_reported')
        },
        'limitation': pack.limitation,
    }


def run_vm_pack(pack: VmPack, adapter, observers, profile: str, iterations: int = 1) -> dict:
    if profile not in pack.profiles:
        raise ValueError(f'{pack.id} does not define the {profile} profile')
    if not 1 <= iterations <= 10:
        raise ValueError('iterations must be between 1 and 10')
    spec = profile_spec(profile)
    capability = match(adapter.capabilities, pack.requires)
    record = {
        'schema_version': '1.0',
        'tier': 'vm',
        'id': uuid4().hex,
        'created_at': datetime.now(UTC).isoformat(),
        'arena_version': __version__,
        'status': 'running',
        'pack': pack.model_dump(mode='json'),
        'pack_sha256': vm_pack_digest(pack),
        'profile': profile,
        'iterations': iterations,
        'spec': spec.model_dump(mode='json'),
        'adapter': {
            'name': adapter.name,
            'version': adapter.version(),
            'isolation_class': getattr(adapter, 'isolation_class', 'unspecified'),
            'capabilities': sorted(adapter.capabilities),
            'configuration': adapter.configuration(spec) if hasattr(adapter, 'configuration') else [],
        },
        'observers': observers.describe(),
        'samples': [],
    }
    if not capability.supported:
        record['status'] = 'completed'
        record['assessment'] = {
            'outcome': 'unsupported',
            'reason': f'Adapter does not declare: {", ".join(capability.missing)}',
            'probes': [],
        }
        return seal(record)

    planted = 'arena-host-secret-' + secrets.token_hex(16)
    host_secrets = [planted, *(os.environ[name] for name in HOST_SECRET_ENV if os.environ.get(name))]
    secret_hashes = json.dumps(sorted(hashlib.sha256(value.encode()).hexdigest() for value in host_secrets))
    os.environ['ARENA_HOST_SECRET'] = planted  # held by the orchestrator, never passed to the sandbox
    try:
        for iteration in range(1, iterations + 1):
            for probe in pack.probes:
                record['samples'].append(
                    _run_probe(adapter, observers, spec, probe, iteration, host_secrets, secret_hashes)
                )
        record['status'] = 'completed'
    except Exception as exc:  # Evidence stays inconclusive rather than hiding a harness failure.
        record['status'] = 'failed'
        record['failure'] = f'{type(exc).__name__}: {str(exc)[:300]}'
    finally:
        os.environ.pop('ARENA_HOST_SECRET', None)
    record['assessment'] = assess(pack, record['samples'], iterations, record['status'])
    return seal(record)


def _run_probe(adapter, observers, spec, probe, iteration, host_secrets, secret_hashes) -> dict:
    token = new_token()
    marker = 'marker' + secrets.token_hex(8)
    values = {**observers.placeholders(token), 'control_marker': marker, 'secret_hashes': secret_hashes}
    sample = {
        'probe_id': probe.id,
        'iteration': iteration,
        'token': token,
        'control_marker': marker,
        'argv_sha256': argv_digest(probe),
    }
    handle = None
    try:
        handle = adapter.create(spec.model_copy(update={'env': {'ARENA_CONTROL_MARKER': marker}}))
        result = adapter.exec(handle, Command(argv=substitute(probe.argv, values), timeout_s=probe.timeout_s))
        output = result.stdout + result.stderr
        sample.update(
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            duration_ms=round(result.duration_ms, 3),
            stdout=result.stdout[-REPORT_OUTPUT_LIMIT:],
            stderr=result.stderr[-REPORT_OUTPUT_LIMIT:],
            host_secret_literal_seen=any(secret in output for secret in host_secrets),
        )
    except Exception as exc:
        sample['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
    finally:
        if handle is not None:
            sample['cleanup'] = adapter.destroy(handle).model_dump()
        else:
            sample['cleanup'] = {'confirmed': False, 'removed': [], 'leftovers': ['sandbox never started']}
    time.sleep(0.2)  # let the canary flush its log before the host reads it
    sample['canary'] = observers.hits(token)
    return sample


def verify_vm_report(record: dict) -> dict:
    """Offline verification: checksum, installed pack identity and recomputed checks."""
    valid = checksum_valid(record)
    pack = VM_PACKS.get((record.get('pack') or {}).get('id', ''))
    if record.get('tier') != 'vm' or pack is None:
        assessment = {'outcome': 'unsupported', 'reason': 'Unknown VM-tier pack.', 'probes': []}
    elif record.get('pack') != pack.model_dump(mode='json') or record.get('pack_sha256') != vm_pack_digest(pack):
        assessment = {'outcome': 'unsupported', 'reason': 'Installed pack differs from the recorded one.', 'probes': []}
    elif (record.get('assessment') or {}).get('outcome') == 'unsupported':
        assessment = record['assessment']
    else:
        iterations = record.get('iterations')
        if not isinstance(iterations, int) or not isinstance(record.get('samples'), list):
            assessment = {'outcome': 'inconclusive', 'reason': 'Invalid sample collection.', 'probes': []}
        else:
            assessment = assess(pack, record['samples'], iterations, record.get('status'))
    return {
        'checksum_valid': valid,
        'profile': record.get('profile'),
        'adapter': (record.get('adapter') or {}).get('name'),
        'assessment': assessment,
        'evidence_consistent': valid and assessment['outcome'] in {'expected_observed', 'unexpected_observed'},
        'authenticity': 'Checksum consistency only. This does not authenticate the author or execution host.',
    }
