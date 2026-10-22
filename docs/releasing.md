# Release procedure

1. Update the package version and regenerate `uv.lock`. Update the workspace
   version label and add `docs/releases/VERSION.md` with changes, validation and
   limitations. Keep scenario pack versions independent of the application version.
2. Open a release PR. CI runs lint, tests, the incident acceptance suite, builds
   both distributions, compares bundled assets and scenario resources with source,
   and exercises the installed wheel outside the checkout.
3. Merge after checks pass. Preserve feature commit history with merge commits.
4. Create an annotated `vVERSION` tag on the merged main commit and push that tag.
5. The release workflow repeats verification and publishes a GitHub prerelease
   with the wheel, source distribution and `SHA256SUMS`. It rejects a tag/version
   mismatch. No PyPI publishing or hosted deployment happens in this workflow.
6. Check the release workflow result and download links. Never move a published
   tag or replace release bytes to conceal a correction; issue a new patch version.

Verify downloads with `shasum -a 256 -c SHA256SUMS` (macOS) or
`sha256sum -c SHA256SUMS` (Linux). These checksums detect corruption; they are not
an independent publisher signature.

For a local build: `uv build && uv run python scripts/check_dist.py`. The script
also rejects accidental inclusion of local artifacts, environment files, virtual
environments or Git metadata. Only reviewed release binaries and checksums are
attached. Local SQLite history and traces are never release artifacts.
