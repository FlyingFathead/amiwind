# Distant building shells ("outer mold")

Status (8 October 2026): **prototype tool and measurements only.** Nothing
here is in the game, the engine is unchanged, and no map ships a shell. The
face budget below is a candidate, not a promise. The FPS effect is not
measured yet (see the planned A/B at the end).

<!-- contents start -->
## Contents

- [Why](#why)
- [Quake first: which mechanisms this reuses](#quake-first-which-mechanisms-this-reuses)
- [The tool: `tools/mold_shell.py`](#the-tool-toolsmold_shellpy)
- [Measured on Balmora (bm019)](#measured-on-balmora-bm019)
- [Engine switch (design, not implemented)](#engine-switch-design-not-implemented)
- [Planned FPS A/B/C/D](#planned-fps-abcd)
- [Why pure Python (and not a Blender step)](#why-pure-python-and-not-a-blender-step)
- [Open questions](#open-questions)

<!-- contents end -->

## Why

Town frame rate is limited by building faces, not by visibility lists:

- Over 94 % of a Balmora map's faces are in brush models (`func_wall`), which
  Quake's `vis` cannot use ([TOWN-VISIBILITY](performance/TOWN-VISIBILITY.md)).
- Structural occluders do not hide distant town buildings: from 213 street
  points, 589 of bm019's 590 building models are still sent with occluders and
  full `vis` (same page, second prototype result).
- A shorter fog distance roughly doubles the Balmora frame rate only because
  distant buildings stop being drawn.

So the remaining lever is to draw less at a distance. The idea: for each
building, a closed low-poly shell, "what sticks" when the building is
shrink-wrapped, drawn instead of the full mesh beyond a distance.

## Quake first: which mechanisms this reuses

Quake 1 has no level of detail for brush or alias models, so the switch is
the smallest addition on top of mechanisms that already exist:

- **Brush submodels** (`dmodel_t` first face / face count). The shells of a
  map are stored as one extra submodel, a "far pool", in the same BSP.
- **Model views over a surface range**, as the engine already does for
  placement render ranges (`aw_render_ranges.c`: a temporary `model_t` copy
  whose `firstmodelsurface`/`nummodelsurfaces` point into a pool model). A
  shell is drawn by the same kind of view, with the building entity's own
  origin and angles.
- **Entity key/value pairs** in the BSP entity lump to link each building
  `func_wall` to its shell range, as the render ranges do.
- **The per-entity far test** in `R_DrawBEntitiesOnList` (`AW_ModelVisible`,
  the fog/draw-distance check) is where the near/far choice is made.
- **Mip selection** (`D_MipLevelForScale`) already picks coarse mip levels for
  distant faces; shell faces use the same textures and texture vectors.

Collision, the server, networking and `vis` do not change: the original
`func_wall` stays the entity, the pool model is never an entity, so it has no
hull, no physics and no leaf links. **The shell is render-only.**

## The tool: `tools/mold_shell.py`

Generic and asset-free (numpy and scipy only), tested on synthetic meshes in
`tests/test_mold_shell.py`. Input is a triangle soup with a material per
triangle (or an OBJ file with `usemtl`); output is a closed triangle shell, a
material and a source triangle per face, and a report.

1. **Voxelise** every triangle at a cell size (prototype: 4 units).
2. **Seal** openings with a morphological closing by a ball of radius
   `keep_opening / (2 * cell) - 1/4` cells. Every voxel the closing adds lies
   within that radius of the original surface, so **an opening at least
   `keep_opening` wide is never sealed** (prototype: 32 units). Openings that
   are sealed are reported one by one (centre, box, width) when at least
   `report_width` wide (default 12 units).
3. **Fill** enclosed cavities (rooms behind sealed windows and doors).
4. **Make the voxel surface a 2-manifold** (2x2x2 blocks with diagonal or
   split patterns are filled), then **extract** the boundary faces.
5. **Simplify** with quadric edge collapse (Garland-Heckbert) that refuses any
   collapse breaking the link condition or turning a face by more than about
   72 degrees, so the shell stays closed. Vertex clustering is a cruder
   fallback.
6. **Snap** shell vertices onto the original surface when it is within 1.8
   cells and no face flips.
7. **Materials**: each shell face takes the dominant material of the nearest
   original triangles that face the same way (7 samples per face vote). Its
   texture vectors come from a nearby original face of that material with the
   most similar orientation (distance + 32 x (1 - normal dot)), so the
   existing textures keep their texel size and direction and do not smear.
8. **Measure**: surface deviation both ways (max and mean), silhouette error
   from 13 directions (share of area that differs, largest distance between
   outlines), roof-line height error from above (mean, 95th percentile, max),
   and the face count after Quake's 240-texel surface-extent split
   (`mesh_geometry.split_surface`, as the converter does). `pick_budget`
   chooses the smallest budget within a silhouette tolerance; `screen_error`
   turns units into pixels.

Why the dominant-texture rule: shells have no lightmaps (converted exterior
meshes have none either, they use the ambient path), so the only appearance
they carry is texture and texture vectors. Reusing the original texture and
vectors keeps distant colour and pattern scale the same as the full building
without new texture memory.

## Measured on Balmora (bm019)

Inputs: the shipped bm019 map's brush models, placements and textures; all
processing in offline Docker containers. bm019 has 31,022 faces; its 590
brush placements reference models with 68,683 faces in total when every
placement is counted. The 23 town houses account for 11,141 of those (16 %).

**Attached parts matter.** Doors are separate meshes, so a house alone has
doorway holes; with two of them a shell gets a tunnel through the house
(genus up to 4), which wastes the face budget. The prototype therefore
shells each house **with its attached parts** (doors, buttresses, balconies,
windows, steps and items on them: placements at least half inside the house
box grown by 8 units, excluding trees, rocks, lamps and creatures). These 23
clusters hold 29,576 faces (43 % of the placement faces). Of the house-only
shells, 20 of 23 have at least one tunnel; of the cluster shells 14 of 23
still have one or two through-passages, openings about 30 units or wider
that the closing may not seal (kept by design).

Shells per budget, 23 clusters, `keep_opening` 32, cell 4 (all 23 shells
closed at every budget):

| triangles per shell | Quake faces after extent split | merged polygons | mean silhouette area error | worst silhouette error, median building | mean Hausdorff |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 24 | 1,043 | 553 | 42.6 % | 111 units | 111 units |
| 48 | 1,945 | 1,054 | 22.4 % | 51 units | 58 units |
| 96 | 3,229 | 2,072 | 8.9 % | 27 units | 32 units |
| 128 | 4,085 | 2,738 | 6.0 % | 17 units | 25 units |
| 192 | 5,619 | 4,092 | 4.0 % | 15 units | 18 units |
| 256 | 7,252 | 5,425 | 3.8 % | 13 units | 15 units |
| 384 | 10,376 | 8,087 | 3.6 % | 10 units | 14 units |
| original | 29,576 | | | | |

Per-building budget by tolerance (smallest budget meeting it):

| tolerance (worst outline error / mean area error) | buildings meeting it | Quake faces |
| --- | ---: | ---: |
| 24 units / 8 % | 22 of 23 | 4,552 |
| 16 units / 5 % | 21 of 23 | 6,337 |
| 12 units / 4 % | 11 of 23 | 9,406 |
| 8 units / 3 % | 0 of 23 | 10,376 (all at 384) |

What this means on screen: an error of E units at distance D covers about
E x 160 / D pixels on a 320-pixel-wide view with a 90 degree field of view.
16 units is about 8 pixels at 300 units and 5 pixels at 540 units (the
current draw distance, where fog is complete). The fixed budgets of 24-48
triangles are too coarse for these houses (outline errors of 50-110 units);
roughly 128-256 triangles per house are needed for 16 units.

Other measured points:

- **The surface-extent split costs 1.35-1.9x.** Quake faces may not span more
  than 256 texels (`model.c`), so large shell polygons are cut like the
  converter cuts mesh faces: 1,054 merged polygons become 1,945 faces at 48
  triangles, 4,685 become 6,337 at the 16-unit tolerance. A smaller budget can
  even give more faces than a larger one for the same house.
- **Sealed openings are reported.** At `keep_opening` 32 the 23 clusters list
  281 sealed openings at least 12 units wide (widest 29 units; none can reach
  32) and 4 filled enclosed cavities. At `keep_opening` 64 the list grows to
  532 openings (widest 56 units) and no through-passage remains.
- **Roof lines.** The 95th-percentile roof height error at 48 triangles is
  about 63 units for the median house: coarse shells flatten stepped roofs and
  fill roof-level gaps. Above-roof views show this (evidence frames below).
- **Texture transfer.** Day and night views show the textures carried over
  with their scale and direction. One visible fault: where a sealed area is
  covered mostly by door or grille faces, the door texture wins the vote and
  spreads over a large shell face. An area-weighted or per-material priority
  vote is the next step.
- **Faces in view** (all 23 clusters as shells beyond 200 units from the
  camera, two street viewpoints): 22,042 to 11,048 (48 triangles) or 12,754
  (16-unit tolerance) brush faces of models in the view; 10,082 to 5,983 or
  7,062 at the second viewpoint. The remaining faces are the near houses,
  the world and the small props (doors not attached to a house, street
  lamps, urns, signs, furniture), which a plain per-entity distance cull
  could handle separately.

Evidence frames are private (they contain game textures). Each shows the same
view twice, original and shells, labelled "PROTOTYPE - not in game", by day
and night and from above the roofs.

## Engine switch (design, not implemented)

Per building `func_wall` the map carries `"aw_far" "start count"` (a surface
range in the far pool model named in worldspawn, like `aw_render_pool`) and
each attached part carries `"aw_far_owner" "<building entity>"`. At map load
the client builds a small table of records, as `AW_RenderRangesNewMap` does.

In `R_DrawBEntitiesOnList`, for a building with a far record:

- distance = from the view origin to the nearest point of the cluster's box;
- **separate switch-down and switch-up distances (hysteresis):** a full
  building becomes a shell when the distance exceeds `aw_far_shell`
  (candidate 300), and a shell becomes full again only below
  `aw_far_shell - aw_far_margin` (candidate margin 48), so a player standing
  near the boundary does not see it flicker; one state byte per entity;
- when it is a shell, draw the pool view with the building's transform and
  skip the attached parts (their owner is in shell state);
- `aw_far_shell 0` disables the feature for A/B tests.

Memory: **both representations stay resident** (originals are unchanged).
Heap cost of the bm019 shells as one far pool, from the engine's target
struct sizes (`check_world_map_heap.compile_target_sizes`): about 224 KB for
48-triangle shells, 368 KB for 96 triangles and 703 KB for the 16-unit
tolerance set, against a modelled loader residency of 5.41 MB for the map
(4 %, 7 % and 13 %). A built map must pass `check_world_map_heap` with its
existing reserves before any of these is chosen. One pool model per map uses
one model slot; one submodel per house would use 23 of the inline-model
budget the builder already guards.

Load time: the file grows by 166 KB (48 triangles) to 515 KB (16-unit
tolerance) on 4.56 MB, and the loader sets up 1,945-6,337 more faces on
31,022. Cell-load timing is part of the A/B.

## Planned FPS A/B/C/D

Same FS-UAE build, route and poses (the two street viewpoints above plus a
walking route through bm019), warp off, fixed clock, three repeats, `r_speeds`
face counts and frame time per variant in one sweep:

- A: current build (drift control, run first and last)
- B: shells at the 16-unit tolerance, `aw_far_shell` 300
- C: shells at 48-96 triangles, `aw_far_shell` 300
- D: shells at the 16-unit tolerance, `aw_far_shell` 200
- E: no shells, fog distance 250 (the known reference)

Plus cell-load time and the heap report for each variant.

## Why pure Python (and not a Blender step)

A pinned, scripted headless Blender step (remesh, decimate, transfer
attributes) would also satisfy the one-builder rule if it ran inside the
builder container. The comparison that led to plain Python here:

- dependencies: numpy and scipy are already build dependencies; Blender would
  add a large pinned binary to the builder image and its own update cycle;
- reproducibility: the Python tool is deterministic and its tests run in the
  ordinary suite; Blender's modifiers change between versions and would need
  a pinned version and result hashes;
- quality: Blender's voxel remesh and decimation are mature and probably give
  better shapes at very low budgets; this tool's measured errors above are
  the baseline to beat;
- maintenance: the Python tool is about 900 lines in the repo, reviewed like
  any other converter code.

This is a comparison, not a rule; if the quality at the needed budgets turns
out to be the limit, a pinned Blender step is a valid alternative.

## Open questions

- Shell quality per face: the quadric reducer on voxel surfaces is the
  limit at small budgets; a box-fitting pass for rectangular houses could
  need far fewer faces for the same outline.
- Whether faces of the far pool may exceed the 256-texel extent (they have no
  lightmaps and are only drawn at a distance) to avoid the split overhead.
- The material vote fault above.
