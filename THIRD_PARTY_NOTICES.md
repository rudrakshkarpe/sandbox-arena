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
styles, icon drawings, and copy here were authored for Sandbox Arena. No branding,
images, source code, or claims of affiliation were copied.
