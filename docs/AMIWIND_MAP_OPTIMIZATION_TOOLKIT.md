# AmiWind Map Optimization Toolkit

*Geometry analysis, compile-time optimization, and validation for AmiWind.*

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

Current evidence and outstanding work are recorded in
[the findings snapshot](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md).

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
