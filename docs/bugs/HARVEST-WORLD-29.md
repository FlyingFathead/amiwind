# HARVEST-WORLD-29: Original mushroom placement, picking and persistent state worldwide

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | unknown, in v0.0.29-dev4 |
| Where | Mushroom placement and picking across world maps |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29-dev4, v0.0.30-rc1 (last seen) |
| Severity | medium: Worldwide harvest incomplete: 43 maps withheld; picking works where admitted. |
| Family | Harvestable plants (`harvest`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-05: HARVEST-WORLD-29: persistent mushroom state and map admission: Category/status: Missing feature / In progress.
- 2026-10-06: HARVEST-WORLD-29: bounded dev4 native pickup result: One original Luminous Russula showed its name and E: Pick, then displayed "Picked up 1 Luminous Russula." and disappeared.
- 2026-10-06: 6 October 2026: bounded native lighting and exact-storage progress: World admission now models 347 of 390 exterior maps within budget; 43 remain withheld.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md): Extra CHIM-native areas get no harvest catalogue: their plants cannot be picked
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [FUNGI-FLOATING-62](FUNGI-FLOATING-62.md): Bracket fungi float in the air on the Bitter Coast with no tree under them
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-CHIM-REGION-LOSS-41](HARVEST-CHIM-REGION-LOSS-41.md): Harvestable plants lost on CHIM region cells: six cells place fewer or different plants than the baseline
- [HARVEST-EXPANSION-FLORA-62](HARVEST-EXPANSION-FLORA-62.md): The plants placed by the Tribunal and Bloodmoon masters are not harvestable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-HYPHA-FACIA-FLOATING-65](HARVEST-HYPHA-FACIA-FLOATING-65.md): In Seyda Neen a Hypha Facia mushroom that grows on a tree's side floats in the air
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORE-ROCKS-62](HARVEST-ORE-ROCKS-62.md): The ore and gem rocks in the mines cannot be mined
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- [HARVEST-TREE-FUNGUS-62](HARVEST-TREE-FUNGUS-62.md): The bracket fungi growing from the tree trunks cannot be picked

<!-- END GENERATED CATEGORY -->
