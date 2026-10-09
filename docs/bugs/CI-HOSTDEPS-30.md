# CI-HOSTDEPS-30: host CI job failed on a NIF-reader dependency

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | ci |
| First noticed | 7 October 2026, in v0.0.30 |
| Where | host CI job host-launcher-parity (tools/prepare_scenery.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.30 (last seen) |
| Severity | medium: Hosted CI job failed on the first v0.0.30 push; game unaffected, fixed before tagging. |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | v0.0.30 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Fixed in source after the first v0.0.30 push; ships in the v0.0.30 release
commit. The first push was not tagged or released.

## Symptom

The hosted CI job `host-launcher-parity` failed on Ubuntu 24.04 (Windows was
cancelled with it) for the first v0.0.30 push: `test_host_asset_formats`
stopped with `ModuleNotFoundError: No module named 'pyffi'`.

## Where

`tools/prepare_scenery.py`, `export_refs`. The game, the maps and the engine
are unaffected.

## How it happened

v0.0.30-dev5 added flame extraction (`model_flames`) to the scenery export.
It asked for the NIF reader (`pyffi`) for every exported model. The host test
feeds `export_refs` a synthetic model that is not a NIF, and the host CI job
installs only `numpy` and `Pillow`, so importing the reader failed.

## Why it was not caught

The local gates run the full suite in the complete tools environment, where
`pyffi` is installed. Nothing ran the host-parity tests with the hosted job's
reduced dependency set before pushing.

## Reproduction

A fresh Python 3.12 virtual environment with only `numpy` and `Pillow`:
`python -B -m unittest discover -s tests -p test_host_asset_formats.py` fails
with the same error before the repair.

## Repair

Flames are read only from real NIF data (files starting with
`NetImmerse File Format`); real conversions are unchanged and still require
the NIF reader. The four host-parity test files pass in the reduced
environment on Linux and natively on Windows.

## Verification

The four host-parity test files (`test_build_host.py`, `test_build_windows*.py`,
`test_setup_windows.py`, `test_host_asset_formats.py`) pass with only
`numpy` and `Pillow` installed, and in the full Linux suite.

## Prevention

Every handoff now also runs the hosted CI job's host-parity tests in a fresh
environment with only that job's dependencies, on Linux and on Windows, before
the transfer kit is built.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
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
