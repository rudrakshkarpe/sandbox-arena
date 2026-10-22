# Local preview validation

Verified on October 22, 2026 with Python 3.14 and pydantic-monty 1.2.0 on macOS arm64.

## Automated checks

- Ruff lint and format checks pass.
- JavaScript syntax and Prettier checks pass for the new interface.
- 39 pytest tests pass, including nine new playground tests (parameterized workload
  cases included in this count).
- The existing 12 incident acceptance cases still pass.
- All five new workloads pass a recorded run: three measured trials and one warmup
  per workload, for 15 measured trials and five warmups.

The self-contained recorded run is [sandbox-suite.json](evidence/sandbox-suite.json).
This small run validates wiring and expected outcomes; it is not a performance
study or a security certification.

## Browser checks

- Loaded the interface and executed Hello, Monty, prime calculation, and fixture access.
- Disabled fixture access and observed the denial in the policy audit.
- Executed the two adapted prime workloads and inspected real timing charts.
- Stopped an active 50-trial runaway-loop suite. It retained 13 completed measured
  trials and one warmup, then became cancelled. Timing depends on when Stop is clicked.
- Reopened persisted history after a server restart.
- Verified export links; API tests verify the downloaded JSON record matches the stored evidence.
- No browser console errors were observed during these flows.

Screenshots: [playground](evidence/sandbox-playground.jpg),
[benchmark report](evidence/sandbox-benchmarks.jpg).

Desktop rendering is visually checked. Responsive CSS is included, but the browser
viewport override did not reliably apply the requested narrow size, so mobile
visual verification remains outstanding.

## What remains unverified

Public hosting, authentication and multi-tenant operation; cloud providers; live
model/agent integration in the new playground; multi-runner concurrency; cold
process startup benchmarks; hostile multi-tenant load; and remote CI for this branch.
No provider credentials or paid model calls were used. No partnership is implied.
