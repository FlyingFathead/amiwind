# BUILD-INTERIOR-INDEX-ROUTED-33: the interior stage expects a convex-piece chain where the hull is now routed

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/collision_index.py (prison ship shell, interior stage) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every full build from integration 9165a2e stops in the interior stage |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | v0.0.33 pass 2 full build (p2b-9165a2e) |
| From commit | source 9165a2e, engine 9165a2e, CHIM world 9165a2e |
| CHIM engine version | CHIM 0.1.0, engine 9165a2e, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 integration line, with a regression test. The next full build verifies.

## Symptom

The first full v0.0.33 build after the routed standing hulls were merged stopped in the interior stage
with "Expected an unindexed convex-piece union".

## Where

`tools/collision_index.py` (`index_model_collision`), which `tools/prepare_interior.py` runs on the
prison ship's room shell after the map is compiled. It adds a bounds index to a model whose hulls are
plain chains of convex pieces.

## How it happened

Since COLLISION-HULL-CHAINS-33 the converter routes the standing hull of a model with more than 16
pieces (`--model-hull auto`). The prison ship shell is such a model, so its standing hull was no longer a
chain, and the index refused it. The point hull is still a chain.

## Why it was not caught

The routed hulls were tested on the region and CHIM converters and with the hull audit; the interior
stage's index step has a unit test on a synthetic chain only, and no full build ran between the two
changes.

## Reproduction

A full build with `--model-hull auto` (the default) from integration head 9165a2e.

## Repair

The index keeps a standing hull the converter already routed and indexes the point hull only (the
routed hull is already a spatial tree). The report says which. Every other model is handled as before.

## Verification

`tests/test_collision_index.py` covers both cases (chain: both hulls indexed, volumes unchanged;
routed standing hull: kept byte for byte, point hull indexed). The next full build must pass the
interior stage.

## Prevention

The regression test; full builds from every integration head that changes the converter.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
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
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep

<!-- END GENERATED CATEGORY -->
