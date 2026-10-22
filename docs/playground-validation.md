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
[benchmark report](evidence/sandbox-benchmarks.jpg). The benchmark screenshot
retains the earlier Sandbox Lab branding; the playground preview uses Sandbox Arena.

Desktop rendering is visually checked. Responsive CSS is included, but the browser
viewport override did not reliably apply the requested narrow size, so mobile
visual verification of the original workspace remains outstanding. See the
homepage update below for the newly checked mobile surfaces.

## What remains unverified

Public hosting, authentication and multi-tenant operation; cloud providers; live
model/agent integration in the new playground; multi-runner concurrency; cold
process startup benchmarks; and hostile multi-tenant load.
No provider credentials or paid model calls were used. No partnership is implied.

## Standalone repository validation

The renamed `sandbox_arena` package passes the same 39 tests and 12 acceptance
cases using the existing Python 3.14 dependency environment. Ruff, JavaScript
syntax and Prettier checks pass. A fresh wheel builds successfully and contains
the static UI, guest workload payloads and both CLI entry points. The renamed
application was opened at localhost:8034 and returned 42 from the Hello example.

GitHub Actions [run 39757096609](https://github.com/rudrakshkarpe/sandbox-arena/actions/runs/39757096609)
passed a clean locked dependency install, Ruff, all 39 tests and the 12 acceptance
cases for commit `2e9046b`. A separate fresh macOS environment download timed out
on `griffelib` despite a 120-second HTTP timeout; the running local preview uses
the previously installed dependency environment. This network failure did not
occur in the clean Linux CI installation.

## Arena homepage and scenario entry points

Verified October 22, 2026:

- Full-width black homepage with provider orbit, live Monty status and
  catalog-derived boundary/compute counts. Other providers are visibly planned.
- Pause/resume controls work; reduced-motion handling is implemented in CSS and
  JavaScript, but a system reduced-motion preference was not independently exercised.
- Both one-click scenarios completed three measured trials with passing checks.
- The homepage benchmark link selected the two compute workloads; both passed
  ten measured trials plus a warmup. Existing code-workspace navigation works.
- No browser console errors observed. Desktop width 1280 and content width 1280.
- Mobile homepage and scenario navigation checked in a 390-pixel same-origin
  iframe on a temporary preview server. An orbital overflow was fixed; viewport
  width and content width both measured 390. This is browser layout testing, not
  a physical-device test. The regular server retains `frame-ancestors 'none'`.
- 39 tests and 12 acceptance cases pass using the existing Python dependency
  environment; Ruff, Prettier and JavaScript syntax checks pass.
- `uv build --offline` succeeds using cached build dependencies; the wheel contains
  `arena.css` and all five bundled provider assets. The online build was stopped
  while retrying dependency access.

Screenshots: [homepage](evidence/arena-home.jpg) and
[390-pixel preview](evidence/arena-mobile.jpg).

No new attack payloads or cloud integrations were added in this interface update.
The scenario shortcuts reuse the versioned filesystem and execution-limit checks.
