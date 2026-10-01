# Local checkpoint build and publication

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Checkpoint 006 is incomplete rc1 source. It includes recovered shoreline source,
Seyda handoff bounds, common map/HUD coordinates, compass, separate key defaults,
native M/N protection, debug Alt+M and Ctrl noclip, executable Python launchers,
and five autosaves by default. Host checks are distinct from native acceptance.
Quicksave browsing and final native walking/input/shoreline validation remain open.

## Apply the full source to the existing checkout

Download the full source ZIP, incremental ZIP, handoff and checksum sidecars to
`~/NeuralNetwork/`. Use the full source with this guarded installer. The
incremental ZIP is an alternative overlay from the uploaded dev1 snapshot; it
is not needed in addition to the full ZIP. The helper leaves Git metadata and
unrelated files intact, backs up replaced files, and stops without writing if
a changed local file differs from both the uploaded dev1 baseline and checkpoint.
If an earlier recovery checkpoint was already applied, compare/merge those files
instead of forcing the guard.

```bash
set -euo pipefail
cd "$HOME/NeuralNetwork"
stem=AmiWind-v0.0.25-rc1-checkpoint-006
sha256sum -c "$stem-public-source.zip.sha256"
sha256sum -c "$stem-from-dev1-source-patch.zip.sha256"
stage=$(mktemp -d "$HOME/NeuralNetwork/amiwind-checkpoint-006.XXXXXX")
unzip -q "$stem-public-source.zip" -d "$stage"
python3 "$stage/amiwind/tools/apply_checkpoint.py" \
  --source "$stage/amiwind" --target "$HOME/NeuralNetwork/amiwind" \
  --backup "$stage/before"
cd "$HOME/NeuralNetwork/amiwind"
chmod +x build.sh tools/AmiWind-FS-UAE-launcher.py tools/run_fs_uae.py
git diff --check
git status --short
git diff --stat
```

## Compile locally outside the repository

First run the asset-free compiler/boot test. This deliberately does not build the
playable game. Setup provisions the pinned native compiler and required tools.
All outputs, logs and dependency environments stay outside the checkout.

```bash
set -euo pipefail
cd "$HOME/NeuralNetwork/amiwind"
run="rc1-checkpoint-006-compile-$(date +%Y%m%d-%H%M%S)"
./build.sh --autoinstall --dry-run \
  --tools-dir "$HOME/NeuralNetwork/amiwind-tools" \
  --workspace "$HOME/NeuralNetwork/amiwind-tests" --name "$run"
```

For the full private conversion, use the original installed Data Files and your
own A1200 Kickstart 3.1 ROM. Install FS-UAE separately if needed. This is the
full pipeline, including island terrain; it can take substantial disk/time.
The existing strict actor-placement audit can stop final HDF creation on the
23 known contact findings. Its failure is retained; this checkpoint does not
pretend a diagnostic build passed that production gate. Earlier outputs/logs
remain available under the chosen run directory.

```bash
set -euo pipefail
cd "$HOME/NeuralNetwork/amiwind"
read -r -p 'Path to installed Morrowind Data Files: ' data_dir
read -r -p 'Path to your A1200 Kickstart 3.1 ROM: ' kickstart
run="rc1-checkpoint-006-playtest-$(date +%Y%m%d-%H%M%S)"
./build.sh --autoinstall --data-files "$data_dir" \
  --tools-dir "$HOME/NeuralNetwork/amiwind-tools" \
  --workspace "$HOME/NeuralNetwork/amiwind-tests" --name "$run" \
  --autorun-fs-uae --kickstart-file "$kickstart"
install -m 755 tools/AmiWind-FS-UAE-launcher.py \
  "$HOME/NeuralNetwork/amiwind-tests/AmiWind-FS-UAE-launcher.py"
```

For an already built private folder, install the same executable launcher beside
the HDF and launch it there. The launcher searches its own folder, not recursively:

```bash
read -r -p 'Private folder containing your HDF: ' playable_dir
install -m 755 "$HOME/NeuralNetwork/amiwind/tools/AmiWind-FS-UAE-launcher.py" \
  "$playable_dir/AmiWind-FS-UAE-launcher.py"
"$playable_dir/AmiWind-FS-UAE-launcher.py"
```

Autosaves: source defaults live in `config/game.cfg`. Existing saved values in
`id1/config.cfg` override defaults. Options > Autosave
history allows 0..16; five is the fresh default. Set `aw_autosaves 5` in the
console to change an existing installation, then exit normally to persist it.

## Owner-run Git/GitHub commands

Review the diff before committing. These commands create a checkpoint branch,
push it, and publish an explicitly incomplete prerelease at a unique checkpoint
tag. They do not merge main or consume the final `v0.0.25-rc1` tag. Stage only
the public source allowlist; unrelated local files stay outside the commit.

```bash
set -euo pipefail
cd "$HOME/NeuralNetwork/amiwind"
git remote -v
git diff --cached --quiet || { printf "Review existing staged changes first.\n"; exit 1; }
git switch -c recovery/v0.0.25-rc1-checkpoint-006
python3 - <<'PY'
import json, subprocess
files = json.load(open("tools/release-files.json")) + ["docs/PACKAGE_MANIFEST.json"]
subprocess.run(['git', 'add', '--', *files], check=True)
PY
git diff --cached --check
git diff --cached --stat
git commit -m "Recover rc1 shoreline, navigation, controls and five-autosave default"
git push -u origin recovery/v0.0.25-rc1-checkpoint-006
git tag -a v0.0.25-rc1-checkpoint-006 -m "Incomplete rc1 recovery checkpoint 006"
git push origin v0.0.25-rc1-checkpoint-006
gh release create v0.0.25-rc1-checkpoint-006 --verify-tag --prerelease \
  --title 'AmiWind v0.0.25-rc1 — recovery checkpoint 006' \
  --notes-file docs/RECOVERY-v0.0.25-rc1.md \
  "$HOME/NeuralNetwork/AmiWind-v0.0.25-rc1-checkpoint-006-public-source.zip" \
  "$HOME/NeuralNetwork/AmiWind-v0.0.25-rc1-checkpoint-006-public-source.zip.sha256" \
  "$HOME/NeuralNetwork/AmiWind-v0.0.25-rc1-checkpoint-006-from-dev1-source-patch.zip" \
  "$HOME/NeuralNetwork/AmiWind-v0.0.25-rc1-checkpoint-006-from-dev1-source-patch.zip.sha256"
```

Private game data/HDFs are never included in the public release command. Future
private downloads must use ZIP wrappers of at most 150 MiB and include per-part
checksums plus reconstruction instructions.
