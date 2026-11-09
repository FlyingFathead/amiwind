# HARVEST-TREE-FUNGUS-62: the bracket fungi growing from the tree trunks cannot be picked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 November 2026, in v0.0.61 |
| Where | Bitter Coast trees (Bungler's Bane and Hypha Facia), 813 placements: 724 outdoors, 89 indoors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61 (last seen) |
| Severity | medium: An original harvestable plant kind is scenery; no crash or data loss |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.61 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (counted from the masters and the v0.0.61 build by the flora census) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61 (7 November 2026)._

## Status: 7 November 2026

Repaired in source for v0.0.62 (branch v0.0.62-flora); to be seen in game.

## Symptom

In the Bitter Coast the shelf-shaped fungi that grow from the sides of the trees, Bungler's Bane and Hypha Facia, are
drawn but cannot be picked: no pick prompt, no ingredient. In the original game they are organic containers like the
small mushrooms on the ground, which AmiWind has let the player pick since v0.0.29.

## Where

813 placements in the base master, four meshes (two of each fungus): 724 outdoors (Bitter Coast 667, West Gash 46,
Ascadian Isles 11) and 89 in interiors (caves and houses of the Bitter Coast). The expansion masters place 4 more
(see HARVEST-EXPANSION-FLORA-62).

## How it happened

The harvest work began with the numbered small-mushroom meshes and its placement index took only that kind. The
fungi carry the same organic and respawn flags and the same kind of contents (a leveled ingredient list each), but no
kind of the flora census named their meshes, so they stayed scenery.

## Why it was not caught

Nothing compared the harvestable placements of the build with every organic container of the masters
(HARVEST-ORGANIC-PLANTS-47, Prevention).

## Reproduction

Any Bitter Coast tree with a fungus on its trunk, for example near Seyda Neen or Hla Oad: aim at the fungus; no
"E: Pick" prompt.

## Repair

- The fungi became a harvest kind of their own (`tree_fungus`), picked exactly like the small mushrooms: the same
  catalogues, pick ray and prompt, the same picking sound, the same pick fact, and the fungus is gone after picking,
  through cell changes and save and load. Interiors and every CHIM area get them the same way (the CHIM world and the
  CHIM rooms leave them out and the image places them as harvest entities).
- They join the saved placement index as a second generation after every mushroom: the mushroom slots and the
  earlier index digest stay as they were, and every catalogue names the earlier index as its base, so a save made
  before keeps its picked mushrooms and is taken over by the first pick or first look at a new plant.
- A Bitter Coast map can now hold the 8 mushroom meshes and the 4 fungus meshes together: up to 16 shared models per
  catalogue (was 8).

## Verification

- Tests: the kind, the index generations (earlier slots and digest kept), the catalogue header, the engine takeover
  of an earlier save (facts kept, unrelated saves still refused) and 16 models per catalogue.
- On the base master: 2,896 placements indexed (2,083 mushrooms as before, digest unchanged; 813 fungi after them),
  2,881 harvestable, 15 left as scenery with their reason (owned plants with a charge or gold value).
- Still to see in game: a fungus picked in the Bitter Coast, its sound and message, and the fungus still gone after
  saving, loading and walking away and back.

## Prevention

The harvest step runs a census of every organic container of the masters on every build
(`tools/harvest_flora_census.py`, `config/harvest-flora.json`): every record is harvestable or pending with its
register entry, and every placement of a harvestable kind is placed or listed with its reason; anything else stops
the build.

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
- [HARVEST-EXPANSION-FLORA-62](HARVEST-EXPANSION-FLORA-62.md): The plants placed by the Tribunal and Bloodmoon masters are not harvestable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORE-ROCKS-62](HARVEST-ORE-ROCKS-62.md): The ore and gem rocks in the mines cannot be mined
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

<!-- END GENERATED CATEGORY -->
