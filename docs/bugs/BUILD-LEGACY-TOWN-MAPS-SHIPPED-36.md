# BUILD-LEGACY-TOWN-MAPS-SHIPPED-36: Cells on CHIM still have their legacy maps built and shipped: the towns' sn0xx (233 MB) and bm0xx (69 MB), and legacy stages run for CHIM cells

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.33-dev at 2026-10-09 (time not recorded): CHIM-LEGACY-CHAIN-33: CHIM builds still run the legacy exterior chain
- Reported with v0.0.36-dev1 at 2026-10-10 (time not recorded): BUILD-IMAGE-CHIM-NATIVE-TOWN-36 and BUILD-LEGACY-CHAIN-DEFAULT-36: legacy maps read or built for CHIM towns
- Reported with v0.0.36-dev3 at 2026-10-11 00:43 +0300: legacy maps of CHIM areas built and removed again (BUILD-CHIM-FRAME-SWAP-LATE-36)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | Image step: Seyda Neen legacy region maps (65 sn files) and every per-map pass over them |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: about 62 s of the Seyda chain plus per-map passes over maps removed before packing; the payload is not affected |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3b5e7a9, engine 3b5e7a9, CHIM world 3b5e7a9 |
| CHIM engine version | CHIM 0.1.0, engine 3b5e7a9, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36: CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)](#build-legacy-town-maps-shipped-36-chim-native-seyda-neen-is-still-built-through-the-legacy-chain-65-sn-maps-are-built-and-removed-before-packing-build-time-not-payload)
- [Status: 11 October 2026](#status-11-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Persisting since](#persisting-since)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Source-only carrier, 15 October 2026](#source-only-carrier-15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

# BUILD-LEGACY-TOWN-MAPS-SHIPPED-36: CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)



## Status: 11 October 2026

Open. PERSISTING, NOT RESOLVED. Found by the maintainer from the harvest step's "not admitted" list in the v0.0.36-dev3 build log. Corrected on 11 October 2026 after the finished dev3 run was checked: the legacy Seyda maps do not ship, they cost build time. The ID keeps its first wording ("shipped"); IDs are never renamed.

Progress on v0.0.36-image-speed (not shipped): the CHIM region frame maps are made from the game data
(`--chim-region-rows game-data`, docs/BUILD_MANIFEST.md step 2), so the image step no longer reads the legacy map of a
CHIM region cell. A/B on all 270 cells of the dev3 run: 117 byte-identical, 150 differ only by the world terrain
compiler's unused `wad` key, and three player starts improve: in vf1636 (frame rcp8_p25, cell 8,25), vf2409 (rcp18_p8,
cell 18,8) and vf2435 (rcp19_p8, cell 19,8) a static stands at the cell centre and the legacy start was inside it; the
new start stands on top of it (vf1636 also drops the `wad` key). The stages still build these legacy maps: making them
skip CHIM cells (world terrain, scenery, flora, with the entity tracker counting the CHIM placements) is scheduled as its
own round, not dropped.


Repaired in source on v0.0.36-image-speed (not shipped; persisting until a build shows it): the world map manifest is made from the CHIM coverage before the first stage, and a collision check refuses the plan before any stage when a CHIM cell has a second maintainer (a cell claimed twice, an open-world stage whose work list would make the legacy map of a CHIM region cell, or a legacy map of a CHIM cell made with no recorded reason), listing the cells. World terrain, world scenery and world flora take the CHIM region cells (--chim-regions-cells) and make no map for them (world terrain keeps their directory rows); the image refuses a staged legacy map of such a cell, writes the cell's frame map from the game data, and the entity tracker counts the cell's CHIM placements. The Seyda Neen legacy chain stayed, recorded as "kept because" (source of its frame maps until Seyda Neen is CHIM-native); see below. Tests: tests/test_world_manifest.py (a mixed plan refused with its cells, a cell claimed twice, the legacy method kept with its reason, the builder giving the cells to every open-world stage, the stages making no map for a region cell).

Repaired in source on v0.0.36-seyda-chim (not shipped; persisting until a build shows it), maintainer order 11 October 2026
("we can't have that kind of a workflow, first builds it, then throws them away"): Seyda Neen is CHIM-native. A new
`chim-town-seyda` stage (`tools/chim_town.py` `prepare_seyda`) takes the town frame's and the two opening scenes' (intro
docks, Census courtyard) entities from the scene stage's complete converted town, by the same cut and flora rules and the
same code the legacy chain used, fits the residents on the CHIM frame's own collision and checks the statics against the
CHIM placements both ways. The actor-contact stage and the image step cut no Seyda Neen region map; the image stages no
Seyda Neen legacy map at all. Parity on the v0.0.36-dev3 run's files: the town frame's 243 entities, the docks' 56 and
the courtyard's 14 are identical to the legacy-chain frame maps (three fitted heights differ by 0.00001 unit), the
activated barrel's box is identical, 360 statics match both ways; the stage takes about 40 s. The world manifest's
"kept because: source of the town frame maps" exception is removed: a legacy chain of any CHIM area is refused before
the first stage unless a retired flag labels the build as an A/B regression test (`--legacy-area seyda` keeps the old
method selectable). Still built: the complete town map itself (the bsp stage, the scene chain's carrier of residents,
hands and intro entities); it is never staged or shipped, and moving it off a compiled map is a follow-up. Tests:
tests/test_seyda_chim_native.py, tests/test_world_manifest.py, tests/test_chim_no_legacy.py, tests/test_chim_town.py.

## Symptom

The v0.0.36-dev3 image step builds the 65 Seyda Neen legacy region maps (`sn0xx`) next to the CHIM-native town (`seyda-chim.chim`), runs every per-map pass over them, and removes them before packing. The Seyda chain takes about 62 seconds, and the per-map passes over the maps that are removed are part of the 5 min 22 s optimizer. The image ships no legacy Seyda map. The 42 `bm*` maps in the image are Balmora interiors and must stay. An earlier version of this page said the image shipped 66 Seyda files (232,902,348 bytes) and 42 Balmora legacy files (69,038,532 bytes); that was wrong and is withdrawn.

## Where

The image step's map list and the stages that build or post-process legacy region maps for areas that are on CHIM.

## How it happened

CHIM-native towns replaced the legacy town chain as the source of the town, but the legacy region maps of those towns stayed in the build's map list and are only removed at the end.

## Why it was not caught

The payload was correct, so no check failed, and no check compares the work done with the maps that ship.

## Reproduction

Always: list the image's maps folder of any v0.0.36 CHIM build.

## Persisting since

Persisting since CHIM-LEGACY-CHAIN-33 (v0.0.33-dev, 9 October 2026, open). Earlier attempts and why they did not hold:

- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): measured and recorded; the build only wrote down which legacy stages it still ran. Nothing stopped them.
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md) (v0.0.36-dev1, marked fixed): the image step no longer reads legacy maps for one town. It fixed one entry point.
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md) (v0.0.36-dev1, marked fixed in v0.0.36-dev3): CHIM-native became the default. The legacy maps are still built and removed later.

Each fix changed one flag or one town. None decided per map, before the first stage, what is built.

## Repair

Design default (maintainer, 11 October 2026): when a cell moves onto CHIM, its previous map format is out of the build by default.
The builder derives the legacy map list from one place, the CHIM coverage (CHIM areas and region cells); every stage that
converts, optimizes, harvests or packs legacy maps skips the covered cells (world terrain, scenery, flora, harvest, the BSP
optimizer, the image), unless a recorded engine need keeps one map (for example a door target). The towns' sn0xx/bm0xx maps
go first. Old method selectable only as a labelled regression build. As CHIMport moves inward, every build shrinks and speeds
up by itself.
Builder rule: a legacy map of an area that is on CHIM is not built and not processed unless the engine still loads it (decided once, from the world map manifest of BUILD-CHIM-FRAME-SWAP-LATE-36). Removing them does not shrink the image; it saves build time. Old method selectable only as a labelled regression build.

## Verification

To do: the next build's log shows 0 legacy maps of CHIM areas built, the Balmora interior maps still in the image, and the build time before and after.

## Prevention

A builder gate fails when a legacy map of a CHIM area is built or processed without a recorded reason.

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

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-CHIM-FRAME-SWAP-LATE-36](BUILD-CHIM-FRAME-SWAP-LATE-36.md): The image step builds 335 legacy maps of cells already on CHIM, then removes them before packing
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): Regression: the image step's BSP optimizer pass cache reused 13 of 2,658 maps; its key covers the whole image tool, so any image-code change redoes every map
- [BUILD-PIPELINE-UNDERUTILIZATION-36](BUILD-PIPELINE-UNDERUTILIZATION-36.md): Umbrella: several builder phases run on one core while the rest of the machine idles, and some do work the build no longer needs

<!-- END GENERATED CATEGORY -->
