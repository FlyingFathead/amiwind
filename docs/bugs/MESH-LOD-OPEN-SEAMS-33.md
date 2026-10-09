# MESH-LOD-OPEN-SEAMS-33: Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | Silt Strider (siltstrider.nif) in Balmora and Seyda Neen; static_lod.reduce_mesh |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32, v0.0.33-dev (last seen) |
| Severity | medium: Visible holes in a landmark model in two towns; no crash, other reduced models to be audited |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3dbaf00 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

Open. Cause found; fixed in source on v0.0.33-strider, not shipped at the time of writing. Present in v0.0.32 (and in CHIM Preview 1, which ships v0.0.32's models); the
strider profile behind it (ratio 0.5) has been shared by Balmora and Seyda Neen since v0.0.24-dev3.

## Symptom

The owner, playing CHIM Preview 1 in Balmora (global -21618 -19058 336, looking up at the Silt
Strider, compass 032, pitch -57): the strider has an "open hull design"; the shell looks ribbed and
the sky shows through gaps between its plates. The model should be closed. The owner then reported
the same at the Seyda Neen strider.

## Where

- `tools/static_lod.py` `reduce_mesh`, used by the converter (`prepare_mesh_bsp._prepare_model`,
  which the legacy region builder and the CHIM model builder both call) and by the size estimates
  (`asset_census`, `world_estimate_data`).
- The Silt Strider `meshes/r/siltstrider.nif`: one profile in `config/scenery_groups.json`
  (`silt_strider`, ratio 0.5), read by Seyda Neen and, through `town_regions.visual_profile`, by
  Balmora. Balmora places it as reference 41523 (13 region maps), Seyda Neen as reference 227023.
- Not the cause: the NIF has no `NiStencilProperty` (no two-sided shapes; 107 shapes, 5,986
  triangles, 386 of them hidden collision), no alpha property, and the polygon stage
  (`surface_polygons`, `split_surface`) keeps 99.99 % of the surface at ratio 1.0.
- Seyda Neen's region maps sn0xx and `seyda.bsp` are recorded v0.0.31 maps
  ([BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md)): they carry an older strider conversion (2,448
  and 2,166 faces) and change only when Seyda Neen is rebuilt (CHIM M2). The builder-made
  `intro_docks.bsp` carries the current one (3,266 faces).

## How it happened

`reduce_mesh` reduces every material component separately with `fast_simplification`. That reducer
also collapses rim edges, so an open part (each shell plate of the strider is a separate open sheet)
shrinks away from the neighbouring plate it met along the rim. Neighbouring plates are reduced
independently, so the shared rim opens into a gap on both sides. With back faces culled (Morrowind
and the Quake renderer draw one side), the gap shows the sky or the inside of the far plate. The
earlier `preserve_shared_seams` option avoided this only by keeping such materials unreduced; for the
strider that is every shell material, so it was never set. GEO-01 (giant mushroom caps, v0.0.27) was
the same mechanism and was repaired that way for the mushrooms only;
[TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md) recorded that the reducer can return open
meshes, without checking the converter's current users.

## Why it was not caught

The v0.0.24-dev3 profile change was checked for restored legs and body at one view and for heap cost;
nothing compared the reduced surface with the source, and no check looks for opened rims after a
reduction. The GEO-01 repair fixed one model family instead of the shared reducer.

## Reproduction

Measured on the owner's data (private receipts): source 5,600 visible triangles; ratio 0.5 gives 3,057
triangles, 3,266 BSP faces (the shipped Balmora maps carry exactly this: bm019 reference 41523, 3,266
faces, the same surface area). Sky-through test, 16 views around and below the model, one-sided
rendering: 8.8 % of the pixels where the source is solid show sky with the shipped reduction, 0 % at
ratio 1.0. The polycount inspector extraction of the shipped maps gives the same face counts.

## Repair

Shared layer, one implementation: `static_lod.reduce_for_profile` is the only reading of a profile's
visual reduction, used by the converter (`prepare_mesh_bsp._prepare_model`, so the legacy town
builders and the CHIM model builder) and by both size estimates (`asset_census`,
`world_estimate_data`). A profile may now ask for:

- `lock_boundaries`: boundary-locked reduction. Every rim vertex (an edge not shared by exactly two
  triangles) and every vertex shared with another component keeps its exact position; only interior
  edges collapse (`mold_shell.quadric_simplify` with a `locked` set, and `anchored` so no face turns
  more than 60 degrees from its source orientation). The reduction fails if a rim vertex moved.
- `preserve_shape_prefixes` (existing, now also honoured by the estimates): NIF shapes kept unreduced.

The earlier reducer stays the default for every other profile, and `preserve_shared_seams` (the
GEO-01 rule) stays selectable (DON'T DELETE ANY METHOD).

The strider's shared profile (one object, `a_siltstrider`, in all nine caravan towns: Seyda Neen,
Balmora, Vivec, Suran, Molag Mar, Ald-ruhn, Maar Gan, Gnisis, Khuul) keeps the shell, arms and legs
unreduced and reduces only the claws, boundary-locked. Owner direction: the strider is a solid object;
0 % sky-through at the 16 views. Variants measured (same views; bm011 rebuilt from the v0.0.32 cache;
heap = the map heap estimate of bm011):

| Variant | BSP faces | Sky-through | Torn seam length | bm011 heap estimate |
| --- | ---: | ---: | ---: | ---: |
| A2 ratio 1.0 (our converter, no reduction) | 5,841 | 0 % | 0 % | +339,136 B |
| B shipped, ratio 0.5 | 3,266 | 8.8 % | 4.8 % | (control) |
| C GEO-01 rule (`preserve_shared_seams`): keeps every shell section, map byte-identical to A2 | 5,841 | 0 % | 0 % | +339,136 B |
| D boundary-locked 0.5 | 3,403 | 1.8 % (legs thinner, seams closed) | 0 % | +12,032 B |
| E shipped fix: shell, arms, legs unreduced, claws locked 0.5 | 5,385 | 0 % | 0 % | +276,992 B |

Heap: the v0.0.32 release maps that carry the strider keep at least 356,604 B clearance (balmora,
bm019), so E leaves about 79 KB there and A2/C about 17 KB; D leaves almost all of it. Every option
stays selectable through the profile.

## Verification

- Headless OpenMW 0.48 at the owner's pose (static camera, eye 396): the shell is closed.
- FS-UAE, fresh copies of CHIM Preview 1 from the sealed ZIP: the shipped CHIM and legacy Balmora
  maps and the Seyda Neen maps reproduce the owner's frame (gaps); a control rebuild of bm011 with the
  shipped profile reproduces them; rebuilds with A2/C, D and E at the same pose close them (headlamp
  off and on pairs, private receipts).
- Unit tests (synthetic): two curved open plates sharing a rim keep every rim vertex and the seam,
  stay wound like the source and are still reduced; the earlier reducer still moves the rims;
  `quadric_simplify` never moves a locked vertex; named shapes stay unreduced and a missing one fails;
  the strider profile keeps shell, arms and legs; the converter and the estimates share
  `reduce_for_profile`; the seam metric finds the torn seam of the old reducer and none for the locked
  one; the gate fails on a new torn mesh and on any tear of a mesh that must stay closed. With the
  owner's data, the builder's `seam-audit` stage measures the real strider in every build: it is listed
  under "closed" in `config/seam-audit-known.json`, so any torn seam or rim (or a build that does not
  measure it) fails the build. The first audit: strider 0 % torn (the old profile: 4.8 %).
- Not yet: the CHIM Balmora world and the Seyda Neen region maps are not rebuilt here (Seyda's are
  recorded maps, BUILD-SEYDA-REGEN-30; they change when Seyda Neen is rebuilt); owner playtest.

## Prevention

`tools/seam_audit.py` measures, for every mesh a static converter reduces, the share of seam length
that the reduction pulls more than max(1 unit, 0.5 % of the model size) away from the reduced
surface. The builder's `seam-audit` stage (default on, before the image) fails on any reduced mesh
above 2 % that is not a registered known finding, or on a known one that tears more than recorded
(`config/seam-audit-known.json`). The first island-wide run found 49 other torn meshes:
[MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md).

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
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate

<!-- END GENERATED CATEGORY -->
