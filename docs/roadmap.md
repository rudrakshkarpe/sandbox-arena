# From Monty workbench to a shared evaluation platform

## Product promise

Bring your workload, choose a sandbox, change its constraints, and inspect the
evidence. Grow by making useful, reproducible experiments easy to share and
contribute. A provider's presence means integration support, not endorsement.

## Milestones and release gates

| Milestone | Deliverable | Gate before the next stage |
| --- | --- | --- |
| 0.2 Local Monty preview | Editor, policy, five workloads, raw samples, persistent history, exports | A new user can install without keys and produce a verified result |
| Monty depth | Session/snapshot experiments, callback overhead, independent cold process startup, bounded concurrency, live agent example | Each suite defines exactly what it measures and has correctness/recovery tests |
| Second runtime | Modal adapter and provider capability registry | Equivalent supported workloads, resource cleanup tests, separately labelled local and remote timings |
| Community release | Contribution templates, reproducible environment manifests, example reports, methodology change log | Outside contributors can add a workload or adapter without modifying the UI |
| Hosted dashboard + user runner | Authenticated control plane, outbound paired runners, selective result uploads | Revocable pairing, explicit credential ownership, tenant isolation tests, quotas and retention |
| Managed execution | Tenant-scoped disposable workers, secret brokerage, cost caps, egress rules, leased jobs, cleanup reconciliation | Independent deployment/security review and abuse/load testing before anonymous access |
| Comparative research | Repeated regional runs, uncertainty estimates, public provenance, regression views | Published methodology and raw evidence; independently repeatable results |

## Start collaborations with a concrete contribution

1. Publish the Monty quickstart and a two-minute walkthrough with real executions.
2. Invite the Monty maintainers to review the capability descriptions, failure
   classifications, and measurements. Do not ask them to endorse security claims.
3. Invite one cloud provider to contribute an adapter plus a workload they consider
   representative. Review it with the same neutral acceptance criteria.
4. Publish integration status as proposed, experimental, verified against a pinned
   version, or maintained. Mark ownership and last successful validation.
5. Offer maintainers a reproducible failure report: workload, environment, raw
   result, expected behavior, and minimal steps. Keep provider credentials local.

Useful initial collaboration targets are the Monty and upstream benchmark
maintainers, followed by a Modal integration. E2B, Daytona, and other runtime
families can follow when the registry and conformance suite have been tested by a
second implementation. No partnerships or outreach are established by this work.

## Preserve trust as participation grows

- Version methodology separately from runtime versions.
- Keep provider-specific tuning visible in exported configurations.
- Require reviewed benchmark PRs; provider contributions cannot silently change
  comparison rules or suppress failures.
- Separate capability coverage, correctness, latency, reliability, and cost.
  Do not compress unlike isolation models into an unexplained winner score.
- Label submissions by provenance: local user run, provider-submitted, or
  independently reproduced. Attestation can be added when the runner is hosted.
- Publish corrections and allow technical disputes backed by repeatable evidence.
- Use synthetic owned targets for boundary tests. Keep exploit research outside
  the public multi-tenant playground until its execution environment is designed
  for that threat model.

## Engineering scale

Keep the first release a modular application. Move SQLite to Postgres and local
artifacts to object storage when a shared control plane exists. Introduce a
durable queue and leased, idempotent jobs before multiple runner workers; add
heartbeats, deadline enforcement, orphan cleanup and per-tenant admission control
together. Event delivery should use cursors and backpressure, not require every
browser to reload a large run document after each trial.

Keep raw measurement collection separate from presentation. The present
dependency-free frontend is easy to ship with the Python package. A larger team
can introduce a typed React client against the same API once the workflows settle.

## What success looks like

Track time to first verified result, successful clean installs, completed runs,
externally reproduced reports, accepted contributions, adapter maintenance
coverage, and unresolved correctness issues. These are proposed measures, not
current traction claims.

More than 100 meaningful commits is plausible across these milestones. Each
commit should be a reviewable implementation, test, fix or documentation change.
Release gates and user outcomes decide progress; commit count does not.
