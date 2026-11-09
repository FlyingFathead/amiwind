# HARVEST-EXPANSION-FLORA-62: the plants placed by the Tribunal and Bloodmoon masters are not harvestable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 November 2026, in v0.0.61 |
| Where | Organic containers placed by the expansion masters: 731 placements (Tribunal 399, Bloodmoon 332) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61 (last seen) |
| Severity | low: Only in the expansion areas, which the build does not convert yet |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.61 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (counted from the masters and the v0.0.61 build by the flora census) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61 (7 November 2026)._

## Status: 7 November 2026

Open. Found by the flora census of every organic container in the masters (FLORA-FAUNA-COVERAGE-62). Waits for the
areas of the expansions (Mournhold, Solstheim) to be built.

## Symptom

The harvest step reads the base master only. The organic containers that the Tribunal and Bloodmoon masters place
(their own plants and their placements of the base game's mushrooms and fungi) are never indexed.

## Where

Tribunal: 45 small mushrooms, 4 bracket fungi and 350 other plants (Horn Lily, Nirthfly Stalks, Meadow Rye, the
sweetbarrels, the sedges and others). Bloodmoon: 308 plants (belladonna, holly, wolfsbane) and 24 ore rocks. These
are in the areas of the expansions, which the build does not convert yet.

## How it happened

The harvest source was made for the base game's island; its index keys every placement by the base master's digest
and refuses a master with dependencies.

## Why it was not caught

Nothing listed the expansion masters' organic containers before the census.

## Reproduction

Not in game yet: the expansion areas are not in the build.

## Repair

Not repaired. When an expansion area is built, its placements join the index as a new generation (the same way the
bracket fungi joined it, so earlier saves keep their facts), keyed by that master.

## Verification

Counted from the masters by `tools/harvest_flora_census.py`, 7 November 2026.

## Prevention

The census reads every master named in `config/harvest-flora.json` on every build and lists their placements apart;
a master it reads that the config does not name stops the build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- FUNGI-FLOATING-62 (no report page): Bracket fungi float in the air on the Bitter Coast with no tree under them
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORE-ROCKS-62](HARVEST-ORE-ROCKS-62.md): The ore and gem rocks in the mines cannot be mined
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- [HARVEST-TREE-FUNGUS-62](HARVEST-TREE-FUNGUS-62.md): The bracket fungi growing from the tree trunks cannot be picked
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points

<!-- END GENERATED CATEGORY -->
