# Validation record

The committed [acceptance report](evidence/evaluation.json) was generated on October 22, 2026 from code revision `64f065f3cc07193857dc70a8c42293d780810dc5`. Later documentation commits do not change that executed code. The report records the exact Python, package and platform versions.

## Observed results

- All 12 scripted acceptance cases passed their status, finding and trace assertions.
- The 30-test Python suite passed, including strict output validation, source verification, session isolation, native trace parentage, web request boundaries, and Pydantic AI generation/repair with FunctionModel.
- Ruff lint and formatting checks passed using the locked version.
- The package built as an sdist and wheel, including the capture and UI assets. The wheel was installed against the locked runtime dependencies and successfully ran a recovery investigation from outside the source directory.
- Browser checks exercised a verified analysis, caught denial, native trace inspection and all acceptance cases. Desktop and narrow layouts had no page-level horizontal overflow.

| Recorded case | Result | Monty execution and verification, this run |
| --- | --- | --- |
| Queue pressure | Verified queue-pressure signal | 8.085 ms |
| Long context | Verified prefill-pressure signal | 1.459 ms |
| Recovery | Verified within-baseline result | 1.294 ms |
| Early close | Verified insufficient-evidence result | 1.554 ms |
| Infinite loop | TimeoutError; session discarded | 251.134 ms |
| Oversized allocation | MemoryError; session discarded | 0.759 ms |
| Recovery after failures | Verified within-baseline result | 1.454 ms |

These are single-run instrumented application timings on one laptop, not Monty throughput or startup benchmarks. They exclude initial pool creation. The first case can include lazy initialization and instrumentation overhead. They are unrelated to the historical H100 inference durations displayed by the analysis.

The capture checksum is `cf04b26477923b1d7b84ad90533a55167257db07e6526a44b44b27ce2b24a0fd`. The unchanged source fixture is protected by a regression assertion.

## Native tracing was checked, not assumed

The initial local trace check failed because an inherited `RUST_LOG=warn` filter hid native Monty spans. Application spans still appeared. The demo now appends the process-local `monty_pool=info` directive before instrumentation, and tests verify this structure:

```text
investigation.run
  sandbox.execute
    session {script_name}       native Monty
      run code                  native Monty
        call {function_name}    native Monty
          evidence.read         trusted host callback
        call {function_name}
          evidence.read
    analysis.verify
```

The [trace projection](evidence/trace-summary.json) contains 135 completed spans from the acceptance evaluation, preserving actual names, IDs, parent IDs and timestamps. Pydantic Evals places its cases in the same evaluation trace. Host resource identifiers, raw span attributes and local source paths were intentionally omitted from this public projection.

The two JPEGs in this directory are screenshots of the running local application. They are not mockups or hosted Logfire screenshots. Their individual browser executions have different trace IDs from the CLI evaluation.

## What was not tested

- No paid live model was called. FunctionModel tests demonstrate integration and repair behavior, not model quality. Run the optional live evaluation with an approved provider and model before claiming generation accuracy or cost.
- No traces from this Monty lab were sent to hosted Logfire. Local spans and parent relationships are verified; hosted ingestion, dashboard queries, retention and access controls are not.
- No GPU inference was rerun. Inputs are the original published capture, with its original limitations.
- No multi-tenant deployment, load test, broad adversarial corpus or OS sandbox assessment was performed.

## Reproduce

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run sandbox-arena --traces artifacts/traces.jsonl evaluate --output artifacts/evaluation.json
uv build
```

Use a fresh output path for independent trace captures. JSONL is append-only; IDs and timings will differ between runs. Evaluation returns a nonzero exit status if a case fails or is missing. Failed task names and trace IDs remain in the report. Live usage totals cover completed workflows only; failed provider requests may be absent.

If hosted export is enabled, confirm the exact run's trace in the destination before asserting successful ingestion. A successful local exporter or HTTP send alone is insufficient evidence of a complete hosted trace.
