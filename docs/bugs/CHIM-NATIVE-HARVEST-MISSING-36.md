# CHIM-NATIVE-HARVEST-MISSING-36: Extra CHIM-native areas get no harvest catalogue

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.36-dev1 |
| Where | tools/harvest_build.py plan_rows: CHIM-native harvest planned only for Seyda Neen and Balmora |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev1 (last seen) |
| Severity | medium: Every CHIM area beyond the two towns loses harvestable plants that the legacy maps had |
| Family | Harvestable plants (`harvest`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source be5d6d3, engine be5d6d3, CHIM world be5d6d3 |
| CHIM engine version | CHIM 0.1.0, engine be5d6d3, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41-dev5 (16 October 2026)._

## Status: 10 October 2026

Open. Found while fixing BUILD-IMAGE-CHIM-NATIVE-TOWN-36.

## Symptom

A CHIM-native area other than Seyda Neen and Balmora (first case: the Bitter Coast test area) is built with no
harvest catalogue, so its mushrooms and plants are expected not to be pickable, although the legacy maps of the same
cells had them.

## Where

`tools/harvest_build.py`, `plan_rows`: CHIM-native harvest rows are planned only for the two towns.

## How it happened

CHIM-native harvest was written for the two CHIM towns; extra areas from the town table were not part of it.

## Why it was not caught

No build had an extra CHIM-native area before, and no check compares an area's harvest catalogue with the
harvestable placements of its cells.

## Reproduction

Always: build an extra town CHIM-native (`--chim-native-towns on --extra-town ID`) and look for its catalogue.

## Repair

Planned: plan harvest rows for every CHIM-native area from the area list, reusing what the legacy harvest stage made
for those cells.

## Verification

To do: the Bitter Coast area's catalogue lists its harvestable placements; a pick test in game.

## Prevention

A check that every CHIM area's harvestable placements are in its catalogue.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): The image step of a CHIM-native town read legacy region maps that are never built: the Bitter Coast test build failed at the end of its image step on maps/bc000.bsp

<!-- END GENERATED CATEGORY -->
