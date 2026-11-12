"""VM-tier contracts, verdict logic and evidence labels, without a Docker daemon."""

import json

import pytest
from pydantic import ValidationError

from sandbox_arena.adapters.base import CleanupReport, ExecResult, Handle
from sandbox_arena.capabilities import match
from sandbox_arena.evidence_integrity import seal
from sandbox_arena.vm_models import ASSERTION_EVIDENCE, VmPack
from sandbox_arena.vm_runner import VM_PACKS, run_vm_pack, substitute, verify_vm_report


class FakeObservers:
    """Simulates the canary. ``leak`` decides whether challenge traffic reaches it."""

    def __init__(self, leak=False):
        self.leak = leak
        self.seen: dict[str, dict] = {}

    def placeholders(self, token):
        return {
            'token': token,
            'allowed_url': 'http://allowed/',
            'allowed_host': 'allowed',
            'canary_url': f'http://canary/{token}',
            'canary_ip_url': f'http://10.0.0.9/{token}',
            'redirect_url': f'http://allowed/redirect?to=http://canary/{token}',
            'exfil_name': f'{token}.exfil',
        }

    def hits(self, token):
        return self.seen.get(token, {'http': 0, 'dns': 0})

    def describe(self):
        return {'kind': 'fake'}


class FakeAdapter:
    """Answers each probe the way a well-behaved or leaky sandbox would, keyed on the probe code."""

    name = 'fake'
    capabilities = frozenset({'exec.shell', 'net.egress_policy'})

    def __init__(self, observers, leak_secret=False, confirm_cleanup=True):
        self.observers, self.leak_secret, self.confirm_cleanup = observers, leak_secret, confirm_cleanup

    def version(self):
        return 'fake 1'

    def create(self, spec):
        return Handle(adapter='fake', id='sbx', detail={'marker': spec.env.get('ARENA_CONTROL_MARKER', '')})

    def exec(self, handle, command):
        code = command.argv[-1]
        token = next(
            (part for part in code.replace('/', ' ').replace("'", ' ').split() if part.startswith('arena')), ''
        )
        if 'getaddrinfo' in code and '.exfil' in code:
            if self.observers.leak:
                self.observers.seen[token.split('.')[0]] = {'http': 0, 'dns': 1}
            return ExecResult(exit_code=0, stdout='{"resolved": false}')
        if 'getaddrinfo' in code:
            return ExecResult(exit_code=0, stdout='{"resolved": true}')
        if 'ARENA_CONTROL_MARKER' in code:
            return ExecResult(exit_code=0, stdout=json.dumps({'marker': handle.detail['marker']}))
        if 'found' in code:
            found = ['x'] if self.leak_secret else []
            return ExecResult(exit_code=0, stdout=json.dumps({'found': found, 'runtime_sockets': []}))
        if 'canary' in code or '10.0.0.9' in code:
            if self.observers.leak:
                self.observers.seen[token] = {'http': 1, 'dns': 0}
            return ExecResult(exit_code=0, stdout='{"reached": false}')
        return ExecResult(exit_code=0, stdout='{"status": 200}')

    def destroy(self, handle):
        return CleanupReport(confirmed=self.confirm_cleanup)


def test_catalog_packs_validate_and_declare_registered_capabilities():
    assert set(VM_PACKS) == {'egress-deny', 'dns-exfil', 'metadata-endpoint', 'secret-exposure'}
    for pack in VM_PACKS.values():
        assert pack.tier == 'vm'
        assert any(probe.role == 'control' for probe in pack.probes)


def test_pack_contract_rejects_missing_control_and_unknown_capability():
    base = VM_PACKS['dns-exfil'].model_dump(mode='json')
    with pytest.raises(ValidationError):
        VmPack.model_validate({**base, 'probes': [p for p in base['probes'] if p['role'] != 'control']})
    with pytest.raises(ValidationError):
        VmPack.model_validate({**base, 'requires': ['exec.shel']})


def test_challenge_cannot_rest_on_exit_code_alone():
    base = VM_PACKS['dns-exfil'].model_dump(mode='json')
    base['probes'][1]['expect'] = [{'check': 'exit_code', 'equals': 0}]
    with pytest.raises(ValidationError):
        VmPack.model_validate(base)


def test_canary_assertions_are_host_observed_and_stdout_is_probe_reported():
    assert ASSERTION_EVIDENCE['canary_http_hits'] == 'host_observed'
    assert ASSERTION_EVIDENCE['canary_dns_hits'] == 'host_observed'
    assert ASSERTION_EVIDENCE['stdout_field'] == 'probe_reported'
    assert ASSERTION_EVIDENCE['host_secrets_absent'] == 'probe_reported'


def test_unknown_capabilities_never_match():
    assert not match(frozenset({'exec.shell'}), ('exec.shell', 'made.up')).supported
    assert match(frozenset({'exec.shell'}), ('exec.shell',)).supported


def test_unresolved_placeholder_is_rejected():
    with pytest.raises(ValueError):
        substitute(('python3', '-c', 'print("<<missing>>")'), {'token': 'x'})


@pytest.mark.parametrize('pack_id', ['egress-deny', 'dns-exfil'])
def test_contained_sandbox_is_expected_and_leaky_one_is_unexpected(pack_id):
    pack = VM_PACKS[pack_id]
    contained = FakeObservers(leak=False)
    record = run_vm_pack(pack, FakeAdapter(contained), contained, 'strict')
    assert record['assessment']['outcome'] == 'expected_observed'
    leaky = FakeObservers(leak=True)
    record = run_vm_pack(pack, FakeAdapter(leaky), leaky, 'default')
    assert record['assessment']['outcome'] == 'unexpected_observed'
    failing = [row for row in record['assessment']['probes'] if not row['passed']]
    assert failing and all(row['role'] == 'challenge' for row in failing)


def test_secret_scan_detects_a_leak():
    observers = FakeObservers()
    record = run_vm_pack(VM_PACKS['secret-exposure'], FakeAdapter(observers, leak_secret=True), observers, 'strict')
    assert record['assessment']['outcome'] == 'unexpected_observed'


def test_unconfirmed_cleanup_fails_the_probe():
    observers = FakeObservers()
    adapter = FakeAdapter(observers, confirm_cleanup=False)
    record = run_vm_pack(VM_PACKS['dns-exfil'], adapter, observers, 'strict')
    assert record['assessment']['outcome'] == 'inconclusive'  # the control fails too


def test_missing_capability_is_unsupported_not_failed():
    observers = FakeObservers()
    adapter = FakeAdapter(observers)
    adapter.capabilities = frozenset({'exec.shell'})
    record = run_vm_pack(VM_PACKS['egress-deny'], adapter, observers, 'strict')
    assert record['assessment']['outcome'] == 'unsupported'
    assert record['samples'] == []


def test_offline_verification_recomputes_and_detects_tampering():
    observers = FakeObservers()
    record = run_vm_pack(VM_PACKS['egress-deny'], FakeAdapter(observers), observers, 'strict')
    assert verify_vm_report(record)['evidence_consistent']
    tampered = json.loads(json.dumps(record))
    tampered['samples'][1]['canary']['http'] = 3
    assert not verify_vm_report(tampered)['checksum_valid']
    resealed = seal({key: value for key, value in tampered.items() if key != 'integrity'})
    # A recomputed checksum hides the edit from the checksum, but the recomputed verdict changes.
    assert verify_vm_report(resealed)['assessment']['outcome'] == 'unexpected_observed'


def test_reports_never_contain_host_secret_values(monkeypatch):
    monkeypatch.setenv('E2B_API_KEY', 'e2b_live_secret_value_123456')
    observers = FakeObservers()
    record = run_vm_pack(VM_PACKS['secret-exposure'], FakeAdapter(observers), observers, 'strict')
    assert 'e2b_live_secret_value_123456' not in json.dumps(record)
    assert 'arena-host-secret-' not in json.dumps(record)
