# Working on Sandbox Arena

- Keep the demo runnable without credentials or a GPU.
- Execute analysis in Monty. Never substitute host Python `exec` or `eval`.
- Distinguish recorded inference measurements, authored scripts, live model calls,
  and current sandbox timings in both the UI and exported evidence.
- Never imply that aggregate percentiles establish request-level causality.
- Validate host callback arguments, bound results, and discard each sandbox session.
- Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
- Use small logical commits. Preserve published history. No em dashes in prose.
- Do not publish traces or call a paid model without explicit user configuration.
