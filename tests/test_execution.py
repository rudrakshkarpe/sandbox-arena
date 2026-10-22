import json

import pytest

from sandbox_arena.cases import CASES
from sandbox_arena.evidence import CAPTURE_SHA256, EvidenceAccess, expected_analysis, verify_analysis
from sandbox_arena.models import RunRequest
from sandbox_arena.programs import ANALYSIS
from sandbox_arena.sandbox import execute
from sandbox_arena.service import run


@pytest.mark.parametrize('name,scenario,challenge,status,finding', CASES)
def test_acceptance(pool, name, scenario, challenge, status, finding):
    result = run(pool, RunRequest(scenario=scenario, challenge=challenge)).attempts[-1]
    assert result.status == status, result
    assert (result.analysis.finding if result.analysis else None) == finding
    assert result.trace_id != '0' * 32


def test_actual_source_numbers(pool):
    result = execute(pool, ANALYSIS, 'queue-pressure').analysis
    assert result is not None
    assert result.requests == 32
    assert result.queue_s == pytest.approx(25.378792993724346)
    assert result.observed_first_content_s == pytest.approx(25.681393457998638)
    assert result.slowdown == pytest.approx(91.0037052)
    assert CAPTURE_SHA256 == 'cf04b26477923b1d7b84ad90533a55167257db07e6526a44b44b27ce2b24a0fd'


def test_no_data_read_means_no_verified_result():
    with pytest.raises(ValueError, match='must read'):
        verify_analysis(expected_analysis('recovery').model_dump(), EvidenceAccess('recovery'))


@pytest.mark.parametrize('replacement', ['float("nan")', 'float("inf")', 'True', '-3'])
def test_bad_numeric_output(pool, replacement):
    code = ANALYSIS.replace('"requests": observed["requests"]', f'"requests": {replacement}')
    assert execute(pool, code, 'recovery').status == 'rejected'


def test_session_state_does_not_leak(pool):
    execute(pool, 'secret_marker = 123\n{}', 'recovery')
    result = execute(pool, 'secret_marker', 'recovery')
    assert result.error_type == 'NameError'
    assert execute(pool, ANALYSIS, 'recovery').status == 'verified'


def test_environment_not_exposed(pool, monkeypatch):
    monkeypatch.setenv('MONTY_LAB_SECRET', 'must-not-leak-123')
    result = execute(pool, 'import os\nos.getenv("MONTY_LAB_SECRET")', 'recovery')
    assert result.status == 'rejected'
    assert 'must-not-leak-123' not in result.model_dump_json()


def test_unknown_capabilities_and_imports(pool):
    for code in ['send_email("hello")', 'import socket', 'import subprocess']:
        result = execute(pool, code, 'recovery')
        assert result.status == 'error'
        assert result.analysis is None


def test_fresh_session_after_limits(pool):
    for code in ['while True:\n    pass', '"x" * 100_000_000']:
        assert execute(pool, code, 'recovery').status == 'limited'
        assert execute(pool, ANALYSIS, 'recovery').status == 'verified'


def test_print_budget(pool):
    assert execute(pool, 'print("x" * 20_000)', 'recovery').status == 'limited'


def test_traces_share_parent_context(pool, telemetry):
    execution = run(pool, RunRequest()).attempts[-1]
    spans = [json.loads(line) for line in telemetry.read_text().splitlines()]
    spans = [span for span in spans if span['context']['trace_id'].removeprefix('0x') == execution.trace_id]
    names = [span['name'] for span in spans]
    assert 'investigation.run' in names
    assert 'sandbox.execute' in names
    assert 'evidence.read' in names
    assert 'analysis.verify' in names
    # Verify native worker instrumentation as well as application spans.
    assert 'session {script_name}' in names, names
    assert 'run code' in names
    assert names.count('call {function_name}') == 2
    ids = {span['context']['span_id'] for span in spans}
    assert all(span['parent_id'] in ids for span in spans if span['parent_id'] is not None)
    by_name = {span['name']: span for span in spans}
    assert by_name['session {script_name}']['parent_id'] == by_name['sandbox.execute']['context']['span_id']
    assert by_name['run code']['parent_id'] == by_name['session {script_name}']['context']['span_id']
    calls = {span['context']['span_id'] for span in spans if span['name'] == 'call {function_name}'}
    assert all(span['parent_id'] in calls for span in spans if span['name'] == 'evidence.read')
