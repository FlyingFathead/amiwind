# BENCH-JIT-PROFILE-32: Every frame-rate and load-time figure was measured with the emulator at host speed

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | FS-UAE benchmark profile (JIT, unlimited CPU speed) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Measurement-method issue: figures are relative to a host-speed emulator. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan.

## Symptom

The playtest and benchmark profile runs FS-UAE with the JIT compiler and unlimited CPU
speed (`jit_compiler = 1`, `uae_cpu_speed = max`) on a host disk. Frame rates, crossing
times and "file reading is 80 % of a load" are therefore relative figures for that profile,
not what a 68040 at 25-40 MHz with an A1200 IDE port does; real hardware is likely far slower.

## Where

`docs/FS-UAE-PLAYTESTING.md` and every benchmark that uses that profile.

## How it happened

The fast profile made playtesting practical.

## Why it was not caught

No cycle-approximate profile or hardware number existed to compare with.

## Reproduction

Read the FS-UAE configuration used by the benchmarks.

## Repair

Not yet: a cycle-approximate (no JIT, fixed 68040 speed) benchmark profile as the relative
reference; counts (faces, fragments, spans, cache rebuilds, bytes read) as the main currency;
one disk and frame-time measurement on a real accelerated A1200.

## Verification

Pending.

## Prevention

Every performance report states its emulator profile.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions

Related bugs in other categories:

- [AUDIO-HOST-LOAD-33](AUDIO-HOST-LOAD-33.md): Music and sound crackle when the emulator shares a fully loaded host CPU

<!-- END GENERATED CATEGORY -->
