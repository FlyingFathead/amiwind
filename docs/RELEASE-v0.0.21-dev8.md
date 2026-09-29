# AmiWind v0.0.21-dev8 - reconciled boot/launcher and paper-font sources

This source prerelease merges the owner's dev7 snapshot with paper-font checkpoint
002. It is not the still-pending whole-pipeline parallelization update.

## Included

The dev7 boot checker, FS-UAE launcher, dry-run builder and version generator are
preserved byte-for-byte. Root VERSION now produces dev8 identities when rebuilt.
The successful preflight countdown and Space/Enter skip, plus the dry-run order
`FailAt 10`, `AmiWindCheck`, `AmiWindDryRun`, remain the dev7 implementation.

TTF stays preferred. Without a usable TTF, the approved bitmap paper candidate
is the default. `--bitmap-paper-ink original` restores the prior appearance.
`config/build-defaults.json` and `--build-config FILE` support persistent choices;
CLI overrides the selected config. Dialogue/menu fonts are unchanged, including
small character UI. Paper uses its own optional cache and safe fallback.
See [paper font options](PAPER_FONT_OPTIONS.md).

The host CPU helper now catches a failed process CPU-count query and continues
with remaining limits. No geometry algorithm, gameplay or save format is changed.

## Validation

See MERGE-v0.0.21-dev8.md for the exact source inputs, preserved-file hashes and
validation results. The owner-side apply/release helper requires a passing full
host test suite with the normal installed build dependencies before publication.
There is no new Amiga cross-compile, HDF, emulator session or hardware test in this
source delivery. The owner's successful dev5 Steam build is historical evidence,
not dev8 native acceptance.

## Preserved diagnostic limitations

The uploaded checker has real conditional pass/fail checks; it is not an
unconditional success screen. Its Fast RAM success label does not independently
prove Z3 bus or address-width properties. The launcher's JIT setting reports
configuration intent, not runtime activation. Neither startup check establishes
gameplay stability or performance. These boot/launcher source files were not
changed by the paper-font merge.

Only the public source ZIPs and their checksums belong on the GitHub prerelease.
No game data, reusable fonts, ROMs or private playable images are included.
