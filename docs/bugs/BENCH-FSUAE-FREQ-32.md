# BENCH-FSUAE-FREQ-32: FS-UAE ignores uae_cpu_frequency in cycle-exact mode

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | emulator profiles in cycle-exact mode |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: A setting is silently ignored; a measurement-method issue. |
| Family | Emulator measurement method (`benchmark-method`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

In cycle-exact mode `uae_cpu_frequency` has no effect and the CPU stays at multiplier 4
(14.2 MHz); only `uae_cpu_multiplier` sets the clock (7 = 24.8 MHz).

## Where

Emulator profiles (`docs/HARDWARE-BENCHMARK.md`, FS-UAE configs).

## How it happened

Emulator behaviour, not documented where we expected.

## Why it was not caught

First cycle-exact profile.

## Reproduction

Set `uae_cpu_frequency` with `uae_cpu_cycle_exact = true` and read `awbench cpu`.

## Repair

The benchmark profile uses `uae_cpu_multiplier`; documented on the counters branch.

## Verification

Pending.

## Prevention

Profile check with `awbench cpu`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions

<!-- END GENERATED CATEGORY -->
