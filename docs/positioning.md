# Positioning: an execution workbench for sandbox adoption

Reviewed on October 22, 2026. This document separates observations of the existing
public site, capabilities implemented here, and proposed future work.

## What already exists

[sandbox-arena.vercel.app](https://sandbox-arena.vercel.app/) provides a public
provider directory, benchmark views, provider comparisons, and a repository
activity feed. The rendered benchmark page has Baseline, Gradual, Peak, Downloads,
Stats, Security, Pricing, and Agent Discovery tabs.

- The Baseline view attributes its sequential provisioning measurements to
  [ComputeSDK](https://github.com/computesdk/benchmarks) and displays median, P95,
  P99, success rate, and a measurement date.
- The [Security view](https://sandbox-arena.vercel.app/benchmarks?tab=security)
  explicitly labels its table as NPM package security metadata. It presents
  package versions, quality, malware, licensing and vulnerability indicators.
- The [Agent Discovery view](https://sandbox-arena.vercel.app/benchmarks?tab=arenaSandboxes)
  attributes evaluations to [2027.dev](https://2027.dev/arena/sandboxes). Its table
  covers agent setup time, tool calls, friction, errors, cost and discoverability.
- The [comparison page](https://sandbox-arena.vercel.app/compare) offers provider
  selection, and [activity](https://sandbox-arena.vercel.app/activity) tracks
  provider-repository pull requests.

These are useful features. This project does not currently match that provider
breadth, public deployment, or aggregated data coverage. We did not audit the
other application's source or backend. No user-code execution workflow was found
in the inspected public pages; that is a bounded observation, not proof that no
such capability exists elsewhere.

## Our current position

| User need | Implemented here | Honest limit |
| --- | --- | --- |
| Try code in a sandbox now | Editable Monty code with limits and controlled fixture access | Local Monty only |
| Understand a policy decision | Recorded allowed/denied host operations and explicit OS denials | Small synthetic policy; not a security certification |
| Repeat a controlled workload | Versioned payloads, warmups, raw samples, correctness checks | Five starter cases; prime calculations are smoke baselines |
| Keep execution evidence | Local history, configuration, runtime version, code hash and JSON export | No signed provenance, sharing or hosted storage |
| Use an external agent client | HTTP submission API | No live agent UI or provider comparison yet |

Our promise is: **evaluate your own workload under your own constraints, and
understand the observed behavior before adopting a sandbox.**

Published provider data can supply context. It is not a substitute for measuring
an application's workload. Likewise, our small interactive tests are not a
substitute for a broad, independently reproduced provider study. Avoid claiming
that this project is already superior overall or uniquely reproducible.

## The workflow worth developing next

An engineer gives an agent a task over a synthetic order fixture. They configure
which tool it can call, how much time it has, and what result is expected. The
workbench captures the generated code, tool decisions, timing and final answer.
They then change one permission or limit, replay the same code, and compare the
two observed outcomes. A failing case becomes a saved regression test.

The current editor, policy control and evidence store provide part of this path.
Live agent generation, frozen-code replay comparison, experiment diffs and
regression gates are planned work. Keep model latency and stochastic agent quality
separate from deterministic runtime replay measurements.

## Priorities and acceptance gates

1. **Monty adoption workflow.** Guided examples, one explicit opt-in agent
   integration, permission diffs, fixture isolation, snapshot/resume experiments,
   and clearly separated cold-process and warm-session tests. Gate: five outside
   developers can reproduce a result and explain a failure without assistance.
2. **Useful application workloads.** JSON/CSV transformations supported by the
   runtime, bounded host-tool fan-out, large-result handling, cancellation,
   recovery and cross-session leakage probes. Gate: every case has a documented
   oracle and capability contract; failures remain visible.
3. **A second provider.** Implement Modal with direct cleanup tests and explicit
   cost ceilings. Gate: compare identical supported computations, label unsupported
   capabilities, and distinguish provisioning from execution.
4. **A provider-maintained contribution path.** Conformance tests, reviewed
   workload contributions, a version matrix and reproducible bug bundles. Gate:
   one external maintainer can add or fix an adapter without changing the UI.
5. **Hosted access.** Start with authenticated dashboards and outbound paired
   user-controlled runners. Add managed execution only after tenant isolation,
   quotas, secret ownership, deadlines and cleanup reconciliation are tested.
6. **Ongoing usefulness.** Add CI regression checks, comparison reports and
   opt-in report sharing so teams return after their initial provider selection.

Do not build ten integrations, an aggregate ranking, or a provider-news feed before
the own-workload workflow has external users. Reuse existing benchmark definitions
where they fit, with licensing, pinned revisions and visible adaptation notes.

## Collaboration and naming

Ask Monty maintainers to review a concrete capability matrix and a reproducible
failure bundle. Ask the next provider for an adapter maintainer and representative
workloads. Preserve independent review of scoring and methodology; commercial
participation must not hide failures. Consider integration with existing benchmark
projects rather than assuming their work must be displaced.

The requested repository slug is `rudrakshkarpe/sandbox-arena`. Another visible
project already uses the sandbox-arena name in its URL. The repository can keep
this slug, but the public brand needs an explicit decision before promotion:
either choose a distinct product name or make authorship and positioning clear.
No affiliation with that site, ComputeSDK, Pydantic, or any provider is claimed.
