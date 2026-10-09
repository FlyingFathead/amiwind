# ROUTED-HULL-NODE-ORDER-33: A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev1 |
| Where | Routed standing hulls (tools/routed_hull.py, route_nested), legacy maps and CHIM models |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev1 (last seen) |
| Severity | high: The engine stops the game the first time a trace enters such a model (the Arena Pit crashed on load). |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source c04404f, engine c04404f, CHIM world c04404f |
| CHIM engine version | CHIM 0.1.0, engine c04404f, world format unknown |
| Unknown because | found on a scratch evidence image of the Arena Pit built from this source; no CHIM world involved |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-arena-interiors, not shipped at the time of writing. Found the first time a
routed hull was loaded in the engine (the Arena Pit, after INTERIOR-HULL-CHAIN-33's repair).

## Symptom

Loading `vai000` with the routed hull of its main mesh (`in_v_arena_01`, reference 466195) crashed
AmiWind at once in FS-UAE: "SV_RecursiveHullCheck: bad node number". The offline checks (stair gate,
actor grounding, floor scan) passed, because they do not apply the engine's node range.

## Where

`tools/routed_hull.py`, `route_nested`: when pieces straddle a cut and are not copied, their chain was
written after the cut's clipnode and returned as the part's root. The model's head node was then
34,667 while the tree reached down to clipnode 362. Quake gives each brush model's hull the range
head node .. last clipnode (`Mod_LoadBrushModel`: `firstclipnode = headnode`) and
`SV_RecursiveHullCheck` stops on any node outside it.

## How it happened

Routing writes a cut node, then its children, then chains the straddlers to it; a chain or
qbsp-compiled hull always starts at its lowest node, so nothing had needed the rule before.

## Why it was not caught

The routed hull's tests compare point contents with the chain, and the offline trace code has no
range check. No routed legacy map had been loaded in the engine.

## Reproduction

Route a model whose first cut is straddled by a piece with no copy allowance (a ring around rows of
boxes; the Pit's bowl tiers around its floor) and walk the clipnodes from the root: one is below it.

## Repair

The straddlers' chain is written first, leading to the cut written directly after it, so every part
(and the model's head) is its lowest clipnode. Same solid set, same clipnode count.

## Verification

Rebuilt `vai000` with the builder's town stage: no node below its head (all 39 models); hull depth
6,711; stair gate passed in 92 s (44 steps, 312 ramps, as with the chain); actor grounding and the
actor gate passed; heap estimate 9,381,668 B. FS-UAE: the room loads, the player walks the Pit floor
from wall to wall, five poses match OpenMW.

## Prevention

`tests/test_routed_hull.py` (`test_every_node_of_a_routed_hull_is_at_or_after_its_root`): every
clipnode reachable from a routed hull's root has an index at or above it; the test fails on the old
layout.

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
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep

<!-- END GENERATED CATEGORY -->
