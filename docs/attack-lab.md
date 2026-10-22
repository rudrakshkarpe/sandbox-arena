# Attack-lab foundation

The local Monty adapter executes 18 authored, bounded scenario packs. These are
not copied exploit payloads or historical CVE reproductions. Each scenario tests
one explicitly named boundary under a pinned policy. It uses synthetic data and
does not probe external machines, real host secrets or production accounts.

## Execution contract

A pack has a stable ID, semantic version, category, objective, capability list,
policy, limitation statement and two to four probes. At least one probe is a
positive control and one is a challenge. The runner executes probes in declared
order for each repetition. Every probe gets a fresh session on the worker pool.
The browser runs three repetitions; the API and CLI permit one to ten. Warmups
are disabled. Timeout, memory and fixture permissions come from the pack and
cannot be overridden by a scenario request.

The host records code SHA-256, output, result, errors, callback audit, truncation
and setup/execution/cleanup timing. The deterministic verifier checks explicit
assertions against those observations. Guest output and guest exceptions never
supply the verdict. An exception without host audit evidence cannot establish a
host-policy denial.

## Interpreting results

| Outcome | Meaning |
| --- | --- |
| `expected_observed` | Complete ordered evidence, passing controls and every declared assertion observed |
| `unexpected_observed` | Controls passed and evidence is complete, but at least one challenge assertion differs |
| `inconclusive` | Failed controls, incomplete coverage, invalid policy, cancellation, interruption or runner failure |
| `unsupported` | The installed catalog cannot match the recorded pack |

An unexpected observation needs investigation. It does not automatically prove
an escape. An expected observation does not certify the sandbox as secure.
Resource limits, filesystem callback denial and JSON transport checks describe
different layers; do not combine them into a provider security score.

## Evidence and replay

Terminal records contain the normalized pack, pack digest, effective RunSpec,
runtime environment, samples, events, assessment and integrity block. The
`arena-json-v1` checksum serializes all fields except `integrity` as UTF-8 JSON
with sorted keys, ASCII escaping, compact separators and finite numbers only.
Verification recomputes assertions instead of trusting stored checks or verdicts.

A checksum detects accidental or unacknowledged edits. Anyone able to replace the
report can recompute it. It is not a signature, host attestation or proof that the
reported execution happened. Share reports only after reviewing their code and
outputs; the application does not redact arbitrary guest content.

Replay validates the source checksum, terminal state, pack snapshot and current
installed version. It preserves the effective configuration and adds a parent
run ID and report digest. Sessions, run ID, timestamps and measurements are new.
The current machine environment is recorded again; timing is not deterministic.

## Author a pack

1. Add a JSON file to `src/sandbox_arena/scenario_packs/` matching its stable ID.
2. Declare the tested boundary and a limitation that prevents overstating results.
3. Add a working control and a bounded challenge. Never execute guest payloads
   through host Python, shell, imports or test setup.
4. Require observable results for successful probes, an error prefix for errors,
   and host audit counts for denials. Check code digests independently.
5. Run `uv run pytest tests/test_scenario_catalog.py`. Its parameterized test
   executes every registered probe through Monty and verifies the assertions.
6. Add verifier regression tests if the new evidence type could produce a false
   positive. Increment the pack version whenever code, policy or expectations change.

The catalog contains reviewed package resources only. Uploading arbitrary pack
files is intentionally not part of this release. A future adapter must check
capabilities before execution and report unsupported cases explicitly.

## API

Discover packs in `GET /api/playground/catalog` or read one at
`GET /api/playground/scenarios/{id}`. Submit:

```json
{"mode":"scenario","scenario_id":"caught-denial","iterations":3}
```

Use the existing run, event, cancellation and export endpoints. Verify at
`GET /api/playground/runs/{id}/verify`; replay with an empty JSON object at
`POST /api/playground/runs/{id}/replay`. Invalid scenario requests return 422;
replay conflicts return 409; a full eight-job queue returns 429.

## Next execution boundary

A historical exploit lab needs disposable outer VMs, denied-by-default egress,
owned canaries, a separate controller, deadlines and cleanup reconciliation.
Monty's current interpreter and host callback checks do not provide that outer
containment. Public hosting also needs authentication, tenant isolation, quotas,
credential ownership and selective evidence uploads. See the roadmap for those gates.
