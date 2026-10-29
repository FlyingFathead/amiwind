# HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47: some mushrooms in the Seyda Neen region cannot be picked because a tree sprite blocks the pick

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 21 October 2026, in v0.0.47-dev1 |
| Where | Every sprite (billboard) tree with harvest plants beside it; first seen near Seyda Neen |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.55 (last seen) |
| Severity | high: maintainer, 29 Oct: billboard trees are unacceptable here; mushrooms grow right next to trees and picking beside a flat tree is really bad |
| Family | Harvestable plants (`harvest`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9 |
| From commit | source 4a2d42b, engine 4a2d42b, CHIM world 4a2d42b |
| CHIM engine version | CHIM 0.2.1, engine 4a2d42b, world format 0.7 |
| Platform or emulator | maintainer's playtest, emulator |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56-dev1 (29 October 2026)._

## Status: 29 October 2026

Open, persisting in v0.0.55, severity raised to high. The maintainer, on the camera-facing billboard trees: "yeah
this is ass", "kind of unacceptable since many mushrooms etc grow directly next to the trees and it's really fucky
to go pick them up if they're just a billboard". So this is not only a Seyda Neen spot: every sprite tree with a
harvest plant at its foot has it, because the flat panel turns with the player and stands between the eye and the
plant from most sides.

Fix direction: no flat camera-facing tree where plants grow beside it. The candidates are in
[the tree study](../WORLD_TREE_SPRITES.md#study-cheap-trees-with-some-depth-29-october-2026): crossed fixed
panels (they stay in place, so the plant stays reachable between them) or the tree's mesh within pick distance of a
harvest plant, measured like for like at 32 MB Fast; and in any case the pick trace must not stop on a sprite
tree's panel. Scheduled in the v0.0.56 TODO (TREES-DEPTH-56).

## Status: 21 October 2026

Open. Cause unknown. Registered from the maintainer's report; no pinned spot yet.

## Symptom

In the Seyda Neen region some mushrooms cannot be picked: the pick does not reach the plant because a tree sprite
stands in the way. The maintainer saw it while playing v0.0.47-dev1.

## Where

The Seyda Neen region, for mushrooms close to sprite trees. The harvest pick test meets the tree sprite's bounds
or collision before the plant. No cell, reference or position is recorded yet.

## How it happened

Unknown. Suggested check: whether the pick trace counts the tree sprite's box, or its collision, as a blocker.
Related earlier findings: the sprite-tree bounds are "too conservative" (TREE-SCALE-001), a
converted tree's convex root piece can swallow a placed plant
([HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md)), and sprite-tree roots extend into pillars
(TREE-PILLAR-28). None of these is shown to be the cause.

## Why it was not caught

The harvest geometry gate checks plant positions against converted collision, not the pick trace from the
player's eye to each plant with the tree sprites in the scene.

## Reproduction

Sometimes: near sprite trees only. To pin it, stand beside a mushroom that will not pick and record the global
position, the plant's reference and the tree's reference.

## Repair

None yet. First step: trace the pick from the player's eye to the plant and report what it hits first (the tree
sprite's bounds, its collision, or something else), then decide whether the sprite must be excluded from the pick
trace.

## Verification

None yet. Fix is verified with the pinned spot in game and a pick test over every harvest plant that has a sprite
tree within the pick distance.

## Prevention

A gate that runs the pick trace from the usual standing positions to each harvest plant and fails on a blocker
that is a sprite tree.

## Related

HARVEST-WORLD-29, [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md),
[HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md), TREE-PILLAR-28,
TREE-SCALE-001.

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
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
