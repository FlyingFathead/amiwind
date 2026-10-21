# BUILD-SEYDA-HULL2-32: From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | bsp stage, Seyda Neen full-town map (tools/prepare_quake.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.41 |
| Severity | critical: From-scratch builds stop at qbsp because hull 2 exceeds the clipnode limit; release blocker for the builder. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 16 October 2026 (v0.0.41-dev2, repair in the builder)](#status-16-october-2026-v0041-dev2-repair-in-the-builder)
- [Status: 15 October 2026 (v0.0.41-dev1, PERSISTING)](#status-15-october-2026-v0041-dev1-persisting)
- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Source-only carrier, 15 October 2026](#source-only-carrier-15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 16 October 2026 (v0.0.41-dev2, repair in the builder)

Repair: a CHIM-native Seyda Neen no longer compiles its town to BSP29 at all. The bsp stage
(`tools/prepare_mesh_bsp.py --seyda-source carrier`, chosen by `tools/build.py` for a CHIM-native Seyda Neen)
writes the source-only carrier instead: the scene's point entities plus every placed static as a `func_wall`
with its exact model-local box (the compiled writer's own metadata, `prepare_seyda_source.seed`), and the
tutorial barrel from its own export when the scenery selection lacks it. No qbsp, vis or light runs, so the
cell-aligned frame (owned cells (-3,-11) to (1,-7)) stays as it is. Every later scene stage (residents, hands,
intro, area, opening references) edits only the entity lump; the opening-references stage binds a carrier's
placements by their reference number and never appends geometry to it; `chim_town.prepare_seyda` takes the
frame rows and the activated objects from it (scene record bound by SHA-256); the image step accepts the
carrier only for a CHIM-native Seyda Neen. The compiled town stays selectable for A/B tests
(`--seyda-scene-source compiled`, a retired option: `--override seyda-scene-compiled`) and is still the
source of the legacy chains.

New checks that fail fast, naming the reference and the map: the bsp stage refuses a carrier without every
exterior object the engine activates (`aw_activated.h`) inside the town area; the chim-town-seyda stage
checks, before it reads the CHIM frame, that each such object arrives as an activated entity of every frame
map whose bounds hold it (the town frame, `sncourt`, `intro_docks`; `chim.frame_map.activated_expected` and
`activated_missing`). The registration papers (172859) and the hall door (172860) are interior references
(Census and Excise Office), so they are expected in no exterior frame map.

Verification: on the v0.0.41-dev1 run's own alias scene and scenery (original data), the carrier stage took
9.2 s (1,345 placements, the barrel from its separate export, 349,052 bytes, no faces); the opening stage
bound the same scenery references as the last compiled builds; the activated check expects and finds
172851 in the town frame, `sncourt` and `intro_docks`. Tests: tests/test_seyda_scene_carrier.py.
Open: the end-to-end image build through tools/build.py with this source.

## Status: 15 October 2026 (v0.0.41-dev1, PERSISTING)

Seen again in a new form. The rings 0-2 build of v0.0.41-dev1 stopped at the bsp stage: qbsp of the Seyda Neen
full-town source map (`seyda.map`) failed with "Map exceeds BSP29 node/leaf limit" (61,981 split nodes,
30,560 leaves). Cause: in v0.0.40 Seyda's CHIM frame was widened to whole game cells (owned cells (-3,-11) to
(1,-7), about 6.8 times the old area) so the frame meets the surrounding ring cells, while the bsp stage still
compiles the full-town source map from that whole box. The map is an intermediate (Seyda ships as CHIM): it is the
source of the opening objects (the tutorial barrel 172851, the registration papers, the hall door) and the Census
courtyard frame map. Proposed repair: compile the source map only from the town area those objects need, keep the
cell-aligned CHIM frame.

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt). Release blocker for the public builder (MANDATORY from-scratch rule).

## Symptom

The builder's `bsp` stage stops: qbsp reports "Clipnode count exceeds bsp 29 max (68655 >
65520)" for hull 2 of the Seyda Neen full-town standing collision map. The builder never uses
hull 2, but qbsp aborts on it. v0.0.26 and v0.0.27 pass; v0.0.28 to today fail identically.

## Where

`tools/prepare_quake.py` (`town_ground_triangles`, `required_edge_samples` added in v0.0.28:
69 more terrain brushes) and the qbsp call for that map.

## How it happened

v0.0.28 added edge samples to the town ground; hull 2 crossed the limit.

## Why it was not caught

No from-scratch build was run between releases; release images were patched up from older images.

## Reproduction

Run `tools/build.py` from scratch with your own data.

Cost signals from the fix: the v0.0.28 edge samples grow the full-town standing hull 1 from
19,156 to 35,292 nodes (+84 %), and the full-town map's hull 0 is at 31,162 of 32,767 nodes (95 %).

## Repair

Fixed in source (v0.0.32-dev, a97861b): the engine uses hulls 0 and 1 only (hull 2 is never
traced: world.c selection rule, every QuakeC and engine trace box fits hull 1). The standing-hull
intermediate is compiled as BSP2 (32-bit indices, no overflow) and only its hull 1 is grafted;
`rebuild_world_hull` is the one standing-hull path for every map (the region converter's inline
copy now calls it). The graft uses the engine's real limit (65,520) with unsigned 16-bit
children, as the engine reads them. A new gate, `check_engine_hulls`, fails a map only when
hull 0 or 1 breaks an engine limit. The v0.0.28 edge samples are kept; maps that already fit
are byte-identical. Residual risk: each map's own base compile is still BSP29 with all hulls.

## Verification

From-scratch build (25 min 38 s) passes `bsp`: the full-town Seyda Neen map has 55,632
clipnodes and 31,162 nodes, within the engine limits. Tests: `tests/test_engine_hulls.py`
(engine contract, synthetic grafts, BSP2/BSP29 intermediates graft to identical bytes).

## Prevention

A periodic from-scratch build (mandatory project rule) and a builder test for hull limits.


### 15 October 2026: actual gate follow-up

Expanded dev2 town remains blocked at the complete-town legacy intermediate: actual floor-corrected compile exceeds BSP29 node/leaf limits (63,579 nodes). Prior standing-hull repair is preserved; no engine limit is raised. A CHIM-native source carrier retaining all original entity/reference semantics is required before rebuilding.

## Source-only carrier, 15 October 2026

The current dev2 source adds an optional original-source entity/model-bound
carrier for Seyda CHIM. Canonical placement transforms, mounting, visual offsets,
intro/exterior actors, activation bounds and original-reference checks remain.
This avoids compiling a complete legacy town terrain map. The intermediate is
marked non-runtime and must not enter an image; the existing CHIM frame-map
writer supplies runtime maps. Forty-seven isolated checks pass. Original-data
execution, combined-source validation, native seams/story/save behavior and
packaging remain pending. No source-only check establishes shipment.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47](BUILD-CHIM-CELLS-PRIVATE-LIST-47.md): The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
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

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells

<!-- END GENERATED CATEGORY -->
