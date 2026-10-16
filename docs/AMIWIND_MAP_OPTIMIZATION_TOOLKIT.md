# AmiWind Map Optimization Toolkit

*Geometry analysis, compile-time optimization, and validation for AmiWind.*

<!-- contents start -->
## Contents

- [Identity and scope](#identity-and-scope)
- [Placement-aware terrain clipping and residency](#placement-aware-terrain-clipping-and-residency)
- [Geometry policy](#geometry-policy)
  - [Canonical terrain is the reference](#canonical-terrain-is-the-reference)
  - [Combined exposure decisions do not require a welded world](#combined-exposure-decisions-do-not-require-a-welded-world)
  - [Exterior maps retain exterior-visible surfaces](#exterior-maps-retain-exterior-visible-surfaces)
  - [Sharing and sky remain distinct concerns](#sharing-and-sky-remain-distinct-concerns)
- [Host optimizer/profiler research](#host-optimizerprofiler-research)
- [Inspector contract](#inspector-contract)
- [Matched A/B protocol](#matched-ab-protocol)
  - [Read-only three-phase storage comparison CLI](#read-only-three-phase-storage-comparison-cli)
- [Acceptance and publication](#acceptance-and-publication)
- [Current implementation and next steps](#current-implementation-and-next-steps)

<!-- contents end -->

7 October 2026: this toolkit is now the map optimisation part of the wider
[AmiWind Toolkit](AMIWIND_TOOLKIT.md); the 3D Map Inspector moved to
`amiwind-toolkit/map-inspector.html`.

Documentation snapshot: 4 October 2026. This overview defines the toolkit's scope
and intended workflow. It does not announce a completed optimization pipeline or
a new playable release. Diagnostic numbers identify experiments, not separate
public game versions.

## Identity and scope

**AmiWind Map Optimization Toolkit** is the umbrella name for the map inspection,
conversion, and verification tools used to reduce AmiWind's compiled-world costs
without damaging the visible scene or gameplay structure.

The interactive front end is **AmiWind 3D Map Inspector**, with the subtitle
**Geometry analysis and optimization planning**. It is not called a runtime
profiler merely because it displays polygon counts, and its previews and painted
exclusions are not described as compiled optimization results.

| Component | Responsibility | Evidence required for a result |
| --- | --- | --- |
| 3D Map Inspector | Inspect serialized geometry; select placements; show counts; preview and annotate proposed changes. | Identify the loaded artifact and distinguish its stored geometry from preview-only changes. |
| Conversion and optimization tools | Produce new compiled candidates with canonical terrain cuts, justified hidden-surface removal, sharing, and exact-data compaction. | Reparse the written output and account for actual changes. Individual passes have separate implementation status. |
| Validation and measurement tools | Check geometry references, terrain joins, sharing, collision/contents/visibility, storage, and target costs. | Keep structural checks, source-bound memory estimates, and native measurements separately labelled. |

The intended workflow is:

```text
Preserved source and baseline
    -> inspect and identify a candidate
    -> apply one documented conversion change
    -> write a new compiled artifact
    -> reparse, compare, and validate
    -> measure target behaviour
    -> accept or retain as a rejected experiment
```

For each converted exterior cell, include a terrain-aware render-face clipping
check in this workflow, especially when placed face counts or the memory gate
are high. Record an unchanged-input clipping-off and clipping-on comparison:
placed and stored faces, crossing faces and generated fragments, terrain faces,
collision representation, serialized bytes and modelled ring peaks. Preserve
the visible ground, the recorded contact overlap, collision and the behavior of
shared models at every placement. A count-only collision match is insufficient;
compare resolved hull graphs and verify native gameplay. Keep the pass opt-in
until matching in-game views against the original and target memory and movement
checks support wider use. The bounded Tel Uvirith (10,1) measurement is recorded
in [CHIM mesh methods](chim/MESH_METHODS.md#tel-uvirith-cell-101-diagnostic-12-october-2026).

Use the 3D Map Inspector's [Filter density range](POLYCOUNT_INSPECTOR.md)
to find candidate placements and nearby geometry before choosing a cut. For
Tel Uvirith (10,1), 64-unit bins and the inclusive 311–463 range isolate the
lantern/support cluster and nearby roots. Reset the filter and review the
unfiltered silhouette, seams and surroundings before accepting any edit.
Density counts placed vertices, not resident bytes; measure compiled model
records and ring memory separately, accounting for shared placements.

For CHIM candidates, report active-ring and wider load-ring peaks separately.
Keep sprite file bytes, sprite runtime allocation and model-zone bytes distinct;
a file-size total cannot establish available runtime memory. A fixed-stage
filter is a diagnostic until runtime state changes and transitions are
implemented and checked.

Substantial optimization work in Seyda Neen, Balmora and Vivec already has its
own [CHIM measurements](chim/FEATURES.md) and issue evidence. Keep those
results and gates. After the current cell's visual and native validation, revisit
only residual opportunities that measured counts or performance justify,
including terrain clipping in other cells; do not start a broad reconversion
on the strength of this one diagnostic.

Current evidence and outstanding work are recorded in
[the findings snapshot](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md).

## Placement-aware terrain clipping and residency

The opt-in CHIM area setting `visual_recipe: tel-uvirith-v1` selects the
checksum-bound rules in `config/visual-recipes.json`. Each rule requires both
the normalized model path and the SHA-256 of its converted source geometry
packet. Unmatched or modified inputs retain their ordinary conversion profile.
The public recipe contains reduction parameters and a procedural lantern shell;
it contains no original mesh arrays or texture pixels. Materials are read from
the user's own game data. Collision preparation continues to use the original
source geometry or its authored collision mesh.

The top-level `everywhere` entry names a recipe applied in every CHIM cell and town frame
(`everywhere-v1`): today the Dunmer streetlight `light_de_streetlight_01` becomes the procedural
lantern shell everywhere, not only at Tel Uvirith. A cell's own recipe wins for the meshes it names;
the everywhere recipe may not cap unnamed meshes. `AMIWIND_VISUAL_EVERYWHERE=off` keeps the original
meshes (the method before).

Eleven reduction rules reproduced the retained diagnostic geometry exactly;
the procedural lantern reproduced its 32-triangle diagnostic shell, including
UVs. Two door-panel rules also reproduced their baked pixels and two-sided
polygons, with unchanged source collision pieces. Optimizer revision and recipe parameters participate in the mesh cache
identity. These checks establish reproducibility, not full-world acceptance.
The recipe is not enabled by default and does not yet provide the complete
diagnostic scene's sprite or fixed-stage selection pipeline.

In a bounded CHIM exterior cell (10,1) trial, clipping a placed rock against
the authoritative LAND changed one selected model from 64 to 39 render faces.
With the other candidate settings held fixed, modelled active-ring peak changed
from 5,839,936 to 5,805,824 bytes (34,112 saved), and wider load-ring peak
from 6,072,240 to 6,039,376 bytes (32,864 saved). All 59 resolved model
collision graphs matched the preceding candidate. These are offline ring
measurements, not native terrain-contact or movement acceptance.

The rock's `terrain_` mesh name does not make it authoritative LAND. Preserve
the original shared asset and derive a cut representation keyed by source,
terrain and clipping context. A face in a shared variant is removable only if
it is buried at every placement using that variant; retain exposed or uncertain
geometry. The measured trial clipped already-existing variants. It did not
test creating additional per-placement variants from a previously shared model.

World disk bytes and simultaneous residency answer different questions.
Specialized variants can increase total stored world data yet reduce a sampled
ring if only some variants are resident together; adjacent cells can also load
several variants at once and erase that saving. Compare the union of distinct
resident models in worst active and load rings, including metadata, textures,
collision and streaming overlap. Do not multiply a shared model's bytes by
its placement count or infer heap savings from face counts alone.

Before wider use, compare clipping off/on with the optimizer fixed, then
review unfiltered silhouettes, ground-contact skirts, cracks, slopes,
overhangs, exposed sides and cell boundaries from ordinary player positions.
Check shared rocks at different heights and headings, water, accessible
underground space and geometry below the finite clip depth. Match the same
views in the original game and target, and repeat collision and worst-ring
measurements for the exact candidate. The current rock result has no such
native acceptance or public deployment.

A subsequent normal-start MiniWind diagnostic loaded the candidate CHIM frame
and ran for 61 seconds. It included three seconds of ordinary walking before
noclip views of rock contact, underside and nearby structures. The frame kept
running; this establishes a bounded load/run observation, not a terrain
appearance comparison or normal collision acceptance at the viewed poses.
The normal quick-character route reported a 2,014,640-byte free Hunk gap,
below the 2 MiB warning threshold; no allocation crash occurred in this run.
Matched original-game views and wider traversal remain pending.

## Geometry policy

### Canonical terrain is the reference

Buried-object decisions must use the canonical, globally aligned terrain/topomap.
The requirement includes removal of the buried portions of crossing faces, not
only removal of wholly buried faces. Preserve the exposed shape, texture mapping,
and valid joins. Water level is not a substitute for terrain; preserve the actual
terrain and visible water.

Any intentional overlap and numerical tolerance must be recorded separately. The
current diagnostic reports a 0.5-unit contact overlap; this is a recorded setting,
not a newly established universal tolerance.

### Combined exposure decisions do not require a welded world

The proposed embedded-object approach considers terrain and static objects
together when deciding which surfaces remain exposed. It does not require every
object to become part of one permanently welded terrain mesh.

The ground may provide closure beneath an otherwise open-bottomed building. That
closure must be established for the actual assembled geometry, not assumed merely
because an object intersects terrain. No general welded union or completed
house-interior removal is established by the current findings.

As a proposed implementation safeguard, keep analysis-only closure geometry and
subdivisions out of the shipped render representation unless they are genuinely
required there. The final visible surface and its terrain cuts must still agree.

### Exterior maps retain exterior-visible surfaces

Separate interior-only render surfaces that cannot be seen during exterior
play should be absent from exterior render data. Door-loaded interiors belong
in their separate maps. Conversely, the reverse side of an exterior polygon is
not automatically an additional removable polygon.

Preserve visible openings, silhouettes, material boundaries, walkable structures,
and required collision. Above-roof views are legitimate inspection cases; the
policy must not depend only on a ground-level camera. A detector declining to
remove a surface means that its test did not justify removal, not that the surface
has been proved necessary.

### Sharing and sky remain distinct concerns

Placement-specific cuts must not corrupt other placements of the same source
model. Keep identical geometry shareable while representing genuine differences
explicitly. Count stored geometry separately from its placed references.

Generated per-cell and per-subcell sky-enclosure render faces are to be absent
from final render data. Sky appearance belongs to the shared renderer/environment
path. A map with no sky faces is not, by itself, proof of a working sky renderer.
Preserve or deliberately replace required structural, contents, collision, and
visibility information independently.

## Host optimizer/profiler research

The [host visibility analysis plan](HOST_VISIBILITY_ANALYSIS.md) records the
proposed GPU face-ID/depth sweeps, assembled-building enclosure tests, graphics
capture tooling, and matched native replay. Surface simplification belongs to
the same A/B workflow, with silhouette, UV, material and terrain-join checks.
Spector.js is a capture-tool candidate; no RTX visibility report has yet been
produced. CUDA-assisted compiler work is a separate research idea requiring
profiling, not a demonstrated acceleration or a prerequisite for this sweep.

## Inspector contract

Terrain recognition must use explicit scene roles consistently for receiver
discovery, visibility controls, and exclusion from object-removal targets. Do not
permanently identify terrain by a particular inline-model number. An empty
receiver set must report that the terrain test was not performed, rather than
presenting zero cuts as a successful clearance check.

The selected-placement count belongs in the bottom status area or immediately
above it. It must include the placement's base and shared/clipped ranges. The
active batch count is supplementary, not a replacement for the whole-placement
count. Keep these quantities distinct:

- Compiled BSP polygons and stored vertices.
- Placement-expanded polygons and geometry batches.
- Inspector fan triangles and preview-only geometry.

Selection highlighting, isolation, and framing should agree on the same placement
group. Exported annotations must preserve their artifact and geometry identities.
A painted exclusion remains a proposal until a converter consumes it and the
written BSP is checked.

## Matched A/B protocol

The proposed embedded-building comparison starts with one identified, untouched
building at the same placement against the same canonical topomap. Record the
source, topomap, settings, tool revision, and output identities.

Use three clearly distinguished observations:

| Observation | Purpose |
| --- | --- |
| A: untouched input | Establish the cost before the first terrain cut. |
| B: raw first cut | Measure removed geometry, newly created intersections and fragments. |
| C: cleaned and compacted B | Measure recovery of unnecessary subdivisions, without changing visible shape or mapping. |
| Finished output repeated with unchanged inputs/settings | Check repeat-pass stability; do not count it as another first-cut saving. |

A building that already meets the terrain cut is not an untouched baseline. A
second pass with no cuts can test repeat-pass behaviour, but cannot establish the
cost or savings of the first pass.

Report both raw clipping output and the final serialized representation. Suggested
fields are vertices before/after, new cut vertices, removed vertices, polygons,
fan triangles, edges/surfedges, fragments per source face, stored/shared ranges,
BSP bytes, decoded residency, and loading peak. State which fields were measured,
estimated, or not measured. Native frame time is a separate result.

A lower final vertex count does not answer whether new cut vertices were created;
report the two quantities separately. Likewise, removed surface area does not by
itself establish smaller storage or faster rendering.

### Read-only three-phase storage comparison CLI

[`tools/compare_bsp_trials.py`](../tools/compare_bsp_trials.py) writes
`comparison.json` and `comparison.md` for three explicitly named phases:
immutable original (`--original`), immediate pass input (`--before`), and output
(`--after`). Each BSP is hash-bound and reports file/lump bytes and supported
stored-record counts. Optional `--original-asset`, `--before-asset` and
`--after-asset` flags include external resources explicitly; unlisted assets are
excluded. This prevents a shared sky or similar resource from being silently
omitted or counted twice.

```sh
python tools/compare_bsp_trials.py \
  --original /inputs/immutable-original.bsp \
  --before /inputs/immediate-pass-input.bsp \
  --after /outputs/candidate.bsp \
  --out-dir /reports/new-trial-ledger \
  --method "name the ordered pass and settings"
```

The report directory must be new. The CLI measures storage and stored records,
not geometry correctness, placed/visible/submitted faces, RAM, native performance
or acceptance; unsupported metrics are marked unknown. It reports unclassified

`non_lump_bytes` separately from recognized lump bytes. Eight host tests cover its
three-phase reporting and input protection. Build stages do not yet invoke
the CLI automatically, so each trial needs an explicit report run. Its machine
report includes input paths; keep private paths and asset-bearing receipts out of
public releases.

## Acceptance and publication

Use the same output artifact for inspection, structural checks, and target tests.
Record failed gates rather than replacing them with a general success label.
Neither a smaller diagnostic nor a working browser view establishes a playable
production build. Production integration must be reproduced through the intended
build entry point before it is claimed complete.

Keep the toolkit source and these documentation summaries public-safe. Original
or converted game assets, embedded-map viewers, private BSPs, ROMs, playable
images, and unapproved screenshots remain outside the public source. Preserve
existing component licence notices. Detailed public documentation belongs under
`docs/`, with a concise link from the main README.

## Current implementation and next steps

The inspector is implemented in [the standalone HTML tool](POLYCOUNT_INSPECTOR.md).
Build 019 groups selection, isolation and framing by placement across base/shared
ranges, retaining a distinct active batch and stable paint identities. Build 018
uses explicit terrain roles and reports when no terrain test was performed.
Neither makes its preview a substitute for canonical compiled-output validation.

The default-on `--hidden-surface-cull` option controls the final serialized,
bounded automatic exterior pass. It can be disabled with
`--hidden-surface-cull false`. This option does not toggle source-side exclusion
policies or terrain cutting. The current closed-convex-shell proof removes zero
house-interior faces in the measured candidate; general assembled-world exterior
visibility remains unfinished. See [the detailed status](EXTERIOR_HIDDEN_SURFACES.md).

Two mesh-converter options are off by default until accepted:
`--texinfo-snap TEXELS` shares texture mappings within TEXELS of the shipped
texture (measured 1/16: texinfo -33 to -51 %, modelled heap -0.45 to -1.06 MB
on dense exterior regions) and `--scenery-reduce ERROR` simplifies scenery
visual meshes with locked UV seams (measured: under 1.1 % of faces). Both are
accepted by `build.py` and the region converters and recorded in the build
receipt. See [Mesh tips](MESH_TIPS_AND_TRICKS.md#texture-mapping-snapping-and-scenery-reduction-2026-10-08).

Exact plane-table deduplication is implemented separately by
`tools/dedup_bsp_planes.py`: it remaps faces, nodes and collision nodes while
preserving complete resolved plane records. Candidate 023 demonstrates a real
storage saving without claiming hidden-surface removal.

The shared exterior sky is a separate renderer path, with no per-cell sky
enclosure render geometry. Regional weather and time-of-day controls are planned
environment parameters, not a reason to restore cell-sized boxes. Interior maps
retain their own lighting/background policy. See [sky and day/night](DAY_NIGHT_AND_SKY.md)
for the implementation status; regional weather and a complete day/night cycle
are not claimed by these geometry diagnostics.
