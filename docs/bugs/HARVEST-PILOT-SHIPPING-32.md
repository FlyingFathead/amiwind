# HARVEST-PILOT-SHIPPING-32: 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Seyda Neen harvest catalogues (24 maps) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | high: Builder shipped the six-plant pilot catalogue instead of the full one. |
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

24 Seyda Neen maps ship the dev4 pilot catalogue (six plants) and 3 pilot models instead of the full
catalogue.

## Where

v0.0.31 harvest files for those maps.

## How it happened

The pilot was never replaced. The standalone chain also could not make the whole set in one run:
`prepare_harvest_alias.convert_plan` caps the entire run at 8 shared models ("External model
registry exceeds 8 shared models"), while the master has 8 non-pilot models and v0.0.31 shipped 11
including the pilot ones, so the shipped set was assembled from three separate runs, and the
pilot run's results stayed in.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

The harvest step generates every catalogue with the same settings (256 plants per map, the runtime
bound) and converts the models once (BUILD-HARVEST-NOT-BUILT-32); nothing is carried forward, so no
pilot catalogue or pilot model can ship. The new step (commit 0331f76) checks the runtime limit of 8
models per map instead of per run (`tools/harvest_build.py`: a map over the plant or model limit is
refused), so one run makes every catalogue.

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- 8 shared models, byte-identical to v0.0.31's 8 non-pilot models; the 3 pilot models are gone.
- Every catalogue is a generated AWH4 catalogue of its map's full placement set; the Seyda Neen
  results are in HARVEST-SEYDA-STALE-32.

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
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
