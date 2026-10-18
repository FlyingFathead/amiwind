# MESH-EBONHEART-DRAGON-PEDESTAL-42: Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.42-dev1 at 2026-10-17 12:02 +0300: maintainer: statue floating in the air, no pedestal drawn
- Reported with v0.0.43-dev1 at 2026-10-18 07:50 +0300: maintainer: the after image (test engine with the popping fix) still has the statue floating in the air

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | Ebonheart plaza, ex_imp_dragonstatue (vivec_city frame, cell 2,-13) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41, v0.0.42-dev1 (last seen) |
| Severity | medium: A landmark statue hangs in the air over the plaza in every build since at least v0.0.41 |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | v0.0.42-dev1 (full-dev1-proof) |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | unknown (the maintainer's own emulator session; reproduced the same day in FS-UAE 3.1.66 (JIT) with the dev1 and v0.0.41 images) |

<!-- END GENERATED FACTS -->

## Symptom

The maintainer, v0.0.42-dev1, 17 October 2026: in the Ebonheart plaza the dragon statue hangs in the air,
"no pedestal drawn in". Its round base is drawn; below it there is sky down to the plaza.

## Where

The converted model `x/ex_imp_dragonstatue@s1` (CHIM model 4447 of the dev1 world, vivec_city frame, cell
2,-13).

## How it happened

Not yet known. Measured on 17 October 2026:

- The original data place one `ex_imp_dragonstatue` at 18577, -101915, z 416 and the plaza
  (`ex_imp_plaza`) at z 48; no other object stands under the statue (every reference of cell 2,-13 within
  700 units). So the column is part of the statue's own model or of the plaza model.
- The converted statue's vertices span z 59 to 347 engine units above its origin (236 to 1,388 original
  units): nothing below 236. Its base therefore starts at about z 652, while the plaza's converted tiles reach
  at most 296 units above their origin (z 344).
- It is not a streaming fault (it was first reported beside CHIM-ZONE-RELEASE-FLICKER-42): the statue floats
  the same in v0.0.41, in v0.0.42-dev1 and with the zone repairs, where every chunk of the ring at that pose
  is loaded.

## Why it was not caught

No check compares a converted model's vertical extent with its original mesh, and the plaza was not looked at
in game before.

## Reproduction

`dbg tp 19705 -101510`, `aw_aim 211 -13`: the statue hangs above the tower roofs to the right of the crosshair.

## Repair

Open. Next: the original mesh (ex_imp_dragonstatue.nif, and the plaza's) against the converted model, in the
mesh inspector and a headless OpenMW view of the same pose (three references: what the original holds, how
OpenMW composes it, the converter's node handling).

## Verification

Open.

## Prevention

Open: a converter check that a model's converted bounds match the original mesh's bounds (per mesh, island
wide), so a lost or shifted part fails the build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- [CHIM-STRIDER-SCALED-SEAMS-36](CHIM-STRIDER-SCALED-SEAMS-36.md): Seyda Neen's silt strider (scale 0.89 variant) still shows open seams; Balmora's (scale 1.0) is closed
- [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md): Terrain triangle diagonals differ from the OpenMW 0.48 reference
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
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames

<!-- END GENERATED CATEGORY -->
