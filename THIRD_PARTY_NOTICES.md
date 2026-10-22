# Third-party notices

## AI Sandbox Benchmark

The two prime-calculation payloads in `src/sandbox_arena/benchmarks/`
are adapted from [nibzard/ai-sandbox-benchmark](https://github.com/nibzard/ai-sandbox-benchmark),
revision `c07127e731ec14e55f93dee767977bf00bb76dce`:

- `tests/test_calculate_primes.py` → `primes_10.py.txt`
- `tests/test_improved_calculate_primes.py` → `primes_1000.py.txt`

Upstream's README and CONTRIBUTING declare Apache License 2.0. The inspected
revision does not contain the LICENSE file linked by those documents or a NOTICE
file. A copy of the declared license is provided in `licenses/Apache-2.0.txt`.
These adapted payloads retain Apache-2.0 licensing; the surrounding application
remains under this repository's MIT license. Credit belongs to the upstream
authors and contributors. No endorsement or partnership is implied.

Modifications: removed the host-side test generator, decorators, package helpers,
guest timer, and formatted output. Kept the trial-division algorithms and input
sizes. Returned structured values for independent correctness checks. Execution
is measured at the Monty adapter boundary. These are adapted workloads, not
numerically comparable reproductions of upstream provider results.

## Design reference

[AI Bottlenecks](https://aibottlenecks.app/) inspired the dark editorial palette,
serif headlines, fine rules, and compact data treatment. All application markup,
styles, application icon drawings, and copy here were authored for Sandbox Arena.
Provider marks below are third-party assets. No application source code or claims
of affiliation were copied. The provider display also takes directional inspiration
from [Sandbox](https://sandbox-arena.vercel.app/); the orbital layout is original.

## Provider marks

The following assets are bundled locally in `src/sandbox_arena/static/providers/`
so the interface makes no third-party asset requests. Retrieved October 22, 2026
from each provider's official website. These marks identify their respective
owners; their inclusion does not imply partnership, endorsement, or an available
integration. Provider marks are not covered by this project's MIT license.

| File | Owner | Source |
| --- | --- | --- |
| `pydantic.svg` | Pydantic | [Official logomark](https://pydantic.dev/brand/pydantic-logomark.svg), linked from the Monty page |
| `modal.svg` | Modal | “Download logo as .svg” on [modal.com](https://modal.com/), decoded from the provided data URI |
| `e2b.png` | E2B | [Official site icon](https://e2b.dev/icon2.png?icon2.2h_70q4cu8mj-.png) |
| `daytona.png` | Daytona | [Dark-mode icon](https://framerusercontent.com/images/cCvSUNbGejoZpWVg0tUGLSqxGC8.png), linked from daytona.io |
| `vercel.png` | Vercel | [Official site icon](https://assets.vercel.com/image/upload/q_auto/front/favicon/vercel/apple-touch-icon-180x180.png) |

Shapes and colors are unchanged; the interface resizes them for display. The
Pydantic organization mark identifies Monty's publisher rather than claiming to
be a separate Monty product logo.
