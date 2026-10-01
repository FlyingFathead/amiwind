# Local source build — rc2

Use the reconciled public-source ZIP. Extract it into a fresh directory outside
~/NeuralNetwork/amiwind; do not overlay either earlier source candidate blindly.
The release version remains 0.0.25-rc2. No private playable is delivered.

Apply to the existing checkout with the extracted tools/apply_source_update.py, passing
--source, --target and a new external --backup directory. The helper accepts
known dev1/original-rc1/checkpoint-001/004/006 file bytes, preserves unrelated
paths, and detects overlapping edits before writing. It removes the two unwanted
journal screenshots and obsolete checkpoint input/default files, after backup.
Your cleanup commit deleting the v0.0.24 image is accepted; that image stays gone.

Compile from the applied checkout or the separate extracted source:

```bash
(
set -euo pipefail
cd "$HOME/NeuralNetwork/amiwind"
bash build.sh --autoinstall \
  --data-files "/media/kahel/DUMP-2025-24-APR/Morrowind/Morrowind" \
  --tools-dir "$HOME/NeuralNetwork/amiwind-tools" \
  --workspace "$HOME/NeuralNetwork/amiwind-tests" \
  --name "rc2-local-$(date +%Y%m%d-%H%M%S)"
)
```

This is a full data build, not --dry-run. No ROM/autorun option is required for
compilation. --kickstart-file is only valid together with --autorun-fs-uae.
The unchanged production actor-contact gate can stop HDF assembly on 23 existing
findings. Read the run logs rather than treating engine compilation as full
image acceptance. Source/host verification is in validation/rc2-source.json;
merged native acceptance remains local work.

Autosaves: config/game.cfg supplies aw_autosaves 5. Existing id1/config.cfg values
override it. Console aw_autosaves N or Options > Autosave history sets 0..16;
zero disables autosaves. Exit normally to persist the setting. Quicksaves are
separate and the save-menu empty/incompatible distinction remains unresolved.

Owner controls all Git/GitHub operations. No original/checkpoint archive or tag
is replaced. Public release attachments must contain public source only.
