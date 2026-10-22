from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from monty_incident_lab.agent import run_live
from monty_incident_lab.programs import ANALYSIS


def model_with_codes(codes):
    iterator = iter(codes)

    def generate(messages, info):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {'code': next(iterator)})])

    return FunctionModel(generate)


def test_agent_generated_program_executes(pool):
    result = run_live(pool, 'long-context', model_with_codes([ANALYSIS]))
    assert result.attempts[-1].analysis.finding == 'prefill_pressure'
    assert result.model_requests == 1


def test_agent_repairs_invalid_output(pool):
    result = run_live(pool, 'recovery', model_with_codes(['{}', ANALYSIS]))
    assert [attempt.status for attempt in result.attempts] == ['rejected', 'verified']
    assert result.model_requests == 2


def test_agent_does_not_retry_denied_capability(pool):
    result = run_live(pool, 'recovery', model_with_codes(['open("/etc/hosts").read()']))
    assert result.attempts[-1].status == 'rejected'
    assert result.model_requests == 1


def test_model_evaluation_reports_requests_and_mode(tmp_path):
    import json

    from monty_incident_lab.evaluation import evaluate

    path = tmp_path / 'evaluation.json'
    assert evaluate(path, model=model_with_codes([ANALYSIS] * 4))
    evidence = json.loads(path.read_text())
    assert evidence['mode'] == 'test-model'
    assert evidence['live_model_evaluated'] is False
    assert evidence['model_requests'] == 4
    assert evidence['first_attempt_verified'] == 4
