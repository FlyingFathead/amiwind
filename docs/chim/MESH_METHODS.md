# CHIM mesh methods

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

Owner's data, the v0.0.36-dev3 world (Balmora, Seyda Neen, 270 CHIMport region cells), every mesh through
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
