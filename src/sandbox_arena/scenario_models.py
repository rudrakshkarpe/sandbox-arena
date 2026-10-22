"""Versioned contracts for bounded, application-owned scenario packs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class Expectation(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: Literal['ok', 'error', 'limited', 'denied']
    check_result: bool = False
    result: JsonValue = None
    error_prefix: str | None = Field(default=None, min_length=1, max_length=200)
    denied_min: int = Field(default=0, ge=0, le=32)
    allowed_exact: int | None = Field(default=None, ge=0, le=32)
    stdout_prefix: str | None = Field(default=None, max_length=4096)
    stdout_max_bytes: int | None = Field(default=None, ge=0, le=4096)
    truncated: bool | None = None

    @model_validator(mode='after')
    def has_evidence(self):
        if self.status == 'denied' and not self.denied_min:
            raise ValueError('A denial expectation requires host audit evidence')
        if self.status in {'error', 'limited'} and not self.error_prefix:
            raise ValueError('Error expectations require a specific error prefix')
        if self.status == 'ok' and not any(
            [self.check_result, self.stdout_prefix is not None, self.truncated is not None]
        ):
            raise ValueError('Successful probes require an observable assertion')
        return self


class Probe(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    role: Literal['control', 'challenge'] = 'challenge'
    code: str = Field(min_length=1, max_length=12_000)
    expect: Expectation


class ScenarioPack(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal['1.0'] = '1.0'
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    version: str = Field(pattern=r'^\d+\.\d+\.\d+$')
    title: str = Field(min_length=1, max_length=100)
    category: Literal['Filesystem', 'Host policy', 'Resources', 'Isolation', 'Evidence']
    objective: str = Field(min_length=1, max_length=500)
    boundary: str = Field(min_length=1, max_length=100)
    limitation: str = Field(min_length=1, max_length=1000)
    requires: tuple[str, ...] = ('python-subset',)
    allow_fixture: bool = False
    timeout_ms: int = Field(default=250, ge=50, le=500)
    memory_mb: int = Field(default=16, ge=4, le=32)
    probes: tuple[Probe, ...] = Field(min_length=2, max_length=4)

    @model_validator(mode='after')
    def controls_and_ids(self):
        if len({probe.id for probe in self.probes}) != len(self.probes):
            raise ValueError('Probe IDs must be unique')
        if not any(probe.role == 'control' for probe in self.probes):
            raise ValueError('A scenario requires a positive control')
        if not any(probe.role == 'challenge' for probe in self.probes):
            raise ValueError('A scenario requires a challenge')
        return self
