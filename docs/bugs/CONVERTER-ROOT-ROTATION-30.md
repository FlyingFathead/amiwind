# CONVERTER-ROOT-ROTATION-30: NIF root-node rotation applied to placed meshes

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 October 2026, in v0.0.30-dev |
| Where | Scenery converter (tools/prepare_scenery.py), placed meshes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.30-dev3 (last seen) |
| Severity | high: Walls turned or missing and see-through holes in interiors; one exterior placement still wrong. |
| Family | Object placement and in-game geometry (`placement-geometry`) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Interiors fixed in v0.0.30-dev3 (Balmora Temple, Tharys Ancestral Tomb, five
fireplace interiors). Still open: one Balmora exterior placement
(`furn_pathspear_03`) in the exterior pipeline, so the bug stays open.

Cause identified and repaired in the converter (`tools/prepare_scenery.py`,
`model_geometry`). Rebuilt maps first shipped in v0.0.30-dev3 (see the status
above).

## What was wrong

Morrowind ignores the rotation stored on a mesh's NIF root node, while keeping
its translation and scale. The converter applied the root rotation on top of
each placement, so any mesh with a rotated root was turned around its own
origin. Most meshes have an identity root and were unaffected.

## Affected converted maps

| Map | Meshes with a root rotation | Effect | Status |
| --- | --- | --- | --- |
| Balmora Temple (`bmtemple`) | Velothi kit `in_v_s_int_wall_01`, `in_v_s_int_entrance_01`, `in_velothismall_room_05`, `in_velothilarge_corner_01` (90 degrees), `in_velothilarge_cap_01` (180 degrees) | Missing and edge-on walls, see-through holes, objects appearing to float | Rebuilt; matches OpenMW at the reported views in FS-UAE. See [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md). |
| Tharys Ancestral Tomb (`tharystomb`) | `in_v_s_int_wall_01`, `in_v_s_int_entrance_01` (90), `in_velothilarge_cap_01` (180) | See-through holes where walls should be | Rebuilt; before/after FS-UAE views show solid walls; owner rated the screenshots 5/5. |
| Arrille's Tradehouse (`tradehouse`), Eldafire's House (`eldafire`), Draren Thiralas' House (`draren`), Terurise Girvayne's House (`terurise`), Census and Excise Office (`census`) | `in_nord_fireplace_01` (180) | Fireplace turned to face away from the room; a few nearby objects were dropped as buried inside the misplaced fireplace | Rebuilt; only the fireplaces changed among existing placements. Recovered objects: a lantern hook and two ferns (Tradehouse), two grass tufts (Terurise), one object (Census). |
| Balmora exterior | `furn_pathspear_03` (90), one placement | Turned a quarter turn | Pending: separate exterior pipeline. |

Root translations (for example `contain_crate_01`, z -32) were already applied
correctly; crates rest on the floor only with that offset, so it is kept.

## Verification per rebuilt map

- The release finishing chain applied to the cached conversion reproduces the
  sealed map byte for byte (lumps 1 to 14) before any change is made.
- After the fix, every model without a root rotation is byte-identical (or
  differs by float rounding only); textures are identical; only the listed
  meshes change. Existing placements keep their order; objects the converter
  previously culled as buried may be admitted again. The sealed worldspawn
  metadata and actors are carried over unchanged.
- Regression test: `tests/test_scenery_root_transform.py`.
- Base-game scope: 487 meshes in the original archives have a root transform,
  369 of them with a rotation; future conversions of other areas use the
  repaired converter.

## Still to verify

Ordinary walking and collision through the rebuilt interiors, the Balmora
exterior placement, and owner playtest of the fireplace interiors.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing

Related bugs in other categories:

- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes

<!-- END GENERATED CATEGORY -->
