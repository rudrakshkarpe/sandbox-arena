# Container/VM tier (preview)

The interpreter tier tests what Monty blocks inside one Python process. This tier
tests what a real sandbox (a container or microVM) lets code reach: the network,
DNS, cloud metadata and credentials held by whoever runs the sandbox.

Status: local Docker only. E2B and Modal adapters are next and plug into the same
contract.

## How it fits together

| Piece | File | Job |
| --- | --- | --- |
| Capability registry | `capabilities.py` | Adapters declare capabilities, packs declare requirements. A mismatch is `unsupported`, never pass or fail. Unknown names never match. |
| Adapter contract | `adapters/base.py` | `create`, `exec`, `put_file`, `get_file`, `destroy`. `destroy` must confirm the sandbox is gone. |
| Monty adapter | `adapters/monty.py` | The existing `MontyProvider`, now declaring interpreter-tier capabilities. |
| Docker adapter | `adapters/docker.py` | Local containers through the Docker CLI. No SDK dependency. |
| Observers | `observers.py` | A throwaway lab per run: an allowed fixture host and a canary that logs every HTTP request and DNS query. |
| Packs | `vm_packs/*.json` | Versioned specs: control, challenges, assertions, limitation. |
| Runner and verifier | `vm_runner.py` | Fresh sandbox per probe, host-side verdicts, sealed reports, offline re-verification. |

## Evidence classes

Every check in every report (both tiers) is labelled:

- `host_observed`: measured outside the sandbox. Canary hits, exit codes, cleanup
  confirmation, host audit events, code digests.
- `probe_reported`: produced by code inside the sandbox. Return values, printed
  JSON, exception classes.

Probes are reviewed and digest-pinned, so `probe_reported` evidence is useful, but
code inside a sandbox can fabricate it. Network verdicts in this tier are always
`host_observed`: a probe that prints "blocked" proves nothing, zero canary hits
does. Agent-generated output will never be a verdict.

## Profiles

Each pack runs under two profiles:

- `default`: the runtime's out-of-the-box posture. For Docker: a normal bridge
  network, root user, default capabilities.
- `strict`: the strictest documented posture. For Docker: an `--internal`
  allowlist network, `--cap-drop ALL`, `no-new-privileges`, read-only rootfs,
  non-root user, PID cap.

The gap between the two is a finding in itself.

## Packs

| Pack | Layer | Challenge | Verdict from |
| --- | --- | --- | --- |
| `egress-deny` | network | Reach the canary by name, by raw IP and via a 302 from the allowed host | Canary HTTP log |
| `dns-exfil` | network | Resolve `<token>.exfil.arena.test` through the sandbox resolver | Canary DNS log |
| `metadata-endpoint` | secrets | Request AWS, GCP and Azure metadata endpoints | Probe report (labelled) |
| `secret-exposure` | secrets | Scan env, `/proc/*/environ` and secret paths for orchestrator credentials; look for a runtime socket | Probe report plus a host check that no secret appears in output |

The secret pack never sends secrets into the sandbox. It sends SHA-256 digests and
the probe reports matches. Reports never contain secret values.

## First local results (Docker 29.9.2, runc)

| Pack | default | strict |
| --- | --- | --- |
| egress-deny | unexpected: 3 of 3 routes reached the canary | expected: 0 hits |
| dns-exfil | unexpected: the token label reached the canary resolver | expected: 0 queries |
| metadata-endpoint | expected (no metadata service on a local host) | expected |
| secret-exposure | expected | expected |

Mutation check: mounting `/var/run/docker.sock` into the sandbox flips
`secret-exposure` to unexpected (see `tests/test_vm_docker.py`).

## Run it on a Mac

1. Install and start Docker Desktop.
2. `docker pull python:3.12-slim` (any image with `python3` works; set
   `ARENA_DOCKER_IMAGE` to use another).
3. Run:

```bash
uv sync
uv run sandbox-arena vm-scenarios
uv run sandbox-arena vm-attack all --profile both
uv run sandbox-arena vm-verify artifacts/vm/egress-deny.default.json
```

Exit codes: `0` all expected, `3` at least one unexpected observation (a finding),
`1` inconclusive or invalid evidence.

## Limitations

- Containers share the host kernel. These results describe Docker's network and
  privilege controls, not VM-grade isolation. Reports record `isolation_class`.
- The local lab can only allowlist its own fixture host.
- `dns-exfil` models a provider resolver that forwards to the internet by making
  the canary the upstream resolver. DNS-over-HTTPS and other resolvers are not
  covered.
- Passing packs do not certify a sandbox. They show these specific routes were
  closed in this configuration on this day.

## Next

- E2B and Modal adapters behind the same contract (needs accounts and credits).
- A canary on a VPS we own for cloud runs.
- Remaining packs from the plan: `cross-sandbox`, `memory-oom`, `disk-fill`,
  `process-flood` (after written OK from providers), `hardening-audit`.
- Egress variants: IPv6, empty versus missing allowlist.
- Route the interpreter-tier runner through the capability registry too.
