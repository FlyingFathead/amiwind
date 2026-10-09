# BENCH-AWBENCH-BUFFERS-32: awbench reported the stale buffer count after AddBuffers

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Benchmark tool awbench (engine/aga/bench/awbench.c), buffers mode |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Tool reports a stale buffer count; measurement tooling. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed on the CHIM branch (v0.0.33-chim-format, commit 66d316b), not merged into the v0.0.32
development line.

## Symptom

The first `awbench buffers` read the buffer count from the drive's mount entry, which AmigaDOS
`AddBuffers` does not update, so it reported the old value after a change.

## Where

`engine/aga/bench/awbench.c`, `buffers` mode.

## How it happened

The mount entry holds the boot-time value; the file system keeps the live count itself.

## Why it was not caught

First use of `awbench buffers`.

## Reproduction

`awbench buffers DW1: 100`, then compare the reported `after=` value with the count the file system
uses.

## Repair

On the CHIM branch (66d316b): `awbench buffers` reports the count returned by `AddBuffers` itself.

## Verification

FFS sweep on the CHIM branch (30, 50 and 100 buffers in one session).

## Prevention

Merge with the CHIM branch; the benchmark output records `before`, `want`, `result` and `after`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions

Related bugs in other categories:

- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type

<!-- END GENERATED CATEGORY -->
