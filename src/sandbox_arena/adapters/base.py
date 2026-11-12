"""Adapter contract shared by every runtime.

An adapter wraps one sandbox product. It declares capabilities (see
``sandbox_arena.capabilities``) and implements only the methods those capabilities
need. Verdicts never come from an adapter's own claims: the runner judges probes
from host-side observations (exit codes, canary logs, cleanup checks) and labels
anything that came from inside the sandbox as ``probe_reported``.
"""

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

OUTPUT_LIMIT = 65_536


class EgressPolicy(BaseModel):
    """Outbound network policy requested before the sandbox starts."""

    model_config = ConfigDict(extra='forbid', frozen=True)
    mode: Literal['open', 'deny_all', 'allowlist'] = 'open'
    allow: tuple[str, ...] = ()


class SandboxSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    image: str | None = None
    cpus: float = Field(default=1.0, gt=0, le=8)
    memory_mb: int = Field(default=512, ge=64, le=16_384)
    pids_limit: int = Field(default=256, ge=16, le=65_536)
    timeout_s: int = Field(default=120, ge=5, le=3600)
    egress: EgressPolicy = EgressPolicy()
    env: dict[str, str] = Field(default_factory=dict)
    # True requests the adapter's strictest documented configuration.
    hardened: bool = False


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    argv: tuple[str, ...] = Field(min_length=1)
    timeout_s: float = Field(default=20, gt=0, le=300)


class ExecResult(BaseModel):
    exit_code: int | None
    stdout: str = ''
    stderr: str = ''
    timed_out: bool = False
    duration_ms: float = 0.0


class Handle(BaseModel):
    adapter: str
    id: str
    detail: dict[str, str] = Field(default_factory=dict)


class CleanupReport(BaseModel):
    """Destroy must confirm the resource is gone, not just that a call returned."""

    confirmed: bool
    removed: list[str] = Field(default_factory=list)
    leftovers: list[str] = Field(default_factory=list)


@runtime_checkable
class SandboxAdapter(Protocol):
    name: str
    capabilities: frozenset[str]

    def version(self) -> str: ...

    def create(self, spec: SandboxSpec) -> Handle: ...

    def destroy(self, handle: Handle) -> CleanupReport: ...


@runtime_checkable
class ShellSandbox(SandboxAdapter, Protocol):
    """Required by the ``exec.shell`` capability."""

    def exec(self, handle: Handle, command: Command) -> ExecResult: ...


@runtime_checkable
class FileSandbox(SandboxAdapter, Protocol):
    """Required by the ``fs.read_write`` capability."""

    def put_file(self, handle: Handle, path: str, data: bytes) -> None: ...

    def get_file(self, handle: Handle, path: str) -> bytes: ...


def bounded(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """Keep evidence bounded; sandbox output is untrusted and can be arbitrarily large."""
    return text if len(text) <= limit else text[:limit] + '... [truncated]'
