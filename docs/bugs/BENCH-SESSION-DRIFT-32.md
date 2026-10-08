# BENCH-SESSION-DRIFT-32: Emulated disk time drifts about 1.6x between FS-UAE sessions

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
