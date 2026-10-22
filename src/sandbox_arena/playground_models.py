"""Public execution contract shared by the UI, API and future adapters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .benchmarks import WORKLOADS
from .scenario_catalog import PACKS


class RunSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['playground', 'benchmark', 'scenario'] = 'playground'
    scenario_id: str | None = None
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
        if self.mode == 'scenario':
            pack = PACKS.get(self.scenario_id)
            if pack is None:
                raise ValueError('Select a known scenario pack')
            if self.code or self.benchmark_ids or self.iterations > 10:
                raise ValueError('Scenario runs use catalog code and at most 10 repetitions')
            for field, value in {
                'warmups': 0,
                'allow_fixture': pack.allow_fixture,
                'timeout_ms': pack.timeout_ms,
                'memory_mb': pack.memory_mb,
            }.items():
                if field in self.model_fields_set and getattr(self, field) != value:
                    raise ValueError(f'Scenario policy fixes {field} to {value}')
                setattr(self, field, value)
        elif self.scenario_id is not None:
            raise ValueError('scenario_id requires scenario mode')
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
