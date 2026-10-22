# Sandbox Arena

**Every sandbox has a boundary. Put it to the test.**

A local sandbox evaluation workbench, starting with Pydantic Monty. Enter through
controlled boundary scenarios or repeatable benchmarks, inspect the evidence, and
open the code workspace when you want to go deeper. The attack-lab foundation
includes 18 versioned packs, host evidence checks, portable reports and replay.

![Sandbox Arena homepage](docs/evidence/arena-home.jpg)

An independent project by Rudraksh Karpe, developed from
[Monty Incident Lab](https://github.com/rudrakshkarpe/monty-incident-lab).
This repository is not affiliated with the separately operated
[sandbox-arena.vercel.app](https://sandbox-arena.vercel.app/) comparison site.

## Run locally

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/). No GPU, Docker daemon,
model API key or Logfire account is needed.

```bash
git clone https://github.com/rudrakshkarpe/sandbox-arena.git
cd sandbox-arena
uv sync --locked
uv run sandbox-arena serve --port 8033
```

Open **http://127.0.0.1:8033**. The server binds only to loopback.
If macOS marks an editable-install `.pth` file hidden and Python cannot import the
package, use `uv run --no-editable sandbox-arena serve --port 8033` instead.

## Try the workbench

1. **Scenarios:** filter 18 packs across filesystem, host policy, resources,
   isolation and evidence handling. Run three repetitions of each pack with its
   fixed policy. Inspect the positive control and challenge separately, verify
   the report, and replay the exact configuration in fresh sessions.
2. **Code workspace:** run Hello, Monty or write your own Python. Adjust the execution
   and memory budgets. View output, setup/execution/cleanup timing, and the timeline.
3. **Permissions:** load Approved tool access, disable the fixture tool and run.
   Inspect the recorded denial in Policy audit. Re-enable it to read three records.
4. **Benchmarks:** run the two selected prime workloads with warmups and repeated
   measurements. Add the runaway-loop and filesystem-boundary checks.
5. **Evidence:** export a JSON record or open a previous run from Run history.

![Actual local benchmark run](docs/evidence/sandbox-benchmarks.jpg)

The homepage’s orbital display supports pause/resume and reduced-motion settings.
All five providers share the orbit, with illustrative signals moving between them.
Runtime availability is explained in “About the runtimes” below the visual. Monty
is the only implemented runtime; the other logos do not imply integrations or
endorsements.

## Run, verify and replay a scenario

```bash
uv run sandbox-arena scenarios
uv run sandbox-arena attack caught-denial --iterations 3 --output artifacts/scenario.json
uv run sandbox-arena verify artifacts/scenario.json
uv run sandbox-arena replay artifacts/scenario.json --output artifacts/replay.json
```

`verify` is offline and never executes code. It checks the report checksum,
installed pack, policy, ordered coverage, controls and host observations. A replay
creates a new run linked to the parent digest. Changed packs are refused rather
than silently substituted. Exit code 0 means the expected observations were
verified; 1 means they were not, and invalid input exits 2.

![Verified scenario replay](docs/evidence/attack-lab.jpg)

See [the attack-lab contract](docs/attack-lab.md) for outcome meanings and pack
authoring. Checksums detect changes; they are not signatures or execution attestations.

## Included workloads

| Workload | Expected result | Origin |
| --- | --- | --- |
| First ten primes | Exact primes, sum 129, average 12.9 | Adapted from AI Sandbox Benchmark |
| Primes through 1,000 | Count 168, sum 76,127 | Adapted from AI Sandbox Benchmark |
| Approved tool access | Three fixture rows, total 60 | Authored here |
| Runaway loop | Execution resource limit | Authored here |
| Filesystem boundary | Explicit OS policy denial | Authored here |

The two compute payloads are adapted from
[nibzard/ai-sandbox-benchmark](https://github.com/nibzard/ai-sandbox-benchmark),
pinned to `c07127e731ec14e55f93dee767977bf00bb76dce`. Attribution, the declared
Apache-2.0 license, and exact modifications are documented in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## What the measurements mean

Every trial uses a fresh session on an existing Monty worker pool. Execution time
includes host-to-worker communication and host callbacks. It excludes process
cold start, queue wait and result persistence. These are local exploratory
measurements, not provider rankings or a reproduction of upstream timing results.

Warmups are excluded. Every failed check remains in the exported record. Summary
latencies use passing trials; P95 requires at least 20 passing samples. Configured
memory is an allocator budget, not measured RSS. Passing boundary cases does not
certify a sandbox as secure.

## Use your own client or agent

The local API accepts generated code through the same bounded execution path.
There is no live LLM connection in the new playground yet.

```bash
curl http://127.0.0.1:8033/api/playground/runs \
  -H 'Content-Type: application/json' \
  -d '{"mode":"playground","code":"6 * 7","allow_fixture":false}'
```

The response supplies a run ID. Read `/api/playground/runs/{id}`, follow
`/api/playground/runs/{id}/events`, or download `/api/playground/runs/{id}/export`.
The offline API reference is at `/docs`, with a machine-readable `/openapi.json`.

## Architecture and next steps

- [Attack-lab scenarios, verification and replay](docs/attack-lab.md)
- [Architecture and measurement contract](docs/playground-architecture.md)
- [Validation evidence and current limits](docs/playground-validation.md)
- [Roadmap and provider collaboration strategy](docs/roadmap.md)
- [Positioning and comparison with existing tools](docs/positioning.md)
- [Contribution guide](CONTRIBUTING.md)
- [Original inference incident example](docs/incident-lab.md), still available at `/incident-lab`

One serial runner, a bounded eight-job queue, separate Monty worker processes,
SQLite history, replayable server-sent events, and no frontend build step.
Cancellation stops between bounded trials. Restarted jobs are marked interrupted.

Records persist code and outputs in `artifacts/playground.sqlite3`; do not paste
credentials or private data you do not want stored. This release is a single-user
local application, with no authentication or tenant isolation. Public hosting
requires the controls described in the roadmap.

## Develop

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run sandbox-arena evaluate
```

The original incident acceptance suite remains supported. Tests cover benchmark
oracles, permission denials, resource limits, session isolation, recovery, queue
admission, cancellation, durable history, event replay, export, and request bounds.

Application code: MIT. Adapted prime workloads: Apache-2.0. Design direction
inspired by [AI Bottlenecks](https://aibottlenecks.app/), with original implementation
and assets. No provider partnership or affiliation is implied.
