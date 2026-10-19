# HARVEST-CHIM-REGION-LOSS-41: Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41-dev3 |
| Where | CHIM region cells (-9,4) (-9,5) (-4,-8) (-8,-2) (-5,-8) (-6,-7) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41-dev3, v0.0.41-dev4 (last seen) |
| Severity | high: a regression: up to half of a cell's harvestable plants missing; blocks the final build |
| Family | Harvestable plants (`harvest`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev4_full-rings01234-r3_87f6534 |
| From commit | source 87f6534, engine 87f6534, CHIM world 87f6534 |
| CHIM engine version | CHIM 0.2.0, engine 87f6534, world format 0.7 |
| Platform or emulator | not in game (the image step's entity tracker records the loss at build time) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41 (16 October 2026)._

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
The image step's entity tracker of the v0.0.41-dev4 build recorded harvestable plants lost against the
v0.0.31 baseline on six CHIM region cells:

| Cell | Original plants | Baseline placed | dev4 placed | Missing in dev4 (reference numbers) |
| --- | --- | --- | --- | --- |
| (-4,-8) | 8 | 8 | 6 | 267471, 267472 |
| (-5,-8) | 10 | 5 | 5 (other plants) | 267696, 267697, 267698, 267741, 267743 |
| (-6,-7) | 33 | 17 | 17 (other plants) | 267827-267829, 267831, 267832, 267937, 267940, 267982-267985, 268010, 268011, 268083-268085 |
| (-8,-2) | 15 | 9 | 7 | 237673, 237702-237705, 237707, 237727, 237728 |
| (-9,4) | 30 | 23 | 12 | 209349-209353, 210664-210667, 210687-210690, 210793-210795, 210805, 210806 |
| (-9,5) | 39 | 24 | 15 | 209261, 209263, 209264, 209266-209286 |

Every missing plant is a harvestable mushroom of the harvest step. The plants the cells still placed are the
other flora containers, which the CHIM world places itself. The dev builds passed only with
`--accept-entity-loss`.

## Where
- `tools/harvest_build.py plan_rows`: the harvest plan took the open-world maps from the region directory and
  kept only those with a legacy map file in `maps/`. A CHIM region cell has no legacy map (no stage makes one,
  docs/BUILD_MANIFEST.md step 2), so it got no catalogue.
- `tools/chim/build.py harvest_numbers`: the CHIM world leaves every harvest placement out of its frames,
  because the image installs them as catalogues.
- `tools/chim/frame_map.py install_region`: when a region frame map replaces an open-world map, the map's
  catalogue was removed ("its plants are not on the CHIM region frame map yet").

## How it happened
A plant of a CHIM region cell was left out of the CHIM world and got no catalogue, so it was nowhere in the
image. The engine already loads `harvest-<map>.txt` for the map it loads (`AW_HarvestBegin`, by the map
name), and a region frame map keeps its cell's map name (`maps/vfNNNN.chim`), so a catalogue under that name
would have worked: the catalogues are AWH4 (proxies that need no map entity), as on the CHIM town frames.
The harvest plan was never extended to the region frames when they replaced the open-world maps.

## Why it was not caught
- Region maps overlap: each legacy open-world map's catalogue also holds the plants of its neighbours'
  borders. The entity tracker counts a plant as placed when any map places it, so while a neighbouring cell
  was still a legacy map, its catalogue hid the loss. In dev3 cell (-9,4) counted all 30 plants, through
  the catalogues of two legacy neighbours, although the cell itself was already on CHIM. The loss showed
  only when the ring 4 cells around it went to CHIM in dev4.
- The baseline is v0.0.31's, so the tracker checks only the cells that had plants then; other CHIM cells
  with plants were not compared at all.
- No check compared the plants the CHIM world leaves out with the catalogues the image ships.

Measured with the new check (below) on the finished builds: dev3 left 213 plants out of their own cell's
frame map (19 frame maps), dev4 413 (33 frame maps).

## Reproduction
Any build with CHIM region frames on cells with harvestable mushrooms (the Bitter Coast and the West Gash
coast): the cell's frame map has no catalogue, and the entity tracker reports the loss once no legacy
neighbour carries the plants.

## Repair
- `harvest_build.plan_rows` takes the CHIM world's region frames (`chim.frame_map.region_frame_rows`):
  a region cell's row stays without a legacy map, with the frame's origin (the frame map's coordinates) and
  `chim=True`; a divided cell's alias rows are left out (the engine never loads them). The image step writes
  each frame map's catalogue after the per-map heap check, like the CHIM town catalogues; the geometry gate
  and the per-map heap check skip it (the frame map does not exist yet and the CHIM world has no baked
  mushroom). A CHIM map over the runtime bounds (256 plants, 8 models) now stops the build instead of losing
  its plants.
- `install_region` keeps the catalogue the harvest step wrote for the frame map (named with its SHA-256 in
  the harvest staging receipt) and refuses a missing or changed one; any other catalogue of a replaced map
  leaves as before.
- The entity tracker counts a region frame's catalogue with its CHIM placements
  (`build_aga.chim_region_placements`), and the payload preflight plans those catalogues too.
- Follow-up: the first fix stopped the v0.0.41 release build at the payload preflight (9.9 s into the
  image step): "Harvest catalogue has no matching map: harvest-vf0225.txt". The preflight planned the region
  frame catalogues but its planned map set (`payload_preflight.planned_maps`) held only the town frame maps,
  not the region frame maps, so every planned region catalogue had no map (vf0225 is the first by name).
  `planned_maps` now adds every CHIM region frame map under the name it is installed under
  (`chim.frame_map.region_map_names`, one per frame). Regression test:
  `tests/test_payload_preflight.py` (`test_region_frame_maps_are_planned_maps`). The unit tests of the first
  fix replaced `planned_catalogues` with a stub, so the preflight never saw a region catalogue.

## Verification
- Regression tests: `tests/test_harvest_build.py` (region rows, catalogue written for a frame, runtime
  bound, coverage check), `tests/test_chim_regions.py` (the frame map keeps its catalogue; a changed one is
  refused), `tests/test_payload_preflight.py`.
- The harvest part of the image step replayed on the dev4 inputs (its harvest source, CHIM world and final
  maps): 47 region frame maps get a catalogue with 571 plants, 229 of them placed by no map before; exterior
  harvestable plants placed go from 8,077 to 8,306. All six cells place every original plant ((-4,-8) 8/8,
  (-5,-8) 10/10, (-6,-7) 33/33, (-8,-2) 15/15, (-9,4) 30/30, (-9,5) 39/39), and the entity tracker reports no
  harvest loss against the baseline. The coverage check passes: 601 plants left out by the CHIM world, 409 in
  their own cell's frame map catalogue, 192 in another shipped catalogue (CHIM town sub-cells or legacy maps).
- The release build's staged inputs (723 cells): the payload preflight's harvest check fails on
  harvest-vf0225.txt before the follow-up and passes after it (87 planned catalogues, 68 of them region frame
  maps, every one with a map in the planned set). The harvest install and coverage check on the same inputs
  (with the Seyda Neen and Balmora region tables of an earlier run, which the image step writes later): 68
  region frame catalogues; 775 plants left out by the CHIM world, 651 in their own frame map's catalogue, 124
  in another shipped catalogue, none left out.
- Pending: a full build, and an in-game look at a region frame's mushrooms (picking, saved state across the
  border to a neighbour map).

## Prevention
- Island-wide check `harvest_build.require_chim_coverage`, run twice by the image step: right after the
  catalogues are written (fail fast, before the frame maps) and on the final payload. Every plant the CHIM
  world leaves out (the CHIM receipt's `harvest_removed`, per frame) must be in a shipped catalogue; a plant
  in a CHIM region cell must be in that cell's frame map catalogue, whatever a neighbour's overlap carries;
  on the final payload each such catalogue needs its frame map. Any plant left out stops the build and is
  named with its reference, cell, frame and map (`harvest-chim-coverage.json`,
  `harvest-chim-coverage-final.json`). It fails on the dev3 and dev4 payloads.
- Open: the CHIM frame-map heap gate does not count harvest catalogues and their models, on town frames or
  region frames; the legacy per-map heap check did.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map

<!-- END GENERATED CATEGORY -->
