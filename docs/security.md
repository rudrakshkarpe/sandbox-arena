# Boundaries and production gaps

This is a local technical evaluation over public data. Do not expose the server on the internet.

## What is granted

The application gives Monty one host callback: `read_evidence(scope, scenario)`. It checks exact string types, a fixed application-owned scope, the selected scenario or baseline, and a four-call budget. It returns copied aggregate fields only. No path, SQL, URL, credentials, or customer account chooser is exposed.

The server accepts a scenario enum. It never accepts an authorized scope or a filesystem mount from the browser. The scope policy demonstrates an authorization boundary, but there is no login, tenant registry, or production identity provider.

## What is bounded

| Resource | Limit | Boundary |
| --- | --- | --- |
| Submitted code | 12,000 characters | Application validation |
| HTTP request body | 64,000 bytes | Streamed body check |
| Monty allocation | 16,000,000 bytes | Worker allocator accounting, not RSS |
| Feed/turn execution | 250 ms each | Interpreter execution time, excluding host waits |
| Worker request | 2 seconds | Pool per-turn watchdog, not a complete HTTP deadline |
| Checkout wait | 3 seconds | Pool queue wait |
| Host round trips | 24 per session | Monty suspension budget |
| Evidence reads | 4 attempts | Host callback |
| Collected print output | 4 KiB | Host collector |
| Live code generation | At most 2 requests, 1,600 requested output tokens each | Pydantic AI plus provider settings |

Callbacks here are bounded in-memory reads. A production network callback needs its own deadline, response size limit, cancellation handling, and server-side authorization. Monty execution-time limits do not bound time spent waiting on arbitrary host code.

Every attempt ends its checkout, including time and memory failures. A later attempt uses a fresh session. The code does not reuse a session after a resource limit trip.

## What is denied

No filesystem mount or external module is provided. OS calls go to an explicit denying handler. Unknown external functions and unsupported imports cannot turn into arbitrary host Python calls. Tests exercise file access, environment reads, unavailable network/process imports, and scope changes.

The session wall clock is fixed to September 27, 2026, random starts from seed zero, and sleep requests are sent to the denying handler. The fixed clock is for reproducibility, not the timestamp of a current inference run.

The host records denied operations outside the sandbox. The verifier rejects a result even if sandbox code catches the permission exception and returns otherwise correct numbers.

These finite tests are not a sandbox-escape assessment. Monty's own [security model](https://github.com/pydantic/monty/blob/main/docs/security.md) explains its language-level isolation and the responsibility of host callbacks. Use additional process/container isolation and operating-system resource controls for a production service handling untrusted code.

## Telemetry and data handling

Default tracing writes local `artifacts/traces.jsonl`. Hosted export is disabled unless `--export-logfire` is passed, and then requires `LOGFIRE_TOKEN`. The application does not mount credentials or the host environment inside Monty.

Startup appends `monty_pool=info` to this process's `RUST_LOG` filter so native session and feed spans are collected even when an inherited filter is `warn`. Other Rust targets retain their configured levels. This does not change your shell or system environment.

Native Monty and Pydantic AI instrumentation can record code, inputs, calls, errors, prompts, and outputs. Logfire's default scrubbing is not a substitute for a data classification review. Never paste customer secrets into the code editor or prompts. Before adapting, agree on collection fields, redaction, access control, residency and retention. The local trace file grows until the operator removes or rotates it.

Only public measurements are bundled. Snapshot loading is not exposed. The project makes no guarantee about accepting untrusted serialized sessions.

## Local web protections and remaining work

The CLI binds to loopback, validates Host, rejects cross-origin POSTs and non-JSON submissions, and caps request bodies. The page has a restrictive content security policy and renders result strings with `textContent`.

This does not provide authentication, rate limiting, a reverse proxy, global request concurrency limits, per-user quotas, audit retention, TLS, or a hard total wall-clock deadline. A public deployment would require those controls and a separate threat review. The CLI's live model path is not exposed through the web API.
