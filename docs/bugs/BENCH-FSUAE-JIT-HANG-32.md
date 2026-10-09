# BENCH-FSUAE-JIT-HANG-32: An FS-UAE JIT session hung with a Windows-folder hard file mounted

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | FS-UAE JIT session with a host-folder hard file |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Seen once in a benchmark sweep; cause unknown. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Cause unknown. Found by the CHIM world-format follow-up (FFS sweep, branch
v0.0.33-chim-format).

## Symptom

One FS-UAE session with the JIT profile stopped making progress for at least 10 minutes while a
hard file in a Windows folder shared into the container was mounted; one row of the JIT table was
left incomplete.

## Where

FS-UAE with the JIT profile; hard file on host storage shared from Windows.

## How it happened

Unknown. Seen once.

## Why it was not caught

First JIT run of the sweep with that hard file.

## Reproduction

Not yet reproduced: rerun the JIT seek sweep with the hard file in a Windows folder, then on a
Docker volume.

## Repair

Not yet. Disk timings use container-native storage anyway
([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)).

## Verification

Pending.

## Prevention

Benchmark sessions have a time limit and report a stalled session instead of waiting.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions

<!-- END GENERATED CATEGORY -->
