"""Deterministic host checks, independent of guest assertions and stored verdicts.

Every check carries an evidence class:

- ``host_observed``: measured by the host outside the sandbox (audit log, output
  collector, code digest). Code inside the sandbox cannot produce it.
- ``probe_reported``: a value produced by code running inside the sandbox (return
  value, raised exception class, printed text). Catalog probes are reviewed and
  digest-pinned, so this is useful evidence, but it is weaker: in-sandbox code can
  fabricate it. For example ``raise MemoryError(...)`` yields the same status and
  error class as a real allocator limit.
"""

import hashlib
import json

from .scenario_models import Probe

HOST_OBSERVED = 'host_observed'
PROBE_REPORTED = 'probe_reported'
EVIDENCE_CLASSES = (HOST_OBSERVED, PROBE_REPORTED)


def verify_probe(probe: Probe, sample: dict) -> list[dict]:
    checks = []

    def check(name, passed, evidence=HOST_OBSERVED):
        checks.append({'name': name, 'passed': bool(passed), 'evidence': evidence})

    expected = probe.expect
    check('code digest', sample.get('code_sha256') == hashlib.sha256(probe.code.encode()).hexdigest())
    # A denial status is derived from host audit events; other statuses depend on whether guest code raised.
    check(
        'status',
        sample.get('status') == expected.status,
        HOST_OBSERVED if expected.status == 'denied' else PROBE_REPORTED,
    )
    if expected.check_result:
        # JSON equality must distinguish booleans from numbers.
        check(
            'result',
            json.dumps(sample.get('result'), sort_keys=True) == json.dumps(expected.result, sort_keys=True),
            PROBE_REPORTED,
        )
    if expected.error_prefix is not None:
        check('error class', (sample.get('error') or '').startswith(expected.error_prefix), PROBE_REPORTED)
    audit = sample.get('audit', [])
    if expected.denied_min:
        check('host denial evidence', sum(event.get('allowed') is False for event in audit) >= expected.denied_min)
    if expected.allowed_exact is not None:
        check('allowed callback count', sum(event.get('allowed') is True for event in audit) == expected.allowed_exact)
    if expected.stdout_prefix is not None:
        check('stdout prefix', sample.get('stdout', '').startswith(expected.stdout_prefix), PROBE_REPORTED)
    if expected.stdout_max_bytes is not None:
        check('stdout byte budget', len(sample.get('stdout', '').encode()) <= expected.stdout_max_bytes)
    if expected.truncated is not None:
        check('result truncation', sample.get('result_truncated') is expected.truncated)
    return checks


def checks_pass(checks: list[dict]) -> bool:
    return bool(checks) and all(check['passed'] for check in checks)


def evidence_summary(checks: list[dict]) -> dict:
    """Count checks per evidence class so reports show how much rests on in-sandbox claims."""
    return {name: sum(check.get('evidence') == name for check in checks) for name in EVIDENCE_CLASSES}
