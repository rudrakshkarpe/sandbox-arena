"""The contract between generated analysis, trusted validation, and the UI."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Scenario = Literal['queue-pressure', 'long-context', 'recovery', 'client-early-close']
Finding = Literal['queue_pressure', 'prefill_pressure', 'within_baseline', 'insufficient_evidence']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Analysis(StrictModel):
    scenario: Scenario
    finding: Finding
    requests: int = Field(ge=0)
    baseline_first_content_s: float = Field(gt=0)
    observed_first_content_s: float | None = Field(ge=0)
    queue_s: float | None = Field(ge=0)
    prefill_s: float | None = Field(ge=0)
    slowdown: float | None = Field(ge=0)
    evidence_refs: list[str] = Field(min_length=2, max_length=2)


class AuditEvent(StrictModel):
    operation: str
    allowed: bool
    detail: str


class Execution(StrictModel):
    status: Literal['verified', 'rejected', 'limited', 'error']
    code: str
    code_sha256: str
    elapsed_ms: float
    analysis: Analysis | None = None
    error_type: str | None = None
    message: str
    audit: list[AuditEvent] = Field(default_factory=list)
    trace_id: str


class CodeProposal(BaseModel):
    code: str = Field(min_length=1, max_length=12_000)


class RunRequest(StrictModel):
    scenario: Scenario = 'queue-pressure'
    challenge: Literal[
        'analysis',
        'file-access',
        'cross-scope',
        'timeout',
        'memory',
        'fabricated-result',
        'caught-denial',
        'host-call-budget',
    ] = 'analysis'
    code: str | None = Field(default=None, min_length=1, max_length=12_000)


class RunResult(StrictModel):
    run_id: str
    mode: Literal['scripted', 'custom', 'live']
    scenario: Scenario
    attempts: list[Execution]
    model: str | None = None
    model_requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    caveat: str = (
        'Historical scenario p95s are separate aggregates, not additive components of one request. '
        'Findings are diagnostic signals, not proof of causality. No inference was rerun.'
    )
