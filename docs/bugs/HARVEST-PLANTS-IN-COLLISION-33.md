# HARVEST-PLANTS-IN-COLLISION-33: 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 10 October 2026, in v0.0.33 |
| Where | Converted terrain and flora/rock collision around harvest placements (Bitter Coast) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | low: No longer blocks picking (HARVEST-BITTERCOAST-29); the solids may still stop the player under tree roots and half-bury plants |
| Family | Harvestable plants (`harvest`) |
| Playtest version | AmiWind-v0.0.33 |
| From commit | source 35720ae, engine 35720ae, CHIM world 35720ae |
| CHIM engine version | CHIM 0.1.0, engine 35720ae, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Open. Found by the harvest pick audit built for [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md). Since
v0.0.34 these solids no longer stop picking; the collision shapes themselves are unchanged.

## Symptom

Plants that Morrowind places in the open sit, in the converted maps, with their centre inside a solid:
under a tree's roots inside the tree's convex collision piece, or partly below the converted terrain.
Before v0.0.34 they could not be picked; the solids may still stop the player where Morrowind lets them
walk (under tree roots) and half-bury plants.

## Where

Converted world maps (vf), terrain and flora/rock collision entities around harvest placements, mostly
the Bitter Coast. Of the 934 placed plants on the v0.0.33 maps, 51 could not be picked from anywhere:
32 have their centre inside world collision (terrain above the authored ground), 19 inside a tree or
rock collision entity. Counting every plant, 283 have their centre inside a solid.

## How it happened

Collision of converted scenery is built from convex pieces of the source collision; a piece spanning a
tree's arched roots fills the space under them. Converted terrain approximates the authored heights and
can lie above a plant's authored position.

## Why it was not caught

No check compared harvest placements with collision until the pick audit.

## Reproduction

`tools/harvest_pick_audit.py audit --id1 <image id1>` reports `centre_in_solid` and the enclosing solid
(`centre_solids`: "world" or the collision entity's reference) for every plant.

## Repair

Not decided: collision pieces that keep authored open space under roots (as the town converter's hollow
collision does for Hlaalu underpasses), or snapping plants to the converted ground.

## Verification

Pending.

## Prevention

The pick audit gates every image (no placed plant may be unpickable); a gate on enclosed plants follows
the repair.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENGINE-HARVEST-MESSAGE-BOUND-35](ENGINE-HARVEST-MESSAGE-BOUND-35.md): The harvest pickup message joined lines into a fixed buffer without a bound
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

<!-- END GENERATED CATEGORY -->
