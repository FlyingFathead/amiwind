# CHIM-DOCK-TERRAIN-SEAM-47: a pale sliver gap shows where a dock end meets the ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 21 October 2026, in v0.0.47-dev1 |
| Where | Bitter Coast cell -5,-6: x/ex_de_docks_end@s1 (model 296) meets the terrain |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.47-dev1 (last seen) |
| Severity | low: a thin visual gap at one dock end; no effect on play |
| Family | Mesh converter geometry (`converter-geometry`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9 |
| From commit | source 4a2d42b, engine 4a2d42b, CHIM world 4a2d42b |
| CHIM engine version | CHIM 0.2.1, engine 4a2d42b, world format 0.7 |
| Platform or emulator | maintainer's playtest, emulator |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47-dev1 (21 October 2026)._

## Status: 21 October 2026

Open. Cause unknown. Registered from one pinned spot; the island-wide extent has not been measured.

## Symptom

At the end of a dock on the Bitter Coast, a thin pale sliver of background shows between the dock end and the
ground. The maintainer, playing v0.0.47-dev1, said that "some of these terrain seams look a bit ripped to pieces
though" and guessed that "it's probably a result of the lowered polycount". That is his guess; nothing here
confirms or rejects it. A screenshot from the maintainer's playtest (private) shows the sliver.

## Where

- Mesh `x/ex_de_docks_end@s1` (CHIM model 296), source reference 384666, cell -5,-6, CHIM placement 11533.
- Placement local position -440.1 -815.8 7.4, yaw -178.3.
- The player stood at GLOBAL -38292 -48273 156 (LOCAL -357 -804 39), Bitter Coast Region, game time 11:36.
- Build 2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9 (commit 4a2d42b9, CHIM 0.2.1, world format 0.7).

## How it happened

Unknown. Candidates to check, none of them established:

- the dock mesh's own edge after the flora/visual reducer or LOD (compare with the open-seam findings below);
- the terrain triangles under the dock end (the terrain diagonals differ from the OpenMW reference in
  [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md), so a dock placed on the original ground can meet a
  slightly different surface);
- the polycount the maintainer suspects (terrain and mesh reduction).

## Why it was not caught

The seam audits look at the open edges of single meshes, not at the gap between a placed mesh and the terrain
under it, and no automatic check compares a placed object's lowest edge with the converted ground.

## Reproduction

Unknown (reported once). Go to the pinned player position above, or to model 296, in the v0.0.47-dev1 build.

## Repair

None yet. First steps: view model 296 and the ground under it in the Toolkit mesh inspector and the headless
OpenMW reference at the same pose (rule: three references before implementing), then list every dock and pier
mesh placement whose lowest edge sits above the converted ground by more than a small tolerance.

## Verification

None yet. The fix is verified with a headlamp off/on pair and a short clip at the pinned pose, and with the
island-wide list of dock and pier ends measured before and after.

## Prevention

A placement-versus-terrain gap audit for every mesh that is meant to touch the ground (docks, piers, steps,
walls), run on the converted frames and kept as a gate.

## Related

Seam and terrain bugs: [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md),
[CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md), [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md),
[CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
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
- [GHOSTFENCE-NO-ANIMATION-46](GHOSTFENCE-NO-ANIMATION-46.md): The Ghostfence's shimmering curtain does not move: its texture scroll is dropped by the converter
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours

<!-- END GENERATED CATEGORY -->
