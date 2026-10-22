"""A bounded host capability. Sandbox code never receives a file path or token."""

import hashlib
import json
import math
from importlib.resources import files

import logfire

from .models import Analysis, AuditEvent, Scenario

SOURCE_COMMIT = '79ef0f2456e64879bd2f41c90d1610a031191495'
SOURCE_URL = (
    f'https://github.com/rudrakshkarpe/logfire-inference-lab/blob/{SOURCE_COMMIT}/docs/evidence/gemma4-h100-run.json'
)
CAPTURE_BYTES = files('monty_incident_lab').joinpath('data/capture.json').read_bytes()
CAPTURE_SHA256 = hashlib.sha256(CAPTURE_BYTES).hexdigest()
CAPTURE = json.loads(CAPTURE_BYTES)
SCOPE = 'inference-lab'


def record(scenario: str) -> dict:
    """Copy only the fields this investigation needs, not full capture metadata."""
    data = CAPTURE['scenarios'][scenario]
    return {
        'ref': f'{CAPTURE["capture"]["capture_id"]}/{scenario}',
        'requests': data['requests'],
        'first_content_s': data['p95_first_content_s'],
        'queue_s': data['p95_engine_time_in_queue_s'],
        'prefill_s': data['p95_engine_time_in_model_prefill_s'],
        'engine_spans': data['engine_request_spans'],
    }


class EvidenceAccess:
    """One fixed scope and two records per run, set by the trusted application.

    Scope represents authorization policy, not a production identity system.
    No account identifier from a browser or a model determines the allowed scope.
    """

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.audit: list[AuditEvent] = []
        self.calls = 0
        self.reads: set[str] = set()

    def read_evidence(self, scope: str, scenario: str) -> dict:
        self.calls += 1
        allowed = (
            type(scope) is str
            and type(scenario) is str
            and scope == SCOPE
            and scenario in {'baseline', self.scenario}
            and self.calls <= 4
        )
        self.audit.append(
            AuditEvent(
                operation='read_evidence',
                allowed=allowed,
                detail='Authorized scenario aggregate' if allowed else 'Outside scope or call budget',
            )
        )
        with logfire.span('evidence.read', allowed=allowed, callback_number=self.calls):
            if not allowed:
                raise PermissionError('Evidence request denied by host policy')
            self.reads.add(scenario)
            return record(scenario)

    def deny_os(self, *, name: str, args: tuple, kwargs: dict, is_async: bool, **future_kwargs) -> None:
        self.audit.append(
            AuditEvent(
                operation='os_access',
                allowed=False,
                detail='Filesystem, environment and OS access denied',
            )
        )
        raise PermissionError('No OS capabilities are granted')


def expected_analysis(scenario: Scenario) -> Analysis:
    """Independent host oracle using source measurements, never the script output.

    This intentionally narrow policy makes the demo falsifiable. Real incident
    analysis needs broader hypotheses and request-level evidence.
    """
    baseline, observed = record('baseline'), record(scenario)
    first, queue, prefill = (observed[k] for k in ('first_content_s', 'queue_s', 'prefill_s'))
    complete = observed['engine_spans'] == observed['requests'] and all(
        value is not None for value in (first, queue, prefill)
    )
    if not complete:
        finding = 'insufficient_evidence'
    elif first <= baseline['first_content_s'] * 2:
        finding = 'within_baseline'
    elif queue >= 0.5 and queue > prefill * 2:
        finding = 'queue_pressure'
    elif prefill >= 0.5 and prefill > queue * 2:
        finding = 'prefill_pressure'
    else:
        finding = 'insufficient_evidence'
    return Analysis(
        scenario=scenario,
        finding=finding,
        requests=observed['requests'],
        baseline_first_content_s=baseline['first_content_s'],
        observed_first_content_s=first,
        queue_s=queue,
        prefill_s=prefill,
        slowdown=first / baseline['first_content_s'] if first is not None else None,
        evidence_refs=[baseline['ref'], observed['ref']],
    )


def verify_analysis(raw: object, access: EvidenceAccess) -> Analysis:
    result = Analysis.model_validate(raw)
    if any(not event.allowed for event in access.audit):
        raise ValueError('A denied operation invalidates this run, even if the script catches it')
    if access.reads != {'baseline', access.scenario}:
        raise ValueError('The script must read both authorized evidence records')
    expected = expected_analysis(access.scenario).model_dump()
    for key, actual in result.model_dump().items():
        target = expected[key]
        if type(target) is float and type(actual) in (float, int):
            same = math.isclose(actual, target, rel_tol=1e-6, abs_tol=1e-9)
        else:
            same = actual == target
        if not same:
            raise ValueError(f'{key} does not match the source evidence and diagnostic policy')
    return result
