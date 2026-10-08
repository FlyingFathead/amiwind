# FFS-DIRECTORY-HASH-32: Thousands of files in one directory are slow to open on a real FFS disk

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan. First emulator measurement
8 October 2026 (CHIM world-format follow-up, branch v0.0.33-chim-format).

## Symptom

Classic FFS resolves names through 72 hash chains per directory. With thousands of maps in
`maps/`, each open walks long chains (an estimated ~135 block reads for 9,698 maps), which
costs seconds on a real disk and is invisible in the emulator.

## Where

Disk layout written by `tools/build_aga.py` (flat `maps/` directory).

## How it happened

Few maps until now.

## Why it was not caught

The emulator reads host files quickly.

## Reproduction

Count files per directory in a whole-world layout; time opens on a real FFS disk.

Measured in FS-UAE (8 October 2026): the legacy `maps/` folder holds about 2,741 entries. The same
maps loaded alone in a directory and among 2,677 dummy files: median 94 ms against 120 ms per map
load, about 20 ms extra per load from the crowded directory alone, in the emulator. A real disk is
expected to be slower per block read.

## Repair

Not yet: few large spatially ordered pack files (Quake PAK) instead of thousands of loose files.

## Verification

Pending: the emulator figure above; a real FFS disk number is still needed.

## Prevention

The builder reports files per directory with a limit (the classic FFS few-files-per-directory rule
of the disk-layout gate).
