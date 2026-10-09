# HARVEST-SEYDA-STALE-32: v0.0.31 ships Seyda Neen harvest catalogues made for older map versions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Seyda Neen and docks harvest catalogues (46 maps) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | medium: Shipped plant catalogues do not match their maps in 46 maps. |
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

46 maps (45 Seyda Neen sub-cells and intro_docks) ship harvest catalogues whose pinned map hashes
differ from the shipped maps. The private queue had noted 193 of 452 Seyda plants outside their map's
new coverage, to be rebuilt before v0.0.31 final; that was not done.

## Where

`id1/harvest-sn*.txt`, `harvest-intro_docks.txt` in v0.0.31.

## How it happened

The Seyda maps were rebuilt; their harvest catalogues were not.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

Every Seyda Neen and intro docks catalogue is now made by the image step from the region table and
maps the image ships (BUILD-HARVEST-NOT-BUILT-32); under the BUILD-SEYDA-REGEN-30 exception those
are the recorded v0.0.31 maps, so the catalogues match them.

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- 63 Seyda Neen and docks maps cover plants (62 sub-cells and intro_docks); the geometry gate passes
  on all of them.
- Of v0.0.31's 46 catalogues: intro_docks and 4 sub-cells keep the same placement set
  (byte-identical); 39 change their placement set; sn000 and sn005 cover no plant under the current
  layout and get none; 19 sub-cells that had none (sn037 to sn051, sn054 to sn057) get one.
- 55 sub-cells admitted with 536 plants; sn018, sn019, sn020, sn021, sn026, sn035 and sn055 are
  refused by the heap check (HEAP-SEYDA-OVERLAP-32) and ship without harvest.
- `tests/test_harvest_build.py`: plan rows from the staged Seyda Neen, Balmora and docks tables.

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
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)

<!-- END GENERATED CATEGORY -->
