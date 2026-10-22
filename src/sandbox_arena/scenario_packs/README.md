# Bundled scenarios

Only reviewed JSON resources in this package are executable scenario packs. Each
pack declares its policy, positive control, challenge, observable assertions and
limits of interpretation. Updating any probe or expectation requires a new pack
version. Catalog SHA-256 covers the entire normalized pack, including policy.

These are authored boundary probes, not reproductions of historical CVEs. Each
probe runs in a fresh Monty session. Host Python never executes pack code.
