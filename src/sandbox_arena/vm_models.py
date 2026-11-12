"""Versioned contracts for container/VM-tier scenario packs.

These packs keep the interpreter-tier contract (a positive control, a bounded
challenge, a host-side verdict and a stated limitation) but run shell commands in
a real sandbox and judge them from host-side observers such as the canary log.

Each assertion declares its evidence class up front so a report always shows how
much of a verdict rests on what code inside the sandbox said about itself.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from .capabilities import REGISTRY

EvidenceClass = Literal['host_observed', 'probe_reported']

# Which evidence class each assertion kind produces. Not configurable per pack.
ASSERTION_EVIDENCE: dict[str, EvidenceClass] = {
    'exit_code': 'host_observed',
    'canary_http_hits': 'host_observed',
    'canary_dns_hits': 'host_observed',
    'stdout_field': 'probe_reported',
    'stdout_contains': 'probe_reported',
    'host_secrets_absent': 'probe_reported',
}


class Assertion(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    check: Literal[
        'exit_code', 'canary_http_hits', 'canary_dns_hits', 'stdout_field', 'stdout_contains', 'host_secrets_absent'
    ]
    equals: JsonValue = None
    field: str | None = Field(default=None, pattern=r'^[a-z_]{1,40}$')
    value: str | None = Field(default=None, max_length=200)

    @model_validator(mode='after')
    def shape(self):
        if self.check == 'stdout_field' and self.field is None:
            raise ValueError('stdout_field needs a field name')
        if self.check == 'stdout_contains' and not self.value:
            raise ValueError('stdout_contains needs a value')
        if self.check in {'exit_code', 'canary_http_hits', 'canary_dns_hits'} and not isinstance(self.equals, int):
            raise ValueError(f'{self.check} needs an integer "equals"')
        return self

    @property
    def evidence(self) -> EvidenceClass:
        return ASSERTION_EVIDENCE[self.check]


class VmProbe(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    role: Literal['control', 'challenge']
    argv: tuple[str, ...] = Field(min_length=1, max_length=8)
    timeout_s: float = Field(default=20, gt=0, le=120)
    expect: tuple[Assertion, ...] = Field(min_length=1, max_length=6)

    @model_validator(mode='after')
    def challenge_has_host_evidence_when_possible(self):
        if self.role == 'challenge' and not any(item.check != 'exit_code' for item in self.expect):
            raise ValueError('A challenge needs an observation beyond its exit code')
        return self


class VmPack(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal['1.0'] = '1.0'
    tier: Literal['vm'] = 'vm'
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    version: str = Field(pattern=r'^\d+\.\d+\.\d+$')
    title: str = Field(min_length=1, max_length=100)
    layer: Literal['network', 'secrets', 'lifecycle', 'resources', 'isolation', 'after-the-sandbox']
    objective: str = Field(min_length=1, max_length=500)
    boundary: str = Field(min_length=1, max_length=100)
    limitation: str = Field(min_length=1, max_length=1000)
    requires: tuple[str, ...] = Field(min_length=1)
    profiles: tuple[Literal['default', 'strict'], ...] = ('default', 'strict')
    probes: tuple[VmProbe, ...] = Field(min_length=2, max_length=4)

    @model_validator(mode='after')
    def contract(self):
        unknown = [name for name in self.requires if name not in REGISTRY]
        if unknown:
            raise ValueError(f'Unregistered capabilities: {unknown}')
        if len({probe.id for probe in self.probes}) != len(self.probes):
            raise ValueError('Probe IDs must be unique')
        if not any(probe.role == 'control' for probe in self.probes):
            raise ValueError('A scenario requires a positive control')
        if not any(probe.role == 'challenge' for probe in self.probes):
            raise ValueError('A scenario requires a challenge')
        return self
