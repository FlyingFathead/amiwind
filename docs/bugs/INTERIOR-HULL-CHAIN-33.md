# INTERIOR-HULL-CHAIN-33: The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev1 |
| Where | Interior converter collision (prepare_mesh_bsp collider), Vivec, Arena Pit (vai000) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.35 |
| Severity | high: Every movement trace in the Pit costs tens of thousands of plane tests on a 68040; the stair gate on the room took 95 minutes on one core. |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 8f11f40, engine 8f11f40, CHIM world 8f11f40 |
| CHIM engine version | CHIM 0.1.0, engine 8f11f40, world format unknown |
| Unknown because | found in source on the legacy interior converter path; no CHIM world involved |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
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

## Status: 9 October 2026

Repaired in source, not shipped at the time of writing: the shared routed standing hull from the CHIM
builder line (`tools/routed_hull.py`, `--model-hull auto`, the default; merged at c04404f) now routes
the Pit's main mesh, with ROUTED-HULL-NODE-ORDER-33 fixed so the engine accepts it. Island-wide
sweep: COLLISION-HULL-CHAINS-33.

Found 9 October 2026 while converting "Vivec, Arena Pit" (`vai000`) for IMPORT-TOWN-NO-INTERIORS-32.
Performance.

## Symptom

The stair gate on the converted Pit took 95 minutes on one core (it passed: 44 steps, 312 ramps
walked). The image stage's actor grounding and a floor scan of the room stopped making progress for
15 to 48 minutes. A profile of 30 stair candidates: 389 traces took 259 s, about 57,000 clipnode
visits per trace.

## Where

The interior converter writes each model's convex collision pieces as one chain of clipnodes
(`tools/prepare_mesh_bsp.py`, `collider`): outside one piece, test the next. The Pit's main structure
`meshes/i/in_v_arena_01.nif` (reference 466195, 15,760 faces) becomes one chain of 36,545 clipnodes
whose depth equals its length, and its bounds cover the whole room. The engine walks the same chain
for every movement trace there (`SV_RecursiveHullCheck` descends it iteratively, so the stack is
safe; the cost is the plane tests).

## How it happened

Chains are fine for a few pieces. Interior shells so far were small; the Pit is one mesh for the
whole bowl, its stands and stairs.

## Why it was not caught

No check counts collision work per trace, and no earlier interior had a model this large.

## Reproduction

Convert the Pit (`tools/import_town.py --town vivec_arena`) and run the stair gate on `vai000`, or
count the clipnodes reachable from each model's standing-hull head node.

## Repair

The routed standing hull (`tools/routed_hull.py`, nested x/y/z cuts, pieces written once in legacy
maps) for models with more than 16 pieces; the chain stays selectable (`--model-hull chain`).

History: the existing compiled standing hull (`collision_bsp.compile_standing`, one qbsp BSP of the
expanded pieces) fails on this mesh: qbsp stops on a non-convex face at merge lattices of 1/64, 1/16
and 1/8 unit, as it does on the Vivec canton bodies. The CHIM builder line is building routed
standing hulls (axial routing over the model's area, short chains per part) for the same problem in
large exterior models; the repair is to give the interior converter the same routed hull for models
with many pieces, with the chain kept selectable.

## Verification

9 October 2026, the builder's town stage on owned data, the same 4-CPU container:

| | Chain | Routed |
| --- | ---: | ---: |
| `in_v_arena_01` hull depth (`tools/hull_chain_audit.py`) | 36,545 | 6,711 |
| Its clipnodes | 36,545 | 37,130 |
| Map clipnodes | 37,393 | 37,978 |
| Stair gate on `vai000` (one core) | 95 min | 92 s |
| Stair gate result | 44 steps, 312 ramps passed | the same |
| Actor grounding (image stage) | over 40 min | under 2 min |
| Floor scan, offline traces over the visit guard | 7 of 5,156 | 0 of 20,329 |

FS-UAE (emulator, relative): the room loads (heap peak 6,538,912 B) and the player walks the Pit
floor from wall to wall.

## Prevention

`tools/hull_chain_audit.py` lists every model whose standing-hull depth passes a limit
(COLLISION-HULL-CHAINS-33); `tests/test_routed_hull.py` covers the routing and the engine's node
order.



12 October maintainer follow-up: severe performance drop reported inside the Vivec Arena Pit. Exact installed hashes, frame times, position, movement state and room format are not yet bound. This is a new performance observation alongside this investigation, not proof that the old hull chain is its cause. Measure idle versus movement, collision trace cost, visibility and render work with the AmiQuake mechanisms before selecting a repair. Keep interiors eligible for BSP29, CHIM or a mixture.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
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

- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
