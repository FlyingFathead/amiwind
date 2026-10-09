# CENSUS-ENTITIES-30: misplaced objects in the Census and Excise Office

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.30-dev5 |
| Where | Census and Excise Office interior map |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.30-rc1 |
| Severity | high: Player fell through the upper floor; objects drawn as the wrong models (67 of 140). |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| Playtest version | v0.0.30-dev5 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Fixed in v0.0.30-rc1 and owner-accepted (WinUAE playtest, 7 October 2026:
"Census office interiors now work"). Present only in v0.0.30-dev5;
v0.0.30-dev4 was correct.

## Symptom

Reported in a v0.0.30-dev5 playtest of the Census and Excise Office:

- The player fell through the upper floor into the room below, and from there
  saw a black hole in the ceiling (HUD position -26 30 2, looking up).
- A rug stood upright on the upper floor (positions -3 -8 72 and 11 13 84).
- A tapestry poked out of a bookshelf (16 -82 77).

The fireplace and its new flames were correct.

## Where

Only the Census map (`id1/maps/census.bsp`). The engine was not involved: the
same symptoms appear with the dev4 engine on the dev5 map. The rebuilt Balmora
Temple from the same build step was checked and is correct.

## How it happened

A converted interior map stores two things that must agree:

- the geometry of every placed object as a numbered brush model (`*1`,
  `*2`, ...), and
- the object list (the map's entity lump): each entry names its model number
  together with the object's position and rotation.

1. The v0.0.30-dev3 rebuild (root-rotation converter fix) admitted one object
   that the old, misplaced fireplace had hidden as buried: a lantern hook. It
   became model `*71`, and every later model moved up by one number. dev3 and
   dev4 wrote a matching object list, so they were correct.
2. The dev5 lighting step added flame entities to the Census map. It rebuilt
   the geometry from the dev3 conversion but kept the object list of v0.0.29,
   which still had the old numbering.
3. In dev5, 67 of the 140 placed objects therefore pointed at their
   neighbour's model. Each was drawn and collided as a different object at its
   own position and rotation: a floor piece became something else (the hole and
   the fall), a rug took a shape meant to stand upright, a tapestry took the
   bookshelf's place.

## Why it was not caught

The dev5 gates compared the map's geometry with dev4 (identical apart from
the expected changes) and checked the flames in place. Nothing compared the
object list with the geometry it was packed with, and the in-game checks did
not cover the affected rooms.

## Reproduction

- Data: the dev4 and dev5 maps have identical geometry lumps; only the
  entity lump differs. Mapping each object reference to its model number:
  rug `321415` is `*87` in dev4 and `*86` in dev5; 67 of 140 differ.
- In game: the dev5 engine on fresh disk copies, teleport to the Census office
  (`dbg tp census`), `noclip`, `aw_view` to the four reported positions. The
  dev5 map shows the reported faults.

## Repair

The repaired map keeps dev5's geometry and flames and uses dev4's object list
with the 51 flame entities appended. Gates on the result: geometry lumps
identical to dev4 and dev5; all 140 object-to-model pairs identical to dev4;
flames identical to dev5.

## Verification

Same engine, same disks, only the map exchanged, at the four reported
positions: the repaired map shows the floor/ceiling intact with its
chandeliers, flat rugs, tapestries on the walls and the bookshelf in place.
The exact v0.0.30-rc1 disks were checked at the same positions afterwards.
The owner playtest of v0.0.30-rc1 confirmed the interiors work.

## Prevention

The lighting rebuild now keeps the object list of the map it replaces and
stops unless every object's model number matches the rebuilt geometry. Any
step that combines an object list with geometry from another build must
check that pairing before packaging.

## Related

AW-20260928-11 (Census missing floor and wall, falling into the void, fixed
in v0.0.21-dev3) had the same symptom from a different cause: a missing room
piece in an early conversion.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing

<!-- END GENERATED CATEGORY -->
