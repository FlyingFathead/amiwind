# CHIM-TERRAIN-DIAGONAL-40: Terrain triangle diagonals differ from OpenMW 0.48

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | tools/prepare_world_regions.py terrain_triangles and town_ground_triangles |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev2 (last seen) |
| Severity | high: The converted surface can differ between original height samples, affecting geometry and collision. |
| Family | Mesh converter geometry (`converter-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.40-dev2 source comparison |
| From commit | source 138bbdd, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format 0.7 |
| Unknown because | Source and reference topology audit; no new world or native runtime was exercised. |
| Platform or emulator | not in game (Source comparison with exact OpenMW 0.48 release tag.) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Combined-world readback, 15 October 2026](#combined-world-readback-15-october-2026)
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

## Combined-world readback, 15 October 2026

The successor completes structural, heap, zone-walk and stair validation with
source and inputs unchanged. Six paired boundaries agree for terrain/water;
static scenery differs at the southern Seyda boundary. Model/sprite, final
actor contact, native and package acceptance remain pending.
[Static boundary finding](CHIM-FRAME-STATIC-SEAM-40.md).
Earlier failed or pending checkpoints below remain historical evidence.


## Symptom

Matching height-grid vertices is not sufficient to reproduce the reference
surface. Splitting a non-planar square along a different diagonal changes the
height inside it. The source converter uses fixed AC splits where the OpenMW
0.48 comparison engine alternates the split by grid parity.

## Where

`tools/prepare_world_regions.py:terrain_triangles` and the fine port patch in
`tools/prepare_quake.py:town_ground_triangles`. These feed visible terrain and
its collision. Exact affected runtime extent has not been measured.

## How it happened

The converter retains a fixed diagonal. OpenMW's exact `openmw-0.48.0` release
(commit `81ab0feb2ec2fda488eec043f6fa3d9b020f1521`) uses alternating diamond
indices in its [terrain buffer builder](https://github.com/OpenMW/openmw/blob/openmw-0.48.0/components/terrain/buffercache.cpp)
and enables diamond subdivision in its [physics heightfield](https://github.com/OpenMW/openmw/blob/openmw-0.48.0/apps/openmw/mwphysics/heightfield.cpp).
This is a verified reference-source difference, not a matched native capture
or a claim about the original executable's implementation.

## Why it was not caught

Existing vertex-height and local subdivision checks did not establish the
reference diagonal rule and its parity across cell boundaries. Coarse-grid
terrain distortion was investigated separately through actor contact failures.

## Reproduction

Compare the two source routines with the exact OpenMW release above. Use a
non-planar four-corner height grid and inspect both triangles at odd and even
grid parity. Repeat with negative cells and translated town coordinates.

## Repair

The current candidate uses alternating diamond diagonals at original sample
spacing: even global grid parity uses AC and odd parity uses BD. The existing
fine port patch shares this sampler. Frame-local lava terrain passes its global
origin explicitly. Coarse/adaptive approximation remains unchanged and is not
claimed to reproduce every original terrain triangle.

Two configured Seyda tiles retain the original LAND samples; their eight
neighbours use the existing required-edge subdivision. No actor ID selects the
geometry. The same surface serves actors, players and objects. The port extent
and sampling density remain unchanged.

The current terrain subdivision and AmiQuake collision trace machinery are
retained as the starting point. No actor movement, omitted actor or widened
contact tolerance is an acceptable substitute for correct terrain.

## Verification

Original-data checks cover 49 LAND cells, 207,025 exact source/local/global
vertex round trips, and 5,460 agreeing shared-cell samples. The candidate keeps
26 port boundary segments and 68 affected chunk-edge subdivisions consistent;
5,724 other town tiles are unchanged. Two detail tiles and their eight neighbours
add 84 triangles; the 42 existing port tiles change only diagonals.

Fifty isolated checks initially yielded 49 passes and one new fixture type
mismatch. Correcting that tuple/list comparison yielded a passing follow-up;
source behaviour was unchanged. The complete source suite ran 4,191 tests:
4,185 passed, three Windows-only checks skipped and three tracked Census checks
failed as expected; no unexpected failures or errors. These are source checks,
not compiled-world or runtime acceptance. Earlier
conversions and failed contact results remain historical evidence.
Matched OpenMW and Amiga views, normal traversal and adjacent-cell seam checks
remain required. No coverage, native acceptance or package completion is promoted.

### Original reference ray and contact distinction

Twelve measured LAND rays in OpenMW 0.48 match Bullet 3.24's accelerated ray
triangle selection within 0.000031 original units. That path uses the opposite
diagonal phase from terrain rendering and the contact-triangle enumeration.
A ray therefore cannot be used as a direct rendered-height or foot-contact
oracle on these non-planar squares. This explains the apparent disagreement;
it does not establish the completed CHIM collision or native seams.

Combined-world preparation stopped before a complete world and its validation
were produced. Preserve the passing source checks separately; this incomplete
output establishes no compiled contact, seam, native or package acceptance.

## Prevention

Add reference parity tests for both diagonal orientations, positive and negative
cells, shared edges and translated towns. Check that render and collision use
the same triangles. Keep height-grid correctness, interpolation topology,
coarse-detail error and actual native contact as separate evidence.

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

- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground

<!-- END GENERATED CATEGORY -->
