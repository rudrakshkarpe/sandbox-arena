"""Runtime adapters behind one capability-based contract."""

from .base import (
    CleanupReport,
    Command,
    EgressPolicy,
    ExecResult,
    FileSandbox,
    Handle,
    SandboxAdapter,
    SandboxSpec,
    ShellSandbox,
)

__all__ = [
    'CleanupReport',
    'Command',
    'EgressPolicy',
    'ExecResult',
    'FileSandbox',
    'Handle',
    'SandboxAdapter',
    'SandboxSpec',
    'ShellSandbox',
]
