# BENCH-JIT-PROFILE-32: Every frame-rate and load-time figure was measured with the emulator at host speed

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
