# Local source checkpoint — v0.0.25-rc3

Verify `AmiWind-v0.0.25-rc3-SHA256SUMS` beside the downloaded archives. Extract the
patch into a fresh directory outside the checkout. Apply with the included
`tools/apply_source_update.py`, supplying `--source`, `--target` and a new external
`--backup` directory. This checkpoint targets the rc2 snapshot identified in
`PATCH-v0.0.25-rc3.json`; overlapping local edits stop the update before writes.

Compile from the updated checkout with a new run name:

```bash
(
set -euo pipefail
cd /path/to/amiwind
bash build.sh --autoinstall \
  --data-files "/path/to/Morrowind/Data Files" \
  --tools-dir "/path/to/amiwind-tools" \
  --workspace "/path/to/amiwind-tests" \
  --name "rc3-local-$(date +%Y%m%d-%H%M%S)"
)
```

Keep the tools and build workspace outside the public checkout. The supplied
source was compiled and exercised through 21 real-input stages. Whole-island
terrain and final image validation remain incomplete. The historical actor-contact
findings can still stop final HDF assembly. No gate is bypassed by this update.
See `RELEASE-v0.0.25-rc3.md` for the precise verification boundary.

The owner runs all commit, push, tag and GitHub release commands. Use a prerelease
for this checkpoint and its matching release notes; retain existing tags and
archives. Attach public source ZIPs and checksums only. `PACKAGE_MANIFEST.json`
is generated and must not be tracked. Public documentation uses generic paths.
