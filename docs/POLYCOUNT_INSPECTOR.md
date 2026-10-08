# AmiWind 3D Map Inspector

**Geometry analysis and optimization planning**

The standalone browser inspector is AmiWind's current tool for viewing compiled
BSP geometry, placements and density, and preparing review plans. It sits within
the aspirational **AmiWind Map Optimization Toolkit** direction. The inspector
helps analyze geometry and plan work; it does not edit BSPs, perform complete
automatic optimization, or profile live runtime performance. Since v0.0.31 it
lives at `amiwind-toolkit/map-inspector.html` as part of the
[AmiWind Toolkit](AMIWIND_TOOLKIT.md); the old `tools/polycount_inspector.html`
link redirects there. See the [toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) and
[exterior hidden-surface status](EXTERIOR_HIDDEN_SURFACES.md).
See the [Map Optimization Toolkit overview](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md)
and [measured findings](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md).
Created during AmiWind v0.0.28. Inspector prototype 0.1.3 includes optional local
base-texture inspection, compass, overhead inspection and polygon planning.
The startup-frame repair remains: an empty viewport
is valid before a scene is loaded, and a runtime error does not terminate the
animation scheduler. Shader and runtime errors appear in the viewport.

Open `amiwind-toolkit/map-inspector.html` (or the toolkit page,
`amiwind-toolkit/index.html`) in a desktop browser with WebGL enabled.
This standalone tool needs no server, package install, CDN or network access.
Click **Open local BSP / scene JSON** and choose a locally converted Quake BSP
version 29. **Synthetic cube** supplies a tiny asset-free demonstration.

The viewport shows actual compiled polygon edges. Fly with **WASD**, use **E/Q**
to ascend/descend, **Shift** for double speed, **Ctrl** for fast flight and the
left/right arrows to turn. These key assignments follow AmiWind's default
`keymaps-default.cfg` and `cl_input.c`. **Enter mouse look** captures the cursor;
**Escape** releases it. Alternatively drag to look. Scroll changes the field of
view without moving the camera; **Overview** resets it. This is a noclip
inspection camera, not an exact simulation of game movement or collision.
Space retains no jump action here because the camera has no gravity.

Click a surface to select its placement. During mouse look, click picks beneath
the centre reticle. The object list also selects placements; **Fit selected**
frames one. Search by model, reference or exported name. Hide the world/terrain
or show only the selected placement to inspect otherwise obscured geometry.
Wireframe is intentionally see-through; picking chooses the nearest triangle
along the cursor ray. No sprites, actor meshes, collision hulls,
engine visibility simulation or gameplay are rendered.

**Load textures** adds depth-tested, unlit solid surfaces from the BSP's embedded
indexed base textures. **Wireframe overlay on solids** retains visible polygon
edges; turning textures off restores the see-through wireframe. For actual
colors choose an owner-supplied `gfx/palette.lmp` containing exactly 768 bytes.
Without a palette, the view is explicitly a grayscale preview. Lightmaps are
not rendered. Every palette index, including 255, is opaque for ordinary BSP
textures; the viewer does not invent transparent holes.

The texture preview list shows locally loaded texture names and dimensions.
Select an object and choose another loaded texture to preview it across that
object. **Original mappings** restores the scene's materials. This overrides
only the viewer's current selected-object draw pass; it changes neither the BSP
nor the exported scene. It is not a converter edit. UVs are computed from local
BSP vertices and texinfo before entity rotation, so mappings move with objects.

**Show heatmap over textures** defaults on and independently mixes density color
over the unlit base pixels. It works even when the display is white wireframe
and when wireframe overlay is off. Turn it off for the base-texture preview.

Heading appears beside XYZ, with a small top-right compass that can be toggled
without reloading. The convention is **+Y north, +X east**, degrees clockwise
from north: N 0°, E 90°, S 180°, W 270°. The eight direction labels choose the
nearest 45° sector. This convention describes the converted scene axes.

**Inspect from above** fits visible geometry in an orthographic, north-up
top-down view and enables density wireframe. It temporarily disables solid
textures so that the density remains visible. Drag to pan, use WASD to move in
the horizontal plane, and scroll to zoom. **Return to fly view** restores the
saved camera, zoom and display settings. Overview/fit selected also return to a
perspective fly camera. Overhead uses the same 3D vertex-bin metric, not a
separate 2D triangle-per-area estimate.

Enable **Filter density range** to use the min/max sliders beneath the legend.
Thresholds are inclusive placed-vertex counts; min is on the left, max on the
right. Moving one past the other moves the opposite limit to keep the range
ordered. Lines use the maximum bin count of their two vertices; solid/pickable
triangles use the maximum count of their three vertices. Primitives outside
the range are discarded, and hidden triangles cannot be picked. The color scale
remains logarithmic over the whole scene. Reset restores the full range;
changing the bin width also resets the range. Density includes all loaded
placements even when individual visibility controls hide some of them.

For a proposed map area, set a finite **Reference plane Z**, click **Draw area**
and click polygon corners. The tool switches to orthographic overhead.
**Finish** closes a simple polygon; repeated corners, crossings, overlaps and
zero-area polygons are rejected. The highlighted area stays while navigating
until Clear or another scene is loaded. Drawing is limited to 256 corners.

**Export polygon JSON** records full-precision world XY in **compiled game
units**, the chosen Z plane, source identity and current density thresholds.
These are not original Morrowind cell coordinates. Corners are ray intersections
with a horizontal reference plane; they do not promise terrain elevation or
walkable boundaries. **Export marked PNG** captures the current viewport,
polygon highlight, numbered corners, coordinate list and enabled compass.
Both exports are private planning artifacts. Neither changes map files,
subcell selection, converter output or the engine.

**Vertex density** counts unique vertices inside each placed model per 3D
spatial bin. Repeated placements contribute again; shared vertices inside one
placement count once. Color uses a logarithmic scale, with the maximum shown in
the legend. This metric is not engine heap usage. The footer distinguishes
placed faces from unique referenced stored-model faces; unused BSP models are
not counted. Texinfo count is a count of material/UV mappings, not necessarily
distinct texture images. Connected components join final BSP edges through shared
vertex indices; coincident coordinates stored at separate indices are not welded.
The selection reports face counts per component and per texinfo mapping when
polygon metadata is available. Coordinates and bin widths use compiled game units.

Earlier pipeline stages cannot be reconstructed from a final BSP. Scene objects
may carry optional `stageCounts` metadata supplied by a separate audit, for
example `source`, `post_coplanar_merge`, `post_uv_split`, and `final_bsp`. The tool
labels these as provided metadata and does not invent unavailable stage counts.

To create a portable private copy that opens with a scene already loaded:

```sh
python tools/export_mesh_inspection.py /path/to/owned/map.bsp --out /private/mesh-navigator-001 --palette /path/to/owned/gfx/palette.lmp
```

The destination must be new. The exporter creates a self-contained HTML, scene
JSON and receipt containing source/output hashes, texture counts, optional
palette hash and validation scope. `--palette` is optional. The exported HTML
starts in wireframe; check **Load textures** to inspect its base pixels.
**Generated geometry from proprietary game files is private.** Never commit
these scene exports or self-contained copies to the public repository or attach
them to public releases. The unpopulated viewer, exporter and synthetic tests
are asset-free tooling.

Limits: BSP v29 only, local files up to 128 MiB, up to two million placed
vertices. Graphics resources and picking time depend on scene complexity.
The tool reports malformed input rather than altering it. It reads standard
inline brush entities with Quake rotation/origin transforms; external alias and
sprite models are deliberately excluded.

Validation of prototype 0.1.1 recorded on 3 October 2026: eight asset-free exporter tests passed on
the host and in the existing project Docker workflow. Pure JavaScript checks
covered parsing, transforms, picking, movement, component counts, the initial
empty frame and subsequent draw submissions. The retained Seyda BSP matched the
Python exporter across all 225 placements. Those JavaScript checks used inert
DOM/WebGL stubs and are not GPU validation. Harry subsequently confirmed that
the corrected inspector works in his local browser. This is a browser smoke
test; exhaustive validation of every navigation and inspection control remains
separate.

Prototype 0.1.2 adds synthetic checkerboard pixel/UV tests, rotated-placement UV
invariance, invalid mip/texinfo rejection, missing texture handling and opaque
palette-index checks. Host exporter tests total twelve. Solid draw submission
checks use inert WebGL stubs; textured GPU rendering needs a local browser smoke
test and is not inferred from the earlier wireframe confirmation.

Prototype 0.1.3 pure JavaScript checks cover eight compass directions/wrap,
orthographic overhead picking, camera restoration, reference-plane corner
projection, simple/crossing polygon validation, preserved coordinates, inclusive
density thresholds and slider ordering/reset. These logic checks use stubs;
the new overlays, filtering, tint and PNG capture need browser smoke coverage.

For future BSP review, use wireframe/density, isolate a selected placement and
compare optional solid textures. Distinguish stored faces, repeated placed
faces and actual runtime-submitted geometry: the viewer reports the first two
and does not measure the engine's submitted scene. Buried surfaces seen through
wireframe are not automatically removable collision or structural geometry.
Door coverage remains pending a separate content audit. Keep derived scenes,
palettes, texture pixels and inspection captures private.

## Polycount heatmap inspection method

1. Open a local BSP/scene and retain its hash. Record XYZ, compass heading,
   projection, bin width and density range for a reproducible camera/view.
2. Find spatial vertex-density hotspots: these are vertices per bin across
   placements, not object face counts or resident memory. Heatmap over textures
   defaults on; compare base texture and wireframe to distinguish actual detail.
3. Isolate the placement, then its separate frame, neighbours and terrain. Read
   component/texinfo counts; a door selection need not include its whole frame.
4. Compare supplied source, post-merge, post-UV-split and final-BSP audit counts.
   Earlier stages cannot be inferred from final output. UV splitting can increase
   compiled faces after reduction; collision has its own representation cost.
5. Separate unique stored faces, repeated placed faces, runtime submitted/drawn
   faces and resident/loading bytes. The viewer does not measure engine memory
   or runtime submission. Hidden geometry is not automatically safe to remove.
6. Min/max sliders filter display/picking only. They do not reduce BSP geometry,
   unload assets or reclaim memory. Preserve thresholds in the comparison receipt.
7. Inspect from above is orthographic. Polygon JSON/PNG marks are private planning,
   not generated regions or accepted residency changes. One central resident core
   requires planner/converter/runtime ownership, coverage and payload/heap gates.

Keep originals; compare one isolated candidate's UVs, appearance, collision and
actual final memory. Keep game-derived scenes, textures, palettes and media private.

## Numbered door optimization recipes

Use `<door_type>_optimization_method_1`, then `_2`, `_3` and so on, retaining
immutable `original` plus each candidate/receipt. A shape-preserving method1 may
retain shell, projecting fittings and collision while baking selected detail;
a flat-body method2 is a separate tradeoff needing opening/silhouette/UV/collision
checks. Pending recipes have no accepted counts or saving. Record stage counts,
texture cost and actual full-map effect. Document migration before renaming old
selector keys; this naming convention changes no current selector/production key.

## Recording optimization methods and comparison tables

Give each isolated recipe a numbered method, retain its original and record the
steps, actual output identities and unresolved limits. Use a table separating
source triangles, merged polygons, UV-split/final faces, unique stored bytes,
placed references, new texture cost, collision evidence and full-map peak. File
savings and standalone model estimates are not target-Hunk or runtime savings.

For terrain-assisted buried-face method1:

1. Bind the actual owning cell/subcell BSP and terrain payload, not a screenshot
   or guessed global elevation. **Water is not terrain.** Ground/seabed topography
   is terrain; retain its collision and surface topology independently of water.
2. Test rendered object faces against that terrain under the documented overlap
   rule; preserve originals, shared/lightmapped cases and uncertain fragments.
3. Build one isolated candidate and record removed faces, clipped faces, retained
   growth/budget cases and file delta separately. Do not add these classifications
   into an invented accounting equation or claim collision was reduced.
4. Verify inline collision and world terrain identity, then run complete source,
   target-ABI final map and visual/transition gates. Current private trial records
   a file reduction; full target heap remains unverified.

An adjustable overlap parameter with default0.5 is in implementation; do not
confuse it with accepted behavior of an older candidate. Door method2 similarly
needs its actual geometry, baked texture, original collision and oblique tradeoff
reported independently. No universal elimination rule or fixed release is claimed.

For screenshots accompanying public method documentation, use only the built-in
asset-free synthetic scene or other project-authored synthetic geometry. Never
substitute owner game-derived BSPs, textures, maps or private annotated media.

### File savings versus a current-source heap estimate

A bounded private trial reduced BSP file size by110,208 bytes. A like-for-like
allocation model using current streamed-sprite source policy and cached target
ABI sizes estimated181,536 fewer resident/peak bytes, leaving only1,824 bytes
against the unchanged map allowance. These are different metrics. This estimate
is not a fresh matching target compilation, complete final-map gate or emulator
measurement. The earlier peak included temporary sprite input, so don't attribute
all cross-policy peak improvement to geometry culling. Inspect the whole town and
pre-bake candidate coverage, then verify actual payloads and all-resource headroom
before accepting a repair. No new playable-image claim is made.

See [Hidden in Dirt: Seyda Neen's graphics performance bottlenecks](HIDDEN_IN_DIRT.md) for terrain/door method tables, file-versus-heap results and non-destructive acceptance.


## Exterior prebake exclusion markup

Use **Draw box** or **Draw polygon** to mark hidden interiors of exterior meshes.
Set min/max Z to define a closed vertical prism. Select fill color, opacity and
zebra pattern to distinguish zones; these settings are display-only and survive
zone/session export and reload. The viewer keeps the source geometry unchanged.

**Export prebake markup JSON** records the exact polygon footprint and height
interval, loaded/source filenames, source SHA-256 when available, inspector
version 0.0.28, UTC/local timestamps and compiled XYZ coordinate frame. X/Y are
horizontal; Z is height; units are compiled units, not original NIF coordinates.

The additive `exterior_prebake_exclusion` intent requests a future placement-level
prebake removal of static exterior render portions inside each volume, clipping
crossing faces while preserving their outside portions. Collision remains
unchanged. Separate door-loaded interior cells are outside this operation.
External visibility review and a verified map-to-source-face binding are required
before compiling the request. The source-model exclusion selector does not yet
consume these world-space volumes; automatic removal is not implemented here.

The existing zone/session format IDs remain compatible. Old styles without
`color` load as grey (`#aeb6bf`); new colors accept only six hexadecimal digits.
Each zone exports `intent: exterior_render_exclusion` and its own style. Sessions
include the default style for subsequently drawn zones. Mismatched source
identity still requires the existing explicit import override. Never equate a
colored box with proof that all enclosed geometry is invisible.


### Exact face paint and undo

Click the paintbrush **Paint mode OFF** button in the top bar to turn painting
on. It stays highlighted and reads **Paint mode ON**. A click marks one visible
triangle in one placed object; the initial fill is opaque black. Use the RGB
picker, opacity or zebra controls for other styles. **Erase marked face** remains
in the markup panel. Dragging groups the stroke into one
undo level; with mouse look locked, the crosshair targets the nearest face. These
are annotations over the unchanged geometry. There is no inferred global flood
or texture-wide selection. **Draw box / cube** still creates a closed prism from
two opposite corners and min/max Z; **Draw polygon** creates an extruded footprint.

The RGB picker applies its new color to all existing marks and zones and to new
markup. Opacity and zebra hatching remain available. **Undo** and **Redo** retain
64 editing levels, including paint/erase, zone create/edit/delete/clear, imports
and global RGB changes. Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z work when the viewport is
focused; text and number fields retain their normal editing shortcuts. History
is local to the current source; export records the current result, not the stack.

The additive `face_mark_schema: amiwind-placed-face-markup-1` stores `face_marks`.
Each entry binds `object_index`, `entity_index`, `model`, `reference`, `origin`,
`angles`, `face_index`, `stored_face_id`, `stored_face_range`, `pool_binding` and
exact compiled-world `points_xyz`. Pool bindings include the pool model, parent
model and relative range. The scope is `this_placement`; other uses of a shared
model remain independent. Source SHA-256 is inherited from the loaded source
record, alongside filename, version and UTC/local timestamps. Import checks the
face binding and exact geometry before restoring marks; unsupported schemas,
duplicate marks and altered coordinates fail validation. Legacy zone files
without face marks load normally. JSON input is bounded to 64 MiB and 20,000 face
marks, with the existing zone/corner limits preserved.

A compiled face ID is not an original NIF triangle ID: compilation may merge or
split source triangles. The source-model selector requires normalized NIF path,
NIF SHA-256, stable shape path and original triangle IDs. A separate verified
provenance map or exact-hash compiled-BSP resolver is still needed to consume
these inspector plans. Neither painted faces nor volumes are currently wired to
automatic compiler removal. Collision and separate door-loaded interior cells
remain outside this proposed render-only cut. Start with one reviewed interior
example when a plan is returned.

Run the asset-free synthetic checks with `node tests/test_polycount_markup.js`.
They check a small closed interior volume, an inside face and an outside shared
placement, export/reload, undo/reapply, RGB and malformed binding rejection.
The test DOM/WebGL are stubs; passing these checks does not establish GPU visual
appearance or validate a compiled cut.


### Build014 paint and demo repair

The Synthetic cube now contains validated polygon metadata, so the same real
pointer handlers used for maps can paint its triangles. Its button changes to
**Return to map**, preserving the original map, camera, marks, undo/redo history
and local palette. With no previous map it changes to **Close synthetic cube**.
Opening another source exits demo mode. The demo never replaces the source file.

New clicked marks add `triangle_index`, a zero-based fan-triangle index inside
the bound compiled polygon, and export exactly three `points_xyz`. Different
triangles of the same polygon are independent. Existing whole-polygon marks
without `triangle_index` remain compatible. This index still does not claim a
source NIF triangle identity. Paint uses compiled source triangles; terrain
preview is an inspection overlay, not new source geometry.

Painted triangles and zone overlays are clipped against the camera near plane
and viewport before projecting/filling, so a large interior wall with a vertex
behind the camera no longer loses its entire mark. Hatching is bounded to the
viewport. The asset-free regression harness now records and dispatches the
actual registered pointer handlers and buttons, including the actual cube
builder, one triangle click, drag grouping, erase/undo, triangle JSON reload,
demo return and a room wall crossing the near plane. These verify draw calls and
state transitions with a stub renderer; real GPU appearance remains unverified.


### Build015 one-sided paint and depth repair

Face paint now uses a WebGL pass with depth testing, rather than the build014
2D planning overlay. A depth-only pass fills opaque source-surface depth from the
same visible/preview triangles and density filters, including wireframe mode.
Paint then uses `LEQUAL` with depth writes disabled and zero polygon-offset bias.
Closer surfaces occlude the marking; the GPU clips near-plane crossings. The
2D overlay remains only for intentional zone/area planning graphics. Mark display
also respects clipped terrain-preview fragments without changing exported source
triangle geometry. The source depth cache refreshes when source, preview, density
or object visibility changes.

A click first finds the nearest renderer-visible triangle, including surfaces
that have no exportable polygon binding. Such an unmarkable nearer surface blocks
painting surfaces behind it. New marks record `clicked_side: front` or `back`,
relative to the triangle winding in compiled XYZ, and
`cut_scope: clicked_render_side_only`. Front is the side toward the geometric
cross-product normal. A mark is drawn only when that side faces the current
camera; painting the inside does not display the annotation on the outside of
the same triangle. Opposite-side marks have independent identity, undo and erase.
Orthographic side visibility uses the viewing direction; perspective uses the
eye relative to the triangle plane.

This requests review of only the clicked render side. It is **not authorization
to delete the complete source triangle or its visible exterior side**, and it
claims no face-count saving. A future compiler resolver must preserve the other
side and collision when applying an approved side-specific operation. No such
compiler resolver is connected yet. Imported older marks without side metadata
are normalized to `clicked_side: unspecified` and
`cut_scope: legacy_unspecified_side_review_required`; they retain their legacy
both-side display for compatibility, but cannot imply an approved side-specific
cut.

Registered-event regressions include two overlapping panels, first-hit stopping,
reverse-side suppression, opposite-side paint/erase/undo and JSON round-trip.
The actual render function is exercised with textures on/off and its WebGL calls
checked for source depth, depth-tested side-gated paint and no offset bias.
These are stub-renderer state/draw-call tests; real GPU pixel appearance is still
unverified. No BSP or source game geometry is modified by this repair.


### Build016 draw boxes from the current interior view

**Draw box / cube** and **Draw polygon** keep the current fly or orbit camera.
They do not switch to aerial view or disable mouse look. In fly and orbit views,
clicks sample the nearest actually visible surface using the same ray picker as
paint. Two surface points with different X and Y define opposite corners of an
axis-aligned XY box footprint. **Min Z** and **Max Z** remain the explicit vertical
bounds; they are not silently replaced by the sampled hit heights. Adjust these
controls to cover the intended interior volume. The sampled point marker is on
the clicked surface, while the hover preview shows the volume at those chosen
height bounds. Move the cursor after the first corner to preview the box.

A second point on a single axis-aligned wall may have the same X or Y as the
first. Such a zero-width box is rejected with feedback, keeping the first point;
aim at an opposite corner on another wall or the floor. A click with no visible
surface is rejected without changing the camera or projecting onto a plane
behind it. Dragging in fly/orbit or mouse look can aim between corners. Use
**Cancel drawing** to discard pending corners. Polygon clicks follow the same
surface sampling and finish with **Finish zone**.

Only the explicit **From above** view retains its existing footprint projection
onto Min Z. Orthographic orbit remains a surface-sampling view. Export stores the
same exact closed footprint and Min/Max Z schema, and undo/redo restores the
finished zone. Registered pointer/button tests cover unchanged fly/orbit camera
and display, actual floor hit points, hover state, meaningful finite box JSON,
height bounds, undo/reload, no-hit feedback and explicit overhead behavior.
The build015 one-sided/depth-tested paint pass is unchanged. Real GPU preview
appearance remains unverified; these are state/event and draw-call regressions.


### Build017 selected mesh polycount

Clicking a mesh in Inspect mode immediately updates a yellow-text selection strip
above the bottom map-status bar. It reports the selected render part's polygon
face count and fan-triangle count when different. For example, the Synthetic cube
shows **6 faces (polygons)** and **12 fan triangles**. A scene with no polygon list
uses its declared `faceCount` and labels that value **reported metadata**.

The main count matches the render object whose wireframe turns yellow. A placed
mesh split between common geometry and pool ranges also shows the highlighted
pool range and a separately labeled **placement original total** across its render
parts, bound to the same parsed entity index. It does not aggregate unrelated
uses of a shared model. Terrain preview reports **Original / current faces** and
**reduction** separately. These are full-part geometry counts before density
range display filtering, not visible-pixel or collision counts; the strip says so
when filtering is enabled.

Clearing selection hides the strip. Session restore uses the exact stored face
range when available so a selected pool part is restored rather than another
range with the same model/reference. Placement sums are cached when a scene is
loaded; per-frame footer updates use existing counts and array lengths, with no
geometry recount. Registered click tests verify immediate cube selection without
a render frame, metadata fallback, clear/reset, preview counts, density wording,
placement/range distinction and exact-range session restoration. Previous paint
side/depth and current-view box tests remain enabled. GPU appearance is still
unverified; no BSP/compiler geometry is changed.


### Build018 terrain roles and honest unavailable checks

Receiver discovery no longer assumes all LAND is stored in world model0. The BSP
parser attaches `terrainRole: canonical_land` only to the explicit entity
`classname: aw_render_diagnostic`, `aw_ref: canonical_land_diagnostic`, regardless
of its inline model number or object-list order. It also exports `entityClassname`,
`entityIndex` and `inspectorOnlyDiagnostic`. World geometry retains the legacy
`world_legacy` role, whose receiver faces are upward LAND materials named `gN`.
Other objects receive `none`. Pool ranges do not inherit the canonical receiver
role. Scene JSON may supply `terrainRole` or `terrain_role`; classname aliases are
accepted for the exact diagnostic provenance fallback.

Receiver discovery, receiver self-exclusion and World/terrain visibility share
these roles. Water materials are excluded from receiver triangles. The World/
terrain checkbox hides both the world batch (which can be water only) and tagged
canonical LAND, rather than leaving LAND visible because its model is nonzero.
Receiver geometry is retained by the preview. The actual terrain is the varying
ground/seabed, not a water plane.

If no usable receiver prisms exist, the result has `checkPerformed: false` and
`terrainStatus: unavailable`. The sidebar and warning say **Terrain unavailable;
check not performed**. Source geometry is retained; there is no zero-reduction
message implying a completed clean check. Available receiver discovery does not
prove full-map coverage or completed culling: this preview still has its existing
finite-bottom, fragment-growth, shared/lightmapped and missing-metadata retention
limits. Native support for diagnostic geometry is not established by this viewer.
A diagnostic-geometry warning remains visible in map status.

The bottom status now distinguishes **render batches**, **distinct entity
placements** represented by nonempty render geometry, and **world batches**.
These are not counts of all game entities. Multiple common/pool ranges share one
parsed entity placement ID. A JSON scene without placement IDs says that entity
placement count is unavailable; it never substitutes object-list length. The
selected mesh footer continues to count the highlighted part explicitly.

Asset-free tests exercise canonical LAND at model47 with reordered objects,
water-only world0, receiver preservation, consistent hide behavior, empty-receiver
feedback, explicit/alias/provenance roles, batch/placement labels and source
immutability. The optional private BSP parser check derives receiver triangle
counts from that exact file instead of assuming an earlier candidate's count.
All prior paint, box camera and selected-polycount regressions remain active.
GPU appearance and native-map acceptance remain unverified.

## Build 019: complete placement selection

Selection, yellow highlighting, Show selected only and Fit selected now use the
same explicit entity-index group across base and shared/delta render batches.
The persistent footer shows whole-placement polygons and inspector fan triangles,
then separately labels the active clicked batch. Missing entity metadata keeps a
batch-only fallback rather than guessing which objects belong together. Paint
object/face/triangle identities, clicked side and source binding are unchanged.
Terrain-role discovery and explicit not-performed feedback from build 018 remain.
Eighteen host regression groups passed, including independent arithmetic for all
226 groups in the private diagnostic. GPU appearance remains unverified.

## Build 020: sub-cell cuts and divider

The **Sub-cell cuts** panel draws planned region borders and section cuts as
translucent coloured vertical rectangles through the loaded map, one colour and
label per region or cut, in perspective, orbit and From above views (seen
edge-on from above they are coloured lines, and each region core gets a faint
fill). Hovering a rectangle shows its name and position. **Show cuts and region
borders** hides everything; **Show coverage** hides the dashed coverage
outlines. The rectangles are a 2D overlay like the planning zones: they are
not depth-tested and never alter, hide or select geometry. Zones, face marks,
their undo history and the session format are unchanged; cuts are saved in
their own files, not in the session.

Quake mechanism: a cut is an axial split plane, as qbsp chooses for its nodes;
a section is the space on one side and a portal is the rectangle where two
sections meet. That is the model of the AWIS1 interior-section portals, so the
divider exports straight into that format.

### Overlay format `aw-cuts-1`

```json
{"format": "aw-cuts-1", "map": "bm019", "space": "map-local", "z": [0, 512],
 "regions": [{"name": "bm019", "core": [[-768, -1536], [0, -768]],
              "coverage": [[-1664, -2432], [896, 128]], "colour": "#ff5d5d"}],
 "planes": [{"label": "cut A", "axis": "x", "at": -384, "from": -2432, "to": 128,
             "z": [0, 512], "colour": "#a98bff", "kind": "cut", "margin": 24}]}
```

- `space` must be `map-local`: compiled BSP XYZ of the map being viewed. Town
  configs already store cores and coverage in that frame (map-local =
  (source - centre) x scale); section plans use the room BSP's own XYZ.
- `regions[]`: `name`, and a `core` and/or `coverage` rectangle
  `[[x0, y0], [x1, y1]]` (x0 < x1, y0 < y1). The core is drawn as four solid
  walls, the coverage as dashed outlines at the bottom and top of the Z range;
  a region with only a coverage gets faint walls.
- `planes[]`: `axis` `x` (constant X, spanning Y from `from` to `to`) or `y`
  (constant Y, spanning X); `at` is the position. `axis` `z` is a horizontal
  plane at height `at` with `x` and `y` ranges. Optional: `z` range, `colour`
  (`#rrggbb`), `kind` (`cut`, `portal`, `region-border`), `margin` (portal
  hysteresis), `label`.
- Z range: the plane's or region's own `z`, else the overlay's `z`, else the
  loaded map's bounds.
- Optional `divider`: `{"margin": 24, "apron": 40}` from a divider export.
- Limits: 256 regions, 256 planes, coordinates within 10,000,000, 16 MiB.

`tools/region_cuts.py` writes and checks overlays (Python standard library):

- `town --config CONFIG --map NAME` takes a Balmora-style settings file
  (`bounds`, `core_size`, `overlap`; regions come from
  `balmora_regions.regions`) or a layout with an explicit `regions` list (the
  Seyda Neen layout). It writes the map's core and coverage and the core of
  every region overlapping that coverage: those borders are the sub-cell cuts
  that pass through the map. `--all` writes every core and coverage;
  `--border-planes` adds each distinct core border inside the coverage as a
  plane; `--z ZMIN ZMAX` fixes the height.
- `plan --plan PLAN` writes each section's coverage as a region and each
  portal as a plane at its split, after checking the plan's sections and
  portals with `prepare_interior_sections.section_text`.
- `check --overlay FILE` and `check --plan FILE` validate without writing.

Verified on `bm019` (Balmora build of v0.0.31-dev2): the map's terrain bounds
are X -1696..928, Y -2464..160, exactly the generated coverage
(-1664..896, -2432..128) plus one 32-unit terrain margin on every side, and the
core walls stand at X -768 and 0, Y -1536 and -768.

### Sub-cell divider

**Add X cut** / **Add Y cut** place a cut through the middle of the map (or
under the view centre in From above), spanning the whole map and its height.
Select a cut in the list to edit its label, position, ends, Z range and colour
in number boxes; the slider moves its position. In From above, drag a cut line
to move it or its end squares to shorten it; the drag neither pans the view
nor selects geometry. Undo and Redo (64 levels, panel buttons) cover adding,
moving, editing, deleting, clearing, importing and the margin and apron;
Ctrl+Z stays with the face and zone markup. At most 16 cuts.

Every cut divides the whole map along its axis; sections are the rectangles
between the cuts (two X cuts and one Y cut give six). From/To and Z give the
portal rectangle where neighbouring sections change over. Each section's
coverage is its rectangle widened by the **apron** (default 40) across every
cut; the portal **margin** (default 24, at most 32) must fit inside the apron.

Statistics, live while editing, for the whole map and each section:

- **by face centre**: compiled faces whose centre lies in the section (they
  add up to the map), stored faces, and lightmap bytes;
- **placements**: whole entity placements inside the section, straddling its
  border, and kept with the apron, with the number of inline brush models;
- **section build**: what a whole-reference section build keeps: every
  placement touching the coverage, plus the world model whole (interior
  section builds keep it) or, with that box unticked, the world faces inside
  the coverage (exterior regions are cut that way);
- **estimated heap**: fixed non-map heap + loader factor x (BSP bytes without
  the lighting lump x kept stored faces / all stored faces + kept lightmap
  bytes), against 11,534,336 B. Defaults 5,245,860 B and 1.09 come from one
  measured Vivec room (heap 9,497,156 B for a 3,900,172 B BSP); both are
  editable. It is an estimate for comparing cut positions, not a heap
  measurement: build the section and run the heap check.

Lightmap bytes follow Quake's CalcSurfaceExtents: per face, the texture
extents in 16-unit luxels (floor of the minimum, ceiling of the maximum, plus
one sample) times the face's light styles, counted once per lightmap offset
because faces can share samples. On `bm019` this sum equals the lighting lump
exactly (4,786 B). File size, light offsets, styles, the entry spawn and every
`aw_ref` entity (including those without geometry) are read from an opened
`.bsp`; for a scene JSON the heap estimate is reported as unavailable.

**Export cut overlay JSON** writes the cuts (`kind: cut`) and the sections
(core = section rectangle, coverage = with apron). **Export section plan JSON**
writes a plan in the `tools/prepare_interior_sections.py` format: sections
named after the map plus a letter (`vi021a`, `vi021b`, ...), each with its
coverage box over the map's full height and the `aw_ref` numbers of every
placement touching it (references without geometry go by origin, to the
nearest section when outside all), one portal per pair of sections sharing a
cut, and the base BSP's size and SHA-256. The entrance section is the one
holding the map's `info_player_start`, whose origin and angle become its
spawn. Fields the inspector cannot know (source and door receipts, cell name,
logical and physical IDs, the other sections' spawns) are `PENDING` strings,
so the section tool refuses the plan until they are filled. The export is
refused, with the reasons listed, when the cuts break the section tool's
rules (2 to 8 sections, 1 to 8 portals, margin inside the apron). The plan also
carries `inspector_cuts`, `inspector_divider` and `inspector_estimate`, which
the section tool ignores. **Import cuts** reads an overlay (its x/y planes) or
a section plan (its `inspector_cuts`, or else one cut per portal split); **Load
cut overlay JSON** also accepts a section plan and draws it.

Asset-free checks: `node tests/test_polycount_markup.js` (milestone
`PASS020 sub-cell cuts`) and `python3 -m unittest tests/test_region_cuts.py`.
The browser check on `bm019` covered drawing in both views, hover text,
overhead drag with one undo level and no pan or selection, export and import
round trips, and a two-section plan accepted by `region_cuts.py check --plan`.
GPU appearance on other machines is unverified.
