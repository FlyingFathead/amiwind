# GATE-EMBERS-31: ember commit broke native torch tests and a header format check

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:preflight |
| First noticed | 7 October 2026, in v0.0.31-dev1 |
| Where | Engine header d_iface.h and native torch test fixtures |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.31-dev1 |
| Severity | low: Gate and test failures; the game is unaffected. |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | v0.0.31-dev1 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Repaired in source before v0.0.31-dev1 was packaged. Never shipped; found by
the release gates on the development branch.

## Symptom

The v0.0.31-dev1 gates failed in two places:

- Preflight: `engine/aga/src/d_iface.h:230: blank line at EOF`, then, once
  that was removed, trailing whitespace at line 125.
- Linux suite: three native torch tests did not link
  (`test_guard_torches_source_registry_cycle_pose_lights_and_depth`,
  `test_torch_controls_bounded_light_surface_illumination_and_overlay`,
  `test_guard_diagnostics_distinguish_flames_from_admitted_lights`), with
  undefined references to `host_frametime` and `AW_EmberSpawn`.

The engine build itself was clean (zero warnings) and the host-parity tests
passed.

## Where

`engine/aga/src/d_iface.h` (particle type list) and the native test fixtures
`tests/aga_guard_torch_test.c` and `tests/aga_torch_test.c`. The game is
unaffected.

## How it happened

The torch-ember change added the `pt_awember` particle type, left an extra
blank line at the end of `d_iface.h`, and made `aw_torch.c` and
`aw_guard_torch.c` call `AW_EmberSpawn` (in `r_part.c`) at a rate scaled by
`host_frametime` (in `host.c`). The native fixtures compile those two files
on their own with test stand-ins for everything else, and had no stand-ins
for the two new symbols.

`d_iface.h` is an original Quake header. Its blank last line and three
trailing spaces in comments come from the original source; the preflight
accepts unchanged historical files byte for byte, but checks every changed
file in full, so editing the header made its old formatting count.

## Why it was not caught

The ember change was verified with full engine builds and in-game clips, and
was committed before the full gate set ran on it. The gates ran only at the
dev1 version bump.

## Reproduction

Run the full Linux suite on the ember commit: the three tests fail to link.
Run the preflight on it: the format check reports the blank line.

## Repair

The two fixtures define `host_frametime` (left at zero, so no embers spawn and
the fixtures' expected results are unchanged) and a no-op `AW_EmberSpawn`.
The header's blank last line and the trailing spaces in three comment lines
are removed (no code change).

## Verification

Preflight, the full Linux suite, the host-parity tests (Linux and Windows) and
the zero-warning engine build pass on the repaired source.

## Prevention

Engine changes that add calls across source files run the full gate set
before they are committed, not only at the version bump.

While recording this bug, its own report page was first left out of
`tools/release-files.json`, so the format preflight did not check it and the
release would have shipped a register link to a missing page. The bug-tracker
test now also requires every tracker file to be in that list.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
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
