"""Optional live code generation. Scripted mode never contacts a model provider."""

import json
import uuid

import logfire
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_monty import Monty

from .models import Analysis, CodeProposal, RunResult, Scenario
from .sandbox import execute

INSTRUCTIONS = """Write a short Python analysis program to investigate recorded inference measurements.
The program executes in Monty, not CPython. Return code, not a diagnosis or Markdown.
The input variable `scenario` names the selected scenario.
The ONLY host capability is read_evidence(scope: str, scenario: str) -> dict.
Call it with scope="inference-lab" and scenario="baseline", then with the input scenario.
Each record has ref (str), requests (int), first_content_s, queue_s, prefill_s
(float or None), and engine_spans (int). These are separate scenario p95 aggregates.
No filesystem, network, subprocess, environment, or arbitrary imports are available.
Return the final dictionary as the last expression. No print needed.

Diagnostic policy, in this order:
1. If engine_spans != requests or first_content_s, queue_s or prefill_s is None:
   finding="insufficient_evidence".
2. If first_content_s <= baseline first_content_s * 2: finding="within_baseline".
3. If queue_s >= 0.5 and queue_s > prefill_s * 2: finding="queue_pressure".
4. If prefill_s >= 0.5 and prefill_s > queue_s * 2: finding="prefill_pressure".
5. Otherwise finding="insufficient_evidence".
slowdown = observed first_content_s / baseline first_content_s, or None if missing.
evidence_refs = [baseline ref, observed ref], preserving that order.
Copy all numeric measurements exactly. Do not invent numbers. Do not sum p95s.
Output must match this schema:
"""


def make_agent(model) -> Agent:
    return Agent(
        model,
        output_type=CodeProposal,
        instructions=INSTRUCTIONS + json.dumps(Analysis.model_json_schema()),
        retries=0,
        model_settings={'max_tokens': 1600, 'timeout': 30},
    )


def run_live(pool: Monty, scenario: Scenario, model, *, max_attempts: int = 2) -> RunResult:
    if max_attempts not in (1, 2):
        raise ValueError('Live runs allow one or two model requests')
    agent = make_agent(model)
    attempts, requests, input_tokens, output_tokens = [], 0, 0, 0
    history = None
    prompt = f'Analyze scenario {scenario!r} against baseline using the permitted evidence reads.'
    with logfire.span('investigation.live', scenario=scenario):
        for _ in range(max_attempts):
            generation = agent.run_sync(
                prompt,
                message_history=history,
                usage_limits=UsageLimits(request_limit=1, output_tokens_limit=1800),
            )
            usage = generation.usage
            requests += usage.requests
            input_tokens += usage.input_tokens
            output_tokens += usage.output_tokens
            attempt = execute(pool, generation.output.code, scenario)
            attempts.append(attempt)
            if attempt.status == 'verified':
                break
            # Retry only ordinary coding/validation errors. Do not retry denied access or resource abuse.
            if attempt.status == 'limited' or any(not event.allowed for event in attempt.audit):
                break
            history = generation.all_messages()
            prompt = f'The program failed validation: {attempt.message} Return a corrected program.'
    return RunResult(
        run_id=uuid.uuid4().hex,
        mode='live',
        scenario=scenario,
        attempts=attempts,
        model=model if isinstance(model, str) else 'test-function-model',
        model_requests=requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
