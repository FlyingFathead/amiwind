# BUILD-SEYDA-OCEAN-FLOOR-40: Expanded Seyda seabed meets the fixed BSP seal

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | Seyda scene terrain prism and water/sky enclosure generation after original-cell expansion |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev2 (last seen) |
| Severity | high: The expanded town gameplay carrier cannot compile; dev2 packaging is blocked. |
| Family | Mesh converter geometry (`converter-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 2ac9b4b, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format unknown |
| Unknown because | Actual scene conversion failed before a playable image existed. |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

## Symptom and reproduction

Build the expanded original-cell Seyda scene. Some original ocean LAND heights
are -2048 original units, or -512 engine units. Their top and hard-coded bottom
are identical. The actual compiler reports duplicate and zero-normal planes,
then rejects an out-of-range face. The failed output is preserved.

## Cause and why it was not caught

The old bounded scene assumed that every terrain sample was above its fixed
-512 seal. The newly included ocean apron violates that assumption. Town-bound
and CHIM sampling tests did not compile this intermediate scene from actual data.
The exact contribution of each degenerate prism to the terminal compiler error
still requires the corrected actual compilation.

## Repair

Derive a lower, grid-aligned hidden seal when original LAND reaches the old
floor. Keep original top vertices, materials, horizontal bounds and water level;
extend water and outer sealing walls down to the same new base. Reject missing
or nonfinite heights, and account for MAP coordinate rounding. Shallow scenes
retain the historical floor. No landscape is deleted or raised.

The repair reuses the existing Quake MAP brush winding and BSP compiler. It
changes converter input, not AmiQuake runtime collision or engine limits.

## Verification

Eighteen terrain, CHIM alignment and palette tests pass. The six new checks
cover flat ocean, deeper and sloped seabed, shallow-scene compatibility, MAP
rounding and invalid input. They independently check nonzero face normals and
that every vertex lies inside every brush half-space. Actual fresh compilation,
water/collision seams and matched native reference checks remain pending.

## Prevention

Keep deep ocean in the converter regression fixtures and compile actual expanded
source before packaging. Do not clip original terrain or relax compiler limits
to hide a failed intermediate.


### 15 October 2026: actual gate follow-up

Deep-seabed seal correction passes 35 combined source checks and actual alias regeneration with original heights preserved. Actual BSP compilation passes the earlier degenerate-floor failure but then hits a separate BSP29 node/leaf limit under BUILD-SEYDA-HULL2-32. Native and package checks remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
- CHIM-ROOM-LAVA-TOP-ROUNDING-48 (no report page): A lava room was kept as a room map: the pool top compared rounded (record -66.55, brush -66.56)
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

- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage

<!-- END GENERATED CATEGORY -->
