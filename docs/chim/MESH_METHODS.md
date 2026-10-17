# CHIM mesh methods

<!-- contents start -->
## Contents

- [Planar merge](#planar-merge)
- [meshoptimizer with locked borders](#meshoptimizer-with-locked-borders)
- [The method table and its rule](#the-method-table-and-its-rule)
- [Measured](#measured)
  - [Tel Uvirith cell (10,1) diagnostic, 12 October 2026](#tel-uvirith-cell-101-diagnostic-12-october-2026)
- [Selecting a method](#selecting-a-method)
- [Determinism, keys and checks](#determinism-keys-and-checks)
- [Licence](#licence)
  - [Cell (10, 1): shared lantern/support and fixed-stage diagnostic (2026-10-12)](#cell-10-1-shared-lanternsupport-and-fixed-stage-diagnostic-2026-10-12)
  - [Ash-tree sprite trial (2026-10-12)](#ash-tree-sprite-trial-2026-10-12)
  - [Door panel candidate (2026-10-12)](#door-panel-candidate-2026-10-12)
  - [Fixed construction-state conversion](#fixed-construction-state-conversion)

<!-- contents end -->

How the CHIM builder turns each mesh into Quake faces. Quake faces are convex planar polygons, not
triangles, and every face costs memory in the CHIM zone and time in the renderer, so the builder makes as
few faces as the shape allows. Three methods exist and all stay selectable:

| Method | Reduction | Faces | Lossless |
| --- | --- | --- | --- |
| `converter` | the mesh's profile reducer (`static_lod.reduce_for_profile`) | the converter's polygon step (`mesh_geometry.surface_polygons`) | the method before v0.0.36-dev3 |
| `merge` (default) | the same | planar merge (`tools/planar_merge.py`), never more faces than `converter` | yes |
| `meshopt+merge` | meshoptimizer's simplifier with locked borders (`tools/meshopt.py`) in place of the profile's reducer | planar merge | no: a different reduction, chosen by measurement |

## Planar merge

The converter already merges triangles whose plane and texture mapping round to the same key, two at a
time while their union stays convex. Planar merge finds the merges that one misses:

1. **Regions.** Triangles joined across a shared edge when they have the same material, lie in the same
   plane (every corner within 0.01 units of the region's first triangle's plane) and carry the same texture
   mapping up to whole texture repeats (every corner within 0.05 texels after removing a whole-texture
   shift: the same texels). The converter's key keeps such triangles apart when their offsets differ by a
   whole repeat or round differently.
2. **Convex faces.** Each region is split into convex polygons by joining faces across their shared edges
   while the union stays convex (the Hertel-Mehlhorn convex partition), longest edges first, at most 32
   corners. Collinear corners on the outline are kept, so a neighbour's edge that meets the face there
   still meets a corner and no T-junction gap opens.
3. **Extent split.** The converter's 240-texel split, unchanged (the engine's surface limit).

The merged list is used when it has fewer faces than the converter's; on a tie the converter's stays. The
surface, materials and texture mapping are the source's, so planar merge is lossless: seams, rims and
shape are exactly those of the reduction before it.

## meshoptimizer with locked borders

For large hard-surface shells that a profile reduces (the arrival ship: ratio 0.2), meshoptimizer's
simplifier (v1.3) replaces the profile's reducer. Each material is simplified on its own to about the
profile's ratio, welded by exact position and texture coordinate first, with `meshopt_SimplifyLockBorder`:
every vertex on a material's open border keeps its exact position, so the rims where parts meet stay where
the source has them (the seam rule of [MESH-LOD-OPEN-SEAMS-33](../bugs/MESH-LOD-OPEN-SEAMS-33.md)). Every
connected part is simplified on its own (parts of at most 12 triangles stay whole, as in the default
reducer); no collapse may move the surface more than 0.25 % of the whole mesh's diagonal; and a part whose
result no longer spans its source part on every axis (a closed mast pole collapsing to a line) is kept whole.
The result references source vertices only. Planar merge then makes the faces.

## The method table and its rule

`config/mesh-methods.json` holds the default method (`merge`) and the meshes that get another one, each
with the measurement that chose it. The rows come from a rule, applied island-wide by
`tools/mesh_methods.py sweep` to every mesh a CHIM area reduces:

> a hard-surface mesh (meshes/x, d, o, i, l, not flora_ or terrain_) that its profile reduces (ratio below
> 1), with at least 200 faces by the converter, gets `meshopt+merge` when that gives fewer faces, no more
> torn seam or rim length (the seam audit) and no larger shape error (Hausdorff distance, sampled both
> ways) than the converter.

Flora, rocks and creatures keep their reducers (organic shapes: the silt strider stays on its
boundary-locked reducer, [reference models](REFERENCE_MODELS.md)). Meshes that no profile reduces (the
Vivec cantons, houses, docks) get planar merge only.

## Measured

Maintainer's data, the v0.0.36-dev3 world (Balmora, Seyda Neen, 270 CHIMport region cells), every mesh through
the converter (`prepare_mesh_bsp._prepare_model`), 11 October 2026. Render bytes: the model record's
render part (planes, vertices, texture vectors, faces, edges).

| Areas | Meshes | Faces, converter | Faces, mesh methods | Render bytes, converter | Render bytes, mesh methods |
| --- | ---: | ---: | ---: | ---: | ---: |
| Balmora | 225 | 41,886 | 40,878 | 4,239,320 | 4,151,012 |
| Seyda Neen (planar merge; the ship below) | 60 | 21,659 | 21,115 | 2,178,844 | 2,181,736 |
| CHIMport region frames | 120 | 37,608 | 36,743 | 3,837,000 | 3,759,348 |
| **TOTALS** | **405** | **101,153** | **98,736** | **10,255,164** | **10,092,096** |

No mesh gets more faces. The largest gains are flat-sided hard surfaces: the shipwreck 3,740 to 3,657
faces, the longboat 3,302 to 3,234, Hlaalu house 06 910 to 853.

### Tel Uvirith cell (10,1) diagnostic, 12 October 2026

A bounded per-cell trial from source `3fac049` compared the original conversion, a `meshopt+merge`
override (ratio cap 0.5), and that override followed by an opt-in terrain-aware render-face cut.
These are compiled CHIM face counts and modelled active-ring peaks, not native frame times or an
accepted world build. Terrain meshes and collision inputs were excluded from mesh simplification.

| Trial | Placed faces | Stored faces | Modelled active-ring peak |
| --- | ---: | ---: | ---: |
| Original conversion | 56,830 | 41,713 | 11,970,016 B |
| Optimizer override only | 51,435 | 36,710 | 11,113,744 B |
| Optimizer override plus terrain cut | 49,925 | 35,466 | 10,964,336 B |
| Stronger all-mesh optimizer plus terrain cut | 30,985 | 21,087 | 9,045,776 B |

Against the original conversion, the optimizer alone removes 5,395 placed faces and 5,003
stored faces, with 856,272 B lower modelled peak. The added terrain cut removes 1,510 placed
and 1,244 stored faces, with 149,408 B lower modelled peak. Together they remove 6,905
placed faces (12.15%) and 6,247 stored faces (14.98%), with a 1,005,680 B (8.40%) lower
modelled peak.

The stronger row is a separate diagnostic, not the same settings as the preceding rows.
It simplifies all 44 nonterrain source meshes at ratio cap 0.2 instead of 0.5,
with maximum geometric error 0.01 of each mesh's diagonal instead of 0.0025;
locked borders and the extent guard remain. `terrain_` meshes and LAND stay
unchanged. It removes 25,845 placed faces (45.48%) from the original conversion
and 18,940 more than the earlier optimized-plus-clipped trial. The modelled
all-stage peak remains 2,803,472 B over the same budget. All 88 resolved
collision graphs match the earlier clipped candidate; the 169,776 clipnodes
and 507 terrain faces are unchanged. Format, terrain seams, hull policy and
all six doors pass offline; 699 stairs have zero failures and 41 advisories.
This is a different stair sample count from the earlier trial, not a matched
native movement test. Sixteen mesh-method regressions pass.

A hypothetical Stronghold stage-residency filter on this stronger candidate
estimates stages 0Ã¢â‚¬â€œ5 below the budget, with stage 5 at 5,941,424 B and only
300,880 B headroom. Stage 6 reaches 6,242,384 B at one sampled position:
**80 B over** the 6,242,304 B budget. The current engine does not implement
stage-selective residency; transition overlap, neighboring demand, metadata
and deferred actors remain unaccounted. The candidate has no native visual
comparison or release acceptance. In particular, this narrow modeled miss
does not turn the all-stage memory failure into a pass.

The terrain cut removed another 1,510 placed and 1,244 stored faces after optimization, clipped
918 stored faces crossing the ground, and lowered the modelled peak by 149,408 B. The final peak
still exceeds the unchanged 6,242,304 B budget by 4,722,032 B. The 507 terrain faces stayed
at the same count. All 169,776 collision clipnodes stayed at the same count, and a separate
resolved-graph comparison found equal plane tuples, child indices and hull 1Ã¢â‚¬â€œ3 roots for all
88 models; byte identity and native collision behavior have not been established.

The cut uses the cell's exact ground triangles with a recorded 0.5-unit contact overlap. It
removes shared faces only when buried at every placement; crossing faces are clipped only for
unique, unlightmapped models whose result remains a safe convex face. Format, terrain seams,
doors and the stair walk pass offline (1,363 steps, zero failures, 86 advisories), as do 13
existing terrain-cull tests. The CHIM hidden-face audit still reports "not measured"; these
trial counts do not establish a renderer-counter comparison. Matched FS-UAE/OpenMW views,
native gameplay and broader deployment remain pending. See
[CHIM-HIDDEN-FACES-33](../bugs/CHIM-HIDDEN-FACES-33.md) and
[CHIM-MOLAG-MEMORY-38](../bugs/CHIM-MOLAG-MEMORY-38.md).

A separate hypothetical stage-residency calculation on the optimized and clipped candidate
estimates active-ring peaks of 1,115,744; 1,451,376; 1,541,344; 5,113,632; 5,721,376;
6,890,304; and 7,329,328 B at Stronghold stages 0Ã¢â‚¬â€œ6. Stages 5 and 6 remain 648,000 and
1,087,024 B over budget. The current engine does not implement this stage-selective loading;
metadata, transition overlap, neighboring frames and deferred actors are not accounted for.

The maintainer repeatedly identifies lantern assemblies as visual density hotspots. In this cell,
the original streetlight mesh has 149 faces and its separate curved support has 264 faces.
Those observations do not establish that lanterns dominate the ring's memory cost.

A model-record audit of the original and optimized-plus-clipped candidates confirms that
these assemblies are unchanged by the conservative pass. The 149-face streetlight has
18 placements but one shared 26,592 B resident model. The 264-face curved support also
has 18 placements, represented by three variants at 37,920 B each (16, 1 and 1
placements). Together they account for 7,434 placement-expanded faces and 140,352 B
summed across distinct resident model records. That sum excludes textures and placement
records and is not a stage-specific ring peak. They are actionable density hotspots,
but cannot by themselves explain the multi-megabyte deficit; multiplying resident
bytes by placement count would overstate their cost.

A separate opt-in 512-unit model-tiling trial at 256-unit grain was applied after
the optimizer and terrain cut. Placed and stored faces stayed at 49,925 and 35,466,
while models rose from 88 to 96, collision clipnodes from 169,776 to 175,324,
and the modelled all-stage peak from 10,964,336 to 11,634,544 B (+670,208 B).
Its hypothetical stage-6 peak is 7,999,536 B, 1,757,232 B over budget, against
7,329,328 B and 1,087,024 B over budget without tiles. This tested setting
worsens memory; it does not rule out other subdivision strategies. Native
geometry, collision and movement acceptance remain pending.

A further root/slavemarket-focused 128-unit model-tiling diagnostic after the same
optimizer and terrain cut also kept 49,925 placed and 35,466 stored faces. It
raised the model count from 88 to 174, clipnodes from 169,776 to 193,228, and
the modelled all-stage peak from 10,964,336 to 13,282,192 B (+2,317,856 B).
Although the largest model block fell from 645,312 to 327,360 B, the extra
pieces made total residency worse. Three hull-limit checks failed (maximum
depth 3,081). This targeted tile setting is rejected; the result does not
evaluate layout sectors or every model subdivision method.

This cell trial builds on substantial earlier conversion and optimization work in Seyda Neen,
Balmora and Vivec. The existing [CHIM feature measurements](FEATURES.md) and this page's
area table hold the established results; this diagnostic does not remeasure or replace them.

The sweep measured all 102 meshes the dev3 world's areas reduce. One of them is a hard-surface shell, and
the rule chose it:

| Mesh | Method | Faces | Triangles | Torn seam / rim | Hausdorff (MW units) |
| --- | --- | ---: | ---: | --- | ---: |
| x/ex_de_ship (ratio 0.2) | converter | 4,046 | 1,954 | 2.2 % / 1.4 % | 204.4 (mean 4.95) |
| | meshopt+merge | 3,690 | 3,142 | 0 / 0 | 29.8 (mean 0.90) |

The ship's record is 18,364 bytes larger (339,052 against 320,688: it keeps 3,142 triangles' corners where the
converter kept 1,954), so Seyda Neen's render bytes rise by 2,892 bytes in all. The ship gets 9 % fewer faces
than before with closed seams and about a seventh of the shape error: the
converter's reducer reached its ratio by collapsing the hull's ribs and rails into slivers (many triangles
end up as faces cut by the 240-texel split), while meshoptimizer keeps every part's outline. Unbounded,
meshoptimizer reached 2,611 faces but removed the four mast poles and the rope entirely (closed thin parts
have no border to lock); the error bound and the part guard below keep them.

## Selecting a method

- `tools/build.py --chim-mesh-method table` (default): the table.
- `--chim-mesh-method converter | merge | meshopt+merge`: one method for every mesh (an override; `converter`
  reproduces the earlier output). `tools/chim_build.py --mesh-method` is the same switch.
- Per mesh: a row in `config/mesh-methods.json` (`"method"` and `"measured"`); the table test checks every row.

Only the CHIM builder's profiles carry the method (`chim.build.prepare_area` for towns and CHIMport cells,
`chim.seyda` for Seyda Neen); the legacy converters are unchanged.

## Determinism, keys and checks

- Same input, same output: planar merge uses fixed orders only; meshoptimizer is single-threaded per mesh
  and returns source vertices only. Tests (`tests/test_mesh_methods.py`) compare SHA-256 over repeat runs
  and with one and two workers.
- Each prepared mesh is a hashed CHIM unit (`chim.units`, shared unit cache), keyed by its record and its
  profile. A mesh's method adds `faces`, `reducer` and `method_version` to its profile; `method_version`
  names the planar-merge version and the SHA-256 of the vendored meshoptimizer sources, so a changed step
  makes new units and everything else is reused. The converter method adds nothing, so converter units
  keep their keys.
- Checks: the seam audit measures the reduction of every mesh (planar merge does not change it); the
  variant audit (`tools/chim/variant_audit.py`) checks every baked variant against its base; the sweep
  records seams and shape error of every `meshopt+merge` row before it enters the table.

## Licence

meshoptimizer is MIT (Arseny Kapoulkine). Its simplifier sources are vendored unchanged with their licence
in `third_party/meshoptimizer` (version, SHA-256 per file in its README) and compiled on the build host
with the C++ compiler the build already needs, into a library named by the sources' SHA-256: no download,
no prebuilt binary, nothing linked into the Amiga runtime. Planar merge and the boundary-locked reducer are
AmiWind's own code (methods credited in [licensing and credits](../LICENSING_AND_CREDITS.md)).


### Cell (10, 1): shared lantern/support and fixed-stage diagnostic (2026-10-12)

The next compiled trial replaces the street lantern with a closed outer shell
(20 polygons / 32 triangles) and reduces all three root-hook variants to 66
triangles each. There are 18 lantern placements and 18 hook placements. Relative
to the previous optimized/clipped candidate, placed polygons fall from 30,985
to 27,007; stored polygons fall from 21,087 to 20,682. Terrain remains 507 faces.
The active-ring peak falls from 9,045,776 to 8,988,352 bytes: 57,424 bytes saved,
but still 2,746,048 bytes above the 6,242,304-byte budget. Shared model bytes are
counted once per resident variant, not once per placement. The resolved standing
collision graphs match for all 88 models; this is not native gameplay acceptance.
Lantern texture projection is provisional; decorative bands still need baking.

The original lantern has 149 polygons / 166 fan triangles and one 26,592-byte
shared model for 18 placements; the new shell has 20 polygons / 32 triangles
and one 9,680-byte model. Each original hook variant has 264 polygons / 264
triangles and a 37,920-byte model; after the stronger optimizer it has 158 /
158 and a 23,504-byte model, and the handcrafted trial has 66 / 66 and a
10,960-byte model. Three hook variants remain. Placement-expanded polygon
savings must not be multiplied into resident model-byte savings.

A separate fixed completed-stage (stage 6) diagnostic excludes 33 inactive
construction placements, leaving 120 placements, 59 models and 19,354 placed
polygons. Active-ring peak is 6,167,056 bytes, giving 75,248 bytes of headroom.
The wider load-ring peak is still 6,590,736 bytes (348,432 over budget).
Source parity validation flags the 33 omitted placements, so the overall
candidate is not accepted. This is a fixed-stage build, not implemented runtime
state filtering; saved state, activation transitions and native comparisons
remain pending. Do not describe this as a production memory pass.

The same optimized candidate already reduces ex_t_doorway_01 from 822 to 408
triangles and its shared zone block from 126,272 to 70,000 bytes. The selected
full-size ex_t_slavemarket variant falls from 966 to 423 polygons, with its zone
block falling from 616,240 to 542,976 bytes. Concealed portions require their own
visibility audit; selection of an entire mesh does not prove it can be removed.

A separate door geometry-only sweep from the original 822-triangle source
produced 408, 310, 282 and 260 triangles at increasing simplification error
bounds. Those trial counts are triangles, not compiled polygon or heap
measurements; none of those extra sweep variants was visually accepted.


### Ash-tree sprite trial (2026-10-12)

A fixed construction-stage test of cell (10,1) replaced five placements of
ash-tree models 03, 04, 06 and 07 with the existing shared sprite representation.
The two scales of model 07 share one bitmap. Source assets and generated sprites
remain private and must be generated from the user's own game installation.

The five visual meshes contained 2,632 polygons / 2,744 fan triangles. Their
combined model blocks fell from 397,488 to 34,672 bytes, retaining collision.
All 59 model collision graphs matched the preceding test. Four sprite files
total 41,903 bytes; file size is not runtime allocation.

The sprite files occupy a separate Hunk allocation from the measured CHIM
model blocks. Neither their file size nor the model-block reduction is a
complete runtime memory balance until that allocation is measured.

CHIM active peak changed from 6,167,056 to 6,032,032 bytes; load-ring peak changed
from 6,590,736 to 6,264,336 bytes. The latter remains 22,032 bytes above the
previous 6,242,304-byte budget, before correcting available room for sprite
residency. Do not report this as complete heap acceptance.

A private FS-UAE diagnostic loaded and ran a 31-second scripted session with
a visible tree sprite. The capture is poorly framed; matched original-game
appearance and normal movement/collision acceptance remain pending. This trial
does not implement construction-stage transitions or establish release readiness.

### Door panel candidate (2026-10-12)

A later compiled bitmap-panel trial covers two source door types and six
placements through four distinct transformed models. Each candidate is a
shaped, double-sided panel of 2 compiled polygons / 24 fan triangles. Door 01
previously had 98 polygons / 134 triangles and its model block changes from
15,232 to 1,712 bytes. Door 02 previously had 42 polygons / 70 triangles;
its three transformed model blocks change from 7,552 to 1,872, 7,392 to
1,712, and 7,552 to 1,872 bytes. These are resident model costs, counted
once per variant, not once per placement. All 59 resolved collision graphs
match the preceding fixed-stage candidate; door activation and traversal have
not been tested.

Against the preceding ash-sprite candidate, modelled active-ring peak falls
6,032,032 to 6,008,192 bytes and load-ring peak falls 6,264,336 to 6,240,496
bytes. Relative to the previous 6,242,304-byte room, that is 234,112 bytes
below at active radius and only 1,808 below at load radius. Sprite runtime
Hunk use has not been charged against this room, so these nominal figures do
not establish a playable memory fit. In a 33-second FS-UAE diagnostic, the
door test map loaded and kept running; both panels were visible. The first
capture is very close and pixelated, while the second shows the panel obliquely
with nearby geometry gaps of unknown cause. The camera used noclip, so this
does not establish normal interaction or collision. Better framed native and
matched original-game views remain pending; the candidate is unshipped.


### Fixed construction-state conversion

An explicit area setting `fixed_visibility_state` (for example,
`{"stronghold": 6}`) can select a single-cell construction snapshot. This is
opt-in conversion behavior, not runtime quest progression. Only the source
auditor's complete, recognized enable/disable predicates may exclude a
reference; unknown or unaudited references remain present.

The source stage records the master hash, cell, requested globals and per-reference
decisions in `fixed-visibility.json`. State and evaluator source are cache inputs.
Changing state rebuilds the source stage while preserving the previous evidence.
The same selection applies to resumed frame references and to CHIM placements
after flora merging, without modifying the shared model pool. Missing or mismatched
state receipts fail conversion. Sprite entity integration and exact-frame/native
validation remain necessary before enabling a release cell with this setting.
