"""Deterministic acceptance cases, not an LLM quality benchmark."""

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from .agent import run_live
from .cases import CASES
from .evidence import CAPTURE_SHA256, SOURCE_URL
from .models import RunRequest, RunResult
from .sandbox import LIMITS, make_pool
from .service import run


class MeetsContract(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        attempt = ctx.output.attempts[-1]
        actual_finding = attempt.analysis.finding if attempt.analysis else None
        return {
            'expected_status': attempt.status == ctx.metadata['status'],
            'expected_finding': actual_finding == ctx.metadata['finding'],
            'has_trace': attempt.trace_id != '0' * 32,
        }


def evaluate(output: Path, *, model=None) -> bool:
    cases = CASES[:4] if model is not None else CASES
    dataset = Dataset(
        name='monty-incident-acceptance',
        cases=[
            Case(
                name=name,
                inputs=RunRequest(scenario=scenario, challenge=challenge),
                metadata={'status': status, 'finding': finding},
            )
            for name, scenario, challenge, status, finding in cases
        ],
        evaluators=[MeetsContract()],
    )
    runs: list[RunResult] = []
    with make_pool() as pool:

        def investigate(request):
            result = run_live(pool, request.scenario, model) if model is not None else run(pool, request)
            runs.append(result)
            return result

        report = dataset.evaluate_sync(investigate, max_concurrency=1, progress=False)
    report.print(include_input=False, include_output=False)
    checks = [
        {'name': case.name, 'assertions': {key: value.value for key, value in case.assertions.items()}}
        for case in report.cases
    ]
    passed = len(checks) == len(cases) and all(
        len(case['assertions']) == 3 and all(case['assertions'].values()) for case in checks
    )
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], text=True, capture_output=True).stdout.strip()
    document = {
        'generated_at': datetime.now(UTC).isoformat(),
        'mode': 'live' if isinstance(model, str) else 'test-model' if model is not None else 'scripted',
        'description': 'Monty execution and source verification over historical inference aggregates.',
        'live_model_evaluated': isinstance(model, str),
        'model': model if isinstance(model, str) else None,
        'first_attempt_verified': sum(run.attempts[0].status == 'verified' for run in runs),
        'model_requests': sum(run.model_requests for run in runs),
        'input_tokens': sum(run.input_tokens for run in runs),
        'output_tokens': sum(run.output_tokens for run in runs),
        'usage_scope': 'Completed workflows only; failed provider requests may be absent.',
        'hosted_logfire_verified': False,
        'platform': platform.platform(),
        'python': platform.python_version(),
        'git_revision': revision,
        'versions': {
            name: version(name)
            for name in (
                'pydantic-monty',
                'pydantic',
                'pydantic-ai-slim',
                'pydantic-evals',
                'logfire',
            )
        },
        'source': SOURCE_URL,
        'capture_sha256': CAPTURE_SHA256,
        'limits': LIMITS,
        'all_passed': passed,
        'cases': checks,
        'failed_cases': [{'name': case.name, 'trace_id': case.trace_id} for case in report.failures],
        'runs': [item.model_dump() for item in runs],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + '\n')
    print(f'Evidence: {output} (sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})')
    return passed
