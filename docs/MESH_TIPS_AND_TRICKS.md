# Mesh tips and tricks: expensive scenery

Working findings for v0.0.23-dev5, 29 September 2026. Separate observed
performance, source inspection and proposed fixes; update this record after
native visual checks. A compiling mesh is not proof that its detail is useful.

## Case 1: Seyda Neen façades and projecting windows

### 1) Problem

In dev4, certain outdoor views become much slower while other views, including
a view containing only the bridge, remain fast. The user identified projecting
window surrounds on a tall house as a priority for flattening. Small decorative
faces can add substantial transformation, clipping, edge and surface work while
contributing little visible detail at the game's resolution. Repetition across
many instances multiplies that cost. A texture can carry such detail more cheaply
than individually rendered bevels and recesses, subject to actual measurement.

Reproduction views, in runtime coordinates:

| Purpose | XYZ | Yaw | Pitch |
| --- | --- | --- | --- |
| Slow exterior view | -37, 792, 75 | 265 | -4 |
| Close façade view | -202, 573, 23 | 279 | -61 |
| Earlier close view | -185, 525, 34 | 265 | -67 |

Lowering view distance to about 360 helped the user. That is a useful clue about
visible-scene workload, not proof of which mesh or subsystem is responsible.

### 2) Investigation

Hold camera, emulator configuration, assets and renderer constant. Hide selected
visual meshes only, retaining collision, and compare frame times. Do not compare
different viewpoints or attribute a frame-rate change to the nearest object.

Initial dev4-engine emulator samples at the slow exterior view:

| Diagnostic variant | Median frame time | Samples |
| --- | ---: | ---: |
| Original scene | 88.4 ms | 15 |
| House group hidden | 49.1 ms | 18 |
| Bridge group hidden | 69.1 ms | 18 |
| Target-name display disabled | 79.9 ms | 16 |

These are short, single-run diagnostic measurements, not final speedup claims.
The house group includes house shells and selected attached architectural parts;
it does not isolate windows. Hiding bridge geometry also helped in this mixed
view, even though the bridge alone is fast. Disabling names changes the target
trace path as well as text rendering, so its result needs repeated isolation.
None of these invisible-mesh variants belongs in a delivered playtest.

Source and converted-map inspection found:

- `ex_common_house_tall_02.nif`: 608 source triangles in the wooden-post material;
  plain wall materials have much smaller triangle counts. This is source triangle
  count, not the number of visible faces submitted every frame.
- The four windows on the reported façade are separate `ex_nord_win_01.nif` and
  `ex_nord_win_02.nif` instances. The initial suspicion that those particular
  windows were embedded in the house mesh was incorrect.
- In the audited dev4 BSP, these window models contain 145 and 123 faces
  respectively. References 113981 through 113984 place the four front windows.
- The tall house reference is 113828. The same house model also appears elsewhere;
  an approved model conversion must therefore be checked at other placements.
- Existing coplanar merging only merges compatible planes and UV mappings.
  Existing triangle simplification preserves components and materials, so it
  cannot reliably collapse many separate decorative components into one panel.

Treat this as excess decorative geometry to investigate, not permission to
remove all structure. Roof outlines, entrances, support silhouettes and terrain
occluders still need geometry. See [What are rocks?](WHAT_ARE_ROCKS.md) for why
removing an apparently decorative object can expose otherwise hidden terrain.

### 3) Solution

Use a reusable, non-destructive host conversion for approved surface types.
`config/surface-flattening.json` defines `decorative_windows.flatten: true` and
explicit model profiles. Setting it to `false` retains the original visual mesh
on rebuild. Original game files and collision geometry are never overwritten.

The current implementation in `tools/surface_flatten.py` projects selected
window geometry, depth-bakes its source textures into a small image, and emits
a flat textured panel with the source's convex projected outline. Profiles name
the projection axis, facing direction and mounting plane explicitly. They do
not guess that every thin mesh is disposable. `prepare_mesh_bsp.py` applies the
conversion before surface merging and keeps full source collision separately.

Initial approved type selection covers the two Nord window models above.
This is implemented conversion code, but native placement, texture and timing
validation is still pending. A panel at its mounting plane is not yet a combined
wall atlas: check whether the profile needs a mounting offset at each placement.
Do not call the visual/performance regression fixed until those checks pass.

Before delivery:

1. Compare original and flattened windows at the two close façade viewpoints,
   including oblique angles, both sides where relevant, and other instances.
2. Check winding, mounting depth, seams, texture orientation and edge dilation.
   Avoid z-fighting, floating panels, wall penetration and black borders.
3. Verify collision remains byte-for-byte/source-equivalent where possible.
4. Record source triangles, resulting BSP faces, repeated instance count,
   texture memory, and matched-camera frame times with flattening on and off.
5. Keep the original path and per-type switch. Extend profiles to another type
   only after inspecting that type; do not flatten all wooden posts by material.

The intended result is recognizable windows with far fewer decorative surfaces,
not a featureless house or a blanket reduction of every mesh's triangle count.

### Conversion validation and mounting correction

The first origin-plane projection hid one of the close-view windows behind its
wall. The pipeline now ray-tests the supporting house façade, accepts only
parallel outward-facing surfaces, and places each visual panel 0.05 runtime units
in front of that wall. Missing support fails conversion instead of guessing.
Original collision is retained; only visual placement is adjusted.

Both Nord window models now merge to one BSP face per instance, from 145 and 123
faces. All 21 matching exterior instances found supporting walls. Native checks
at `-202 573 23 / 279 / -61` and `-81 267 73 / 206 / 3` show the baked frame and bars;
the latter was repeated after fixing the initially hidden window.

At `-37 792 75 / 265 / -4`, with the same dev5 engine, the final 15 stationary
samples had median frame times of 86.425 ms with original windows and 77.619 ms
with correctly mounted flat windows, about 10.2% lower frame time. These are
reference-emulator observations, not physical Amiga results or a claim that all
exterior performance problems are solved. Remaining house detail still matters.

The private playtest applies the conversion to the dev4 BSP without deleting
unused original face records, preserving existing collision and visibility. It
reduces submitted visual geometry, not resident map memory. A full source rebuild
applies flattening before BSP assembly and avoids those unused visual records.

![Native close view after flattening and mounting](images/amiwind-v0.0.23-dev5-windows.png)

## Case 2: invisible scenery, residency and cleanup

### 1) Problem

Window flattening helps but does not explain all location-dependent stalls.
The user asked whether unneeded geometry is being offloaded and whether a
cleanup routine is missing.

### 2) Investigation

`Host_ClearMemory` flushes rendering caches, clears model state and frees the
map allocation back to the host mark during map changes. This is an explicitly
managed C renderer, not a managed-runtime garbage collector.

During a map, the selected BSP and scenery remain resident. Distance, PVS and
screen-frustum checks reject work, but rejection is not unloading. The scenery
compiler appends houses as brush submodels after the base terrain visibility
build. Those house walls do not automatically become occluders in the base PVS.
A potentially-visible set can consequently contain scenery hidden behind houses;
later clipping/rasterization may still do work before that scenery is occluded.
`R_MarkLeaves` already avoids rebuilding leaf visibility while the view leaf is
unchanged. Rotated brush bounds currently use a conservative radius box, which
can also admit more work than a tight rotated bound.

### 3) Solution

Keep map-change cleanup. Do not add periodic cache flushing as an FPS fix:
reloading useful assets could introduce stutters. Profile traversal, brush
submission, clipping and rasterization separately, then consider tighter cached
bounds and conservative host-baked house occluders or visibility groups. Preserve
openings and sightlines; never trade frame rate for disappearing scenery.
Streaming and resident-memory reduction remain separate future work. The dev5
window pass reduces rendered geometry; it does not claim a streaming system or
complete hidden-house rejection.
