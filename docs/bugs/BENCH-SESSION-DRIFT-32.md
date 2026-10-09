# BENCH-SESSION-DRIFT-32: Emulated disk time drifts about 1.6x between FS-UAE sessions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | FS-UAE disk timing across sessions |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Identical read lists take up to 1.6x longer between emulator sessions; a measurement-method issue. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open (benchmark method). Found by the CHIM world-format follow-up (branch v0.0.33-chim-format).

## Symptom

The same read lists on the same hard file took up to about 1.6 times as long in one FS-UAE session
as in another, even with the cycle-approximate 68040 profile. Even the FFS sweep's drift-control
rerun of its first variant moved random reads from 19.7 to 21.8 ms and 1 MiB skips from 5.3 to
8.6 ms.

## Where

Every FS-UAE disk timing compared across sessions.

## How it happened

Cause not measured. The host was heavily loaded by concurrent builds during these sessions (a dev1
image pass and a 16-job profiling build on the 24-thread host); host load is a likely contributor
but is unmeasured. Host storage also matters ([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)).

## Why it was not caught

Earlier comparisons were serial A/Bs in separate sessions without a drift-control rerun.

## Reproduction

Run the same `awbench replay` list in two FS-UAE sessions on the same hard file and compare the
totals.

Builds now record host load (8 October 2026, 1776e16): the build profiler stores, per stage, how
busy the whole machine was and marks stages run while other work used more than 25 % of it as
`host_busy` ([BUILD_PROFILE.md](../BUILD_PROFILE.md)). Emulator benchmark sessions do not record it
yet.

## Repair

Not yet: only same-session runs with a drift-control rerun (A, variants, A again) are compared.

## Verification

Pending: repeat on a quiet host to separate host load from emulator drift.

## Prevention

Timing runs record the concurrent host load (other containers and their CPU use) and are repeated
on a quiet host before any conclusion is drawn; every sweep includes a drift-control rerun.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed

Related bugs in other categories:

- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
