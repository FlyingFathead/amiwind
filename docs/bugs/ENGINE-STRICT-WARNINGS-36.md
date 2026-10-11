# ENGINE-STRICT-WARNINGS-36: The engine builds warning-free only under -Wall -Wno-unused; stricter flags show 482 warnings

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/src (view.c 35, chim/chim_world.c 18, ...); engine/aga/Makefile WARN_FLAGS |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | medium: uninitialised, shadowed and unused code can hide real faults that the gate cannot see |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | v0.0.36-dev3 |
| From commit | source 3b5e7a9, engine 3b5e7a9, CHIM world 3b5e7a9 |
| CHIM engine version | CHIM 0.1.0, engine 3b5e7a9, world format 0.7 |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Open. Planned repair below. No earlier register entry covers compiler warnings beyond the gate's flags, so this is a
first report.

## Symptom

The engine gate builds with `-Wall -Wno-unused` and requires zero warnings. A diagnostic build of c8bf614 (the
v0.0.36-dev3 line) with `-Wall -Wextra -Wuninitialized -Wmaybe-uninitialized -Wmissing-field-initializers -Wshadow
-Wunused` at the same -O1 shows 482 distinct warnings. Among the files changed since v0.0.35: view.c 35,
chim/chim_world.c 18, sv_phys.c 5, chim/chim_far.c 5, aw_music.c 2, and one each in sv_main.c, chim/chim_models.c,
chim/chim_graft.c and chim/chim_chunks.c. None in aw_aread.c, where the dev3 crash was.

## Where

`engine/aga/Makefile` (`WARN_FLAGS = -Wall -Wno-unused`) and the engine sources.

## How it happened

The zero-warnings rule was enforced only for the flags the gate uses; stricter warnings were never looked at.

## Why it was not caught

The gate's flags hide unused, shadowed and possibly uninitialised variables, and missing field initialisers.

## Reproduction

Build the engine with the flags above (`make -B fpu WARN_FLAGS="..."`) and count the `: warning:` lines. The full list
of the diagnostic build is kept with the private evidence of the dev3 crash investigation.

## Repair

Planned (checklist T10): fix every warning (uninitialised and shadowed variables first), then raise the gate's
`WARN_FLAGS` so the stricter set stays at zero; one change per file group, each gated.

## Verification

Open.

## Prevention

The raised gate flags keep it at zero.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- [AW-RESULT-RECIPE-SAVED-36](AW-RESULT-RECIPE-SAVED-36.md): The master builder's result of a failed build from a requested recipe does not validate (recipe.saved left in)
- [AW-RUN-NAME-LONG-REASON-36](AW-RUN-NAME-LONG-REASON-36.md): aw gate refuses a long --reason after leasing the gate number: the run name, used as the request id, passes 128 characters
- [BUILD-EXECUTABLES-LIST-UNGATED-36](BUILD-EXECUTABLES-LIST-UNGATED-36.md): A file committed executable but missing from tools/release.py EXECUTABLES (tools/engine_smoke.py) broke the source ZIP only at kit time
- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-NEW-BUILDER-RULES-35](CI-NEW-BUILDER-RULES-35.md): Hosted CI failed on v0.0.35: the previous-release check refused the one-commit checkout and the run-name rule refused the Docker check's run name
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies
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
- [OPS-GATE-UNLISTED-TESTS-36](OPS-GATE-UNLISTED-TESTS-36.md): The gate runs only the tests listed in the public file list, and nothing checked that every test file is listed
- [PLAYTEST-SHIPPED-WITHOUT-SMOKE-36](PLAYTEST-SHIPPED-WITHOUT-SMOKE-36.md): The v0.0.36-dev3 private playtest package was published with an engine that dies on every map load: no ship step or gate booted it
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [SMOKE-PASSES-WITHOUT-MAP-36](SMOKE-PASSES-WITHOUT-MAP-36.md): The engine boot smoke passed while its first map ran under the title menu: a loaded server was taken for a played map
- [TEST-CHIM-BIG-FRAME-TIMEOUT-33](TEST-CHIM-BIG-FRAME-TIMEOUT-33.md): The Balmora-sized CHIM world test times out on a busy host
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded host (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- [TEST-GODMODE-UNLISTED-36](TEST-GODMODE-UNLISTED-36.md): The dbg godmode test was never run by the gate (missing from the public file list) and its escape check failed
- [TEST-NATIVE-STALE-IMPORT-33](TEST-NATIVE-STALE-IMPORT-33.md): Native engine tests run alone generate their version headers with the builder image's old tools copy
- [TEST-NATIVE-TMPDIR-32](TEST-NATIVE-TMPDIR-32.md): A native test overflows a 64-byte name buffer when the temp path is long
- [TEST-PARALLEL-ORDER-FLAKY-36](TEST-PARALLEL-ORDER-FLAKY-36.md): test_processes_keep_order_and_limit_nested_threads is timing-sensitive and fails now and then
- [TEST-PARALLEL-ORDER-LOAD-33](TEST-PARALLEL-ORDER-LOAD-33.md): The process-pool order test fails on a fully loaded host (one worker process takes every item)
- [TEST-PARALLEL-SHARE-TIMING-36](TEST-PARALLEL-SHARE-TIMING-36.md): The fair-share scheduler test watched the freed budget for a fixed 4 s and failed on a busy host
- TEST-PORT-01 (no report page): Focused tests depended on repo root and Windows UTF-8 mode
- TEST-PORTABILITY-01 (no report page): Pre-release test fixtures assumed host features and links
- [TEST-PROFILE-OVERHEAD-SAMPLES-36](TEST-PROFILE-OVERHEAD-SAMPLES-36.md): The profiler overhead test sampled for a fixed 2 s and got too few samples on a busy host
- [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md): The build profile section test fails on a loaded host (CPU time read in clock ticks)
- [TEST-PROFILE-STAGE-WALL-32](TEST-PROFILE-STAGE-WALL-32.md): The build profile stage test needs an idle host (wall time compared with CPU time)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a busy host
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded host (timeline CPU above the stage's own CPU)
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
