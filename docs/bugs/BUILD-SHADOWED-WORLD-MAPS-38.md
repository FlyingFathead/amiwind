# BUILD-SHADOWED-WORLD-MAPS-38: Full image retains shadowed exterior BSP maps

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | Final image world routing and exterior BSP payload |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | medium: Unused exterior payload may remain despite the used-map-only build requirement. |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | none |
| From commit | source and engine 4772bff |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Offline final-image routing and payload dependency audit; not an emulator finding.) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Full-image catalogue failure, 13 October 2026](#full-image-catalogue-failure-13-october-2026)
- [Prevention](#prevention)
- [Pre-conversion ownership checklist, 13 October 2026](#pre-conversion-ownership-checklist-13-october-2026)
- [Pre-frame scene classification, 13 October 2026](#pre-frame-scene-classification-13-october-2026)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

A final-image routing audit flags 135 retained exterior BSP maps whose complete core rectangles are covered by higher-priority town or region routes.

## Where

The full v0.0.38 image, world region directory and exterior map payload.

## How it happened

Current cleanup removes named town chains and same-name CHIM replacements. It does not prove that every remaining exterior core has reachable space after town and region routing priority is applied. Exact retention dependencies remain under investigation.

## Why it was not caught

The earlier check proved absence of same-name BSP/CHIM duplicates. That does not establish reachability of every other legacy world map.

## Reproduction

Read the packaged world directory and map inventory. Subtract higher-priority town and region rectangles from each legacy map core in runtime order. Compare empty residual areas with maps still present in the payload.

## Repair

Candidate: normal CHIM image assembly now subtracts higher-priority runtime cores and removes fully shadowed legacy BSPs only after checking metadata, entity lumps and included save files for explicit dependencies. Partial cores and CHIM frames remain. Every removal records size, hash and reason; dependencies record retention reasons. Directory indices and metadata remain unchanged. External saves from older builds are not migrated: the existing scene loader refuses unavailable saved scenes. Direct debug loading of retired legacy maps is no longer supported; coordinate teleports resolve the active owner.

## Verification

Exact HDF readback and hash verification cover the map entity lumps and configuration metadata. All 135 flagged maps have no explicit payload dependency, totaling 141,790,676 bytes. Four Docker regressions pass: half-open boundaries and partial cores, direct door retention, entity references and CHIM frames with legacy extensions, and malformed-map refusal before removal. The full gate then caught direct frame-path construction in the candidate helper. It now uses the canonical map resolver; all eleven map-helper tests pass. The superseded build was stopped before image assembly. Fresh image readback and native boundary routing remain pending. No repaired package has been delivered.

## Full-image catalogue failure, 13 October 2026

The first complete image using pruning failed before HDF creation: `Harvest catalogue has no matching map: harvest-vf0302.txt`. Pruning removed maps but retained their map-named harvest files. The heap audit calls the shared catalogue validator without the fingerprint step's removal list, so it correctly rejected that orphan. Earlier payload fixtures had no harvest catalogues and missed the integration.

The candidate removes and hashes each unused map catalogue together with its fully shadowed map, using the same retirement rule as existing regional CHIM replacement. `aw_harvest_runtime.c` loads catalogues by active map or town-region name; town-region tables remain explicit retention dependencies. A regression now passes the pruned fixture through the real harvest fingerprint validator while preserving partial-core and referenced catalogues. No engine behavior is changed. Rebuilt image and native verification remain pending.

## Prevention

Extend the final payload check beyond duplicate filenames to runtime reachability, with explicit retention reasons for any compatibility requirement. Reuse the town-first and then region-order logic in aw_world.c; no engine change is established.


## Pre-conversion ownership checklist, 13 October 2026

The final-image cleanup alone does not prevent wasted conversion. The dev1 candidate inventories every original exterior CELL and height-bearing LAND record before any build stage and records its BSP or CHIM owner. Town cores follow the existing town-first routing rectangles in `aw_world.c`; partial cells explicitly keep their required BSP remainder and rendering apron. Selected CHIM regions are unchanged from the chosen build recipe.

Terrain resolves each subdivided map against that checklist before invoking a compiler. Fully town-owned cores retain their stable directory IDs but produce no legacy BSP. Scenery and flora take the same checklist, verify it against the terrain receipt, and skip those cores too. Missing placements are allowed only where their source positions belong to CHIM; an outside placement still fails coverage. Interiors are absent from this exterior ownership calculation.

This candidate is under test. It does not establish a newly packaged or native-accepted world. The v0.0.38 release build continues from its separately pinned source.


Read-only comparison against the v0.0.38 selection and survey accounts for 1,404 exterior cells: 360 regional CHIM cells, 26 fully town-owned cells and 1,018 cells with required BSP space. The subdivided work list has 465 CHIM rows, 135 town-owned routing-only rows and 1,953 BSP rows. The 135 skipped maps match the prior dependency-reviewed retirement list exactly, with zero unexpected or missed exclusions. Twenty planner/scheduling tests pass, including a compiler-call spy proving only the required BSP row is compiled. Final candidate image acceptance remains separate.

## Pre-frame scene classification, 13 October 2026

13 October 2026: RC1 finalization still demanded the 135 intentionally uncompiled town-owned exterior maps during sky preparation. The shared sky, cull, hand-metadata, always-included and night-lighting classifier now excludes only checklist-validated omissions, bound to the validated CHIM town plan before frame generation. Other missing maps still fail. Final fingerprint and packing still require actual CHIM owner frames. Engine and converted content are unchanged; exact-image checks remain required.

The integration regression uses the real checklist and omission validator. It checks the absent owner frame before generation, rejection of an unplanned owner and continued rejection of a genuinely missing required BSP.

## Exact RC1 evidence, 13 October 2026

The exact RC1 image and independently extracted package contain 360 verified
whole regional cells, including Tel Uvirith (10,1). Six selected cells
(-3,-11), (-2,-11), (-1,-11), (0,-11), (5,-14) and (6,-14) overlap packaged
town frames only partially and are excluded from that whole-cell count.
All 9,360 frame/chunk files for the 360 cells and all 9,774 CHIM payload files
remain byte-identical to the verified predecessor. The index and four named
town frame maps are present; town coverage and interiors are separate counts.
The 135 town-owned routing-only BSPs are absent under the validated checklist;
required map/dependency readback passed. Native boundary routing remains open.

The exact HDF comparison removes 142,235,493 payload bytes across 212 files:
135 redundant BSP maps and 77 orphan harvest catalogues. No map additions or
unexpected map removals are reported. The independently extracted RC1
playtest ZIP is 2,060,379,345 bytes. Payload savings and compressed archive
size are distinct measurements; these figures do not identify a final039 ZIP.

RC1 package and matching source delivery finalized on 13 October 2026 at
18:06:05 UTC (21:06 in Finland), with source `57a8699` and image `fbf9a6c`
kept distinct. The six partial overlaps remain outside the shipped whole-cell
count. Final v0.0.39 remains in preparation pending explicit owner inspection
approval; RC1 shipment does not supply owner or universal gameplay acceptance.

Conversion/audit data is the unchanged 13 October 2026, 14:04:49 UTC snapshot:
1,190 converted cells including 15 failed audits, 99 empty sea, three not
converted, and 1,274/1,292 audit milestones. The package layer was reconciled
at 17:45 UTC and its local served data was read back. The 865 ocean cells are
outside the denominator. Converted and packaged per-type actor/gameplay
counts remain unknown; the original reference census is preserved. Planned
cells are not included cells and package presence does not prove gameplay.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- [AW-RESULT-RECIPE-SAVED-36](AW-RESULT-RECIPE-SAVED-36.md): The master builder's result of a failed build from a requested recipe does not validate (recipe.saved left in)
- [AW-RUN-NAME-LONG-REASON-36](AW-RUN-NAME-LONG-REASON-36.md): aw gate refuses a long --reason after leasing the gate number: the run name, used as the request id, passes 128 characters
- [BUILD-CHECKLIST-JSON-CELLS-39](BUILD-CHECKLIST-JSON-CELLS-39.md): Exterior checklist rejects JSON cell coordinates before scenery conversion
- [BUILD-DEV1-EMULATOR-PRESETS-39](BUILD-DEV1-EMULATOR-PRESETS-39.md): Version bump omitted the matching dev1 emulator presets
- [BUILD-EMPTY-ACTOR-GATE-38](BUILD-EMPTY-ACTOR-GATE-38.md): Actor contact gate rejects a MiniWind exterior without residents
- [BUILD-EMPTY-RESIDENT-POOL-38](BUILD-EMPTY-RESIDENT-POOL-38.md): Town conversion starts a zero-worker pool when no residents are present
- [BUILD-EXECUTABLES-LIST-UNGATED-36](BUILD-EXECUTABLES-LIST-UNGATED-36.md): A file committed executable but missing from tools/release.py EXECUTABLES (tools/engine_smoke.py) broke the source ZIP only at kit time
- [BUILD-LAVA-CORE-BOUNDS-38](BUILD-LAVA-CORE-BOUNDS-38.md): Lava sandbox bounds are not divisible by its core size
- [BUILD-LAVA-PRESET-FIXTURE-38](BUILD-LAVA-PRESET-FIXTURE-38.md): Lava sandbox addition omitted the preset inventory fixture
- [BUILD-VERSION-EMULATOR-PRESETS-38](BUILD-VERSION-EMULATOR-PRESETS-38.md): Version bump omitted matching emulator presets
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](BUILD-WORLD-FINGERPRINT-RETIRED-38.md): Content fingerprint requires an explicitly retired exterior BSP
- [BUILD-WORLD-PACK-RETIRED-38](BUILD-WORLD-PACK-RETIRED-38.md): World disk packer requires explicitly omitted exterior BSP maps
- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-NEW-BUILDER-RULES-35](CI-NEW-BUILDER-RULES-35.md): Hosted CI failed on v0.0.35: the previous-release check refused the one-commit checkout and the run-name rule refused the Docker check's run name
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies
- [ENGINE-STRICT-WARNINGS-36](ENGINE-STRICT-WARNINGS-36.md): The engine builds warning-free only under -Wall -Wno-unused; stricter flags show 482 warnings
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
- [RELEASE-LAVA-IMAGE-ALLOWLIST-38](RELEASE-LAVA-IMAGE-ALLOWLIST-38.md): Lava documentation images were listed without image-type approval
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [RELEASE-PATCH-TARGET-VERSION-39](RELEASE-PATCH-TARGET-VERSION-39.md): RC1 publication baseline lacks its target version
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
- [TEST-RC1-INTEGRATION-CONTRACTS-39](TEST-RC1-INTEGRATION-CONTRACTS-39.md): RC1 regression tests assume the old fingerprint location and a separate class cache unit
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
