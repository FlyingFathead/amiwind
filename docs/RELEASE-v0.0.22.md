# AmiWind v0.0.22 - normal public source release

v0.0.22 promotes the reconciled v0.0.21-dev8 source checkpoint to a normal GitHub
release. It is a version/publication promotion, not a new gameplay checkpoint.

## Included

- The reconciled dev8 boot checker, FS-UAE launcher, dry-run builder and version
  generator are carried forward unchanged apart from generated version identity.
- TTF remains the preferred paper-font source. When a usable TTF is unavailable,
  bitmap-derived paper text uses the approved stronger ink treatment by default;
  `--bitmap-paper-ink original` restores the previous bitmap appearance.
- Dialogue/menu fonts remain unchanged.
- Automatic CPU-count detection retains the dev8 exception handling fix.
- GOG GOTY remains the preferred Morrowind source installation; Steam GOTY remains
  supported through the documented bitmap-font fallback when required inputs pass
  validation.

## Validation and limits

Publication must pass the complete host test suite, `tools/release.py --check`,
`git diff --check`, source-package validation and downloaded GitHub-asset checksum
verification. The publication helper performs those checks before/after release.

This promotion does not claim a new HDF, Amiga cross-compile, emulator playtest or
physical-hardware test. The successful Steam GOTY dev5 build remains historical
compatibility evidence. Whole-pipeline parallelization remains future work.

Only public source ZIPs and checksum sidecars belong on the GitHub release. Original
Morrowind data, converted assets, ROMs and private playable images remain private.
