# BENCH-DISK-BYTES-32: FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | emulated hard disk benchmark (awbench replay in FS-UAE) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The emulator moves disk bytes far faster than real IDE, so walk read costs are only estimates. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open (benchmark method). Found by the CHIM world-format follow-up (branch v0.0.33-chim-format).

## Symptom

Emulated hard disk transfers run at about 90 MB/s, far above an A1200 IDE port. An emulator run
therefore prices seeks and AmigaDOS calls but not the bytes read, so it cannot judge CHIM against
the legacy layout over a whole walk, where CHIM reads about 1.8 times the bytes in fewer runs
([CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md)). At an assumed 2 MB/s IDE rate the Balmora walk would
take about 20.9 s with CHIM and 35.1 s with the legacy layout: an estimate, not a measurement.

## Where

`awbench replay` results in FS-UAE; the CHIM validator's read cost model.

## How it happened

The emulated hard disk is a virtual device backed by the PC's file cache.

## Why it was not caught

First whole-walk comparison of the two layouts.

## Reproduction

`awbench replay` of the walk's read list in FS-UAE: bytes per second far above any real IDE drive.

## Repair

Not yet: one `awbench replay` run of the walk on a real accelerated A1200 (see
[HARDWARE-BENCHMARK.md](../HARDWARE-BENCHMARK.md)); until then byte counts and read runs are the
currency, and any time per byte is an assumption that is labelled as one.

## Verification

Pending a hardware report.

## Prevention

Performance reports state which costs the emulator can price and mark assumed transfer rates.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions

Related bugs in other categories:

- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate

<!-- END GENERATED CATEGORY -->
