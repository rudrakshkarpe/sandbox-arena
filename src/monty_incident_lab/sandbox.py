"""Monty execution and independent verification, with fresh sessions per attempt."""

import hashlib
import time
from datetime import datetime

import logfire
from opentelemetry import trace
from pydantic import ValidationError
from pydantic_monty import CollectString, Monty, MontyCrashedError, MontyError, MontyRuntimeError

from .evidence import EvidenceAccess, verify_analysis
from .models import Execution, Scenario

LIMITS = {
    'max_memory': 16_000_000,
    'max_feed_duration_secs': 0.25,
    'max_turn_duration_secs': 0.25,
    'max_recursion_depth': 100,
    'max_suspensions': 24,
    'max_total_sleep_secs': 0.1,
}


def make_pool() -> Monty:
    return Monty(max_processes=2, request_timeout=2, checkout_timeout=3)


def execute(pool: Monty, code: str, scenario: Scenario) -> Execution:
    access = EvidenceAccess(scenario)
    started = time.perf_counter()
    digest = hashlib.sha256(code.encode()).hexdigest()
    result = None
    status, message, error_type = 'verified', 'Computed result matches the source evidence.', None
    with logfire.span('sandbox.execute', scenario=scenario, code_sha256=digest) as span:
        trace_id = f'{trace.get_current_span().get_span_context().trace_id:032x}'
        try:
            if len(code) > 12_000:
                raise ValueError('Code exceeds the 12,000 character limit')
            # Ending the checkout discards state on success, rejection and limit trips.
            with pool.checkout(
                limits=LIMITS,
                os_policy={'datetime': datetime(2026, 9, 27), 'sleep': 'call_host', 'random_start': {'seed': 0}},
            ) as session:
                raw = session.feed_run(
                    code,
                    inputs={'scenario': scenario},
                    external_lookup={'read_evidence': access.read_evidence},
                    os=access.deny_os,
                    print_callback=CollectString(max_bytes=4096),
                )
            with logfire.span('analysis.verify'):
                result = verify_analysis(raw, access)
        except (ValidationError, ValueError) as exc:
            status, error_type = 'rejected', type(exc).__name__
            # ValidationError can contain untrusted output. Do not echo that into traces.
            message = 'Output does not match the required schema.' if isinstance(exc, ValidationError) else str(exc)
        except MontyRuntimeError as exc:
            name = exc.display(format='type-msg').split(':', 1)[0]
            error_type = name
            if name in {'TimeoutError', 'MemoryError'}:
                status, message = 'limited', f'{name}: execution budget exceeded; session discarded.'
            elif any(not event.allowed for event in access.audit):
                status, message = 'rejected', 'Host policy denied the requested capability.'
            else:
                status, message = 'error', 'Sandbox code failed before producing a valid analysis.'
        except MontyCrashedError as exc:
            status, error_type = 'limited' if exc.timed_out else 'error', type(exc).__name__
            message = 'Worker stopped; this session was discarded.'
        except MontyError as exc:
            status, error_type, message = 'error', type(exc).__name__, 'Monty could not execute the supplied code.'
        span.set_attribute('outcome', status)
        span.set_attribute('audit_denials', sum(not event.allowed for event in access.audit))
    return Execution(
        status=status,
        code=code,
        code_sha256=digest,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
        analysis=result,
        error_type=error_type,
        message=message,
        audit=access.audit,
        trace_id=trace_id,
    )
