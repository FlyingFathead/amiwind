# HARVEST-BITTERCOAST-29: Only one of three nearby Bitter Coast mushrooms can be picked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 6 October 2026, in v0.0.29-rc2 |
| Where | Bitter Coast cluster 266620-266622 (map vf0850 and its neighbours); aw_harvest_runtime.c target() |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29-rc2, v0.0.33 (last seen) |
| Severity | medium: Placed mushrooms that are drawn cannot be picked: 51 of 934 plants island-wide |
| Family | Harvestable plants (`harvest`) |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Cause found and fixed in source for v0.0.34 (engine pick rule plus an island-wide pick audit that
gates the image); owner playtest pending. Seen again by the owner in v0.0.33 at the same cluster.

## Symptom

In the Bitter Coast, of three Luminous Russula growing together, one can be picked; looking at the
other two shows no prompt and the use key does nothing. Reported in v0.0.29-rc2 (global about
-15287 -59485 735) and again in v0.0.33 (global -15174 -59631 692, local -209 -59 -210, map vf0850,
facing west).

## Where

- The three plants are references 266620, 266621 and 266622 (`flora_bc_mushroom_02`, `_01`, `_05`;
  all Luminous Russula, organic containers with the same leveled list). All three are in the
  harvest catalogues of the maps around them (vf0770 to vf0852); species and catalogues are not the
  cause.
- Engine: `aw_harvest_runtime.c` `target()`, the pick ray of the prompt and the use key.

## How it happened

`target()` traces a point 72 units along the view (`SV_Move`, world and solid entities) and accepts a
plant only when its box is entered before that trace hits something. Collision of converted scenery
is an approximation: the Bitter Coast tree beside the cluster (reference 266608, drawn as a sprite)
has a convex collision piece that also fills the open space under its roots, where 266621 and 266622
grow. The view trace stops on that invisible solid before it reaches either plant, so neither can be
the target; 266620 stands just outside it.

## Why it was not caught

The v0.0.29 report was recorded without map or reference IDs and never reproduced. No check replayed
the pick ray: the harvest gates check catalogues, bounds, heap and geometry clearance, not whether a
placed plant can actually be picked.

## Reproduction

Offline, with `tools/harvest_pick_audit.py audit` on the v0.0.33 image: at the owner's position the
replayed pick ray picks 266620 and is stopped by 266608's collision for the other two (both have
their centre inside that solid). Island-wide, 51 of the 934 placed plants could not be picked from
any standing position within reach (32 Luminous Russula, 19 Violet Coprinus). Every one of the 51 has
its centre inside a solid: 32 inside world collision (terrain), 19 inside a tree's or rock's
collision entity.

## Repair

Shared layer, one rule for every map type (legacy maps and CHIM, brush plants and alias proxies): a
solid that contains the plant's own centre does not hide that plant. `target()` keeps the earlier
test for every plant (box entered before the view trace's hit) and, only for a plant whose box lies
on the ray but beyond the hit, makes a point test at the box centre; if that point is inside a solid,
the plant stays a candidate. A wall between the eye and a plant in the open still hides it.

## Verification

- Native tests: the runtime fixture (brush plants) and the alias-proxy fixture each check that a
  solid in front hides the plant and that a solid enclosing the plant does not.
- `tools/harvest_pick_audit.py` on the v0.0.33 maps: 51 plants unpickable with the earlier rule, 0
  with the new one (934 plants, 325 maps); 9 plants have no standing position within reach (water or
  steep ground) and are reported, not judged.
- Not yet: owner playtest at the reported cluster.

## Prevention

The image step runs the pick audit on the final maps right after the harvest catalogues are
installed, before any disk is made, and stops the build if a placed plant cannot be picked
(`config/harvest-pick-known.json` lists accepted exceptions with their bug ID; it is empty). The
collision approximations that enclose plants are tracked as
[HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

<!-- END GENERATED CATEGORY -->
