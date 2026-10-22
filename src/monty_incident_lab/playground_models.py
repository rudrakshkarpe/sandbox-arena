"""Public execution contract shared by the UI, API and future adapters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .benchmarks import WORKLOADS


class RunSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['playground', 'benchmark'] = 'playground'
    provider: Literal['monty'] = 'monty'
    code: str = Field(default='', max_length=12_000)
    benchmark_ids: list[str] = Field(default_factory=list, max_length=5)
    iterations: int = Field(default=10, ge=1, le=50)
    warmups: int = Field(default=1, ge=0, le=5)
    timeout_ms: int = Field(default=250, ge=50, le=500)
    memory_mb: int = Field(default=16, ge=4, le=32)
    allow_fixture: bool = True

    @model_validator(mode='after')
    def valid_work(self):
        if self.mode == 'playground' and not self.code.strip():
            raise ValueError('Provide code to execute')
        if self.mode == 'benchmark':
            if not self.benchmark_ids or any(key not in WORKLOADS for key in self.benchmark_ids):
                raise ValueError('Select at least one known benchmark')
            if len(set(self.benchmark_ids)) != len(self.benchmark_ids):
                raise ValueError('Benchmark IDs must be unique')
            if self.code:
                raise ValueError('Benchmark runs use versioned workload code')
        return self


class Sample(BaseModel):
    workload_id: str
    iteration: int
    warmup: bool
    status: Literal['ok', 'error', 'limited', 'denied']
    verdict: Literal['pass', 'fail', 'unverified']
    result: object = None
    result_truncated: bool = False
    stdout: str = ''
    error: str | None = None
    setup_ms: float
    execution_ms: float
    cleanup_ms: float
    total_ms: float
    code_sha256: str
    audit: list[dict] = Field(default_factory=list)
