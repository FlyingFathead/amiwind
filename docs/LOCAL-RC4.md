# Local source checkpoint — v0.0.25-rc4

Verify `AmiWind-v0.0.25-rc4-SHA256SUMS` beside the downloaded files. Extract the
patch outside the checkout and apply the standalone source updater with a new
external backup directory. The baseline is the published rc3 source archive
identified in `PATCH-v0.0.25-rc4.json`. The optional Windows-roadmap update 001
is also accepted. Conflicting changes stop application before writes; unrelated
local edits are preserved. Review the diff before committing.

Compile from the updated checkout with a new run name:

```bash
(
set -euo pipefail
cd /path/to/amiwind
bash build.sh --autoinstall \
  --data-files "/path/to/Morrowind/Data Files" \
  --tools-dir "/path/to/amiwind-tools" \
  --workspace "/path/to/amiwind-tests" \
  --name "rc4-local-$(date +%Y%m%d-%H%M%S)"
)
```

Keep build output and tools outside the source checkout. The fresh rc4 native
compile is a separate result from a full image build. The earlier rc3 full run
stopped on disk exhaustion during world-terrain assembly; the unchanged image
gate also retains 23 historical actor-contact findings. Do not replace or alter
an existing build run to claim a fresh verification.

Windows is untested. `py -3 tools\build.py --host-plan` can collect an inventory
without installing or executing native tools. It is not a working full-build
recipe; follow the [roadmap](WINDOWS_BUILD_ROADMAP.md) for pending acceptance.

The owner performs all Git/GitHub publishing, using a new rc4 prerelease and
matching source assets. Do not replace rc3 tags or assets. The generated
`docs/PACKAGE_MANIFEST.json` remains untracked. No private playable is delivered.
