# CI-BOOTSTRAP-NUMPY-32: The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | ci |
| First noticed | 8 October 2026, in v0.0.32-pre |
| Where | tool bootstrap (tools/build.py, tools/scenery_reduce.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-pre (last seen) |
| Severity | critical: The public builder cannot bootstrap on a bare Python, failing two CI jobs. |
| Family | Gates, CI and tests (`tests-ci`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (6cb4fc4), not shipped at the time of writing.

## Symptom

GitHub CI on main 5e97310 (v0.0.32-pre) failed in two jobs: `source-and-dry-run` at "Bootstrap all
public tools into an empty directory" and `docker-builder` at "Build tools-only image and validate
the Linux container builder". `python tools/build.py --autoinstall --install-dependencies` stopped
with `ModuleNotFoundError: No module named 'numpy'` before it could install anything.

## Where

`tools/scenery_reduce.py` imported numpy at module level; `tools/build.py` imports its option
helpers while it builds the command-line parser.

## How it happened

The scenery reduction options were added to the builder's command line. The helper module also
holds the numpy mesh code, so importing the options pulled in numpy on the system Python.

## Why it was not caught

The local gate runs every check inside the finished tools environment, where numpy is installed.
Nothing ran the builder on a bare Python before the push.

## Reproduction

On a Python without numpy: `python tools/build.py --help`.

## Repair

numpy is loaded on first use in `tools/scenery_reduce.py`; the option helpers need only the
standard library.

## Verification

`tests/test_build_bootstrap_imports.py` runs `tools/build.py --help` and
`tools/build.py --install-dependencies --plan` with every third-party module blocked (standard
library and the repository's own modules only). It fails on 5e97310 with the numpy import and
passes with the repair.

## Prevention

The same test is part of the full suite, so any third-party import reached before the tools
exist fails the gate.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [GATE-EMBERS-31](GATE-EMBERS-31.md): Ember commit broke native torch tests and a header format check
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SHARED-SOURCE-32](GATE-SHARED-SOURCE-32.md): The local gate always tested the main checkout, in one shared folder
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
