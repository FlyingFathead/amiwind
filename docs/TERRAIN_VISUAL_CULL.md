# Terrain visual culling (created during AmiWind v0.0.28)

## Current status: coherent town host checks pass; native acceptance pending

The coherent 049/050 Seyda batch passes bounded host validation, and the assembled
V3 image is undergoing independent native testing. All 64 maps passed a strict
serialized second cut covering 2,129,800 placed polygons, with zero further
changes and zero winding failures. Twelve distinct NPCs pass identity/support
checks; 1,696 standing probes over the actual town cores plus a 32-unit guard
pass, with maximum measured height error 0.00015736 compiled units.

Seven maps required a float32 serialization correction: 13 replacement faces
add 1,776 bytes. Actual serialized coordinates are re-clipped with the same
0.5 overlap and 0.00002 boundary tolerance; no tolerance or coverage expansion
is used. Collision, PVS, actors and unchanged faces remain preserved. The 35
focused host checks pass. The 29 older probes outside mapped town coverage remain
historical diagnostics; they do not demonstrate a current defect or certify a
native route. Wider-world coverage and native appearance/ground/NPC traversal
remain open. This is bounded experimental source work, not global certification.

See [canonical culling evidence](CANONICAL_TERRAIN_CULLING.md) and
[stable preparation](RELEASE-v0.0.28.md) for current scope.

## Historical candidate010 rejection and 011 diagnosis

Owner review rejected candidate010 with hanging geometry at 24,650 stored faces.
Independent read-only audit002 subsequently verified that this candidate's final
serialized BSP contains zero sky render faces; this is binary geometry evidence
only, and the replacement sky/background appearance has not been verified on the
target. The same audit says terrain culling used compiled local LAND and did not
use the canonical NPZ heights. It reports 482 placed faces (277 distinct stored
IDs) wholly beneath one local LAND triangle by a conservative lower-bound test,
122 deep vertical world LAND faces at Z <= -500 that are not sky and are not all
proven removable, and 112 exactly zero-area stored faces (5 world, 107 inline).
The original source had zero and candidate010 has 112 exactly zero-area faces.
The regression arose somewhere in the original-to-candidate pipeline; the exact
emitting instruction/stage has not been traced. Do not attribute it specifically
to the culler or BSP writer. Shared/lightmap and fragment-growth retention categories remain. These are
candidate-specific independent-report results, not measurements rerun for this
document update and not a complete global-topology audit.

The 011 receipt uses the canonical NPZ for alignment diagnosis only: 288
source-grid corners, zero residual, source scale 0.25 and global origin
[-2816, -17920, 0]. The global surface is continuous near Z=80 where compiled
terrain is about Z=71 west and Z=80 east. No geometry was changed by that check;
it is not a repaired or accepted BSP. At that historical checkpoint the terrain operation remained
incomplete. Acceptance requires final serialized output with all inspector
hide/preview controls OFF and target sky appearance/loading verified.

The method details below describe bounded implementation behavior and candidate
trials. They are historical implementation evidence, not acceptance policy or
proof that the required culling is complete.

## Non-destructive compile-time behavior

Terrain culling is a pre-baked compiler operation on render faces. It writes or
clips those faces only in a fresh derived BSP; it does not edit or delete the
original source maps or source assets. The default is ON, with independently
configurable route overrides. ON and OFF candidates are separate builds from the
same preserved unculled source. OFF cannot restore faces removed earlier in a
pipeline, so keep the pre-cull source and build outputs distinct.

Candidate010 was incomplete because the implementation used compiled local LAND
instead of the required canonical terrain heights and retained unsupported
shared/lightmapped or fragment-growth cases. Those are receiver and fallback
limits in the culling implementation, not a destructive-action policy. A fresh
candidate is reviewable and reversible while the preserved source remains
unchanged.

## Mandatory Morrowind exterior map acceptance requirements

1. Remove EVERY local sky-enclosure render face: per-cell and per-subcell ceilings, walls, undersides and fragments, above or below ground. Subdivision does not make enclosure pieces legitimate scenery. Preserve current sky appearance through a separate shared/background rendering path, never another enclosure baked into each map.
2. Remove EVERY buried portion of static exterior render geometry using the actual, globally aligned canonical topomap surface and its varying slopes and seabed. Remove wholly buried faces and buried portions of crossing faces. Water level, flat planes, compiled local LAND proxies and finite-depth bands are not substitutes for the canonical global terrain input.

Keep the visible terrain surface intact. Preserve visible foundations, underwater structures above the seabed and visible water. Water is not terrain. Door-entered Morrowind caves and tombs load separate interior cells and are outside this exterior pass. Preserve required collision, contents and visibility behavior independently; they do not authorize retaining unwanted render faces.

Shared models and lightmaps require correct placement-specific clipping and deduplication/rebaking, with measured representation costs. They are not automatic exemptions. Missing terrain coverage, unsupported clipping, unresolved coordinate transforms or fragment-budget fallbacks must BLOCK ACCEPTANCE and be reported as incomplete. Do not report retained geometry as finished culling.

The serialized final BSP must satisfy both conditions with ALL inspector hiding and preview options OFF. Verify serialized geometry, render references, degeneracies, seams, shared placements and preserved collision/visibility, then matching-ABI memory and target appearance/loading. Attempted-face counts, collision checks alone and viewer-only hiding are insufficient.

These are required outcomes, not claims that the current implementation is complete. Candidate010 was rejected by owner visual review. It used compiled LAND proxies, not direct canonical NPZ evaluation. Direct NPZ alignment was subsequently checked at 288 source-grid corners with zero residual; that diagnosis is not a repaired BSP. The global packet exposed a continuous terrain surface where the compiled coarse/fine terrain had a height step.

For the existing sky background path, see [Day/night and sky](DAY_NIGHT_AND_SKY.md#existing-renderer-background-and-sky-enclosure-geometry).

## Canonical source-to-compiled terrain mapping

The global source heightfield and compiled BSP use different coordinate frames.
Record the source origin, compiled origin, scale, covered cells and heightfield
identity with each alignment receipt. The general mapping is an explicit scale
and translation:

```text
compiled_global = source * scale + translation
compiled_local  = compiled_global - compiled_tile_origin
```

For the 011 alignment diagnosis, the reported scale is 0.25 and compiled tile
global origin is [-2816, -17920, 0]. The equivalent source origin is
[-11264, -71680, 0], so source X/Y spacing of 128 units maps to 32 compiled
units and source Z is scaled by 0.25. Preserve negative source heights, including
seabed. The reported grid has 65 by 65 height samples per LAND cell; evaluate the
original triangle diagonal rather than substituting a flat plane or arbitrary
interpolation. Water is not part of the terrain heightfield.

The 011 check reports zero residual at 288 source-grid corners. It establishes
alignment at those checked points; it does not establish full coverage, correct
interior triangle evaluation, or geometry removal. Candidate010 records the
canonical heightfield for provenance but says it was **not used for culling**;
that pass used compiled town LAND and local guards. The global heightfield must
actually drive classification and clipping before the terrain requirement can
pass. See [Day/night and sky](DAY_NIGHT_AND_SKY.md#existing-renderer-background-and-sky-enclosure-geometry)
for the independent sky-background path.

## Coarse/fine terrain boundary diagnosis (separate from object culling)

Inspection004 reports a source terrain join defect at a fine port patch beside
coarse terrain. The canonical surface is continuous near compiled Z=80, while
the original BSP and candidate010 contain both lower and upper LAND surfaces at
the same join (about Z=71 and Z=80). Removing a vertical connector beneath the
canonical height without first making the rendered terrain surfaces continuous
can expose an opening. That is a terrain-generation defect; it does not justify
retaining deep underground geometry, nor does a seam repair remove buried objects.

A separately patched source checkpoint reports this bounded shared-edge result:

| Measurement | Before | After |
| --- | ---: | ---: |
| Coarse/fine boundary segments checked | 26 | 26 |
| Segments with mismatched shared vertices/heights | 23 | 0 |
| Largest measured height difference | 15 units | 0 |
| Source LAND triangles | 4,756 | 4,825 |

The +69 are **source terrain triangles**, not BSP faces or a memory estimate.
The patch adds matching intermediate source-height samples only along affected
coarse/fine edges; it does not uniformly increase terrain resolution. The report
also states that all 2,496 existing neighboring source-cell edge pairs agree in
the canonical data. Source-checkpoint reports list 25 focused tests and 9
synthetic reader tests as passing; this documentation update did not rerun them.
Native engine fixture compilation was not established because the supplied source
subset lacked `VERSION` and `progdefs.q1`. Treat the stitch as a review checkpoint;
do not mark the production source join fixed until a full-source handover and
reproducible receipt are available.

This source checkpoint is not an integrated/rebuilt final BSP. Full canonical
buried-object clipping remains in progress. A separate whole-face witness in the
report places one face at least 17.628961953 compiled units below the canonical
surface; this uses the global heightfield and is distinct from the earlier
22.55-unit witness against local rendered LAND. Neither the alignment check nor
the boundary stitch is acceptance of the serialized map, collision, memory,
visibility or target appearance.

## Current bounded implementation (incomplete; retained behavior is not acceptance)


The exterior mesh compiler enables `terrain_visual_cull` by default. This is
host-side preprocessing; no runtime format flag or visibility switch is added.
Original terrain geometry and all original model collision components are kept.
Only opaque LAND (`g<material>` faces emitted by the converter) is used. Water,
sky, closure stone, missing coverage and arbitrary scene interiors are excluded.

The compiler subtracts bounded triangular ground prisms from visual polygons.
The upper cut follows the sloping compiled terrain, leaving a configurable skirt (default 0.5 compiled units)
below the ground to prevent cracks. The lower bound is the lowest LAND vertex;
geometry below that finite bound is retained. Polygon corners and edges are
clipped, rather than testing only a centroid or a few sampled camera positions.
Uncertain fragment growth retains the original surface.

Shared visual geometry is removed only when the complete face is buried at
**every placement** sharing that representation. It creates no placement-specific
mesh variants. Crossing surfaces for shared or lightmapped models stay original.
A unique unlightmapped placement may clip a crossing face when the remaining
pieces merge into one convex polygon with bounded edge growth. Texture affine
mapping and face normals stay original; clipping therefore preserves the UVs.
Lightmapped crossing-face rebaking and additional shared variants are pending.

`config/terrain-visual-cull.json` uses strict JSON booleans and a finite nonnegative numeric overlap:

```json
{"default": true, "overlap": 0.5, "cells": {}, "subcells": {}, "bsps": {}}
```

Priority is BSP override, then subcell override, then cell override, then global
default. An explicit `--terrain-visual-cull true|false` on the direct mesh compiler
has highest priority. Keys are case-insensitive; a `.bsp` suffix is optional.
Duplicate normalized keys and non-booleans are rejected. Cell keys are the
existing coordinate pair, for example `-9,-9`; subcell and BSP keys are the
existing logical map names. Exterior region callers forward those identities.
Direct API callers can pass `terrain_cull_config`, `map_identity`,
`cell_identity`, and `subcell_identity`; `terrain_visual_cull=False` forces the
original visual path. Interior scenes are not terrain-culled.

Each compile receipt includes the effective boolean and its provenance, ground
policy/depth/overlap, input and output faces, clipped/removed/retained counts,
and sharing policy. A face or BSP byte reduction is not target heap acceptance:
run the normal geometry, content, target-loader and memory gates before promotion.
The Polycount Inspector density filter is diagnostic only and never an export
simplification method. Red density includes hidden stored geometry, not measured
runtime submitted drawing or heap bytes. Camera sampling can nominate hidden
faces for review but cannot prove that a face is never visible.


Each override can remain a boolean or independently override enabled/overlap:

```json
{"default": true, "overlap": 0.5,
 "cells": {"Seyda Neen": {"enabled": true, "overlap": 0.75}},
 "subcells": {"sn045": {"overlap": 0.25}},
 "bsps": {"sn012.bsp": {"enabled": false}}}
```

The same BSP > subcell > cell > global precedence applies **independently** to
both fields; an enabled-only override inherits overlap. The direct compiler and
bounded Seyda compiler accept `--terrain-cull-overlap NUMBER`; an explicit value
has highest overlap priority. Zero is valid; negative, boolean, nonnumeric,
NaN and infinity values are rejected. Overlap is measured in compiled BSP units,
not original TES3 coordinates. Water is always excluded: submerged geometry is
clipped only below actual opaque LAND/seabed, never merely below the water level.

`prepare_seyda_regions.py` applies this stage to every freshly compiled bounded
region and established special route before installation, saving separate
pre-cull source and cull receipts. Seyda's logical cell-group key is `Seyda Neen`;
its subcell/BSP keys are `sn000` through `sn063`. A common full-town source must
remain unculled before partitioning if individual subcells need an OFF comparison;
otherwise source-deleted faces cannot be restored by a later OFF override.
The bounded-builder's original metrics are explicitly labelled pre-cull metrics;
the changed final candidate requires the normal final target gates.

For a retained local BSP, `tools/cull_bsp_terrain.py INPUT --out FRESH.bsp
--terrain-visual-cull true --terrain-cull-overlap 0.5` creates a separate private
candidate. It never overwrites its input or an existing output. Input textures
and geometry remain local. The default 0.5 candidate does not validate other
settings or demonstrate whole-town target fit; receipts identify actual settings.
