# Face validation

`tools/check_faces.py` checks every face of every model of a BSP29 map as the
engine reads it (`engine/aga/src/model.c`: `Mod_LoadFaces`, `Mod_LoadTexinfo`,
`Mod_LoadSurfedges`, `CalcSurfaceExtents`; `r_draw.c` for winding). It is
read-only, asset-free and runs on any map, converted or compiled.

```sh
python3 tools/check_faces.py MAP.bsp|DIRECTORY... [--report report.json] [--maps]
    [--severity CHECK=fail|warn|off] [--threshold CHECK.warn|fail=VALUE] [--worst N]
    [--extent-rule engine|binary32|extended]
python3 tools/check_faces.py --list-checks .
```

Exit code: 0 clean or warnings only, 1 when a `fail` check has failing faces,
2 when a map cannot be read as BSP29. The JSON report has per-check counts
(`flagged` = above the warn level, `failing` = above the fail level), the worst
cases (map, model, entity class, face, texture, value) and a per-model
breakdown; `--maps` adds every per-map report.

## Why

Three converter faults (CONVERT-FACE-PLANE-32, CONVERT-MERGE-NONPLANAR-32,
CONVERT-TEXCOORD-RANGE-32) and four lightmap/extent faults (EXTENTS-FPU-RULE-31,
LIGHTMAP-GRID-31, LIGHTMAP-TAIL-31, MESH-EXTENT-GRID-31) were each found late,
on one map, by a different tool. Every one of them is visible in the stored
faces. The repair is one shared face builder used by every converter path
(plane from the whole polygon and refit after merging, the engine's extent
rule, the 16-bit texture range, lightmap size from the stored values), with
this validator run on every built map as a builder gate. No path-specific
patches.

## Checks

Every check is `fail`, `warn` or `off`. Metric checks have a warn and a fail
threshold; flag checks count every hit at their severity. Faces that fail a
structural check are left out of the geometric checks (their vertices cannot
be trusted); faces whose edge loop is open are left out of the geometry
checks only.

### Structure (index ranges)

| Check | Default | Meaning |
| --- | --- | --- |
| `face_plane_index` | fail | plane index (unsigned 16 bits) outside the plane lump |
| `face_texinfo_index` | fail | texinfo index (unsigned 16 bits) outside the texinfo lump |
| `face_edge_range` | fail | firstedge/numedges outside the surfedge lump |
| `surfedge_index` | fail | a face's surfedge points outside the edge lump |
| `edge_vertex_index` | fail | an edge of the face points outside the vertex lump (the engine does not check this) |
| `texinfo_miptex_index` | fail | texinfo miptex outside the texture table |
| `edge_zero_used` | fail | the face uses edge 0: `CalcSurfaceExtents` reads it forward (`e >= 0`), the renderer backward (`e > 0`) |
| `edge_loop_open` | fail | consecutive edges do not share a vertex |
| `face_unowned` | warn | face in no model's face range |
| `face_multiple_models` | warn | face in partly overlapping model face ranges; models with an identical range are instances of one geometry, counted as `instanced_models`, not flagged |
| `model_face_range` | fail | model face range outside the face lump |
| `node_face_range` | fail | node face range outside the face lump |
| `marksurface_index` | fail | marksurface outside the face lump |
| `leaf_mark_range` | fail | leaf marksurface range outside the lump |
| `plane_normal` | fail | normal length off 1 by more than 1e-4 (warn) / 1e-2 (fail) |
| `plane_type` | fail | type outside 0-5, or an axial type (0-2) whose normal is not exactly +axis: the engine then uses `dist` and the coordinate directly and gets the side wrong |

### Geometry

| Check | Default | Meaning |
| --- | --- | --- |
| `planarity` | warn > 0.02, fail > 0.25 units | largest vertex distance from the stored plane |
| `plane_tilt` | warn > 0.5, fail > 5 degrees | angle between the stored normal and the polygon's Newell normal |
| `plane_side` | fail | winding faces the other way than the plane and side flag say |
| `degenerate_vertices` | fail | fewer than 3 edges, distinct vertex indices or distinct positions |
| `degenerate_area` | warn | area below 0.001 square units (collinear or coincident vertices) |
| `degenerate_sliver` | warn | width (2 x area / longest chord) below 0.01 units |
| `zero_length_edge` | warn | a repeated consecutive vertex (edge shorter than 0.001 units) |
| `nonconvex` | warn > 0.01, fail > 0.5 units | depth of the deepest reflex vertex inside the chord of its neighbours |

Winding: Quake faces are clockwise seen from the front. In `R_EmitEdge` an
edge going down the screen is a trailing (right) edge, so the boundary runs
down the right side and up the left. The right-handed Newell normal of a
correct face therefore points away from its facing normal (the plane normal,
negated when the side flag is set). A face with the wrong winding gets its
leading and trailing edges swapped.

Threshold reasons. Stored vertices are single precision; within the map's
+-32768 units one float step is at most 0.004 units, so storage alone keeps a
vertex within 0.004 of an exact plane. The planarity warning (0.02) is five
storage steps and catches the 0.05-unit bend of rounded coplanar grouping.
The failure level (0.25) is where the renderer's 1/z gradients and backface
test, both taken from the stored plane, start to show at close range;
qbsp-class compilers keep faces within 0.1 of their plane. Rounded grouping
normals tilt by under 0.01 degree, so 0.5 degree is fifty times that; 5
degrees is a visibly wrong plane. The span renderer draws one span per surface
and scan line, so a reflex vertex deeper than half a unit can leave gaps or
overdraw at close range; 0.01 units is the noise level of merged polygons with
collinear runs. Faces below 0.001 square units have no stable normal and are
not judged for orientation or convexity.

### Surface extents

| Check | Default | Meaning |
| --- | --- | --- |
| `extents_engine` | fail | engine-rule extent above 256 texels on a non-special face (`Bad surface extents`) |
| `extents_target` | warn | single-precision or 68040-extended rule above 256 texels while the engine rule fits |
| `extents_rule_disagreement` | warn | the FPU rules give different texture minima or extents: the lightmap size depends on the arithmetic (EXTENTS-FPU-RULE-31); engines before the double-precision rule are exposed |

The engine rule is `tools/surface_grid.py`'s (double precision after every
product and sum, in source order, from the stored single-precision values);
the tests check that both give the same grid.

`--extent-rule` chooses the arithmetic used for the extent, 16-bit and
lightmap checks: `engine` (default, the current engine), `binary32` (single
precision after every step: engines before the double-precision rule,
compiled for the 68040) or `extended` (68040 extended intermediates, as an
emulator may compute them). Running a map under two rules shows whether its
lightmaps fit one engine but not the other.

### Texture coordinates

| Check | Default | Meaning |
| --- | --- | --- |
| `texcoord_range` | fail | `texturemins` or `texturemins + extents` outside the 16-bit fields of `msurface_t` |
| `texcoord_margin` | warn | a vertex coordinate within 2048 texels of the 16-bit edge |

### Lightmaps

Sizes use the engine rule: `((extent >> 4) + 1)` samples per axis times the
number of light styles before the first 255. Faces with special texinfo (sky,
water) read no lightmap.

| Check | Default | Meaning |
| --- | --- | --- |
| `lightmap_offset` | fail | negative light offset other than -1 |
| `lightmap_outside_lump` | fail | the lightmap runs past the end of the lighting lump (LIGHTMAP-TAIL-31) |
| `lightmap_overlap` | fail | the lightmap runs into the next face's samples (LIGHTMAP-GRID-31) |
| `lightmap_span_mismatch` | warn | the stored block (up to the next offset) is longer than the engine reads: the bake grid differs from the engine's |
| `lightmap_shared_size` | warn | faces sharing one offset need different sizes |

## As a builder gate

The converter repair puts one face builder behind every converter path and
runs this validator on every map the builder writes, with the defaults above:
a map with a failing face stops the build with the face named. Warnings are
reported in the build summary. Maps compiled by the Quake tools pass the same
checks, which makes the validator usable as an A/B oracle for converter
changes.
