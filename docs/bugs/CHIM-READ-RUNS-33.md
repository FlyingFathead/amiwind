# CHIM-READ-RUNS-33: CHIM crossings read little but in many separate runs, so FFS seeks dominate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | CHIM model pack order and world format |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Crossings read little but in many runs, so FFS seeks dominate load time. |
| Family | Loading and disk reads (`disk-loading`) |
| CHIM | World format ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine unknown, world format unknown |
| Unknown because | registered before found-in-build records existed; found on a CHIM development branch, the finding commit and world format were not recorded |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the first CHIM world-format build of Balmora (branch v0.0.33-chim-format, format 0.1).

Note (8 October 2026): the 36 ms per random seek quoted below came from a hard file in a Windows
folder shared into the container; on container-native storage it is about 18-21 ms
([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)). The emulator also cannot price the bytes read
([BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md)), so CHIM against the legacy layout over a whole
walk needs a hardware `awbench replay`.

## Symptom

A Balmora street crossing reads a median 277 KB (max 1.81 MB) instead of 4.43 MB, but in 24 separate
runs (median; up to 63) because newly needed models are scattered through the model pack. At the
measured 36 ms per random FFS seek (STREAM-FFS-SEEK-32) that is about 0.9 s per crossing, worse than
today's single 4.4 MB read (about 0.26 s at 17 MB/s).

## Where

CHIM model pack order (`tools/chim/`), `docs/chim/WORLD_FORMAT.md`.

## How it happened

Models are stored once, in mesh order, not in the order a walk needs them.

## Why it was not caught

First measurement of the format.

## Reproduction

The CHIM builder's crossing walk report for Balmora.

World format 0.2 (8 October 2026, branch v0.0.33-chim-format): one file per 3x3-chunk sector, each
model and texture stored once in the first sector that needs it. Balmora walk (70 doors, 83
crossings), estimated with a cost model fitted to FS-UAE FFS measurements (cycle-approximate 68040,
relative): median 4 / 3 / 3 read runs per crossing with 0 / 1 / 2 MiB extra cache (format 0.1: 11 /
9 / 6.5; today 1), median 32 / 16 / 11 ms per crossing (today 287 ms), largest 220 / 204 / 204 ms,
whole walk 4.2 / 3.3 / 2.7 s (today 4.8 s). Cost: about 1.2 MB more resident at peak and about 1.8x
the bytes read; entering the town cold reads 3.5 MB (about 247 ms). The cost model is not yet
checked against real reads (an `awbench` replay of the walk is next).

## Repair

Not yet: measure short forward seeks on FFS (emulator and hardware), then store models per frame in
first-need order (still once), read through small gaps, and prefetch ahead of the player.

## Verification

Pending.

## Prevention

Read runs per crossing in the validator report, with a limit.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS

<!-- END GENERATED CATEGORY -->
