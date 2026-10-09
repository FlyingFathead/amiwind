# GATE-SHARED-SOURCE-32: The local gate always tested the main checkout, in one shared folder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Local gate runner (source staging, temp folders) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Gate tested the main checkout, not the job's branch; gates collided. |
| Family | Gates, CI and tests (`tests-ci`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Local gate fixed 8 October 2026 (the developers' integration gate runner, not part of the
repository). Found when two gates ran at the same time and one engine step failed.

## Symptom

The local integration gate (preflight, Linux suite, host parity, engine build) always staged the
main checkout into one shared source folder, whatever branch or worktree the job asked it to gate.
A job gating its own branch therefore tested the main line. Gates running at the same time
collided in the shared source folder and in fixed temporary paths: one engine step failed with
`FileExistsError`, and a stale-directory cleanup could have removed another gate's staged source in
the middle of its run.

## Where

The local gate runner (source staging, temporary folders, report header). The repository's own
tests and hosted CI are unaffected.

## How it happened

The gate was written for one developer gating one checkout at a time. Parallel jobs on their own
branches and worktrees reused it without a way to name the source.

## Why it was not caught

Gate reports did not name the repository and commit they tested, so a report for the main line
looked like a report for the branch.

## Reproduction

Run two gates at once from two worktrees on different commits with the old runner: both stage the
main checkout into the same folder.

## Repair

Local gate runner, 8 October 2026: a repository selector (`REPO`, default the main checkout), a
staged source per gate number, temporary folders per gate, a refusal to reuse a gate number, and a
header line in every report naming the repository and commit gated.

Consequence: branch gates reported earlier on 8 October 2026 from worktrees without the selector
may have tested the main line instead of the branch. Merges were gated again on the merged main
line, which is what the register's results rely on.

Follow-up 1 (8 October 2026, same day): the per-gate temporary folders were not removed when a
gate finished. About 35 MB per gate number plus older leftovers filled the build container's
512 MB temporary file system; preflight and engine steps of later gates then failed with empty
logs (exit 1 although the preflight receipt had been written). Fixed in the local gate runner:
each step removes its own temporary folders when it ends, and the gate refuses to start with less
than 150 MB free.

Follow-up 2: that first cleanup also removed the engine build folder from the preflight step
while the engine step was still compiling ("getcwd() failed"). Fixed: only the engine step owns
the engine build folder. The next full gate after the fix was green in every step.

## Verification

Two gates ran concurrently on different sources: one on the main checkout at 2935df6, one on a
worktree at b03ca3f. Each staged its own source and named it in its header. The main-line gate was
green in every step, and the worktree gate found a real problem on its branch (a version bump
without the versioned emulator templates), which the old runner would have missed by testing the
main line.

## Prevention

Every gate report is checked for the header line (repository and commit) before its result is
used; a gate number is never reused.
A gate leaves no temporary folders behind and refuses to start when the temporary file system is
nearly full.

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
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SOURCE-RACE-33](GATE-SOURCE-RACE-33.md): The local gate copies the working tree after its clean check, so edits during the copy reach the tested source
- [GATE-SUITE-WRITABLE-32](GATE-SUITE-WRITABLE-32.md): The test suite needs a writable source copy and an executable /tmp; the documented command does not say so
- LINUX-VALID-02 (no report page): Linux test fixtures failed to link (missing stubs)
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded host (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- [TEST-NATIVE-STALE-IMPORT-33](TEST-NATIVE-STALE-IMPORT-33.md): Native engine tests run alone generate their version headers with the builder image's old tools copy
- [TEST-NATIVE-TMPDIR-32](TEST-NATIVE-TMPDIR-32.md): A native test overflows a 64-byte name buffer when the temp path is long
- TEST-PORT-01 (no report page): Focused tests depended on repo root and Windows UTF-8 mode
- TEST-PORTABILITY-01 (no report page): Pre-release test fixtures assumed host features and links
- [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md): The build profile section test fails on a loaded host (CPU time read in clock ticks)
- [TEST-PROFILE-STAGE-WALL-32](TEST-PROFILE-STAGE-WALL-32.md): The build profile stage test needs an idle host (wall time compared with CPU time)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a busy host
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded host (timeline CPU above the stage's own CPU)
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
