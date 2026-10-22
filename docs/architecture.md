# Design decisions and learning path

## Follow one investigation

1. `service.py` opens the investigation span and chooses an authored script or the submitted code. Live CLI runs instead use `agent.py` to generate a typed code proposal with Pydantic AI.
2. `sandbox.py` checks out a fresh Monty session. It supplies only the selected scenario and one host callback. The script runs in a Monty worker subprocess.
3. Calling `read_evidence` suspends execution. `evidence.py` validates authority on the host and returns one bounded record. The host owns this decision even when the script changes or catches an exception.
4. The sandbox returns a Python value across the worker protocol. `models.py` defines its strict shape. `verify_analysis` then checks reads, denials, provenance references, measurements, arithmetic, and the diagnostic rule.
5. The result is either verified or an explicit failure. The checkout ends in every case. No action changes infrastructure.
6. Logfire's application spans and native Monty instrumentation share the active trace. `telemetry.py` exports the actual spans locally, with an opt-in hosted exporter.

## Why a fixed diagnostic policy?

It provides an oracle independent of the generated program. If both the program and an LLM judge invent the same plausible diagnosis, an evaluation can appear successful while being wrong. Here, source values and arithmetic are mechanically checkable.

The tradeoff is narrowness. The validator intentionally rejects novel hypotheses, even if they are plausible. This proves the execution and verification path for an agreed contract; it does not demonstrate general root-cause analysis. Broader diagnosis should use a larger evidence model, independent labels, and explicit uncertainty.

## Policy, in order

1. Missing first-content, queue, prefill or complete engine coverage means insufficient evidence.
2. First-content p95 at most twice baseline is within the baseline policy.
3. Queue p95 at least 0.5 seconds and greater than twice prefill is a queue-pressure signal.
4. Prefill p95 at least 0.5 seconds and greater than twice queue is a prefill-pressure signal.
5. Otherwise, insufficient evidence.

These are demonstration thresholds, not universal SLOs. Slowdown is the ratio of observed and baseline first-content p95. It is not a per-request slowdown distribution. Never add the timing percentiles.

## Why no direct database connection?

A general SQL or HTTP tool would move most of the security problem into a large host capability. A narrow read function is easier to authorize, test, limit, and explain. The next connector should preserve that interface, retrieve only approved fields, and enforce identity at the host boundary.

## Why no automatic remediation?

An aggregate latency signal is not sufficient evidence to scale a cluster, modify a queue limit, or change a customer's model. This demo stops at a verified analysis and a human investigation step. Read access and write authority should be separate evaluation decisions.

## Learn by changing the system

1. Change the request count in a returned result and observe schema versus evidence validation.
2. Catch an access exception inside Monty. Explain why the host still rejects the result.
3. Add a scenario with mixed queue and prefill signals. Define the expected outcome before changing the program.
4. Replace the fixture callback with a bounded test HTTP service, then add its deadline and error cases.
5. Inspect a trace tree. Find which spans are application spans and which came from Monty's own instrumentation.
6. Run live code generation on a held-out question set. Record first-pass success, repairs, unsupported outputs, token usage, total latency and provider/model revision.

Use the [Monty host-function docs](https://github.com/pydantic/monty/blob/main/docs/host-functions.md), [resource limits](https://github.com/pydantic/monty/blob/main/docs/resource-limits.md), [Pydantic AI testing guide](https://ai.pydantic.dev/testing/), and [Pydantic Evals](https://ai.pydantic.dev/evals/) as primary references. The lockfile determines this lab's tested versions; current upstream docs may describe newer features.
