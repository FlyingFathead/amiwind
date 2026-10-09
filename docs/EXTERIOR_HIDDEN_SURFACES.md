# Exterior hidden surfaces and one-sided drawing

Recorded 4 October 2026. The source/provenance checks below are complete for the
named inputs. An optional source-bound per-asset shape/triangle exclusion stage is now
implemented and synthetically tested. Asset-local volumes, placement overrides
and the inspector-zone connection remain proposals. No production house geometry
was removed by this investigation; no target-rendering acceptance is implied.

<!-- contents start -->
## Contents

- [Owner imperative: default compile-time hidden-surface culling](#owner-imperative-default-compile-time-hidden-surface-culling)
- [Verified mesh pipeline gap and BSP storage](#verified-mesh-pipeline-gap-and-bsp-storage)
  - [Source-loop winding and serialized-output validation — 4 October 2026, 04:23 EEST](#source-loop-winding-and-serialized-output-validation--4-october-2026-0423-eest)
- [Cell loading, backface rejection and stored geometry](#cell-loading-backface-rejection-and-stored-geometry)
- [Verified exterior-export provenance](#verified-exterior-export-provenance)
- [What the converter actually creates](#what-the-converter-actually-creates)
- [Permanent exclusion catalog: proposed contract](#permanent-exclusion-catalog-proposed-contract)
- [Whole-scene exterior reachability proposal](#whole-scene-exterior-reachability-proposal)
  - [Diagnostic 022: bounded helper made no house cut](#diagnostic-022-bounded-helper-made-no-house-cut)
  - [Build integration and scope assessment](#build-integration-and-scope-assessment)
  - [Independent BSP plane and terrain-UV audit](#independent-bsp-plane-and-terrain-uv-audit)
  - [Independent sn045 package review and memory accounting](#independent-sn045-package-review-and-memory-accounting)
- [Combined object and canonical-ground boundary: proposal and A/B](#combined-object-and-canonical-ground-boundary-proposal-and-ab)
  - [Idempotence and boundary acceptance](#idempotence-and-boundary-acceptance)
- [Inspector plans and the compiler boundary](#inspector-plans-and-the-compiler-boundary)

<!-- contents end -->

## Owner imperative: default compile-time hidden-surface culling

Recorded 4 October 2026 01:33 EEST. Compile-time omission of permanently hidden
static exterior render surfaces is an owner-required default: the effective
`--hidden-surface-cull` setting must be `true` unless explicitly overridden with
`--hidden-surface-cull false`. Build diagnostics must report the effective value
and the relevant input, examined, excluded and retained surface counts so the
setting and its effect are auditable.

The option controls only the final serialized bounded automatic exterior pass.
Reviewed source-bound exclusions and source hidden-node flags are separate export
behavior; this option does not toggle them. The bounded pass does not remove every
interior face from every house. No general automatic sealed-interior solver
exists; the available helper proves only a bounded class of closed opaque convex
shells. Exact-face paint remains a review aid; whole-
world manual painting is not a prerequisite. Inspector plans are not connected
to the compiler and must not be described as baked culling.

This is a required setting contract, not a claim that the code path is complete.
The repository now contains the default-on `--hidden-surface-cull` option and a
bounded closed, opaque-shell containment helper. The setting and helper are in
source, while production gating and evidence remain pending; no new production
house savings have been measured. Canonical topomap terrain clipping remains a
separate `--terrain-visual-cull` path with incomplete production acceptance. Viewpoint-occluded surfaces still needed as
viewpoints move belong to runtime visibility. Preserve visible exteriors, water,
and collision independently; door-loaded interiors remain outside this exterior
render pass.

## Verified mesh pipeline gap and BSP storage

Source review recorded 4 October 2026 01:37 EEST confirms a gap in the
`prepare_mesh_bsp.py` static-mesh route. Its `prepare()` runs `qbsp`, `vis` and
`light`, rebuilds the world hull, then calls `append_meshes()` to add static mesh
surfaces. Those appended surfaces therefore bypass the brush CSG performed on
the earlier map brushes. This finding is scoped to this route; it does not
describe every build pipeline. The optional canonical terrain-visual-cull pass
is separate and has incomplete production acceptance. See [`prepare()` and
append step](../tools/prepare_mesh_bsp.py#L414) and [`append_meshes()` call](../tools/prepare_mesh_bsp.py#L432).

The runtime loader allocates a `msurface_t` record for every face stored in the
BSP face lump and sets `numsurfaces` to that full count. It also allocates loaded
vertex, edge and texinfo arrays from their serialized lump counts. The renderer's
backface checks in [`r_bsp.c`](../engine/aga/src/r_bsp.c#L355) decide whether a
surface is drawn from the current viewpoint; they do not remove its serialized
records or recover the corresponding Hunk memory. See [`Mod_LoadFaces`](../engine/aga/src/model.c#L913),
[`Mod_LoadVertexes`](../engine/aga/src/model.c#L693),
[`Mod_LoadEdges`](../engine/aga/src/model.c#L759),
[`Mod_LoadTexinfo`](../engine/aga/src/model.c#L787), and the lump loader sequence
in [`Mod_LoadBrushModel`](../engine/aga/src/model.c#L1504).

All loaded BSP faces are not necessarily drawn in a frame. The inspector's
two-sided display can expose a stored face's back; it is not evidence that the
BSP contains a duplicate face. Separately stored, permanently hidden inner walls
still consume serialized and loaded geometry until compile-time exclusion removes
them. The default-on hidden-surface flag and conservative closed, opaque-shell
containment helper are now present in source. Diagnostic 022 below removed no
faces; production gating and broader algorithm coverage remain pending. No
successful production BSP cut, face-count reduction, memory saving or target
acceptance is established yet.

### Source-loop winding and serialized-output validation — 4 October 2026, 04:23 EEST

A source review found that the older `canonical_bsp_cull.py` and
`canonical_world_cull.py` writers forced each clipped loop to match the oriented
BSP plane. That could reverse an otherwise valid loop copied from the source
polygon. Both writers are now corrected to preserve source winding. Three
regressions against the old source were reproduced, and the current focused suite
passes 30 tests across the world writer, placement writer and visible-water
preservation cases.

This exposed a validation gap: proving winding in the clip helper alone did not
prove what the serialized writer emitted. Acceptance must inspect the actual BSP
after writing and reloading it, including directed source/output loops, resolved
plane orientation and side fields. The current policy preserves visible upward
water surfaces while terrain-clipping buried closure sides and bottoms; water is
not a terrain receiver or barrier.

A new candidate is being built from the immutable original with aligned canonical
terrain, clipped objects and shared-sky conversion. It is not complete, serialized,
or accepted yet. A bounded stump audit classified 67 removals, 24 crossing cases,
27 unchanged cases, and 3,421 above-ground samples that survive. In that sample,
the local rendered LAND surface differed from canonical terrain by as much as
9.29443 compiled units. These bounded counts do not establish whole-world
coverage, correctness or savings. Keep the earlier receipts as historical records;
do not rewrite them to imply this candidate has been produced.

## Cell loading, backface rejection and stored geometry

These mechanisms answer different questions:

| Mechanism | What it does | What it does not establish |
| --- | --- | --- |
| Exterior/interior cell selection | Selects which placed scene records are loaded | Whether an exterior mesh has hidden inner surfaces |
| One-sided polygon drawing | Rejects a face viewed from its back | Removal of that face's vertices, planes, UVs or collision from memory |
| Compile-time hidden-surface exclusion | Removes proven unnecessary render surfaces from serialized output | Permission to remove collision, visible openings or other placements |
| Subcell selection | Limits the region and apron loaded at one time | Removal of hidden surfaces inside each retained object |

OpenMW's inspected `master` source unloads cell objects through the rendering
manager, removes non-exterior cells when changing exterior grids, and unloads
active cells before loading an interior. Its interior transition configures the
cell's environment rather than interpreting every exterior building as a loaded
interior. See [Scene cell transitions](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwworld/scene.cpp)
(`unloadCell`, exterior-grid changes and `changeToInteriorCell`).

OpenMW enables `GL_CULL_FACE` in its
[rendering manager](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwrender/renderingmanager.cpp).
Its [NIF loader](https://github.com/OpenMW/openmw/blob/master/components/nifosg/nifloader.cpp)
handles hidden/collision nodes and can disable culling for a stencil property's
`DrawMode_Both`. These links were inspected on 4 October 2026; they follow
`master`, not a verified immutable revision. They show source behavior, not a
measurement of the original commercial engine.

AmiWind's actual software renderer already tests the visible side using
`SURF_PLANEBACK` and `BACKFACE_EPSILON` in
[`r_bsp.c`](../engine/aga/src/r_bsp.c). The current inspector displays both sides
of its triangle geometry; its view from inside a shell can therefore expose the
back of a face the engine rejects. Changing that viewer display would not save
map RAM. An independently authored inward-facing polygon is a different stored
face and needs a separate compile-time exclusion proof.

## Verified exterior-export provenance

The exterior reader in [`mwad/audit.py`](../src/mwad/audit.py) checks the original
CELL interior flag and excludes interior cells before building `placements.json`.
[`prepare_scenery.py`](../tools/prepare_scenery.py) reads that placement cache;
the assembly and bounds selectors retain complete eligible exterior references.
The separate [`mwad/interior.py`](../src/mwad/interior.py) reader selects a named
interior, including its authored lighting, for a different conversion route.

A read-only audit against the authorized base master independently checked:

| Input | Checked references | Interior-cell matches | Unresolved/ambiguous |
| --- | ---: | ---: | ---: |
| Retained Seyda placement cache | 1,849 | 0 | 0 |
| Retained scenery index | 637 | 0 | 0 |
| Candidate017 numeric `aw_ref` entities | 299 | 0 | 0 |

The first two rows match reference number, base ID, source cell and source
position. The last row matches the numeric source reference and, where supplied,
the source ID; actor grounding may deliberately change its compiled position.
That row includes 283 scenery-index references plus 12 actors and four additional
dressing references. Generated terrain diagnostics are classified separately.
The retained master/cache/BSP hashes and full placement/model mapping are in the
private audit receipt. This proves no interior CELL reference leak in these
checked inputs; it does not identify an arbitrary surface from a screenshot or
prove that every exterior face is useful.

## What the converter actually creates

[`prepare_scenery.model_geometry`](../tools/prepare_scenery.py) propagates hidden
node flags and `RootCollisionNode` ancestry, excluding both from the visible
packet. It retains visible triangles and their winding. It now also records
inherited `NiStencilProperty` draw mode, the property origin, hidden/collision
exclusion reasons, stable source shape paths and source triangle ranges. A nearer
node property overrides its ancestor. Preserving this metadata does not implement
alternate rasterization: clockwise, double-sided, explicit application-default,
ambiguous or enabled-stencil cases require acceptance and are reported as issues.
The legacy export route retains geometry and reports incomplete visibility
acceptance; it does not silently duplicate or discard those triangles.

The four examined eastern common-building meshes have no stencil property on
their shapes or ancestors. Their hidden collision triangles are already absent
from the visible packets:

| Examined asset | Source visible triangles | Hidden collision triangles excluded |
| --- | ---: | ---: |
| Common balcony | 878 | 138 |
| Common house addon | 747 | 144 |
| Common tall house 01 | 652 | 96 |
| Common tall house 02 | 958 | 234 |

These are source triangles, not final BSP-face totals. A collision packet can be
absent from the exported index because its profile did not request extraction,
even though the original NIF contains a collision node.

For static meshes, [`prepare_mesh_bsp.py`](../tools/prepare_mesh_bsp.py) constructs
visual polygons from those triangles, merges compatible coplanar patches and
splits excessive texture extents. It writes those surfaces directly into the
BSP face lump. [`mesh_geometry.py`](../tools/mesh_geometry.py) separately builds
convex collision pieces or thin collision prisms. Their side/back planes enter
collision nodes, not textured face records. There is no static-mesh rule that
turns every triangle into a textured wedge.

Terrain uses a different path. `town_ground_brushes` in
[`prepare_quake.py`](../tools/prepare_quake.py) forms each terrain triangle into
a prism down to Z=-512 and applies the same `gN` material to its top, bottom and
three sides. Some generated closure surfaces can survive compilation. This is
an identified source of unnecessary terrain render geometry, separate from
interior CELLs or static-mesh collision. The required correction must preserve
visible canonical terrain and collision/contents/visibility while excluding
unwanted closure render faces. See [Hidden in dirt](HIDDEN_IN_DIRT.md).

## Permanent exclusion catalog: proposed contract

A first bounded selector is implemented in
[`exterior_visibility.py`](../tools/exterior_visibility.py). The optional
`prepare_scenery.py --exterior-visibility-policy PATH` input must use format
`AmiWind exterior visibility policy 1` and explicit exterior scene context.
Each model rule binds a normalized model path, exact original NIF SHA-256,
stable `source_shape_path`, original shape-local triangle IDs (or `all` for one
shape), rule ID and reviewed exterior-hidden evidence. Stale hashes, missing
shapes, out-of-range/overlapping selections, interior context and unsupported
retained source draw policies fail that selection's acceptance. No production
exclusion rules are bundled or inferred from normals/material names.

The original geometry packet and collision inputs remain intact. The BSP model
preparation stage applies the selected omissions only to visual triangles before
LOD, coplanar merging and texture splitting. It rechecks the source selection
against the packet's material ranges. Combining selected exclusions with panel
flattening currently rejects explicitly; that interaction is not silently assumed
safe. The original collision array remains the input to collision generation.
The existing `collision_only` profile is a separate whole-model mechanism for
specific sprite foliage. Inspector volumes are still planning annotations and
are **not** consumed by this selector.

Eight new synthetic tests include an actual TES3 NIF read/write round-trip,
inherited property/child override, hidden/collision ancestry, stale/invalid policy
rejection and a tetrahedron's four-to-three visual-surface change with unchanged
collision input. Together with the affected existing exporter/mesh checks,
34 focused Python tests passed. No native renderer behavior changed here.

The measured common tall house 01 retains 652 source triangles and 578 prepared
surface polygons; its 96 hidden collision triangles were already omitted. Its
geometry packet is byte-identical to the retained source packet. The audit found
50 center-facing triangles in one 316-triangle shape, but that is not proof of
invisibility in a concave/open object. Stable candidate IDs were recorded
privately; zero additional house triangles were excluded and zero surface or
memory savings are claimed. A transparent inspector material would not change
those stored geometry costs either.

## Whole-scene exterior reachability proposal

A future general solver could work like pouring black paint into an upside-down
hollow world mold: start from the open air that is reachable from outside, then
trace that reachable empty space through the actual assembled exterior scene.
Compare the scene with the canonical topomap so ground and seabed define the
exterior boundary. Water is neither ground nor a wall that can seal a gap. A
render surface is a candidate for removal only when it bounds a sealed void that
exterior air cannot reach in the assembled geometry.

Build the connectivity graph from real geometric intersections. Split surfaces
where they truly intersect, overlap or meet at T-junctions so adjacency is
represented correctly. Do not invent caps, convex closures, snapped contacts or
voxel gap closures to make a shell watertight. Treat uncertain gaps and
non-manifold connections as open and retain their surfaces. A door that loads a
separate Morrowind interior is outside this exterior connectivity pass; an actual
dynamic opening in the assembled exterior remains a possible air path and must
be treated conservatively.

This whole-scene flood fill is a proposal, not implemented. Current source has a
bounded exact-topology, closed, opaque convex-shell containment helper. The
helper does not synthesize closure geometry and is not a general scene flood fill.

Host-side camera visibility measurement and optional surface simplification are
also research proposals, distinct from enclosure classification and canonical
terrain clipping. A finite camera sample can nominate candidates but cannot by
itself prove that an unseen face is never visible. No RTX capture, camera-sweep
classifier or simplifier is implemented or accepted. See the proposed
[host visibility-analysis and optimizer-profiler workflow](HOST_VISIBILITY_ANALYSIS.md).

### Diagnostic 022: bounded helper made no house cut

Recorded 4 October 2026 01:48 EEST. The default-on flag and helper were active in
the diagnostic; the unchanged result is an algorithm coverage limitation, not a
disabled flag. Diagnostic 022 retained 32,209 stored faces and 5,013,620 file bytes, both
unchanged from 021. Its audit saw 240 static placements, 212 assemblies and 70
closed shells, but certified no whole face as enclosed. It reported 1,769
open/non-manifold, 138 nonconvex, 15 duplicate and one budget-retained. These
class counts are diagnostic accounting, not removed-face totals.
A separate two-house run also removed zero faces. In common tall house 01, the
reviewed source wall subset contained zero inward-facing triangles: the geometry
was one outward-facing sheet at x=-256 without an opposing coplanar mate. No
duplicate-geometry groups were found among all 652 source triangles. This
specific source finding does not explain every inspector screenshot or establish
that the algorithm is the project's performance bottleneck. The first
test-first bounded approach did not satisfy the intended house-interior removal
outcome. It remains a partial proof class; general exterior connectivity,
serialized BSP cuts, production savings and target acceptance are pending.

The build exposes `--hidden-surface-cull` with default `true`. Omit the option for
the default; append `--hidden-surface-cull false` to a build invocation for an
explicit diagnostic opt-out. Each BSP map/cell has a row in the private
`hidden-surface-cull/hidden-surfaces.json` receipt, including effective setting,
scene kind, input/output hashes, before/after file bytes and face/vertex/edge/
texinfo counts, removed stored faces, bytes saved and classifier details. The
per-cell console line also names the map, ON/OFF state, scene kind, stored-face
counts before and after, removed count and result. See [`hidden_surface_build.py`](../tools/hidden_surface_build.py#L19),
[`build.py` option forwarding](../tools/build.py#L495), and [`build_aga.py` receipt path](../tools/build_aga.py#L574).

### Build integration and scope assessment

Recorded 4 October 2026 01:54 EEST. The main `build.py` option defaults to `true`
and is forwarded to the image build. The finalizer runs the hidden-surface pass
after scene assembly and before BSP compaction, actor contact checks, heap audit
and content fingerprinting. It uses the explicit exterior-map manifest; it does
not guess scene kind from geometry. For changed maps, the original BSP is kept
in the private run's `originals` area. The private JSON receipt records per-map
input/output hashes and counts; console output reports each map's effective
setting and before/after stored-face counts. See [`build_aga.py` finalizer](../tools/build_aga.py#L572)
and [`hidden_surface_build.py`](../tools/hidden_surface_build.py#L37).

True interior-CELL-only render geometry is already excluded from the exterior
BSP by exterior-cell selection. Separate interior CELL maps retain their
geometry and authored lighting. This does not remove interior-facing walls that
are part of an exterior model. Keep the back side of an outer wall triangle when
the triangle is needed to form the exterior shell; one-sided drawing from a
viewpoint does not make the serialized triangle unnecessary. Collision remains
independent of render-face exclusion.

A limited private prototype-16 portal experiment used 16 selected planes and
produced 322 cells and 838 portals;
all modeled space was reachable, so it produced zero cuts. It omitted canonical
topography, neighboring cells and door connectivity, so it was not a full-scene
flood-fill experiment. House interior removal remains unfulfilled: diagnostic
022 and the separate two-house run both made zero cuts. No performance-bottleneck
cause or target acceptance follows from these zero-cut experiments.

The current source checks passed: 27 focused flag/serializer/helper tests and 16
builder/recovery/canonical checks. One combined test command also reported an
import error because a test name was mistyped; the correctly named
`test_render_pool_inspection` and compact-BSP tests then passed (10 tests). The
first full source run exposed a missing final blank line in a new test file; that
was corrected, and the rerun passed 1,054 source tests. These checks do not turn
the zero-cut house result into a completed feature or establish target behavior.

### Independent BSP plane and terrain-UV audit

Recorded 4 October 2026 02:06 EEST. An independent professional audit found
57,009 plane-lump rows in diagnostic 017, of which 52,817 were unique. The 4,192
exact duplicate 20-byte rows represent 83,840 bytes of duplicate serialized
records. In diagnostics 021/022, 55,412 rows contained 52,865 unique records;
2,547 exact duplicates represent 50,940 bytes. These are audit counts only:
Plane deduplication by itself does not improve geometry. Receipt 023 below verifies
serialized-byte savings, but does not establish live-RAM savings or native fit.

Diagnostic 017 also counted 1,520 terrain-quad pairs under the same UV criterion,
with five exceeding the 64-pixel gate. Diagnostics 021/022 have zero remaining
pairs under that criterion. Inspector 018 fixes role discovery and visibility
classification; it does not complete canonical terrain clipping. These findings
do not establish whole-scene hidden-surface acceptance or target behavior.


Receipt 023 applies the exact plane-record deduplication: rows decreased from
55,412 to 52,865, removing 2,547 duplicate 20-byte records (50,940 serialized
bytes). The BSP still contains 32,209 faces; its file size fell from 5,013,620
to 4,962,680 bytes. No face geometry changed. This measured file reduction is
not a live-RAM measurement or a target-native fit result.

### Independent sn045 package review and memory accounting

Recorded 4 October 2026 02:23 EEST. Independent byte comparison confirmed that
021 and the attempted 022 output are identical; 022 made no cut. Between 017 and
021, total faces fell by 1,445. Terrain model *119 fell from 8,192 to 6,595
faces (-1,597), while world-model faces rose from 382 to 534 (+152). Shared pool
model *120 remained at 5,218 faces, and other inline models 1..118 remained at
19,862. These counts do not prove exact geometric identity or establish an
interior-surface cut.

For 021, the matching-ABI report gives a BSP-only loader peak of 6,856,336 bytes
and BSP resident allocation of 6,717,664 bytes. Shared sprite residency is
600,256 bytes and the shared-range registry is 11,536 bytes. The report's
phase-ordered conservative combined estimate is 7,329,456 bytes. That combined
value includes sprite/registry costs and is not the BSP-only peak; the estimate
is 1,038,000 bytes above the 6,291,456-byte map allowance.

Receipt 023's plane remaps reduce the modeled plane-array allocation by 50,928
bytes. Straight arithmetic projects a 7,278,528-byte combined estimate, still
987,072 bytes above the map allowance. This is a projection from existing
receipts, not a fresh complete target-ABI measurement or fit result.

The reviewed BSP has zero sky-textured render faces, and shared-sky resource
metadata is present. The package still lacks production terrain spawning and
verified alignment with coarse collision terrain; native visual verification
also remains pending. Zero sky faces do not establish playable terrain or target
appearance.
## Combined object and canonical-ground boundary: proposal and A/B

For visibility, treat each embedded object and the canonical ground as one
combined occupied region. Internal and buried boundaries could then be removed
while preserving the exposed shape and material. This is a proposed way to
classify and clip visibility. A physical mesh weld or Boolean union is a separate
operation: it changes mesh topology and may add subdivisions, so it needs its
own before/after measurement. No general terrain/object Boolean union or weld is
implemented. The current house convex-containment detector still finds zero cuts.

The owner-directed A/B record compares float vertices, polygons, fan triangles,
serialized bytes, exposed shape and material, plus collision separately. Do not
infer net savings from removed surface area or an appearance check alone. In one
bounded private mesh experiment, the original had 616 float32 local vertices,
578 polygons and 864 fan triangles. The clipped result had 675 vertices (net +59,
including 83 new), 590 polygons and 919 fan triangles. Surface area fell 12,360.891177 square compiled units (5.217138%). The above-
terrain area consistency error after float32 serialization was 0.000077400473
(relative 3.45096033147e-10). Both above-terrain measurements use the same
clipper, so this is a consistency check, not independent proof of geometric
accuracy. Original texinfo mappings were reused; no texture or lightmap rebake
was measured. No BSP variant was written, so there is no serialized-BSP-byte
comparison or applied optimization claim.

The 021 repeat clip increased output counts from 675 to 704 vertices, 590 to 594
polygons and 919 to 948 fan triangles due to numeric fragmentation. This proves
representation instability in that trial, not a moved resolved boundary, duplicate
surface coverage, or growth in the whole BSP after sharing and compaction. The
general combined-region solver remains a proposal, and the zero-cut house result
remains open.

A later bounded full-023-002 stress check exercised 224 placements and 37,948
polygons through ten float32-array repetitions. It reported zero geometry
changes, unknown results or degeneracies. Eighteen conservative error bounds
still exceeded `2e-5`, so this is not a universal numerical certificate. The
array stress check did not emit a new BSP.

Separately, the corrected one-house fixture retained 675 vertices, 590 polygons
and 919 fan triangles through ten raw float32 repeats and ten actual BSP
write/reload recuts under an explicit `2e-5` tolerance. Its first clip removed
12,360.891177 square compiled units. This fixture passes its bounded repeat
check, but it is not the older 021 repeat that grew to 704 / 594 / 948 and is
not a whole-scene result. Full-scene numeric certification and a fresh BSP remain
pending.

### Idempotence and boundary acceptance

For a fixed source surface `S` and the same occupied boundary `B`, clipping must be
idempotent in resolved geometry: `C_B(C_B(S)) = C_B(S)`. That requirement is
separate from representation stability. A second pass may retessellate equivalent
geometry, but the resolved surface, material, UV mapping and placement must remain
the same within a documented numeric tolerance. Exact polygon/vertex counts, face
loops, float32 coordinates and serialized bytes are a second set of measures; do
not use matching counts or hashes alone as proof that the boundary is correct.

The focused regression should trace one face through this sequence: original input,
first clip, cleanup, repeat clip with the identical boundary, then cleanup again.
Compare the resolved coverage and boundary, normals/winding, material, UV-to-surface
mapping and placement at every stage, as well as fragment/polygon/fan-triangle and
vertex counts. Then serialize the actual BSP float32 fields, reload that BSP, repeat
the same clip and cleanup, and compare again. Report boundary movement separately
from coordinate-rounding or tessellation changes. Any cleanup must preserve the
surface contract rather than weld across materials or move the clipping boundary.

Do not use an `already_clipped` marker to skip the diagnostic repeat: the no-op
repeat must exercise the operation. Conversely, a no-op repeat is not evidence that
the first cut was necessary or correct; compare the untouched input with the first
clipped result and prove the excluded region against the canonical boundary.
The proposed catalog records an asset's local-space exclusion volumes or stable
source shape/triangle selections, bound to the exact asset hash. Placement
overrides additionally bind the master hash and source reference identity.
Transform those selections through the same authored placement transform as
the model. A shared stored surface can disappear only if every retained use is
excluded, or an explicitly measured placement-specific representation replaces
it. Preserve the original source and produce a new selectable output.

Selections need evidence that the surface is unreachable from the exterior:
enclosed back surfaces may qualify, while doors, windows, arches, open sheds,
balconies and visible roof undersides may not. An inward normal, material name,
single camera view or user-drawn box alone is not that evidence. Preserve
collision independently and keep a provenance trail from source triangle to
merged/split output faces. Omit accepted surfaces before visual face emission;
do not merely stop drawing them in the inspector. Validate serialized face,
vertex, edge, plane, UV and texture changes, then matching-ABI resident bytes,
collision/visibility and target appearance.

First remove proven hidden/under-terrain render work and measure the complete
result. The central Seyda Neen playable area must remain continuously resident;
subdivision is not a substitute for that requirement. Splitting still-hidden
meshes into more subcells does not delete their faces and can add apron overlap,
transitions and reloads. Optimize the representation first, then evaluate a
layout against the required continuous central footprint and measured budget.


## Inspector plans and the compiler boundary

The [AmiWind 3D Map Inspector](POLYCOUNT_INSPECTOR.md) exposes compiled geometry and review plans;
it does not apply those plans to BSP output.

Exact-face paint and box/polygon-volume plans express owner intent. They are not
currently inputs to the source triangle selector above. Display RGB, opacity and
zebra style do not change that contract. A volume cut can also create partial
faces, which cannot be represented by simply dropping whole source triangles.

A compiled-face plan must bind the exact loaded BSP SHA-256 and filename, stored
face ID, placed reference (`aw_ref` where available), entity/model identity and
any shared render-pool/range identity. Its scope must distinguish one placement
from all uses of a shared surface. Refuse a mismatched input instead of applying
the same integer IDs to another build.

The current converter can merge several source triangles into one BSP face or
split one source triangle into several output faces. Consequently, a painted
compiled face ID is not a source triangle ID. The path to a source rule requires
an emitted provenance map from that exact compiled face through each merge/split
to the original model hash, stable shape path and triangle/fragment coverage.
Resolve a whole source-triangle exclusion only when the plan covers its intended
full visible contribution. Partial coverage needs an explicit clipping operation.
The current metadata establishes stable source identities but does not serialize
that complete compiled-face provenance map.

An alternative future resolver could consume a hash-bound compiled-face plan
directly, removing that placement's specified render references and repacking the
BSP while preserving collision and other uses. It would need tests for shared
instances, mutable surface state, pool/range remapping, partial volume clipping
and reloaded output. Neither resolver is connected by this change. Do not report
painted inspector plans as baked map edits until one is implemented and verified.

A separately recorded [terrain cuts and surface-packing proposal](TERRAIN_SURFACE_PACKING_PROPOSAL.md)
describes one possible approach to canonical clipping, contour reconstruction
and placement-specific shared surfaces. It is an alternative to evaluate, not
a claim of completed converter or target acceptance.
