# Contributing to Sandbox Lab

Start with a reproducible workload, a clear expected result, or a minimal failure
case. Read `AGENTS.md`, `docs/playground-architecture.md`, and the provenance in
`THIRD_PARTY_NOTICES.md` before changing execution or benchmark code.

## Add a workload

1. Add a Workload to `src/monty_incident_lab/benchmarks/__init__.py`. For larger
   programs, use a `.py.txt` payload in the same directory. These are guest programs,
   not Python modules to import or execute on the host.
2. Give it a stable ID, version, category, description, required capabilities,
   expected outcome, and an independently computed expected result where applicable.
3. Include pinned upstream links, licensing, and adaptation details for reused code.
4. Add failure checks when a correct-looking return value could hide a policy denial.
5. Run the suite with multiple budgets and inspect exported raw evidence.

The parameterized benchmark contract test automatically covers registered
workloads, but it does not replace testing the oracle itself when it is complex.
Never use a model to grade arithmetic or deterministic sandbox boundary results.

## Add a provider

Provider support is experimental infrastructure work, not just a logo change.
Implement the Provider execution contract; add configuration, a registry entry,
capability matching, and environment metadata. Prove cleanup on success, timeout,
cancellation and transport failure. Keep provider credentials out of guest inputs,
logs and exports. Provide an opt-in smoke test with a clear cost ceiling.

Do not compare remote provisioning with warm local session checkout under the
same metric name. Record where measurements are taken and what they include.

## Validation and review

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run monty-lab evaluate
```

For UI changes, verify execution, denials, benchmark results, history, export,
keyboard controls and narrow layouts in a browser. Avoid external fonts, scripts,
or assets so the local workbench remains usable offline after installation.

Use small coherent commits, descriptive branch names, and normal follow-up commits
on published PRs. Include what changed, why, validation evidence, and known limits.
Do not claim partner endorsement, security certification, or unmeasured speedups.

Contributions to application code are MIT licensed. Apache-2.0 derived workload
files retain that license and their attribution notices.
