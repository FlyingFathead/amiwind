# MESH-LOD-TORN-MESHES-33: Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | town flora/rock profiles, open-world rock scenery, arrival ship (static_lod reduction) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: Open seams on 49 reduced meshes (13,448 placements); visible where the reduced mesh is drawn |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 9582693 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found by the seam audit written for [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md). The
torn meshes are recorded as known findings in `config/seam-audit-known.json`; the builder's
`seam-audit` stage fails on any other reduced mesh above the threshold, and on a listed mesh that tears
more than recorded. No profile is changed by this entry.

## Symptom

Same mechanism as the Silt Strider: the static reducer moves the rims of separately reduced parts,
so parts the source joins come apart and gaps open where the reduced mesh is drawn.

## Where

`tools/seam_audit.py audit` over the reference GOG data: 3,775 meshes placed by the static
converters (exterior and interior statics, activators, doors and containers of the three masters),
666 mesh/converter pairs reduced, 49 above 2 % of seam length torn, on 13,448 placements: 36 under the
town profile (`town_regions.visual_profile`: flora 120-triangle target, terrain rocks 64), 12 under the
open-world scenery profile (`prepare_world_scenery.visual_profiles`, 64-triangle rocks) and the
arrival ship (`ex_de_ship`, scenery group ratio 0.2, 2.2 %). Trees that the build replaces with
sprites show the tear only where their mesh is drawn. Top 20:

| Mesh | Converter | Seam torn | Rim torn | Triangles | Placements |
| --- | --- | ---: | ---: | --- | ---: |
| `flora_bc_tree_01.nif` | town | 91.9 % | 76.6 % | 1743 -> 488 | 84 |
| `flora_bc_tree_04.nif` | town | 89.1 % | 40.7 % | 1376 -> 167 | 89 |
| `flora_tree_ac_03.nif` | town | 73.4 % | 59.6 % | 788 -> 126 | 78 |
| `flora_bc_tree_06.nif` | town | 72.4 % | 67.0 % | 1339 -> 153 | 5 |
| `flora_bm_snow_log_02.nif` | town | 70.8 % | 0.0 % | 529 -> 117 | 15 |
| `ex_t_rock_coastal_02.nif` | world | 70.3 % | 75.5 % | 228 -> 63 | 441 |
| `flora_treestump_wg_02.nif` | town | 62.8 % | 74.5 % | 356 -> 118 | 30 |
| `flora_tree_ac_04.nif` | town | 61.8 % | 61.7 % | 872 -> 163 | 178 |
| `terrain_ashland_rock_05.nif` | world | 61.6 % | 95.2 % | 200 -> 63 | 927 |
| `ex_t_rock_coastal_01.nif` | world | 59.9 % | 72.0 % | 228 -> 62 | 487 |
| `flora_ashtree_01.nif` | town | 57.9 % | 27.2 % | 584 -> 149 | 441 |
| `terrain_ashland_rock_03.nif` | world | 57.7 % | 70.9 % | 227 -> 64 | 729 |
| `flora_ash_log_04.nif` | town | 56.0 % | 0.0 % | 956 -> 183 | 50 |
| `terrain_ashland_rock_08.nif` | world | 56.0 % | 84.5 % | 240 -> 63 | 627 |
| `flora_tree_ac_01.nif` | town | 54.8 % | 49.5 % | 1672 -> 153 | 135 |
| `flora_bc_mushroom_02.nif` | town | 54.2 % | 83.3 % | 150 -> 119 | 70 |
| `flora_emp_parasol_02.nif` | town | 52.6 % | 29.9 % | 611 -> 132 | 238 |
| `terrain_ashland_rock_10.nif` | world | 51.3 % | 100.0 % | 400 -> 64 | 589 |
| `flora_tree_ac_02.nif` | town | 49.2 % | 48.2 % | 1018 -> 115 | 176 |
| `terrain_ashland_rock_04.nif` | world | 44.6 % | 89.4 % | 348 -> 62 | 301 |
The GEO-01 rule (`preserve_shared_seams`) covers the open-world giant mushrooms only; the same
parasol meshes under the town profile tear (`flora_emp_parasol_02`, 52.6 %).

## How it happened

See [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): per-component reduction with a reducer
that collapses rim edges, applied with fixed triangle targets.

## Why it was not caught

No check compared reduced seams with the source until the audit was written.

## Reproduction

`tools/seam_audit.py audit --data-files <Data Files> --out seam-audit.json --jobs N` (about 5.5
minutes on 3 workers); the ranked list is in the report.

## Repair

Not yet. Options per profile: `lock_boundaries` (keeps rims; reaches lower reductions on closed
parts), `preserve_shape_prefixes` for structural parts, or a lower reduction. Each changes face and
heap budgets of many maps and needs the heap gate and an owner look.

## Verification

Audit report (private receipt); the builder gate passes with the known list and fails on a new tear
(tests/test_seam_audit.py).

## Prevention

The `seam-audit` builder stage (default on, before the image) and the known list, which must name a
registered bug for every row.

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
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

<!-- END GENERATED CATEGORY -->
