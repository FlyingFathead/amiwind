# MESH-LOD-TORN-MESHES-33: Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 7 times; something has to be done

- Reported with v0.0.33 at 2026-10-09 (time not recorded): found by the island-wide seam audit: 49 reduced meshes tear their seams
- Reported with v0.0.36-dev3 at 2026-10-11 03:36 +0300: measured as visible holes: 39 of 150 open-world rocks at 64 triangles show the sky through on more than 5 of 100 pixels, worst 48 (terrain_ashland_rock_01)
- Reported with v0.0.43-dev2 at 2026-10-18 19:03 +0300: maintainer: Ashlands rocks still open underneath (cell -4,12, func_wall model *52, source ref 283924); 'the same rocks I've mentioned', should not be open
- Reported with v0.0.43-dev2 at 2026-10-18 19:04 +0300: maintainer: another open rock, cell -4,13 (func_wall model *44, ref 245627); fixed in some map spots but not in others
- Reported with v0.0.43-dev2 at 2026-10-18 19:06 +0300: open rocks at -4,12/-4,13 are on classic region maps in dev2 (not CHIM); one step into CHIM cell -5,13 the same rocks are closed; dev3 has all three on CHIM
- Reported with v0.0.43-dev2 at 2026-10-18 19:20 +0300: maintainer: two long spikes hang from a rock/terrain face in Balmora (cell -3,-3, global -20051 -19320 80, local 107 -1758 20); Balmora is a CHIM town frame
- Reported with v0.0.43-dev2 at 2026-10-18 19:21 +0300: maintainer: the Balmora spikes may be the overpass poking through the rocks; wants its ends hidden inside the rocks

<!-- END GENERATED PERSISTING -->

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

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 7 times; something has to be done](#persisting-reported-7-times-something-has-to-be-done)
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

Open. Found by the seam audit written for [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md). The
torn meshes are recorded as known findings in `config/seam-audit-known.json`; the builder's
`seam-audit` stage fails on any other reduced mesh above the threshold, and on a listed mesh that tears
more than recorded. No profile is changed by this entry.

11 October 2026, measured as visible holes: the open-world scenery profile (64 triangles per rock, 160 per
giant mushroom) reduces 150 of the 174 meshes the open-world scenery stage converts (rocks and giant
mushrooms only; no building is converted by it). Rendered as the engine draws them (one side, 16 views
around and below), 139 of the 150 show the sky through the model where the source is solid on more than
1 % of the pixels, 39 on more than 5 %, the worst 48 % (`terrain_ashland_rock_01`). meshoptimizer with
locked borders at the same ratio closes them (38 rocks: 14.4 % to 0.0 % on average) but keeps 4.6 times the
triangles (2,409 to 11,154), because every open rim stays where it is: not a free repair for heap-limited
open-world maps. Options for the maintainer: a triangle floor per rock, the CHIM mesh method `meshopt+merge` for
rocks once the open world is on CHIM, or a rim-aware target.

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
heap budgets of many maps and needs the heap gate and a maintainer look.

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
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams

<!-- END GENERATED CATEGORY -->
