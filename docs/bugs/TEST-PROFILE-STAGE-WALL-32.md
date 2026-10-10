# TEST-PROFILE-STAGE-WALL-32: The build profile stage test needs an idle host (wall time compared with CPU time)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:local-full |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | tests/test_build_profile.py stage CPU and wall time assertion |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.32-dev, v0.0.32 (last seen) |
| Severity | low: A false gate failure; no build or game effect. |
| Family | Gates, CI and tests (`tests-ci`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on v0.0.33-doc-toc (1d7b743), not shipped at the time of writing.

Update 9 October 2026: not cleared under full host load. Gate 448 (v0.0.33-miniwind 76a324f) failed
`test_cpu_and_wall_of_a_stage_and_all_its_children`: the children's CPU 2.20 s against the stage's
own 2.12 s plus the 0.1 s tolerance, while two builds used every core. Isolated reruns on the same
host failed 2 of 3. The test still depends on host load.

## Symptom

The full gate failed one test: "2.06 not less than 1.936", the assertion
`burn['wall'] < burn['cpu']`. The next gate on the same commit passed.

## Where

The test runs a stage that starts three children, each burning 0.6 s of CPU, and checks the
profile the builder records for it.

## How it happened

The test checked that the profiler counts the children's CPU by expecting the children to run
at the same time: wall time below CPU time, more than 1.2 cores on average, more than 1.5 cores in
one timeline sample. Whether they run at the same time is up to the host. On a busy host they
share fewer cores, so the stage's wall time exceeds its CPU time although every number recorded
was right (1.936 s of CPU is three children at 0.6 s plus interpreter start-ups).

## Why it was not caught

The test passed on idle hosts. Gates usually run beside other work, but this one ran while
other jobs held the host at 100 %.

## Reproduction

`docker run --cpus 2` with eight `while True: pass` loops, then the test: before the repair
5 of 5 runs failed ("4.291 not less than 1.865" and similar).

## Repair

The test compares the profiler with independent readings of the same stage instead of with how
well the host overlapped the children:

- CPU: the stage writes its own `getrusage` (itself plus its waited-for children); the
  profiler's CPU must match it within 0.1 s, and lie between 1.7 and 2.8 s.
- Wall: at least the span the stage itself saw and at least 0.6 s, at most the time measured
  around the whole run.
- `cores_avg`: CPU divided by wall.
- Timeline: summed over the samples, more than 1.0 s of CPU and no more than the stage's CPU.
  No single sample may hold half of it, so a sampler that misses live children (and sees their
  CPU in one jump when they are reaped) still fails.

## Verification

Same container, 2 CPUs, 8 busy loops: the repaired test passes 10 of 10 runs. With a mutated
profiler whose sampler ignores child processes, it fails 3 of 3 ("1.85 not less than 0.94"). The
whole module passes on an idle container. Full gate on the branch.

## Prevention

Timing tests compare a measurement with an independent reading of the same work, not with the
parallelism a host happens to give. Same family: [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- [GATE-EMBERS-31](GATE-EMBERS-31.md): Ember commit broke native torch tests and a header format check
- [GATE-HOSTPARITY-TEMP-RACE-33](GATE-HOSTPARITY-TEMP-RACE-33.md): Two gates running at once share the host-parity step's log file, so one gate can report the other's error
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-NUMPY-PATH-SCRATCH-33](GATE-NUMPY-PATH-SCRATCH-33.md): The gate's NumPy and Pillow import folder lived in a temporary per-session folder, so gates broke once it was removed
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SHARED-SOURCE-32](GATE-SHARED-SOURCE-32.md): The local gate always tested the main checkout, in one shared folder
- [GATE-SOURCE-RACE-33](GATE-SOURCE-RACE-33.md): The local gate copies the working tree after its clean check, so edits during the copy reach the tested source
- [GATE-SUITE-WRITABLE-32](GATE-SUITE-WRITABLE-32.md): The test suite needs a writable source copy and an executable /tmp; the documented command does not say so
- LINUX-VALID-02 (no report page): Linux test fixtures failed to link (missing stubs)
- [MWAD-TEXT-WRITER-LF-35](MWAD-TEXT-WRITER-LF-35.md): Some JSON and text writers do not pin LF and UTF-8
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [TEST-CHIM-BIG-FRAME-TIMEOUT-33](TEST-CHIM-BIG-FRAME-TIMEOUT-33.md): The Balmora-sized CHIM world test times out on a busy host
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded host (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- [TEST-NATIVE-STALE-IMPORT-33](TEST-NATIVE-STALE-IMPORT-33.md): Native engine tests run alone generate their version headers with the builder image's old tools copy
- [TEST-NATIVE-TMPDIR-32](TEST-NATIVE-TMPDIR-32.md): A native test overflows a 64-byte name buffer when the temp path is long
- [TEST-PARALLEL-ORDER-LOAD-33](TEST-PARALLEL-ORDER-LOAD-33.md): The process-pool order test fails on a fully loaded host (one worker process takes every item)
- TEST-PORT-01 (no report page): Focused tests depended on repo root and Windows UTF-8 mode
- TEST-PORTABILITY-01 (no report page): Pre-release test fixtures assumed host features and links
- [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md): The build profile section test fails on a loaded host (CPU time read in clock ticks)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a busy host
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded host (timeline CPU above the stage's own CPU)
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
