# HARVEST-GEOMETRY-GATE-32: The harvest geometry gate was never re-run on the shipped Seyda Neen maps

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Harvest preparation chain (Seyda Neen, intro docks maps) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | medium: The no-baked-mushroom geometry gate was never re-run on the shipped Seyda Neen maps. |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.32-harvest (not shipped at the time of writing). Found by the builder coverage work (comparing the
v0.0.31 harvest files with their plan).

## Symptom

`reject_existing_geometry` (no baked mushroom left where a harvestable one is placed) was not run again on
the shipped Seyda Neen and intro_docks maps.

## Where

The harvest preparation chain.

## How it happened

Maps changed after the gate ran.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

The image step runs `reject_existing_geometry` on the final map of every map that gets a catalogue,
after the last map change, and stops the build on any failure (BUILD-HARVEST-NOT-BUILT-32). Brush
mushrooms a converter bakes where a harvestable plant goes are removed before the final map passes
(`tools/remove_harvest_geometry.py`), and such a map must then be admitted.

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- The gate passes on all 388 candidate maps, including the 62 Seyda Neen sub-cells and the intro
  docks: the recorded Seyda Neen maps carry no baked harvestable mushroom.
- Without the removal it stops on the 17 Balmora maps that bake mushrooms (134 placements).
- `tests/test_harvest_build.py`: the gate refuses a map with a mushroom bound to a placement and a
  map with scenery at a placement's pose; the removal takes out exactly the bound entity; a map
  whose mushrooms were removed but refused by the heap check stops the build.

## Prevention

Harvest becomes a builder step that rebuilds its catalogues from the maps it ships with, with
the geometry gate in the image step.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
