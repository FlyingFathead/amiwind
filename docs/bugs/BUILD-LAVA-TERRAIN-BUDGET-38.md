# BUILD-LAVA-TERRAIN-BUDGET-38: Detailed lava terrain exceeds region storage budget

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 12 October 2026, in v0.0.38-dev3 |
| Where | Legacy exterior world-terrain stage |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev3 (last seen) |
| Severity | high: Blocks full development playtest packaging. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.38-dev3 full candidate |
| From commit | source 5d509f1, engine 5d509f1, CHIM world 5d509f1 |
| CHIM engine version | CHIM 0.2.0, engine 5d509f1, world format unknown |
| Unknown because | Legacy terrain BSP compile; no packaged candidate accepted. |
| Platform or emulator | unknown (Build-time failure before emulator playtest.) |

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-NPC-GALLERY-SKIPPED-DEV-42](BUILD-NPC-GALLERY-SKIPPED-DEV-42.md): Development and playtest builds leave out the NPC gallery to save build time
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-TORCH-CREATURE-RESIDENT-42](BUILD-TORCH-CREATURE-RESIDENT-42.md): Image step stops in the torch guard on Vivec, an interior creature resident placed as an NPC entity
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [CHIM-LAVA-DUPLICATE-VERTEX-40](CHIM-LAVA-DUPLICATE-VERTEX-40.md): Float32 duplicate vertices falsely fail lava surface coverage
- [CHIM-OCEAN-ROUTING-UNNAMED-41](CHIM-OCEAN-ROUTING-UNNAMED-41.md): The world-terrain stage refused ocean routing cells without naming a cell or which rule failed
- [CHIM-VISIBILITY-APRON-SCOPE-41](CHIM-VISIBILITY-APRON-SCOPE-41.md): Fixed stronghold visibility rejects regional aprons
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [CHIM-WINDOW-TOWER-SUPPORT-41](CHIM-WINDOW-TOWER-SUPPORT-41.md): Thatched tower omitted from decorative window facade support
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells

<!-- END GENERATED CATEGORY -->
