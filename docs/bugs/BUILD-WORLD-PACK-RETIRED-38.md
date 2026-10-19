# BUILD-WORLD-PACK-RETIRED-38: World disk packer still opens omitted exterior BSPs

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | World partition input selection after validated exterior-map omissions |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.39-rc1 |
| Severity | critical: Full-world image assembly would stop before partition writing on intentionally absent maps. |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine a382647 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Offline disk-packer source audit; no new game or emulator failure observed.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [RC1 preflight integration, 13 October 2026](#rc1-preflight-integration-13-october-2026)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

A source audit found that the disk packer reconstructs every world-region map
path, including deliberately omitted town-owned exterior BSPs. It then calls
`stat()` on these absent files before writing any world partition. The affected
full-world selection contains 135 such routing-only rows, starting at `vf0302`.
The earlier full image stopped at fingerprinting and did not reach this stage.

## Where

`tools/world_volumes.py`, `pack`, called from `tools/build_aga.py`.

## How it happened

Town routing needs stable region indices although the corresponding exterior
geometry belongs to CHIM. The prebuild checklist correctly excludes those BSPs
from compilation, but the disk packer only understood divided-cell aliases.
It did not receive the fingerprint's verified list of absent map files.

## Why it was not caught

The omission integration regression ended at the content fingerprint. Disk
partition tests covered size and readback but not deliberately absent routing
rows. Reviewing the next stage exposed the missing handoff before another full
image attempt.

## Reproduction

Keep a town-owned row in `regions.awr`, omit its BSP under the validated exterior
checklist, and call `world_volumes.pack`. Before the correction, map size
accounting tries to open the absent BSP even after fingerprint validation passes.

## Repair

Pass the exact validated omission list from the image fingerprint to the disk
packer. Exclude only those exact paths from its partition inputs. Unexpected
missing maps still fail before any partition is written, and an allegedly
omitted map still present on disk is rejected. Existing CHIM frames, required
BSPs and interiors remain independent. This changes offline image assembly;
it does not change the engine or compile replacement BSPs.

## Verification

Source correction and regression cases are prepared. The integration case now
follows the prebuild command through the real image parser, fingerprint and
disk-packer input selection. Other cases cover postbuild removals, unexpected
missing maps and files falsely declared absent. These new checks, complete
image readback and native routing acceptance remain pending.

## Prevention

Carry one explicit, validated map-ownership decision through compilation,
fingerprinting and partition writing. Exercise stage boundaries together;
checking the prebuild planner alone cannot prove final image assembly.

## RC1 preflight integration, 13 October 2026

The full RC1 build completed conversion, then stopped in the first image
preflight on `maps/vf0302.bsp`. The disk packer already accepted the validated
omission list, but its earlier layout check reconstructed every routing row
without that list. The missing BSP was correctly excluded before compilation.

The image wrapper now passes its exterior terrain receipt to preflight. The
same ownership validator checks stable routing rows, town cores, source
classification and absence of redundant BSPs and catalogues. Before frames
exist, owners must occur in the validated CHIM world receipt; the final
fingerprint still requires the actual owner frames. Disk layout excludes only
those declared paths. Unexpected missing maps remain errors.

Thirty focused Docker regressions pass, including the real image wrapper,
layout calculation, fingerprint and packer handoffs. No engine behavior or
converted geometry changes. Complete repaired image readback and native
routing are still pending; this is not a delivered fix.

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
count. Final v0.0.39 remains in preparation pending explicit maintainer inspection
approval; RC1 shipment does not supply maintainer or universal gameplay acceptance.

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
- [BUILD-SEYDA-CARRIER-VOICE-DIR-40](BUILD-SEYDA-CARRIER-VOICE-DIR-40.md): Fresh Seyda carrier cannot publish a resident voice without an inherited sound directory
- [BUILD-SHADOWED-WORLD-MAPS-38](BUILD-SHADOWED-WORLD-MAPS-38.md): Full image retains BSP maps shadowed by higher-priority world routes
- [BUILD-TOOLKIT-VERSION-40](BUILD-TOOLKIT-VERSION-40.md): Development source retains the prior Toolkit release label
- [BUILD-VERSION-EMULATOR-PRESETS-38](BUILD-VERSION-EMULATOR-PRESETS-38.md): Version bump omitted matching emulator presets
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](BUILD-WORLD-FINGERPRINT-RETIRED-38.md): Content fingerprint requires an explicitly retired exterior BSP
- [CHIM-SEYDA-RECEIPT-TEXT-40](CHIM-SEYDA-RECEIPT-TEXT-40.md): New Seyda metadata and carrier writers omit explicit UTF-8 and LF
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
- [TEST-CENSUS-CONTRACTS-40](TEST-CENSUS-CONTRACTS-40.md): Three quick-character expected failures lack reconciled contracts
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
- [TEST-TOWN-BOUNDS-40](TEST-TOWN-BOUNDS-40.md): Town expansion left recovery fixtures and coordinate audit stale
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
