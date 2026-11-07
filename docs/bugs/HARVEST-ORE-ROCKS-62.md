# HARVEST-ORE-ROCKS-62: the ore and gem rocks in the mines cannot be mined

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 November 2026, in v0.0.61 |
| Where | Raw ebony, raw glass and diamond rocks in mines and caves, 234 placements, all indoors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61 (last seen) |
| Severity | low: An original harvestable container kind is scenery; no crash or data loss |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.61 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (counted from the masters and the v0.0.61 build by the flora census) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61 (7 November 2026)._

## Status: 7 November 2026

Open. Found by the flora census of every organic container in the masters (FLORA-FAUNA-COVERAGE-62). No repair yet.

## Symptom

The raw ebony, raw glass and diamond rocks inside the mines and caves are drawn but cannot be taken from. In the
original game each is an organic container: activating it gives its ore or gem.

## Where

234 placements, all indoors: 210 in the base master (raw ebony 94, raw glass 88, diamonds 28) and 24 in the
Bloodmoon master. 22 records.

## How it happened

Harvesting covers the plant kinds of the census (the small mushrooms, and since v0.0.62 the bracket fungi on the tree
trunks); the ore rocks are no plant kind and were never indexed.

## Why it was not caught

Nothing compared the harvestable placements with every organic container of the masters before the census.

## Reproduction

Inside any ebony or glass mine (the Caldera mine, for one): aim at an ore rock; no prompt.

## Repair

Not repaired. The harvest path already fits (an organic container with an ingredient-like item list, picked once,
the fact saved); unlike a plant, the rock should stay drawn when emptied (it is part of the cave wall), which the
harvest path does not do yet. The index has room (2,896 of 4,096 saved facts in use).

## Verification

Counted from the masters by `tools/harvest_flora_census.py`, 7 November 2026.

## Prevention

The census runs on every build; this group is listed as pending under this entry in `config/harvest-flora.json`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXPANSION-FLORA-62](HARVEST-EXPANSION-FLORA-62.md): The plants placed by the Tribunal and Bloodmoon masters are not harvestable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- [HARVEST-TREE-FUNGUS-62](HARVEST-TREE-FUNGUS-62.md): The bracket fungi growing from the tree trunks cannot be picked
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

<!-- END GENERATED CATEGORY -->
