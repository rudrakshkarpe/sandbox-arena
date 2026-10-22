"""Deterministic host checks, independent of guest assertions and stored verdicts."""

import hashlib
import json

from .scenario_models import Probe


def verify_probe(probe: Probe, sample: dict) -> list[dict]:
    checks = []

    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})

    expected = probe.expect
    check('code digest', sample.get('code_sha256') == hashlib.sha256(probe.code.encode()).hexdigest())
    check('status', sample.get('status') == expected.status)
    if expected.check_result:
        # JSON equality must distinguish booleans from numbers.
        check('result', json.dumps(sample.get('result'), sort_keys=True) == json.dumps(expected.result, sort_keys=True))
    if expected.error_prefix is not None:
        check('error class', (sample.get('error') or '').startswith(expected.error_prefix))
    audit = sample.get('audit', [])
    if expected.denied_min:
        check('host denial evidence', sum(event.get('allowed') is False for event in audit) >= expected.denied_min)
    if expected.allowed_exact is not None:
        check('allowed callback count', sum(event.get('allowed') is True for event in audit) == expected.allowed_exact)
    if expected.stdout_prefix is not None:
        check('stdout prefix', sample.get('stdout', '').startswith(expected.stdout_prefix))
    if expected.stdout_max_bytes is not None:
        check('stdout byte budget', len(sample.get('stdout', '').encode()) <= expected.stdout_max_bytes)
    if expected.truncated is not None:
        check('result truncation', sample.get('result_truncated') is expected.truncated)
    return checks


def checks_pass(checks: list[dict]) -> bool:
    return bool(checks) and all(check['passed'] for check in checks)
