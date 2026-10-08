# BENCH-FSUAE-FREQ-32: FS-UAE ignores uae_cpu_frequency in cycle-exact mode

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
