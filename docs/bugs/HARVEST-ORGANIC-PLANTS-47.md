# HARVEST-ORGANIC-PLANTS-47: only the small mushrooms can be picked; every other harvestable plant is scenery

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 21 October 2026, in v0.0.46 |
| Where | Harvest placement index and saved pick state, indoors and outdoors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: Most original harvestable plants cannot be harvested; no crash or data loss |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.46 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.1, engine unknown, world format 0.7 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (counted from the master and the image's harvest catalogues) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47 (21 October 2026)._

## Status: 21 October 2026

Open. Present in v0.0.46 and every build since harvesting began (v0.0.29). Found while counting the interior plants for
HARVEST-INTERIOR-PICK-47. No repair yet.

## Symptom

In the original game every organic container plant can be harvested: Comberry, Heather, Corkbulb, Trama Root, Black
Anther, Gold Kanet, Stoneflower, Willow Flower, Scathecraw, Kollops, Kwama Egg Sacks and the rest. In AmiWind only the
small mushrooms (Luminous Russula and Violet Coprinus) are pickable; every other harvestable plant is drawn and cannot
be picked, indoors and outdoors.

## Where

Counted from the master against the v0.0.46 image: outdoors 21,238 organic container placements, 21,040 drawn, 934
pickable (all of them small mushrooms); in interiors 3,725 placements, 490 drawn in the shipped rooms, none pickable.
The largest groups in interiors are the Kwama Egg Sacks of the egg mines (1,555, none in a shipped room yet); in the
shipped rooms Heather (25), Corkbulb (16), Trama Root (27), Scathecraw (10), Black Anther (10) and Comberry (6) in the
Vivec plazas, shops and houses.

## How it happened

The harvest work began with the mushrooms of the Bitter Coast and stayed with them: the placement index
(`tools/prepare_harvest.py` `placement_index`) takes only the flora kind `small_mushroom`, and the saved pick state
holds 4,096 placement facts (`AW_HARVEST_SLOTS`), enough for the 2,083 mushrooms but not for the about 25,000 organic
plants of the whole island.

## Why it was not caught

The harvest checks (coverage, geometry gate, pick audit) measure the plants the index contains; nothing compared the
index with every organic container of the master.

## Reproduction

Outdoors near Seyda Neen or indoors in a Vivec plaza: aim at a Comberry bush or a Heather plant: no "E: Pick" prompt.

## Repair

Not repaired. The original rule (OpenMW 0.51 `apps/openmw/mwclass/container.cpp`, `apps/openmw/mwworld/cellstore.cpp`
`CellStore::respawn`): a container with the Respawn flag that was touched gets its contents back when its cell is
loaded and at least `iMonthsToRespawn` game months have passed since that cell last respawned (`iMonthsToRespawn` is 4
in the master: 2,880 game hours). 83 of the 94 flora container records have the Organic and Respawn flags; the Kwama
Egg Sacks are Organic only and do not respawn. OpenMW's graphic herbalism (on by default) changes only meshes that
carry a herbalism switch node; the original meshes do not, so in the original a picked plant stays drawn as an empty
container. AmiWind hides a picked plant (decided for the outdoor mushrooms; HARVEST-WORLD-29) and has no respawn yet.

To extend picking to every organic plant: index every organic container placement (a new index digest), grow the
saved pick state past 4,096 facts (a save format step with a migration of the mushroom facts by their full original
key, as the earlier legacy migration did), and decide respawn by the rule above.

## Verification

Counts from the master and the v0.0.46 image's entity tracker data and harvest catalogues, 21 October 2026.

## Prevention

When the index grows, a test compares the index with every organic container placement of the master and lists what
is left out with a reason.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)

<!-- END GENERATED CATEGORY -->
