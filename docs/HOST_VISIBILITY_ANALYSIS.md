# Host visibility analysis and optimizer/profiler pipeline

Status: proposed research and implementation plan, recorded 4 October 2026.
This is part of the [AmiWind Map Optimization Toolkit](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md).
It is not an implemented GPU visibility sweep, a completed interior-removal pass,
or a performance claim about the Amiga. The current 3D Map Inspector provides
geometry inspection and proposed exclusion annotations.

<!-- contents start -->
## Contents

- [Start with a bounded, repeatable experiment](#start-with-a-bounded-repeatable-experiment)
- [Existing tools to evaluate](#existing-tools-to-evaluate)
- [Proposed batch pipeline](#proposed-batch-pipeline)
- [Parallel work and hardware verification](#parallel-work-and-hardware-verification)
- [From candidates to justified removal](#from-candidates-to-justified-removal)
- [Required report and first acceptance gates](#required-report-and-first-acceptance-gates)

<!-- contents end -->

## Start with a bounded, repeatable experiment

Use the host GPU and CPU workers for offline analysis before compilation. Start
with one actual Seyda Neen building, then the assembled town. Seyda Neen is a
manageable first scene, but workload still depends on camera count, resolution,
overlap and material handling. Measure these rather than assume a runtime.

The proposed first milestone is one graphics capture and a deterministic
placed-face visibility report, with evidence images and machine-readable IDs.
Automate batches of views or rays; do not require a model call or manual inspection
for every camera. Collision data can help locate and reject camera positions.
It is not a substitute for render geometry: collision can omit decoration,
approximate openings, or disagree with the current diagnostic terrain.

## Existing tools to evaluate

| Tool | Intended use | Integration status |
| --- | --- | --- |
| Spector.js | Inspect WebGL commands, draw calls, shaders, textures and render state; export frame capture JSON. | Upstream capabilities reviewed; not installed or captured as part of this work. |
| Spector.js MCP | Automate frame inspection through its upstream browser interface. | Upstream README documents Playwright/Chromium and capture/query operations; no local integration claimed. |
| RenderDoc | Investigate native graphics frames and scripted analysis where API support fits. | Alternative to evaluate, not a current dependency. |
| NVIDIA Nsight Graphics | Investigate GPU execution and graphics events on supported host paths. | Alternative to evaluate, not an Amiga cost estimator. |

[Spector.js](https://github.com/BabylonJS/Spector.js) supports embedded and extension
use, including JSON capture callbacks. Its [MCP documentation](https://github.com/BabylonJS/Spector.js/blob/master/mcp/README.md)
lists `capture_frame`, `get_draw_calls`, `get_command_details`, `get_shaders` and
`get_context_info`. A frame debugger supplies capture infrastructure; AmiWind must
still implement camera coverage, persistent face identities and scene reports.
See the [RenderDoc project](https://github.com/baldurk/renderdoc) and
[Nsight Graphics](https://developer.nvidia.com/nsight-graphics) for those tools'
supported environments. Pin and record a version before adopting any dependency.

The current inspector requests a **WebGL 1** context. Do not assume WebGL 2
integer attachments or query APIs are available. An initial compatible ID pass
can encode bounded integer IDs in an RGBA8 offscreen target; verify round-trip
accuracy, reserve the background ID and report overflow. A deliberate WebGL 2
path would need its own compatibility checks. Khronos documents
[WebGL 1](https://registry.khronos.org/webgl/specs/latest/1.0/) and
[WebGL 2](https://registry.khronos.org/webgl/specs/latest/2.0/) separately.

## Proposed batch pipeline

1. **Freeze inputs.** Record the BSP hash, canonical terrain hash and transform,
   tool revision, material rules, camera set, resolution, FOV and numerical policy.
   Turn off inspector hiding, preview clipping, selection isolation and annotations
   for the baseline analysis. Keep original inputs unchanged.
2. **Build placed-face identities.** Identify source artifact, entity placement,
   base/shared/clipped range, stored polygon and generated triangle. Distinct
   placements of a shared polygon must have distinct analysis IDs. Aggregate
   results into the inspector's whole-placement selection without losing the
   contributing batch IDs.
3. **Render identification and depth passes.** Render the nearest contributing
   face ID per covered pixel. Disable blending, dithering, multisample ID mixing
   and presentation color transforms in this pass; validate the framebuffer and
   readback with a small known fixture. Match winding, backface and alpha-test rules
   to the intended target policy, rather than the inspector's two-sided debug view.
4. **Sweep a deterministic camera set.** Include streets, alleys, entrances,
   stairs, waterfront, bridges, region joins and elevated/above-roof views for
   eventual levitation. Use the agreed 90-degree FOV, recording whether horizontal
   or vertical, at target resolution and a higher diagnostic resolution. Add
   reproducible offsets for thin features. A ground-only route is insufficient.
5. **Classify observations.** Report sampled visible pixels and tested views per
   placed face. Investigate zero-hit faces with additional tests distinguishing
   out-of-view, back-facing, depth-occluded, subpixel and unknown cases. Zero hits
   alone do not establish which explanation applies.
6. **Compare candidates.** Replay identical cameras on untouched, first-cut,
   cleaned and repeat-cut artifacts. Compare silhouette, coverage, depth and
   material appearance alongside exact geometry, topology and storage checks.
7. **Measure target cost separately.** Replay the camera set in the native renderer
   when supported, logging submitted surfaces, clipped edges, spans, cache activity,
   loading peak and frame time. Accept a change against explicit target gates.

Treat transparent or alpha-cutout foliage correctly. Movable doors, actors and
removable objects must not become permanent opaque occluders. Water is not the
ground boundary. Its transparency and contribution require an explicit material
policy. Unresolved material behavior is a reported limitation, not permission to
classify hidden faces as safe to remove.

An optional depth-complexity heatmap counts projected overlapping layers. It
measures geometric overlap, not necessarily expensive shading operations in the
Amiga software renderer. Equal screenshots can conceal duplicate fragments;
equal face counts can conceal changed geometry. Keep both image and geometry tests.

## Parallel work and hardware verification

CPU workers can prepare independent views, spatial queries and summaries. Batch
GPU work to avoid repeated uploads and needless synchronous readbacks. More
browser contexts do not automatically produce more throughput on one GPU; compare
one batched context with bounded concurrency before increasing it. Record wall
time, upload/readback cost, peak host/GPU memory and job count.

Record browser version, graphics backend, available extensions and renderer
identity. If the renderer identity is unavailable, report it as unverified.
Chromium supports a CPU-based [SwiftShader path](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md);
a successful headless render therefore does not establish an RTX run. Use
[GPU timer queries](https://registry.khronos.org/webgl/extensions/EXT_disjoint_timer_query/)
only when supported and valid, including disjoint checks. CPU submission timing
is a different measurement. Host GPU frame rate must not be presented as Amiga FPS.

CUDA/ray-tracing acceleration is an optional backend to evaluate after profiling
the first implementation. The owner's CUDA-accelerated QCC/compiler idea belongs
to the same host-compute research direction, but it is a separate proposal:
profile actual compiler stages, identify sufficiently parallel work and account
for transfer/setup cost. Neither a CUDA compiler speedup nor a CUDA visibility
backend has been demonstrated here. A WebGL sweep does not itself require CUDA.

## From candidates to justified removal

Sampled visibility finds candidates and regressions. It cannot prove that a face
is invisible from every permitted camera position. Permanent exclusion requires
a canonical-terrain burial proof, a verified assembled-enclosure result or an
explicit reviewed exclusion with its supported scope recorded.

Test **the assembled building plus actual ground**, including neighboring pieces
across streaming boundaries. A wall, roof and foundation can each be open meshes
yet jointly enclose space. A closed shape need not be convex; for example, CGAL's
[point-in-mesh test](https://doc.cgal.org/latest/Polygon_mesh_processing/classCGAL_1_1Side__of__triangle__mesh.html)
has closure/intersection requirements rather than a general convexity requirement.
Replacing a concave building with its convex hull could wrongly seal courtyards
and overhangs.

Distinguish separate vertex indices at coincident positions from actual gaps and
unresolved intersections. Reconcile these in a temporary analysis representation
while preserving original UV and normal seams. Flood exterior-accessible space
against fixed opaque barriers and the canonical terrain; include all legitimate
camera regions. Water level and subcell boundaries must not become artificial
sealing planes. Flood connectivity is conservative: it can travel around corners
that a straight viewing ray cannot.

The first enclosure report must show either verified enclosing surfaces and
candidate internal faces, an opening with a path to outdoors, or the location of
a numerical ambiguity. Coarse voxel closure alone is insufficient: small real
windows can disappear in a grid. Keep uncertain openings open until refined or
geometrically resolved. Do not automatically patch holes to obtain a result.

Analysis subdivisions must not automatically become shipped render geometry.
Prefer whole redundant-face removal for the first trial; leave surviving exterior
faces unchanged. Map decisions back to original placed-face IDs. Preserve sharing
where decisions agree; account for any placement-specific copies. Terrain cuts
remain a separate pass and may create genuine intersection vertices.

## Required report and first acceptance gates

| Output | Required evidence |
| --- | --- |
| Visibility report JSON | Input hashes, camera/material policy, hardware status, per-face observations and unresolved cases. |
| Inspector selection links | Stable placement and batch identities matching the report. |
| Evidence images | A few highest-overlap views, thin-feature cases, differences and enclosure/leak explanations. |
| Representation comparison | Created and removed vertices/fragments, final counts, BSP bytes and allocated-memory estimates. |
| Target replay | Native renderer counters and timings, labelled unavailable until actually run. |
| Removal proof | Terrain/enclosure/exclusion justification, preserved visible geometry and separate collision/PVS checks. |

Begin with a known synthetic visibility fixture, then one real building, then
Seyda Neen. Reparse saved outputs; exercise repeat clipping rather than bypass it
with an `already_clipped` flag. A no-op clipper can be stable, so the first-cut
test must also prove buried portions disappear and exposed portions survive.
See [hidden-surface findings](EXTERIOR_HIDDEN_SURFACES.md) and
[the dated findings snapshot](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md).
