# Monty Incident Lab

Bounded Python execution over a pinned public inference capture, with host authorization, source verification and connected OpenTelemetry spans.

```bash
uv sync --locked
uv run pytest tests/test_execution.py
```

The measurements come from [Logfire Inference Lab](https://github.com/rudrakshkarpe/logfire-inference-lab). The authored programs run in Monty; they do not rerun GPU inference.
