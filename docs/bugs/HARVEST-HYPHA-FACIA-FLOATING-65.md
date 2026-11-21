# HARVEST-HYPHA-FACIA-FLOATING-65: In Seyda Neen a Hypha Facia mushroom that grows on a tree's side floats in the air

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.66-dev1 at 2026-11-13 (time not recorded): Seen again on v0.0.66-dev1: tree-side mushrooms still hang in the air in Seyda Neen by the lighthouse (cell -2,-9, local about -43 20).
- Reported with v0.0.66 at 2026-11-17 (time not recorded): Seen again on the v0.0.66 release (Bitter Coast, Seyda Neen region): with the reduced tree model (the mesh flora_bc_tree_08 variants, drawn as a solid low trunk) the bracket fungi that grow from the side of the tree are not seen where the original places them: in cell -2,-9 (local 1 90 64) none shows at the trunk, and in cell -2,-8 (local -603 2489 151, a Hypha Facia aimed at, placement 74598) the fungus stands apart from the trunk. A tree drawn as sprites gives no trunk surface to hold a fungus or to pick it, and the radius of the tree blocks the pick of a fungus behind it. Two ways, both to leave the fungus pickable: (a) the fungi are drawn as sprites together with the tree, or (b) the trunk is drawn as polygons so the fungus sits on it (the flora support list, config/flora-support.json, holds the measured shifts).
- Reported with v0.0.67 at 2026-11-20 15:24 +0200: Seen again on the v0.0.67 release image: with the reduced tree model the bracket fungi are no longer at the side of the trunk where the original places them. Also, the vines of that tree model appear to hang in the air; drawing the vines as crossed sprite panels is suggested.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 November 2026, in v0.0.65 |
| Where | Seyda Neen, a tree with the Hypha Facia bracket fungus on its side |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.65 (last seen) |
| Severity | medium: a pickable plant hangs in the air beside its tree |
| Family | Harvestable plants (`harvest`) |
| Playtest version | v0.0.65 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | Raspberry Pi 4B, Amiberry, the v0.0.65 release image |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-13: reported in v0.0.65
- 2026-11-13: seen again in v0.0.66-dev1: Seen again on v0.0.66-dev1: tree-side mushrooms still hang in the air in Seyda Neen by the lighthouse (cell -2,-9, local about -43 20).
- 2026-11-17: seen again in v0.0.66: Seen again on the v0.0.66 release (Bitter Coast, Seyda Neen region): with the reduced tree model (the mesh flora_bc_tree_08 variants, drawn as a solid low trunk) the bracket fungi that grow from the side of the tree are not seen where the ...
- 2026-11-17: v0.0.66: Plan for the tree fungus, three ways, each leaving the fungus pickable and selectable as a method: (a) the fungi drawn as sprites together with the tree; (b) the trunk drawn as polygons so the fungus sits on it; (c) a level of detail by ...
- 2026-11-20 15:24 +0200: seen again in v0.0.67: Seen again on the v0.0.67 release image: with the reduced tree model the bracket fungi are no longer at the side of the trunk where the original places them.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

## Status

Open and persisting. Seen on the v0.0.65 release, again on v0.0.66-dev1 and again on the v0.0.66 release.

## What happens

The bracket fungus (Hypha Facia) that grows from the side of a tree has no trunk to sit on where the tree is drawn as a sprite, so it floats or is missing; with the reduced tree model the fungi are not seen where the original places them. The radius of a sprite tree also blocks picking the fungus behind it.

## Ways to fix it

Each way leaves the fungus pickable and is selectable as a method:

- the fungi drawn as sprites together with the tree;
- the trunk drawn as polygons, so the fungus sits on it (config/flora-support.json holds the measured shifts);
- a level of detail by distance: trees as sprites in the distance and polygons up close, so the fungus sits on a real trunk near the player.

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
- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORE-ROCKS-62](HARVEST-ORE-ROCKS-62.md): The ore and gem rocks in the mines cannot be mined
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): Some mushrooms in the Seyda Neen region cannot be picked: a tree sprite blocks the pick
- [HARVEST-TREE-FUNGUS-62](HARVEST-TREE-FUNGUS-62.md): The bracket fungi growing from the tree trunks cannot be picked
- [HARVEST-WORLD-29](HARVEST-WORLD-29.md): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it

<!-- END GENERATED CATEGORY -->
