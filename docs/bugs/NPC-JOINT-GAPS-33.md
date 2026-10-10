# NPC-JOINT-GAPS-33: NPC bodies open at the joints because each body part is reduced on its own

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | NPC model baker (tools/npc_geometry.py simplify_shape), every humanoid model |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: Visible openings at necks, wrists, elbows, knees and clothing edges on many NPCs; gallery and residents alike. |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine cb44369 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Present in every build that converts NPCs (measured on the v0.0.32 release gallery and on
the gallery built from parts on the branch v0.0.33-modular-npc, not shipped at the time of
writing). Both methods bake the same parts the same way, so both have the same gaps. Design and
numbers: [MODULAR_NPCS.md](../MODULAR_NPCS.md#joint-seams).

## Symptom

Owner, 9 October 2026: humanoid bodies sometimes show gaps and openings. Morrowind builds a body
from separate meshes (head, neck, chest, groin, upper arms, forearms, wrists, hands, upper legs,
knees, ankles, feet; clothing and armour replace some of them) whose rims meet at the joints.
After conversion the background shows through at some of those joints.

ISLAND_NUMBERS

## Where

`tools/npc_geometry.py`, `simplify_shape` (called from `bake` for every shape over its triangle
quota): fast_simplification reduces each shape alone and also collapses rim edges, so a part's rim
moves or loses vertices and no longer meets the rim of the part beside it. Every humanoid model is
affected: gallery models, residents and the town imports. Creatures are separate meshes and were not
audited.

## How it happened

The baker splits one triangle budget (480 faces) over the shapes of an outfit and reduces each
shape independently to its share. Nothing ties two rims that meet at a joint together. The same
mechanism opened the shell plates of a static model on another branch (static meshes,
boundary-locked reduction there).

## Why it was not caught

No check compared the reduced model with the source at the joints; budget audits count faces and
vertices only. The gallery is inspected by eye, and small openings are easy to miss at gallery
scale.

## Reproduction

`tools/npc_seam_audit.py audit` with a parts store (posed source parts) and a gallery output: for
every joint rim (a rim within 0.05 units of another part), a point 0.5 units in from the rim on the
part's own source surface must stay within 0.25 units (two alias grid steps) of the reduced model.

## Repair

Measured prototypes on 20 appearances (same budgets, same cascade):

| Reduction | Open joint share | Largest gap | Faces (mean) | Needed the 1,024-face profile | Bake time |
| --- | --- | --- | --- | --- | --- |
| Today (rims free) | 0.206 | 1.65 | 491 | 0 of 20 | 1x |
| All rims locked (boundary-locked quadric) | 0.018 | 1.48 | 686 | 10 of 20 | 7.5x |
| Joint rims only locked | 0.023 | 1.48 | 702 | 10 of 20 | 9x |
| Rim vertices snapped back to the source rim | 0.197 | 1.71 | 489 | 0 of 20 | 1.1x |

(Measured with the first, rim-line version of the audit, which undercounts one-sided openings; the
island-wide numbers above use the inset version.) Locking rims closes the joints but body-part rims
carry so many vertices that half the outfits then exceed the 666-face alias limit: not acceptable
at the same budget. Snapping alone does not help, because the two sides keep different subsets of
the rim. Planned repair: coordinated rim reduction, where both parts that meet at a joint reduce the
shared rim to the same subset of its source vertices (chosen from the rim's own geometry, so both
sides choose alike), lock that subset and let only interior edges and the remaining rim vertices
collapse onto it. Selectable next to today's reduction (DON'T DELETE ANY METHOD).

## Verification

Not repaired yet. The audit itself is tested (`tests/test_npc_parts.py`: a closed joint measures
nothing open, a pulled-back part opens it, the check names the open appearance).

## Prevention

The gallery built from parts runs the joint-seam audit over every appearance and fails when the
island-wide open joint length, the number of appearances with open joints or the largest gap
exceeds the recorded limits (`config/npc-seam-limits.json`): no new gaps, and a repaired joint
cannot open again. The limits are lowered as the repair lands.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [CONVERT-COLLISION-FALLBACK-32](CONVERT-COLLISION-FALLBACK-32.md): Five Balmora meshes fall back to a collision union in qbsp
- [CONVERT-DEGENERATE-FACES-32](CONVERT-DEGENERATE-FACES-32.md): The converter writes degenerate faces (no area, slivers, repeated vertices)
- [CONVERT-FACE-PLANE-32](CONVERT-FACE-PLANE-32.md): Converter takes a merged face's plane from its first three vertices
- [CONVERT-FACE-WINDING-32](CONVERT-FACE-WINDING-32.md): Six prison faces are wound opposite to their plane side
- [CONVERT-MERGE-NONPLANAR-32](CONVERT-MERGE-NONPLANAR-32.md): Merged polygons can be slightly non-planar (up to about 0.05 units)
- [CONVERT-QHULL-FLAT-32](CONVERT-QHULL-FLAT-32.md): Collision building fails on a flat mesh (chitin shortbow)
- [CONVERT-TEXCOORD-RANGE-32](CONVERT-TEXCOORD-RANGE-32.md): Converter does not check the 16-bit texture-coordinate range
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
