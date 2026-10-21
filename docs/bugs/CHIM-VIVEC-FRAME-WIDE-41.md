# CHIM-VIVEC-FRAME-WIDE-41: Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41-dev2 |
| Where | CHIM town frame vivec_city (config/vivec_city.json owned_cells, source_radius) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.41 |
| Severity | high: Blocks the image actor gate; a private playtest needs a maintainer waiver |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev2_full-rings012-v040cells_427e29b |
| From commit | source 427e29b, engine 427e29b, CHIM world 427e29b |
| CHIM engine version | CHIM 0.2.0, engine 427e29b, world format unknown |
| Unknown because | world format not read from this run's receipt |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Measured causes: 16 October 2026](#measured-causes-16-october-2026)
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

## Measured causes: 16 October 2026

Correction to the report: `owned_cells` is a half-open rectangle, so [[1,-14],[7,-8]] is the
6 x 6 block of cells x 1..6, y -14..-9 (36 cells, as `tests/test_town_grid.py` records), not 7 x 7.
Two of the three residents stand inside it. Narrowing the frame alone would not ground them:
it would move them to open-world CHIM region cells, which place no residents, so they would
leave the game.

Measured on the v0.0.41-dev4 Vivec frame in frame-local units (one unit is four original units),
probing its collision and the original LAND samples at each resident:

| Resident | Cell | Under its feet | Original LAND | Frame tile | Finding |
| --- | --- | --- | --- | --- | --- |
| Nels Llendo (204678) | 0,-9 (Seyda Neen's) | terrain | 133.7 (feet 134.0) | 142.5 | placed by both town frames; buried 8.8 units, the support probe starts inside the ground (blocked) |
| Pilus Amatius (388940) | 1,-13 (Ebonheart) | terrain | 154.6 (feet 174.9) | 154.0 | 15-degree tile slope; no offset fits (tightest whole-sole spread 1.71, band 1.5) |
| Dreamer (297836) | 4,-9 | terrain | 140.0 (feet 145.3) | 137.1 | 28-degree original slope; no offset fits on either ground (1.61 tiles, 1.75 original) |

No placed object lies under any of the three. Nels's cell belongs to Seyda Neen's frame, but
Vivec's 768-unit reference apron reaches into it, so both frames placed him (Seyda Neen's fits
him on its original-sample tiles). Pilus was fitted on the Vivec frame from v0.0.36 to v0.0.38,
22 units east, on the same tile ground; his resident model has since changed (14 sole samples
instead of 13) and no longer fits any of the 12,853 offsets of the support search on the coarse
slope. The Dreamer was never placed before: the open-world maps carry no residents.

## Symptom
The v0.0.41-dev2 full build stops at the image step's actor placement gate with three
unresolved CHIM frame residents of the Vivec frame: Nels Llendo (original reference 204678,
cell 0,-9, blocked), a Dreamer (297836, cell 4,-9, unresolved mesh contact) and Pilus Amatius
(388940, cell 1,-13, unresolved mesh contact). 521 other actors are grounded.

## Where
The CHIM town frame `vivec_city` (`config/vivec_city.json`). Introduced in v0.0.40 (f73aaa6):
`owned_cells` was added as the whole cells (1,-14) to (7,-8), a 7x7 block, and `source_radius`
went from 3 to 4 cells. Scale (0.25), centre and source cell are unchanged: nothing is stretched;
the frame claims more of the map. v0.0.36 used a handoff core of about 4 x 4.5 cells around the city.

## How it happened
The frame was aligned to the original cell grid by rounding its border outward to every whole
cell the city touches. That block also holds Ebonheart and open land north of the cantons, and
the wider source radius reaches cell (0,-9), which Seyda Neen's frame owns. Residents standing on
terrain or buildings in those areas are now judged on the Vivec frame's collision, which does not
support them. Nels Llendo is also a held finding of the Seyda frame (CHIM-SEYDA-ACTOR-CONTACT-33):
one actor in two town frames.

## Why it was not caught
No v0.0.40 or v0.0.41-dev1 build ran the full image step through the repo builder after the
change; the frames were assembled by hand. The exterior lookup table checks that every cell has
one format, but not that a town frame's source reach stays out of another town's owned cells.

## Reproduction
Build the full rings 0-2 selection (371 cells) at 427e29b with the default CHIM-native towns;
the image step's actor gate fails on the three references above.

## Repair
Three changes at the shared layer, without per-actor exceptions:

1. One town frame per resident. A town frame places a resident only when no other town owns
   the cell of its origin (`tools/town_grid.py` `resident_owner`, `tools/import_town.py`
   `resident_cast`). A resident left out is logged with the town that owns it and listed in the
   town stage's `residents.json` (`left_to_owner`). Nels Llendo stays in Seyda Neen's frame only.
2. Original LAND under ground residents. A CHIM town frame keeps the original 32-unit LAND
   samples on every terrain tile within 48 units of a ground-mode resident whose feet are within
   32 units of the original ground (`tools/chim/build.py` `resident_detail_tiles`, through the
   same refinement as the lava tiles). It is the frame-wide form of Seyda Neen's hand-listed
   `terrain_detail_tiles`. Residents on walkways and roofs keep the plain tiles. Vivec gets 45 such
   tiles, Balmora 38. `--chim-terrain-resident-detail off` (`chim_build.py --terrain-resident-detail
   off`) keeps the plain tile grid, the method before v0.0.41.
3. Wide support search ring (project decision, 16 October 2026: the recommended option). When no
   spot within 32 units fits an actor, the support search goes on to the spots between 32 and
   48 units, nearest first (`tools/actor_grounding.py` `WIDE_RING`, `search_offsets`). Every
   32-unit spot is tried first, so an actor the 32-unit search places never moves.
   `--actor-search near` (environment `AMIWIND_ACTOR_SEARCH=near`) keeps the 32-unit search
   only, the method before v0.0.41. The image step's frame-map refit takes the same search.
   The Dreamer is placed 37.5 units north of its authored spot, on the original ground.

The Dreamer in the game data: Dreamers serve Dagoth Ur and appear as the Sixth House plot
advances. The original `Startup` script disables `Dreamer_Talker11` when a game starts, and
the record's own script `dreamer_talkerEnable` enables it once the journal `A2_2_6thHouse`
reaches index 50. It is not there at the start, but the placement must still be valid for
when it appears.

## Verification
Image gate report `actor-initial-contact.json` of run 2026_10_16_v0.0.41-dev2_full-rings012-v040cells_f704ed1:
summary grounded 521, explicit exceptions 5, failed frame fit 3.

16 October 2026, the Vivec frame alone built with the change (`chim_build.py --area vivec_city`,
compiled terrain hull, terrain references, the dev5 inputs): CHIM validation passed, heap gate
passed (active ring peak 5,655,424 of 6,242,304 bytes; 5,548,496 with the switch off), zone walk
passed, stair gate passed (14,793 steps and ramps, 0 failed). The residents of the v0.0.41-dev4
town stage, refitted with the town stage's own fitter (`chim_town.ground_actors`) and judged as
the image gate judges frame residents:

| Vivec frame | Grounded | Not supported |
| --- | --- | --- |
| resident detail off (plain tiles), 32-unit search | 56 | Pilus Amatius, Dreamer |
| resident detail on, 32-unit search (`--actor-search near`) | 57 | Dreamer |
| resident detail on, wide ring (default) | 58 | none |

Nels Llendo is left to Seyda Neen in both. Pilus Amatius is fitted 14.5 units from his authored
spot at height 157.08. Fourteen other residents now stand on the original ground: their heights
change by 0.15 to 3.1 units, and two need no horizontal offset any more. Balmora's frame with the
change: heap gate passed (active ring peak 4,957,168 bytes; 4,897,056 off), stair gate passed
(3,655 steps and ramps), all 18 residents grounded.

The wide ring, measured on the merged v0.0.41-dev source (the same frame gates again: heap
5,655,424 bytes, zone walk passed, stair gate 14,793 steps, 0 failed; Balmora 4,957,168 bytes,
3,655 steps): all 58 Vivec residents grounded with no waiver. Against `--actor-search near`,
57 of the 58 have the same status, position and attempt count; only the Dreamer differs
(attempt 17,656 of 28,917: placed at 599.59, 5,760.17, 131.80). Balmora's 18 residents are
identical in both modes.

## Prevention
`tests/test_town_frame_residents.py`: a resident in another town's owned cells is left to that
town, the owned cells of the town frames do not overlap, the tiles under ground residents are
listed and take the original samples, the wide ring is tried only after every 32-unit spot (an
actor that fits nearer is placed the same in both modes), and both switches keep the previous
methods. Every frame
change runs the full image step through the builder before a playtest.

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
- [CHIM-WINDOW-TOWER-SUPPORT-41](CHIM-WINDOW-TOWER-SUPPORT-41.md): Thatched tower omitted from decorative window facade support
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-ACTOR-GATE-CHIM-FRAMES-36](BUILD-ACTOR-GATE-CHIM-FRAMES-36.md): The actor placement gate ignores CHIM frame residents: a CHIM-only build fails with no actors, and a blocked frame resident passes silently
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-STATICS-FALLBACK-41](CHIM-STATICS-FALLBACK-41.md): A frame map with more than 512 streamed statics crashes when its CHIM world cannot load, instead of running without its chunks

<!-- END GENERATED CATEGORY -->
