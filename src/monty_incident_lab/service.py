import uuid

import logfire
from pydantic_monty import Monty

from .models import RunRequest, RunResult
from .programs import PROGRAMS
from .sandbox import execute


def run(pool: Monty, request: RunRequest) -> RunResult:
    run_id = uuid.uuid4().hex
    with logfire.span('investigation.run', run_id=run_id, scenario=request.scenario):
        result = execute(pool, request.code or PROGRAMS[request.challenge], request.scenario)
    return RunResult(
        run_id=run_id,
        mode='custom' if request.code else 'scripted',
        scenario=request.scenario,
        attempts=[result],
    )
