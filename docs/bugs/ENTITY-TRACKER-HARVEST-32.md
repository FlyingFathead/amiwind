# ENTITY-TRACKER-HARVEST-32: The entity tracker did not count plants placed by harvest catalogues

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Entity tracker (tools/entity_tracker.py), harvest catalogues |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Tracker undercounts catalogue plants, so a plant loss could be hidden. |
| Family | Harvestable plants (`harvest`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (commit 0331f76); not shipped at the time of writing.
Found by the builder harvest step work (BUILD-HARVEST-NOT-BUILT-32).

## Symptom

The entity tracker counted only placements found in a map's BSP. Plants placed through a map's
harvest catalogue read as "not placed": v0.0.31's 7,336 world plants, and removing Balmora's baked
mushrooms (replaced by harvestable ones) would have looked like a loss against a baseline.

## Where

`tools/entity_tracker.py`.

## How it happened

Harvest catalogues were added to the payload after the tracker, and it never read them.

## Why it was not caught

Harvest data was made outside the builder, so the tracker's placed counts were never compared
before and after a harvest change.

## Reproduction

Run the entity tracker on a v0.0.31 image: harvest plants count as missing.

## Repair

`entity_tracker.harvest_refs` reads the references of each map's harvest catalogue; a map's placed
set is its BSP references plus its catalogue's.

## Verification

`tests/test_harvest_build.py` `test_entity_tracker_counts_catalogue_plants` (catalogue references
read; an empty catalogue gives none). A finished image's tracker report is pending.

## Prevention

That test; the tracker is run after the harvest install in the image step.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
