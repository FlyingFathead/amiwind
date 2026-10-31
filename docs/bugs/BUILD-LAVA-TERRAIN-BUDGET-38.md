# BUILD-LAVA-TERRAIN-BUDGET-38: Detailed lava terrain exceeds region storage budget

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.41-dev2 at 2026-10-16 00:57 +0300: vf1697 4.74 MB, vf2544 4.35 MB over 4 MiB; two more splits
- Reported with v0.0.43 at 2026-10-19 (time not recorded): A tester's default build from the public repository (native and Docker) stopped at world-scenery: 7 regions over 4 MiB (vf1178 4,468,264 bytes ...)
- Reported with v0.0.46 at 2026-10-21 (time not recorded): Reproduced on the v0.0.46 tree, default options from scratch: same 7 regions, vf1178 byte for byte; v0.0.47 fix: 11 refinement splits, both stages pass

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 12 October 2026, in v0.0.38-dev3 |
| Where | Legacy exterior world-terrain and world-scenery stages of a default build (no CHIM region selection) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.47 |
| Severity | high: Stops a default build from the public repository at the world-scenery stage (no image). |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.38-dev3 full candidate |
| From commit | source 5d509f1, engine 5d509f1, CHIM world 5d509f1 |
| CHIM engine version | CHIM 0.2.0, engine 5d509f1, world format unknown |
| Unknown because | Legacy terrain BSP compile; no packaged candidate accepted. |
| Platform or emulator | unknown (Build-time failure before emulator playtest.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47-dev1 (21 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom
The full v0.0.38-dev3 build stops with a terrain budget error at `vf1177`.
The actor-contact and gallery stages passed, but this does not produce a complete playtest.

## Where
Seven completed outputs exceed the 4 MiB region storage limit: vf1177, vf1179,
vf1258, vf1457, vf1695, vf1696 and vf1819. Sizes range from 4,276,864 to
5,644,052 bytes. Face and clipnode counts remain below their independent limits.

## How it happened
The candidate retains original terrain detail around lava. In vf1177 the BSP is
4,450,656 bytes, including 3,006,198 visibility bytes, 11,503 faces and 19,146
clipnodes. Visibility storage dominates this measured output; the complete
causal relationship and smallest safe repair remain under investigation.

## Why it was not caught
Single-region lava diagnostics and source tests did not exercise every full-world
terrain region. The full build caught the failure before packaging.

## Reproduction
Build the full candidate from source 5d509f1 with the recorded release recipe,
legacy lava enabled and fast visibility. Inspect the world-terrain stage and
independent storage, face and clipnode limits.

## Repair
Pending. Preserve the failed outputs and passed stage caches. Investigate
visibility encoding and region complexity before reducing source terrain detail.
Do not raise the limit or drop original lava references to make the gate pass.

## Verification
Failure reproduced by the full build; seven over-budget outputs independently
measured. No corrected full build, exact package or native acceptance.

12 October diagnostic: split each failing map core into four children while
retaining the 896-unit apron and original terrain/lava conversion. All 28
terrain-only children passed the existing storage, face and clipnode limits.
An independent generated-geometry comparison found identical world-space core
triangle multisets before and after all seven splits (no missing or extra
triangles). A guarded subcell-refinement helper passed 13 focused tests, including
negative-coordinate coverage and unchanged sibling map identities. Production
layout selection was unchanged in that diagnostic. The subsequent candidate
adds all seven measured parent refinements to the versioned configuration.
The real survey produces 2,553 regions instead of 2,532: all 2,525 unaffected
entries remain identical, and all 28 child core/origin/apron geometries match
the measured diagnostic. Scenery budgets, compiled collision, cross-apron
stitching, full build and native/package acceptance remain outstanding.

## Prevention
Exercise dense lava regions before the next full build. Keep original lava
exposure, source heights, collision and final region storage as separate checks.



12 October follow-up: after the seven terrain refinements, the full candidate at source 3fac049 stopped at the world-scenery budget gate on vf1397. Its retained scene.bsp is 4,917,272 bytes, above the 4,194,304-byte region storage cap. Other collision and face counts still require inspection. The earlier terrain-only checks did not prove scenery-overlay headroom. Earlier outputs are retained. No budget bypass, package or delivery; any further refinement must preserve original terrain and reference ownership and be checked through the final overlays.


12 October CHIM inclusion follow-up: the failing outputs were verified BSP29 (header 29), not CHIM. Cells (5,-2) and (5,-1) were outside the full build's CHIM selection despite historical conversions. Fresh conversions at source3fac049 pass the offline audits, with maximum hull depths144 and116, zero models over the limit. Two normal-margin playable CHIM frames also pass heap, format, zone-walk and stair gates:2,376 simulated streaming steps each without allocation failure or partial activation;247 stair/ramp checks with27 advisories and zero gating failures. Both cells are added to the next candidate selection, preserving358 previous cells for360 total. Native and exact-package acceptance remain pending; neither the register nor the public cell tracker is promoted to fixed or accepted.

12 October whole-region follow-up: the next full build confirms cells (5,-2) and (5,-1) are selected as CHIM, but stops at BSP29 scenery vf1516, cell (7,-4). A complete scenery-only scan of 2,103 legacy regions finds two storage failures: vf1516 is 4,384,176 bytes with 17,986 faces and 22,671 clipnodes; vf1907, cell (11,-1), is 4,551,576 bytes with 16,395 faces and 15,690 clipnodes. Both exceed the 4,194,304-byte cap while passing the face and clipnode limits. Both belong to Molag Mar Region. The current selection contains 26 of its 123 exterior cells. Whole-region CHIM coverage, collision validation, later overlays and exact-package native acceptance remain pending.


### Final-image verification, 13 October 2026

Full image assembly completed with the overflowing regions converted to CHIM; production map-memory gate passes. All360 regional CHIM cells pass final HDF frame/chunk readback. Release delivery remains pending; conversion is not complete gameplay acceptance.

### PERSISTING: v0.0.41-dev2 full build, 16 October 2026

The rings 0-2 full build at source 585afff stopped in the world-terrain stage after 23 minutes. Two legacy BSP29 regions of
cell (9,0), Molag Mar Region, were over the 4,194,304-byte region storage cap: vf1697 at 4,739,260 bytes (13,318 faces,
13,665 clipnodes) and vf2544, a child of the earlier vf1695 split, at 4,352,800 bytes. Face and clipnode counts were within
their limits. In v0.0.36 vf1697 was 549,140 bytes. In v0.0.38-dev3, with lava, it was 4,087,788 bytes, just under the cap,
so it was not split with its siblings. It has grown past the cap since then.

Repair: two more rules in the versioned refinement table. vf1697 goes from 2 to 4 divisions, like its siblings vf1695 and
vf1696. vf2544 goes from 4 to 8 divisions. Original core triangles and the 896-unit apron are kept. The real survey now lays
out 2,559 regions; earlier region names and indices are unchanged. The budget error now names the region, its cell and
split, and every exceeded limit with the measured value and SHA-256. Earlier it named only the region.

Still open: the remaining near-cap regions (vf1603 at 3,968,800 bytes, vf1821 at 3,951,208 bytes) have no headroom for
further lava growth. A pre-build budget scan of every dense lava region would catch the next one before a full build.

### PERSISTING: public default builds, 19 and 21 October 2026

A tester built the game from the public repository with the default builder options on 19 October 2026, both natively
and in Docker (from the map names, v0.0.43: its region layout is the one from BUILD-WORLD-LAYOUT-DRIFT-32). Both runs
stopped at the end of the world-scenery stage, after converting all 2,384 regions: 7 regions were over the
4,194,304-byte region storage cap. The register had closed this bug in the 20 October audit as superseded, because the
project's own builds put these cells on CHIM.

Checked on 21 October 2026 with the v0.0.46 release tree: the world-terrain and world-scenery stages run from scratch
with the default options (no CHIM region selection; the survey and the scenery export are the same in both kinds of
build) stop the same way, with the same seven regions. vf1178 is byte for byte the size the tester reported:

| Region | Cell | Split | Bytes | Faces | Clipnodes |
| --- | --- | --- | ---: | ---: | ---: |
| vf1818 | 10,0 | quarter 0,0 | 4,923,988 | 17,330 | 17,014 |
| vf1394 | 5,-2 | whole cell | 4,872,748 | 18,726 | 19,454 |
| vf1600 | 8,0 | quarter 1,0 | 4,765,484 | 18,058 | 14,131 |
| vf1179 | 2,-1 | whole cell | 4,669,588 | 18,072 | 21,683 |
| vf2543 | 9,0 | sixteenth 1,1 | 4,604,696 | 15,522 | 17,131 |
| vf1178 | 2,-2 | quarter 1,1 | 4,468,264 | 17,210 | 20,037 |
| vf1395 | 5,-1 | whole cell | 4,325,612 | 17,373 | 20,723 |

Face and clipnode counts are within their limits; only storage is over.

Why it came back: the 12 October scenery failures (vf1397, vf1516 and vf1907 at the time; cells 5,-2, 5,-1, 7,-4
and 11,-1) and the later lava growth were repaired by putting the cells on CHIM, through the CHIM cell list the project
passes to its own builds. That list is not a public default. A default build still converts these cells as BSP29
regions, and nothing measured them: the project's builds skip them and reuse the open-world stages from earlier runs,
and no from-scratch default build had run since the cells moved to CHIM. The terrain stage's own 4 MiB check passes,
because the scenery overlay adds the size.

Repair (v0.0.47): eleven more rules in the refinement table, config/world-region-refinements.json. The seven regions
above are split into four children each. Four more regions within 5 % of the cap that could still be split are split
too, for headroom: vf1513 (cell 7,-4, 4,116,252 bytes), vf1904 (11,-1, 4,079,536), vf1689 (9,-1, 4,050,484) and vf1587
(8,-3, 4,026,920). Original core triangles, scenery references and the 896-unit apron are kept. Earlier region names
do not change; the new children are added at the end of the world directory (2,589 rows, 2,417 BSP29 maps in a default
build). In the project's own builds these cells are CHIM, so they only gain directory rows.

Verification: the same two stages from scratch with the repaired table pass: 2,417 regions converted, the overlay
covers all 37,081 source references, none over a limit. The largest is vf2555 (cell 9,0, an eighth-split child) at
4,147,976 bytes. It is already at the finest split, so it is the region to watch.

Prevention: the scan is recorded in config/world-region-budget-scan.json by tools/world_budget_scan.py (the largest
regions, the limits and the refinement table it was measured with). tests/test_world_region_budget.py fails when the
refinement table changes without a new scan, or when a recorded region is over a limit. A from-scratch default build
of the open-world stages belongs to every release check (it takes about 30 minutes on 6 cores).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-ACTOR-MODEL-UNSUPPORTED-48](BUILD-ACTOR-MODEL-UNSUPPORTED-48.md): A Balmora build-speed measurement stopped on Unsupported actor model
- BUILD-CACHE-NO-RETENTION-55 (no report page): The build cache keeps every entry forever: about 603 GB nothing recent uses
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47](BUILD-CHIM-CELLS-PRIVATE-LIST-47.md): The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells
- BUILD-CHIM-EARLY-CHECK-POOL-55 (no report page): The chim stage's early frame checks forked a worker pool of their own outside the stage's memory allowance
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-DISK-NEED-UNKNOWN-52](BUILD-DISK-NEED-UNKNOWN-52.md): A public build can die halfway when the disk fills: the only space check runs once at the start, against a fixed 20 GiB, not what the release really takes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- BUILD-GUARD-BLIND-NO-CGROUP-55 (no report page): Without a container memory limit the build's memory guard, its alarm and every pool's memory governor saw no memory at all
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- BUILD-MINIWIND-SEYDA-KELP-INDEX-54 (no report page): A Seyda Neen MiniWind can never pass: the chim-town-seyda stage stops because the kelp additions need the original scenery index, which a MiniWind plan does not build
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-NPC-GALLERY-SKIPPED-DEV-42](BUILD-NPC-GALLERY-SKIPPED-DEV-42.md): Development and playtest builds leave out the NPC gallery to save build time
- BUILD-OOM-DEGRADE-NOT-DIE-54 (no report page): A worker killed for memory broke its stage's pool and failed the whole build
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [BUILD-ROOM-SHELL-WRITER-UNPINNED-48](BUILD-ROOM-SHELL-WRITER-UNPINNED-48.md): The room shell form writes its conversion report without pinned encoding and line ends
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- BUILD-STAGE-KEY-NPC-MODULE-53 (no report page): The CHIM and town stages are keyed on the whole of src/mwad/npc.py, so a change to four NPCs in outfit() re-keys the CHIM world (22 of 43 stages, about 7 hours)
- [BUILD-TESTS-UNLISTED-48](BUILD-TESTS-UNLISTED-48.md): Seven test files of the v0.0.48 fix branches were not on the release list, so no gate ever ran them
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-TORCH-CREATURE-RESIDENT-42](BUILD-TORCH-CREATURE-RESIDENT-42.md): Image step stops in the torch guard on Vivec, an interior creature resident placed as an NPC entity
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-FRAME-ALONE-FLAMES-48](CHIM-FRAME-ALONE-FLAMES-48.md): A town frame map read alone stops in its flames step: the frame-alone world holds its frames by index, the flames lookup walked them as a list
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [CHIM-LAVA-DUPLICATE-VERTEX-40](CHIM-LAVA-DUPLICATE-VERTEX-40.md): Float32 duplicate vertices falsely fail lava surface coverage
- [CHIM-OCEAN-ROUTING-UNNAMED-41](CHIM-OCEAN-ROUTING-UNNAMED-41.md): The world-terrain stage refused ocean routing cells without naming a cell or which rule failed
- [CHIM-ROOM-SHELL-ACTORS-EARLY-48](CHIM-ROOM-SHELL-ACTORS-EARLY-48.md): The scene stage actor check measured residents of shell rooms, which have no collision until the image: 110 refused
- [CHIM-VISIBILITY-APRON-SCOPE-41](CHIM-VISIBILITY-APRON-SCOPE-41.md): Fixed stronghold visibility rejects regional aprons
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [CHIM-WINDOW-TOWER-SUPPORT-41](CHIM-WINDOW-TOWER-SUPPORT-41.md): Thatched tower omitted from decorative window facade support
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [ENGINE-FRAME-REFUSE-PROTOTYPE-48](ENGINE-FRAME-REFUSE-PROTOTYPE-48.md): The engine build stops on a missing prototype: AW_SceneFrameRefuse has no declaration
- MINIWIND-EXTERIOR-DIRECT-START-CELL-57 (no report page): An exterior MiniWind direct start at cell 0,-7 (the Ascadian Isles creatures recipe) fails in the image step: no map of the build holds the point
- PREFLIGHT-GUARD-UNSTAMPED-NPCS-48 (no report page): The payload preflight guard count refused census.bsp: its three NPCs get their source identity later in the image step
- [RELEASE-FINAL-LINE-STALE-RC-48](RELEASE-FINAL-LINE-STALE-RC-48.md): The v0.0.48 final line was cut from an older rc1 head than the image: it lacked the two layout fixes the shipped image was built with
- RELEASE-GUARD-NO-FROMSCRATCH-RULE-54 (no report page): No release guard rule requires a from-scratch build: v0.0.52 and v0.0.53 shipped without one
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells

<!-- END GENERATED CATEGORY -->
