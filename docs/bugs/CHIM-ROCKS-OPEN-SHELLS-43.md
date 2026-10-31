# CHIM-ROCKS-OPEN-SHELLS-43: several rock meshes on CHIM do not close up

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.44 at 2026-10-19 19:11 +0300: sweep: 168 CHIM rock meshes, no converter cause (faces, winding, rotation match the original); rims buried as in the original; in-game and OpenMW look pending
- Reported with v0.0.46 at 2026-10-20 20:09 +0300: Listed under Known in this build in the v0.0.46 release notes (still open at the release).
- Reported with v0.0.54-dev1 at 2026-10-27 16:58 +0200: PERSISTING, one class cause with MESH-LOD-TORN-MESHES-33 (27 October 2026): 651 of 666 reduced mesh spaces are reduced without lock_boundaries, 136 with half or more of their rim torn (26,198 placements); the seam audit reports them as ok (SEAM-AUDIT-IGNORES-RIM-TEARS-54).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Bitter Coast cell -4,-6 (terrain_rocks_ai_02, model 1750, ref 476548) and other rock types |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | medium: visible holes in common scenery across the island |
| Family | Mesh converter geometry (`converter-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 19 October 2026](#status-19-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 19 October 2026

Reported by the maintainer. Island-wide sweep done (19 October 2026, below): the converter keeps every rock's faces,
winding and rotation as the original has them; no converter cause found. The in-game look at the reported spot and an
OpenMW comparison at the same pose are still to do.

## Symptom

Some rocks show open faces: from some angles the rock is hollow or a side is missing, where the original game draws
a closed rock. The maintainer saw it on several rock types, not only one mesh.

## Where

First pinned on the Bitter Coast, cell -4,-6: `terrain_rocks_ai_02` (CHIM model 1750, reference 476548). Other rock
types show the same.

## How it happened

Unknown. A first look at `terrain_rocks_ai_02` (18 October 2026) found that the rock is not reduced (393 of its 396
faces kept) and that its open edges match a one-sided source mesh. The maintainer's lead: an incorrect angle
calculation, such as a face orientation or rotation that comes out wrong for some rocks.

19 October 2026, island-wide sweep (`tools/rock_shell_audit.py` over the v0.0.44 release build, every rock mesh the
open-world converter knows: 246 meshes, 168 of them on CHIM in 9,591 stored variants with 37,133 measured
placements):

- Morrowind's rocks are one-sided shells that are open where the game buries them: 151 of the 168 CHIM rock meshes
  have open rims in the source itself. A boulder is open at the bottom; a rock cluster such as `terrain_rocks_ai_02`
  is ten small cups (36 or 42 triangles each, ten or twelve open edges each), every cup open on the side that faces
  into the ground or into a neighbouring cup. None of the 246 asks to be drawn from both sides: no rock has a
  NiStencilProperty, and OpenMW turns face culling off only for that property's "both" draw mode, so the original
  draws these rocks one-sided too.
- The stored CHIM models keep the source: for the 68 unreduced meshes (219 stored variants compared, scaled and
  tilted copies included) every sampled source point has a stored face within 1.4 source units facing the same
  way: 0 % missing, 0 % turned. Their open rim length matches the source's (ratio 0.96 to 1.08). No source rock has
  a face wound against its neighbours. The three faces `terrain_rocks_ai_02` loses (393 of 396) are slivers below the
  converter's minimum face area; their neighbours still cover them.
- The rotation is right. The converter turns a placement Z first, then Y, then X (`prepare_scenery.reference_rotation`),
  the order OpenMW uses for statics. Placed that way, the original rims lie under the original LAND: 2.8 % of rim
  samples stand more than 4 units above the ground, against 5.5 % to 9.4 % with the other three readings (other
  order, other sign, both), and the converter's reading buries the rims best for 173 of 210 placed meshes. For
  `terrain_rocks_ai_02` (80 of its 82 placements tilted): 0.8 % against 7.5 % to 30.8 %.
- In the CHIM world the stored rims, placed with the engine's own origin and yaw, lie under the CHIM chunk terrain as
  often as the original rims lie under the LAND: 0.99 % of rim samples above the ground against 1.07 % (37,132
  placements). The mirrored yaw would expose them (reference 476548: 217 of 560 samples instead of 35).
- Five meshes stand out: their CHIM rims are above the ground 9 to 15 percentage points more often than the original's
  (`terrain_rock_wg_15` over 154 placements, `terrain_rock_bc_10`, `_bc_13`, `_ai_01`, `_ai_05`). Three are reduced
  to 64 triangles (a reduced rim may rise); two are not reduced, so part of the gap is the audit's reading of the
  ground (CHIM terrain triangles against a bilinear LAND reading). Recorded in `config/rock-shell-known.json`.

So the converter does not open the rocks. What remains: whether the original also shows the open cups at the
reported spot (a rim the original leaves visible), or whether the engine shows a buried rim through the terrain
(software Quake orders brush models against the world by its BSP leaves, not by depth).

## Why it was not caught

No check compared the closed surfaces of converted meshes with their source over the whole island. Since
19 October 2026 `tools/rock_shell_audit.py` does, for every rock mesh.

## Reproduction

Always, at the reported spot.

## Repair

To do: sweep every rock mesh on CHIM for open edges against its source, compare the worst ones with OpenMW at the
same pose, and check the converter's face winding and rotation for the meshes that differ.

19 October 2026: the sweep, the winding and the rotation are done (How it happened); no converter change, because
the converter has nothing to repair there. Drawing every rock from both sides was measured as an alternative and
not done: the rock models hold 1,574,349 stored faces (200.8 MB of the 691.3 MB of model render data); back faces
would add about as much again and double the rock faces drawn per frame, to show surfaces the original culls. Next:
an orbit at reference 476548 (headlamp off and on) and OpenMW at the same pose; if the original shows a closed rock
there and CHIM does not, the engine's ordering of the rock against the terrain is the place to look.

## Verification

19 October 2026: data only, on the v0.0.44 release build (`2026_10_19_v0.0.44_release-try2_c84f8506`):
`rock_shell_audit.py audit` then `check`: 246 meshes, 0 two-sided, 0 unreduced stored models missing or turning
faces, the converter's rotation best, 0 failures with the five known meshes. Not yet seen in game: the orbit at
reference 476548 and the OpenMW view at the same pose are still to do.

## Prevention

To do: an island-wide open-edge audit of converted meshes against their source, kept as a gate.

19 October 2026: `tools/rock_shell_audit.py` (tests in `tests/test_rock_shell_audit.py`) checks every rock mesh: a
source that draws both sides, an unreduced stored model that misses or turns more than 1 % of its source, a mesh
whose CHIM rims stand above the ground clearly more often than the original's (known ones in
`config/rock-shell-known.json`, each no worse than recorded), and another rotation reading burying the rims better
than the converter's. The test pins the rotation order to OpenMW's. It reads a finished CHIM world and the game data
(about 15 minutes on 8 cores) and is not yet a builder stage.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- BALMORA-GROUND-DENTS-51 (no report page): Sharp V-shaped dents in Balmora s ground beside the canal wall (cell -3,-2), reported by the maintainer as back
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- CHIM-COLLISION-ROOM-FILLED-54 (no report page): One convex collision piece fills the room above a floor of the same mesh: seven trapdoors and a Redoran hut door cannot be used
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- CHIM-DOOR-TERRAIN-COARSE-54 (no report page): The 128-unit terrain tiles bridge the dip a door sits in: two Dwemer doors have ground 170 to 190 units above the threshold
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
- SEAM-AUDIT-IGNORES-RIM-TEARS-54 (no report page): The seam audit reports meshes with torn rims as ok
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still

<!-- END GENERATED CATEGORY -->
