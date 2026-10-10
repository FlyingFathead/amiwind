# CI-NEW-BUILDER-RULES-35: Hosted CI failed on v0.0.35 under two new builder rules

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | ci |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | tools/previous_release.py; tools/build_docker.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.35 |
| Severity | high: blocks the release (no tag or release while CI is red) |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine aefcdb5 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in v0.0.35 in two repair commits. The first repair (e0d5984) fixed the two failures below; its CI run then
failed a third time on the same naming rule: the engine step runs `build.py --dry-run --name ci`. The second repair
makes the naming rule strict only for developer-mode builds; a dry run, CI and public users following the docs
(`--name first-town`) get the loud warning instead.

## Symptom

The pushed v0.0.35 commit failed hosted CI in two jobs. `source-and-dry-run` stopped after 7 seconds:
"the published v0.0.34 commit b336341 is not in this repository". `docker-builder` stopped on
"--name 'docker-ci-...' does not contain the source version 0.0.35".

## Where

`tools/previous_release.py` (ancestry check) and `tools/build_docker.py` (the Docker check's run name).

## How it happened

Hosted CI checks out one commit without history, so the published parent cannot be found; the check
treated that as a missing release. The new run-name rule refused the Docker check's own generated name.

## Why it was not caught

The first repair fixed the one caller the CI log showed instead of sweeping every caller of the rule;
the sweep afterwards found CI's dry run and the public docs' examples.

The local gate and the release suite run on full clones and never on a one-commit checkout, and the
Docker check's name is only built inside the hosted job.

## Reproduction

`git clone --depth 1` of a release commit, then `python tools/build.py --autoinstall --yes`.

## Repair

A one-commit checkout (no `HEAD^`) leaves the ancestry check to the release gate with a note, as a tree
without git does. The Docker check passes `--any-run-name`. The naming rule refuses only developer-mode image builds
(`build.run_name_lenient`); everyone else gets a warning.

## Verification

`tests/test_previous_release.py` (shallow checkout) and `tests/test_build_docker.py` (run name); hosted CI.

## Prevention

Both regression tests; the release flow's CI run stays the final check before any tag.

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
- [TEST-PROFILE-STAGE-WALL-32](TEST-PROFILE-STAGE-WALL-32.md): The build profile stage test needs an idle host (wall time compared with CPU time)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a busy host
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded host (timeline CPU above the stage's own CPU)
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
