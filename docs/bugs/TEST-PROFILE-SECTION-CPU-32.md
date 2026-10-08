# TEST-PROFILE-SECTION-CPU-32: The build profile section test fails on a loaded host (CPU time read in clock ticks)

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (test tolerance), not shipped at the time of writing. Found by
the full gate of the BUILD-EXTRA-TOWN-OPTIN-32 change while a full build was running on the same
host.

## Symptom

`tests/test_build_profile.py` `SectionTests.test_sections_are_free_without_the_builder_and_recorded_with_it`
fails with "0.08 not greater than 0.08": two calls of a section that each burn 0.05 s of CPU
(`time.process_time`) are recorded as 0.08 s.

## Where

The test's assertion `cpu_self > 0.08`; `tools/build_profile.py` records section CPU with
`os.times()`.

## How it happened

`os.times()` reports CPU time in whole clock ticks (10 ms at the usual 100 Hz), and the kernel
divides a process's CPU time into user and system time lazily, while `time.process_time()` reads
the exact CPU clock. Each section reading can lose about a tick, so two 0.05 s calls can read
0.08 s; under load this happens.

## Why it was not caught

The test passed on idle hosts; the gate host was busy with a full build (about 18 cores in use).

## Reproduction

Run the full suite while the host is under heavy load; the assertion fails intermittently.

## Repair

The test checks that the section recorded the work (at least 0.05 s of the 0.1 s burnt), not a
tick-exact value. The profiler itself is unchanged: section CPU is a measurement for reports,
accurate to the clock tick.

## Verification

The same test passes in the full gate of the change that found it; the other section checks
(calls, depth, wall time, child CPU, errors) are unchanged.

## Prevention

Timing assertions in tests allow for the resolution of the clock they read (`os.times()`: one
tick per reading).
