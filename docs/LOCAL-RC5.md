# Local source checkpoint — v0.0.25-rc5

Verify `AmiWind-v0.0.25-rc5-SHA256SUMS` beside the downloaded files. Apply the
source patch to the rc4 source baseline using the standalone updater and a new
external backup directory. If the checkout is still rc3, apply rc4 first.
Conflicting edits stop before writes; unrelated changes are preserved. Inspect
the resulting diff before committing.

Use a new run name to build the updated checkout:

```bash
(
set -euo pipefail
cd /path/to/amiwind
bash build.sh --autoinstall \
  --data-files "/path/to/Morrowind/Data Files" \
  --tools-dir "/path/to/amiwind-tools" \
  --workspace "/path/to/amiwind-tests" \
  --name "rc5-local-$(date +%Y%m%d-%H%M%S)"
)
```

Keep tools, logs, output and backups outside the source checkout. The new
[completion summary](BUILD_OUTPUT.md) applies to newly started builds; it cannot
retroactively change a builder process that is already running.

All 353 source tests and a fresh native compile/asset-free image build passed.
A complete game conversion is a separate gate and has not passed here. No
private playable is supplied. Windows remains an untested roadmap target.

The owner performs Git/GitHub publishing. Create a new rc5 prerelease with the
matching source assets; do not replace rc4 tags or archives. The generated
`docs/PACKAGE_MANIFEST.json` stays untracked.
