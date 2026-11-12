"""Capability registry: adapters declare what they can do, packs declare what they need.

The runner only executes a pack when every required capability is declared by the
adapter. Anything else is recorded as ``unsupported``, never as a pass or a fail.
This keeps an in-process interpreter (Monty) and full container or VM sandboxes in
one arena without forcing either into the other's shape.
"""

from dataclasses import dataclass

# Interpreter tier. Names match the existing scenario packs so their digests stay stable.
INTERPRETER = {
    'python-subset': 'Run a Python-subset snippet inside an interpreter sandbox',
    'host-callbacks': 'Expose host functions to guest code through a mediated callback',
    'os-policy': 'Route guest filesystem, environment and clock access through a host handler',
    'resource-limits': 'Enforce allocator, recursion, output and execution-time budgets',
    'fresh-sessions': 'Start every probe in a fresh interpreter session',
}

# Container and VM tier (v1 set from the build plan).
VM = {
    'exec.shell': 'Run a command and return exit code, stdout and stderr',
    'fs.read_write': 'Upload and download files',
    'net.egress_policy': 'Choose open, deny-all or an allowlist before the sandbox starts',
    'lifecycle.pause_resume': 'Pause and resume with memory state',
    'lifecycle.snapshot': 'Snapshot and restore the filesystem',
    'multi.sandbox': 'Run two sandboxes in one probe',
    'limits.cpu_mem': 'Set CPU, memory and process caps',
}

REGISTRY = {**INTERPRETER, **VM}


@dataclass(frozen=True)
class Match:
    supported: bool
    missing: tuple[str, ...]
    unknown: tuple[str, ...]


def match(declared: frozenset[str] | set[str], required: tuple[str, ...] | list[str]) -> Match:
    """Compare an adapter's declared capabilities with a pack's requirements.

    Unknown capability names never match. A typo in a pack must surface as
    unsupported rather than silently running a probe the adapter cannot honour.
    """
    unknown = tuple(name for name in required if name not in REGISTRY)
    missing = tuple(name for name in required if name not in declared or name in unknown)
    return Match(supported=not missing, missing=missing, unknown=unknown)


def validate_declared(declared: frozenset[str]) -> None:
    unknown = sorted(name for name in declared if name not in REGISTRY)
    if unknown:
        raise ValueError(f'Adapter declares unregistered capabilities: {", ".join(unknown)}')
