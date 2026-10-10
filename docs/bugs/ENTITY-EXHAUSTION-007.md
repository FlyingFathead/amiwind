# ENTITY-EXHAUSTION-007: entity exhaustion investigation history

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 3 October 2026, in v0.0.28-rc1 |
| Where | Engine entity allocator (ED_Alloc, 600 slots) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.28-rc1 (last seen) |
| Severity | high: Running out of entity slots ended the game with a fatal error; only a safe session end exists, not capacity. |
| Family | Engine table limits (`engine-limits`) |

<!-- END GENERATED FACTS -->

The following journal entry is retained verbatim. Moving its detailed
history here keeps the main journal within the public source size gate.
Current status remains in [the issue index](../BUGS.md).

<!-- contents start -->
## Contents

- [ENTITY-EXHAUSTION-007: interactive entity exhaustion recovery](#entity-exhaustion-007-interactive-entity-exhaustion-recovery)
  - [Balmora catalogue admission and heap accounting addendum](#balmora-catalogue-admission-and-heap-accounting-addendum)
  - [BUILD-QCC-PATH-008: assembly received a source directory as its compiler](#build-qcc-path-008-assembly-received-a-source-directory-as-its-compiler)
  - [ENTITY-DIAGNOSTIC-009: allocation high-water count described as live slots](#entity-diagnostic-009-allocation-high-water-count-described-as-live-slots)
  - [WORLD-FLORA-HEAP-010: Seyda sprite payload exceeds final headroom](#world-flora-heap-010-seyda-sprite-payload-exceeds-final-headroom)
  - [WORLD-FLORA-HEAP-010: contained-collision experiment and refreshed diagnostics](#world-flora-heap-010-contained-collision-experiment-and-refreshed-diagnostics)
  - [Development inspection follow-up: Blender mesh views (3 October 2026)](#development-inspection-follow-up-blender-mesh-views-3-october-2026)
  - [SPRITE-STREAM-VALIDATION: development wrapper and legacy alignment failures](#sprite-stream-validation-development-wrapper-and-legacy-alignment-failures)
  - [POLYCOUNT-INSPECTOR: initial empty-scene render stops animation](#polycount-inspector-initial-empty-scene-render-stops-animation)
  - [Sprite validation follow-up: bounded native and full suite results](#sprite-validation-follow-up-bounded-native-and-full-suite-results)
  - [WORLD-FLORA-HEAP-010: unresolved fallback diagnostic accounting](#world-flora-heap-010-unresolved-fallback-diagnostic-accounting)
  - [POLYCOUNT-INSPECTOR release admission and current estimate follow-up](#polycount-inspector-release-admission-and-current-estimate-follow-up)
  - [TERRAIN-CULL: global topology and local sky enclosure remain unaccepted](#terrain-cull-global-topology-and-local-sky-enclosure-remain-unaccepted)
  - [POLYCOUNT-INSPECTOR: fly navigation and repeated-count regressions open](#polycount-inspector-fly-navigation-and-repeated-count-regressions-open)
  - [TERRAIN-CULL audit follow-up 002: sky geometry removed; global terrain still pending](#terrain-cull-audit-follow-up-002-sky-geometry-removed-global-terrain-still-pending)
  - [TERRAIN-CULL inspection004: source join repair is separate from buried-object removal](#terrain-cull-inspection004-source-join-repair-is-separate-from-buried-object-removal)
  - [SKY-FOG v0.0.28: shared resource and reserved depth validated natively; target pending](#sky-fog-v0028-shared-resource-and-reserved-depth-validated-natively-target-pending)
  - [EXTERIOR-SURFACES v0.0.28: no checked interior-cell leak; storage exclusion remains open](#exterior-surfaces-v0028-no-checked-interior-cell-leak-storage-exclusion-remains-open)
  - [EXTERIOR-VISIBILITY v0.0.28: source policy metadata and bounded selector added](#exterior-visibility-v0028-source-policy-metadata-and-bounded-selector-added)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## ENTITY-EXHAUSTION-007: interactive entity exhaustion recovery

- **Version/location:** unreleased v0.0.28-rc1 allocator investigation, 3 October
  2026. MAX_EDICTS=600 is inherited; first introducing version is unknown.
- **Reproduce/cause:** occupy all reusable gameplay entity slots, then request
  another through ED_Alloc. Previously Sys_Error terminated the application.
- **Mitigation:** archived aw_ent_count_exceed_soft_fail defaults to 1. Prints
  WARNING with map, used slots and limit, opens the console, then uses Host_Error
  to safely end the current interactive session while retaining the application.
  Value 0 preserves the fatal path for troubleshooting. No invalid entity is
  returned and no object silently dropped. Dedicated-server or recursive
  Host_Error remains fatal. Mitigation is not a capacity fix or seamless recovery.
- **Validation/results:** real allocator Docker test passed: default, warning
  numbers, recovery, fatal opt-out and reuse of a free slot at the ceiling.
  Combined checkpoint006 passed 607 tests (3 skips) and matching Amiga compile.
  Packaged HDF and target behavior remain pending; no limit/reserve increased.

### Balmora catalogue admission and heap accounting addendum

Town admission now distinguishes raw BSP records from live gameplay slots for
exact Balmora catalogue names. Captured func_wall placements retain meshes and
collision in the immutable catalogue; the audit conservatively retains every
noncaptured record in its live-slot estimate. Catalogue capacity 1,000 and
visible-entity floor 1,112 remain explicit checks. No objects deduplicated away.
The 32,767 world clipnode conversion reserve remains unchanged. Town admission
uses the existing engine unsigned clipnode format limit of 65,520; this does not
certify memory fit. Final actual-ABI heap and complete transport checks remain
mandatory with the unchanged 3 MiB baseline and 2 MiB safety headroom.
Target compiler probes catalogue-record alignment/size. Heap estimates add its
Hunk allocation conservatively to loading peaks, including sprite input overlap;
recovered edict slots do not imply free catalogue memory. All 21 heap regression
checks and two typed admission checks passed. Final-map and target gates pending.

### BUILD-QCC-PATH-008: assembly received a source directory as its compiler

- **Version/location/circumstances:** v0.0.28-rc1 private image002 assembly, 3 October 2026; normal conversion reached QuakeC compilation after vegetation conversion.
- **Reproduction:** pass the toolkit's `Quake-Tools/qcc` source directory to `--qcc`; subprocess execution fails with Permission denied.
- **Cause:** the private assembly wrapper confused the QCC source directory with the existing Docker executable `Quake-Tools/qcc-host`. This was a wrapper configuration error, not a geometry failure.
- **Trial/solution:** preserve failed output; use the existing compiler in numbered image003 and preflight all supplied tools as executable regular files before conversion. No new Windows executable was created.
- **Result/fixed version:** corrected wrapper and preflight launched image003 under v0.0.28-rc1; final assembly and target validation pending. The incident is not closed merely because the rerun started.

### ENTITY-DIAGNOSTIC-009: allocation high-water count described as live slots

- **Version/location:** v0.0.28-rc1 entity-exhaustion warning in ED_Alloc; source review on 3 October 2026. Introducing version of this new warning is v0.0.28-rc1.
- **Cause/circumstances:** sv.num_edicts is the allocated high-water mark. Exhaustion can occur below 600 live entities when free slots are still subject to the allocator's reuse quarantine.
- **Proposed reproduction:** reach the pool ceiling after startup, free a slot recently, then request allocation before it becomes reusable. This reproduction has not been run.
- **Proposed fix/trials:** distinguish live, high-water, reusable, quarantined and expandable slots. Read-only source review completed; diagnostic correction is not implemented in the frozen candidate. Fixed version pending.
- **Validation qualification:** the existing allocator fixture stubs Host_Error with longjmp. It verifies dispatch, configuration and reuse, not complete session teardown, console recovery or Amiga behavior. Controlled session abort remains mitigation, not a capacity fix.


### WORLD-FLORA-HEAP-010: Seyda sprite payload exceeds final headroom

- **Version/where/when:** v0.0.28-rc1 image003 final heap gate, 3 October 2026, after complete map optimization and actor-contact acceptance. 29 Seyda Neen subcells fail; Balmora and regional maps do not fail this report.
- **Reproduction:** run normal image assembly with worldwide flora and the bounded Seyda town flora stage, then audit the exact final maps with matching target-ABI loader receipt.
- **Cause established by estimate:** worst sn045.bsp BSP-only peak is 6,015,520 bytes, below the 6 MiB map allowance. Its BSP resident 5,870,912 bytes plus 600,256 bytes resident sprite cost and 148,592 bytes sprite input overlap produces a 6,619,760-byte modeled peak, 328,304 bytes over the allowance. Catalogue cost is zero here. Sprite residency/loading overlap consumes the remaining town margin; this is not the Balmora edict incident.
- **What was tried/results:** matching engine compilation and 607 tests passed; exact-sharing verification completed for 2,723 maps; actor-ground acceptance passed. Final heap audit accepts 2,694 maps and rejects 29, stopping before HDF assembly. These are source/host estimates, not Amiga memory measurements.
- **Proposed repair:** focused review of sprite representation, input overlap, image resolution and retained town payload. Measure actual savings and preserve placements, silhouettes, collision and required reserves. No proposed option is yet established as the fix.
- **Fixed version:** pending. Preserve failed image003 and its receipts; previous playable images remain intact. The 3 MiB baseline and 2 MiB safety reserve are unchanged. Mitigation is not a fix.


#### WORLD-FLORA-HEAP-010 inspection addendum

Read-only final-BSP contributor inspection and private OBJ/wireframe export were completed. The first isolated shack geometry A/B merged 13 adjacent coplanar faces with matching texture transforms/styles: 1,113 to 1,100 faces. Model bounds were unchanged; surface-area difference was about 0.000149 over about 110,036 square engine units. This is only a host geometry experiment; no production BSP was changed, and lighting/rendering/collision were not accepted. It does not repair the 29 heap failures. An initial analysis report accidentally recorded whole-map rather than model bounds; a fresh numbered comparison corrected that diagnostic field, preserving the earlier report.

Owner-directed inspection now targets eastern house roofs and overhang assemblies. Selective baked panels and residency rebalancing remain candidates, not established fixes. Sprite streaming alone cannot close 17 of the 29 failures even with zero temporary input. Exact transparent-border cropping plus zero input overlap still leaves the worst model 41,568 bytes over allowance, before meaningful growth room. No reserves or original placements were reduced.


#### WORLD-FLORA-HEAP-010 geometry/collision investigation

Source and final-output inspection separate visible complexity from collision and sprite residency. For sn045, 19,716 of 50,172 plane records are referenced by visible faces; the remaining 30,456 are collision-tree-only, totaling 609,120 bytes of plane payload before node arrays. This is representation cost, not proof of duplicate rendered worlds.

The retained eastern balcony/addon/tall-house models lack a separate authored collision mesh. The existing converter uses original geometry for fallback convex pieces, independently of visual reduction. A private interpreted source-model probe generated 37/47/55/80 collision pieces for balcony/addon/tall-house01/tall-house02. Counts precede placement-specific plane deduplication and final compilation; they are not target memory measurements. Wooden post components account for 656 of 878 balcony source triangles and 608 of 958 tall-house02 triangles. No component has yet been classified safe to remove.

The arrival ship and Silt Strider already have visual reduction profiles. UV-patch splitting can increase emitted BSP faces after that reduction, so a lower reduction ratio is not guaranteed to decrease final payload. Existing coplanar/material/UV merging is already active. Next comparisons must report pre/post reduction, UV splitting, collision and sprite costs separately, preserve original inputs, and rerun the final heap gate. No complete repair is established.

The first standalone collision-inspection helper failed because putting tools before src on sys.path allowed tools/mwad.py to shadow the mwad package. A fresh helper with src before tools completed the probe. This was an inspection-script import failure; no runtime or production source changed.


### WORLD-FLORA-HEAP-010: contained-collision experiment and refreshed diagnostics

On 3 October 2026, v0.0.28-rc1 image003 remained stopped at the final memory gate (29 of 2,723 maps fail). A bounded tall-house-02 trial retained the original point/standing expansion rules and tested removal only of duplicate or strictly certified contained convex members. All 80 point and 80 standing members remained: **zero bytes saved**. The output was byte-identical; this experiment did not fix or mitigate the 328,304-byte worst-map deficit. No active maps changed, no new fixed version, target testing pending.

The private polygon heatmap was regenerated from all 64 current regular Seyda owner BSPs with final-file hash checks and current combined loading margins. Density counts placed compiled brush polygon centroids inside disjoint owner cores; it excludes repeated aprons, sprite pixels and collision planes. It must not be presented as total resident memory or original mesh triangle counts. Special routes remain in the build but are outside this regular-core mosaic. An overhead building layout now maps selected actual final placements to their original reference IDs and shared face counts. Generated visualizations and asset-derived geometry stay private.

#### WORLD-FLORA-HEAP-010 bounded wood-detail trial and lifecycle audit

A four-building, wood-only reduction trial completed on 3 October 2026 and was
rejected for integration. Seam-protected candidates saved 100 faces with a
17,052-byte standalone geometry-payload estimate; relaxing seam protection saved
208 faces/35,244 estimated bytes. These are not measured full-map Hunk savings.
Original collision packets were retained, but sampled silhouette support moved
up to 1.169 units and material selection cannot guarantee structural openings.
No complete map rebuild, target acceptance or fix is established. Two isolated
probe harness errors were corrected before candidate generation; neither is a
production regression. The final heap incident remains open.

A follow-up lifecycle audit should distinguish story-hidden scenery from freed
memory. Source inspection shows the opening-state hide path clears render/solid
state without freeing resident BSP data, and its current town-name condition
requires verification for numbered town routes. This is an unresolved scope
question, not a confirmed target defect. Reproduce post-introduction transitions,
save/load, collision and bounded-route behavior before changing content residency.
Hidden geometry must not be counted as recovered heap without loader evidence.


### Development inspection follow-up: Blender mesh views (3 October 2026)

During the v0.0.28-rc1 memory investigation, a private Blender view of four exact compiled common-building models initially rendered blank because the camera far-clipping distance excluded the objects. A second view corrected clipping but had inadequate lighting; a third added scale-independent inspection lighting and explicit materials, then passed visual inspection. Numbered attempts and original payloads were preserved. This corrected the inspection setup, not the memory failure or production mesh behavior.

The next proposed representation trial retains a small roof/wall silhouette mesh and bakes fine surface detail into textures. Openings, overhangs, ridge/eave shapes and original collision require explicit checks. Generic material LOD alone is not an accepted substitute, and a successful Blender render is not target validation. Derived models, images and scene files remain private; public tooling may contain converter logic and synthetic fixtures only.

### SPRITE-STREAM-VALIDATION: development wrapper and legacy alignment failures

Observed during v0.0.28-rc1 development on3 October2026; recorded2026-10-03 20:20:50 +03:00.
First introducing version of the legacy decoder issue is unknown.

- Trial001's isolated Docker wrapper omitted tools from PYTHONPATH. Native
  fixture setup failed importing project_version before compilation; the source
  dispatch check passed. Corrected wrapper002 imports/compiles successfully.
  This is a validation wrapper error, not a production sprite failure.
- Trial002 passed source dispatch and the existing scale fixture, but new stream/
  generic equivalence failed under UBSan. After a synthetic three-pixel payload,
  the original generic Mod_LoadSpriteFrame casts the next unaligned header to
  dspriteframe_t; member access triggered the sanitizer at model.c:2026.
  Source inspection confirms the cast; actual game-data/target impact is unproven.
- Proposed next trial retains sanitizers, compares aligned legacy-supported
  layouts and separately tests odd payloads through the stream path. That isolates
  stream equivalence from the pre-existing decoder limitation; it does not fix
  the generic decoder or establish real-asset acceptance. Root rerun pending.
- Both runs exit1; no verified loader fix, Amiga compile or final map acceptance
  from these trials. Preserve failure logs and track the legacy issue separately.
  A restricted comparison is a validation scope adjustment, not a production fix;
  mitigation is not a fix. Fixed version and target verification remain pending.

### POLYCOUNT-INSPECTOR: initial empty-scene render stops animation

v0.0.28-rc1 development, 3 October 2026; recorded 2026-10-03 20:47:55 +03:00. Initially the first
render accessed scene.source before a file was loaded, terminating the animation
callback. Loading later populated the object list while the canvas stayed blank.
An empty-scene guard, visible error reporting and requestAnimationFrame scheduling
in finally correct the startup path. Synthetic empty-to-loaded rendering passed;
the owner then manually confirmed browser operation. Stub rendering checks and
actual browser/GPU confirmation are distinct evidence. Eight focused Docker tests
passed. This fixes the inspector startup incident, not the game's heap failure;
first introducing production release and target gameplay acceptance are not claimed.

### Sprite validation follow-up: bounded native and full suite results

Trial004's 11 focused native checks passed with sanitizers. Its broad wrapper
failed on package import shadowing and a read-only current directory, then
trial005 corrected the environment using a disposable writable copy and package-
first search order: 611 tests passed with 3 skips in 18.903 seconds. These are
validation-environment incidents, not established gameplay regressions. Preserve
all failed receipts. Passing checks do not establish final-map or target acceptance.

### WORLD-FLORA-HEAP-010: unresolved fallback diagnostic accounting

Source review confirms normal combined peak uses the maximum of the BSP loading
phase and sprite loading phase, rather than double-counting BSP temporary input.
Separately, the classifier-allocation-failure diagnostic combines fallback peak
with a sprite phase derived from normal BSP residency. Fallback resident geometry
can be larger, so that diagnostic can understate the conservative fallback sprite
phase. Source-established issue; focused reproduction/correction and verified
fixed version pending. The normal 29-map rejection remains unaffected. Current
worst-map persistent residency alone still exceeds the unchanged map allowance,
so eliminating temporary overlap is not a complete repair. Mitigation is not a fix.

#### Geometry investigation method: heatmap, inspection and recipe identity

The documented inspection method separates spatial vertex-density hotspots from
object counts and memory, isolates placements/frames, compares supplied source,
merge, UV and final stages, and records reproducible camera/filter settings.
Display filters and planning polygons do not alter BSPs or repair the heap failure.
Numbered door recipes preserve originals and record visual/collision/texture
tradeoffs. This is method documentation, not a new bug or accepted savings claim.

### POLYCOUNT-INSPECTOR release admission and current estimate follow-up

The development HTML inspector was registered for transfer but rejected by the
release admission validator as an unexpected distributable type. Root added an
exact source-owned HTML path exception rather than permitting arbitrary assets;
source correction is present, final package acceptance remains a separate check.
This was a toolkit integration issue, not a gameplay or proprietary-asset exception.

The buried-face candidate's actual BSP file saving is110,208 bytes; a cached-ABI
current-source streaming model estimates181,536 fewer resident/peak bytes and
only1,824 bytes margin. No fresh matching compile, complete new map gate or target
validation is established by that estimate. Earlier sprite overlap and geometry
saving must be accounted separately. The heap incident remains open and no new
HDF or fixed version is claimed.

### TERRAIN-CULL: global topology and local sky enclosure remain unaccepted

Recorded 3 October 2026. Owner visual review rejected candidate010: 24,650
stored faces remained with hanging geometry; the candidate used compiled local
LAND proxies and did not consume the canonical global terrain NPZ. The subsequent
011 receipt is only an alignment diagnosis: 288 source-grid corners had zero
residual at source scale 0.25 and global origin [-2816, -17920, 0]. The canonical
continuous surface is near Z=80 while the compiled surface is about Z=71 west
and Z=80 east. No repaired BSP is established.

An independent read-only audit of closure candidate005 (24,786 stored faces)
found 169 referenced sky faces, 265 distinct static stored faces proven buried
at one or more placements by a conservative test against local BSP terrain, 124
zero-area stored faces, and 50 low `*water` faces outside local LAND coverage.
This diagnostic is not a complete global-topology cull, and water remains
separate from terrain. The screenshots also record a doorway ground slit; a
matched original/candidate comparison is still required to attribute it. Keep
this candidate rejected/incomplete until serialized geometry is audited with
all preview/hide controls OFF, including sky references, crossing/shared-face
behavior, seams, degeneracies, and preserved collision/visibility.

### POLYCOUNT-INSPECTOR: fly navigation and repeated-count regressions open

The 011 inspector receipt is ready to copy JSON, but fly-navigation and count
traversal acceptance remain open. Recorded regressions are: textarea/contenteditable
focus conflicts with navigation input; Ctrl browser shortcuts can fire while
editing; the 50 ms elapsed-time clamp halves movement below 20 fps; and repeated
per-frame face-count traversal processes about 43,000 faces per frame. HTML012 is
the fly-fix work item; these defects are not documented as fixed until the owner
can verify navigation, editing shortcuts, frame-rate behavior and count updates.

### TERRAIN-CULL audit follow-up 002: sky geometry removed; global terrain still pending

Recorded 3 October 2026 from an independent read-only binary audit report; this
document update did not rerun its measurements. The audited universal-sky
candidate010 final BSP has 24,650 stored faces and **zero stored sky render
faces** (169 in the earlier closure candidate005). This verifies serialized sky
geometry removal for that candidate. The sky texture resource remains, and
replacement background appearance and loading have not been verified on target.
The candidate remains rejected/incomplete because its culling record says the
canonical NPZ heights were recorded for provenance but not used for culling.

The same report's conservative local-LAND test found 482 placed nonzero-area
faces, representing 277 stored face IDs, wholly below one local terrain triangle
by at least 0.5 units. This is a lower-bound diagnostic, not a global deletion
list. It separately counted 122 deep vertical world LAND faces reaching
Z <= -500; these are not sky faces, and depth alone does not prove they are all
buried or removable. Stored degeneracy count was 112 (5 world, 107 inline).
The original source had zero exact-zero-area faces and candidate010 has 112.
The change arose somewhere in the original-to-candidate pipeline; the exact
emitting instruction/stage remains untraced. Do not assign it specifically to
the culler or BSP writer.

The object-stage receipt sums to 1,446 shared/lightmapped and 412 fragment-growth
retained model-face decisions; these are not placed-instance totals. The report
also distinguishes a failed per-placement variant experiment of 39,141 faces
from the final candidate's 24,650; do not conflate them. Its matching-ABI estimate
clears the 11 MiB total by 4,496 bytes after the modeled 3 MiB baseline reserve
and 2 MiB safety headroom. That clearance is not actual free runtime RAM or live
measurement.

The 011 canonical-NPZ check is alignment diagnosis only (288 grid corners,
zero residual, scale 0.25, global origin [-2816, -17920, 0]); it changed no BSP
geometry. Preserve candidate005's earlier 169-sky/265-buried/124-degenerate
findings as candidate-specific history. Neither audit establishes complete
terrain clipping, target sky appearance, or gameplay acceptance.

Culling is a pre-baked operation on render faces in fresh derived BSP outputs.
Original maps/assets remain intact; ON/OFF are separate builds from the preserved
pre-cull input, and the configured default is ON. The incomplete result came from
using the wrong terrain receiver and retaining unsupported fallback classes; it
was not a destructive-action policy.

### TERRAIN-CULL inspection004: source join repair is separate from buried-object removal

Recorded 3 October 2026 from the independent report; these measurements were not
rerun by this journal update. The canonical surface is continuous at the checked
coarse/fine port-patch boundary, while the original and candidate BSP terrain
meet at both about Z=71 and Z=80 at the same XY. A vertical connector can conceal
the step; deleting it below canonical Z without first fixing the rendered join
can expose an opening. This identifies a seam mechanism, not permission to keep
buried walls. The report also records continuity across 2,496 neighboring
canonical source-cell edge pairs.

A separate source checkpoint reports 23 mismatched boundary segments out of 26
before its bounded shared-edge stitch and zero after; maximum measured boundary
difference changed from 15 to 0. Source LAND triangle count changed 4,756 to
4,825, an increase of 69 **source** triangles, not BSP faces. The report states
that 25 focused tests and 9 synthetic reader tests passed, but this journal did
not rerun them. Native engine fixture compilation was blocked by missing
`VERSION` and `progdefs.q1` in the supplied inspection subset. The checkpoint
was not a rebuilt or accepted final BSP; full canonical object culling remains
in progress.

Inspection004 also reports a canonical whole-face burial witness of at least
17.628961953 compiled units. This is distinct from the earlier 22.55-unit
local-LAND witness. The original source has zero exact-zero-area faces and
candidate010 has 112; the report localizes their introduction to somewhere in
the original-to-candidate pipeline but does not identify the emitting stage.
No claim of a BSP-writer-specific cause is established. The full cut, collision,
visibility, memory and target appearance gates remain open.

### SKY-FOG v0.0.28: shared resource and reserved depth validated natively; target pending

Recorded 4 October 2026. Removing map sky textures exposed a renderer dependency:
the old background selection required a texture named `sky`, and that map texture
also initialized the process sky buffers. A first-load exterior with no sky
texture therefore lacked an initialized background. The source fix adds explicit
worldspawn exterior/interior selection and a fixed shared raw sky resource loaded
into the existing static buffers. It keeps no map allocation pointer. Exterior–
interior–exterior transitions preserve the shared pixels and saved world-clock
cloud phase while interior mode disables exterior sky. Independently authored
interior lighting/environment is not replaced by exterior weather or day/night.

The former negative background depth also entered ordinary maximum-distance fog.
Only sky-filled background spans now receive the reserved value -32768; the fog
pass skips exactly that value. Zero and other negative values still receive fog.
The depth audit found that unchecked near inverse-depth conversion could itself
overflow into a reserved negative value. World and sprite depth writes now clamp
exceptional values to 0–32767, with regression coverage for high, crossing, zero
and negative inputs. Opaque foreground writes replace the sky marker; transparent
sprite texels preserve it. The sky metadata reader is bounded locally; this does
not claim to repair unrelated uses of the engine's general token parser.

The refreshed offline Docker validation passed both render-range parser/view
fixtures, all three focused sky/fog/sprite test methods (including real particle
depth replacement and undefined-behavior-checked world depth spans), and the
matching asset-free Amiga compile. This is focused native/compile evidence, not
a new full-suite result or a target appearance acceptance. The source package
also registers the synthetic auxiliary-render-pool inspection regression.

Remaining gates are extraction and packaging of the exact authorized 32,768-byte
shared image, first-load and exterior/interior transitions with that resource on
target, pitched/FOV sky appearance, actor/particle/water/torch occlusion, and
measured resident memory/frame cost. Serialized sky-enclosure removal and global
terrain clipping have separate geometry/collision/visibility gates. Native sky
fixtures do not establish completion of those converter gates. See
[day/night and sky](DAY_NIGHT_AND_SKY.md) for the runtime resource contract.

### EXTERIOR-SURFACES v0.0.28: no checked interior-cell leak; storage exclusion remains open

Recorded 4 October 2026. A read-only source/master audit matched all 1,849 cached
Seyda placements, all 637 scenery-index references and all 299 numeric source
references in candidate017 to exterior CELLs, with no interior or unresolved
matches. This does not identify screenshot geometry or prove every exterior
surface is needed. The inspector's two-sided display differs from the engine's
existing backface rejection; neither display policy removes stored inward faces.

Static-mesh collision prisms are separate from textured render faces. The
identified terrain closure mechanism instead textures top/bottom/sides of LAND
prisms down to Z=-512. Hidden NIF nodes and collision nodes are excluded from
visual packets; stencil draw-mode metadata is not retained, but none occurs on
the four sampled eastern building meshes. No general exterior per-face exclusion
catalog is implemented. The proposed source-bound asset/instance catalog, current
evidence and remaining geometry/memory/target gates are recorded in
[Exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md). No geometry changed in
this audit. Resolve hidden/under-terrain costs while preserving the continuously
resident central area before using additional subcells as a memory strategy.

### EXTERIOR-VISIBILITY v0.0.28: source policy metadata and bounded selector added

Recorded 4 October 2026. Source visibility properties previously disappeared
after NIF extraction. The exporter now retains inherited stencil draw modes and
their origin, stable shape/triangle provenance, and hidden/collision exclusions.
Metadata preservation does not add clockwise/double-sided/stencil renderer
support: unsupported cases are reported, and retained unsupported policies block
an explicit exterior selection's acceptance.

The new optional model/hash-bound exterior selector filters visual triangles
before merging, keeping the original collision packet/arrays intact. Interior
context, stale identities and invalid selections fail closed. No production rule
is enabled, no inspector volume is automatically consumed, and panel-flattening
combinations remain explicitly unsupported. The sampled house stays at 652 source
triangles and 578 prepared surfaces; source flags prove no additional interior-only
faces, so the measured new cut count is zero. Center-facing normals are only
candidate evidence. Eight new synthetic tests and 26 affected existing Python
checks passed; no new native/target result is claimed. Initial test preparation
revealed an import-path shadow and floating palette channels in a fictional packet;
both fixture issues were corrected before the passing run. See
[Exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md) for scope and remaining work.

#### EXTERIOR-SURFACES follow-up: default hidden-surface cull contract

Recorded 4 October 2026 01:33 EEST. Owner direction requires compile-time
removal of permanently hidden static exterior render surfaces by default, with
`--hidden-surface-cull` defaulting to true and `--hidden-surface-cull false` as
the explicit opt-out. Build audit output must disclose the effective setting and
surface counts. Root implementation is in progress; this entry records the
required contract and does not claim that the flag or its audit is complete.

The flag controls only the final serialized bounded automatic exterior pass.
Reviewed source-bound exclusions and source hidden-node flags are separate export
behavior and are not toggled by this option. There is no general sealed-interior solver
now, so this does not imply wholesale removal of house interiors. Paint remains
a review aid; full-world manual painting is not required, and inspector plans
are not connected to compiler input. Current diagnostic maps are unchanged and
no production house savings are measured. `--terrain-visual-cull` is a separate
canonical-topomap clipping path whose production acceptance remains incomplete.
Preserve visible exterior geometry and water; retain collision independently.
Surfaces hidden only from one viewpoint remain subject to runtime visibility.
Door-loaded interiors stay outside the exterior pass.

The pre-existing issue remains open: no general accepted hidden-surface rule,
serialized-map audit, measured production memory saving or target acceptance is
established by this requirement. See [Exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md).

#### EXTERIOR-SURFACES source review: appended static faces bypass brush CSG

Recorded 4 October 2026 01:37 EEST. This is a known source-architecture gap in
the static mesh `prepare_mesh_bsp.py` route; its introducing version is unknown
and no production regression is attributed to a particular change. `prepare()`
runs `qbsp`, `vis` and `light`, rebuilds the world hull, and then calls
`append_meshes()`. The static mesh surfaces appended at that stage bypass brush
CSG on the earlier map brushes. This scope is specific to this route; the
separate canonical terrain-visual-cull pass has incomplete production
acceptance. See [pipeline source](../tools/prepare_mesh_bsp.py#L414) and
[append call](../tools/prepare_mesh_bsp.py#L432).

`Mod_LoadFaces()` allocates `count * sizeof(msurface_t)` for every stored BSP
face and records the full face count. Vertex, edge and texinfo loaders likewise
allocate arrays according to their serialized lump counts. Runtime backface
rejection tests whether a surface is drawn from a particular viewpoint; it does
not remove loaded face records or free their Hunk storage. See [face loading](../engine/aga/src/model.c#L913),
[vertex loading](../engine/aga/src/model.c#L693), [edge loading](../engine/aga/src/model.c#L759),
[texinfo loading](../engine/aga/src/model.c#L787), and [backface tests](../engine/aga/src/r_bsp.c#L355).
This does not mean every loaded face is drawn in a frame. A two-sided inspector
view is not proof of duplicate storage. Independently stored inner walls remain
in the BSP and resident arrays until an accepted compile-time exclusion removes
them.

The default-on `--hidden-surface-cull` implementation and conservative
closed-opaque-shell containment helper are in progress; a fresh diagnostic was
requested. No successful BSP cut or production face/memory saving is yet verified.
The issue remains open pending the diagnostic, serialized-output audit, measured
memory result and target acceptance. This source review records an existing
pipeline limitation, not a newly introduced regression. See [Exterior hidden
surfaces](EXTERIOR_HIDDEN_SURFACES.md).

#### EXTERIOR-SURFACES diagnostic 022: bounded containment found no house faces

Recorded 4 October 2026 01:48 EEST. This is the result of the initial
closed-opaque-convex proof approach: it did not satisfy the intended removal of
house interior surfaces. The default-on flag was active, so zero removals indicate
that this bounded algorithm found no qualifying whole faces; they do not show the
flag was disabled. Diagnostic 022 remains at 32,209 stored faces and 5,013,620
file bytes, unchanged from 021. It examined 240 static placements, 212
assemblies and 70 closed shells, with zero whole faces certified inside a shell;
reported classes include 1,769 open/non-manifold, 138 nonconvex, 15 duplicate
and one budget-retained. These are audit classifications, not successful culls.

The separate two-house run also removed zero faces. Source review of common tall
house 01 found zero inward-facing triangles in the examined source wall subset:
one outward-facing sheet at x=-256 had no opposing coplanar mate. No duplicate
geometry groups were found among all 652 source triangles. These facts do not
explain all inspector screenshots or establish the cause of the performance
problem. Treat this as a partial algorithm result, with the general exterior
flood-fill and acceptance gates still pending.

A general solver proposal is to classify exterior-reachable empty space in the
actual assembled scene against the canonical topomap boundary, then consider only
surfaces bordering sealed unreachable voids. Water must not act as ground or a
barrier. A door that teleports to a separate interior is outside this pass; an
actual dynamic opening in the exterior must remain a possible connectivity path.
Real intersections, overlaps and T-junctions need exact splitting; do not invent
convex closures or voxel bridges to close gaps. This flood-fill solver is not
implemented. The available helper proves only a bounded class of strictly
contained faces inside exact-topology closed opaque convex shells.

The default is `--hidden-surface-cull true`; omitting the option keeps that
default, and `--hidden-surface-cull false` is the explicit opt-out. Per-map/cell
JSON rows record effective setting, scene kind, hashes, before/after lump counts,
removed faces, bytes saved and classifier details. A zero-cut result remains a
zero-cut result, not success. No production memory saving or target acceptance
is established. See [Exterior hidden surfaces](EXTERIOR_HIDDEN_SURFACES.md).
#### EXTERIOR-SURFACES build integration and validation follow-up

Recorded 4 October 2026 01:54 EEST. The main build now exposes
`--hidden-surface-cull` with default `true` and forwards it to image creation.
The finalizer applies the pass to the explicit exterior-map manifest after scene
assembly and before BSP compaction, contact checks, heap audit and fingerprinting.
Changed originals remain in private run storage. Per-map receipts and logs retain
effective settings, hashes, counts and classifier details. This is source and
focused test evidence; no house faces were removed and requested house-interior
removal remains incomplete.

Scope review confirms true interior-CELL-only render faces are absent from the
exterior BSP; separate interior CELL maps retain their geometry and lighting.
The back side of an exterior triangle needed for the outside shell must remain,
and collision is handled independently. A limited private prototype-16 portal
model (16 selected planes, 322 cells, 838 portals) made zero cuts because all modeled space was
reachable. It omitted canonical topography, neighboring cells and doors, so it
does not test full-scene connectivity and does not complete the requested house
culling. General exterior flood fill remains unimplemented.

Validation notes: 27 focused flag/serializer/helper tests and 16
builder/recovery/canonical checks passed. One combined invocation had an
ImportError from a mistyped test name; the correctly named
`test_render_pool_inspection` plus compact-BSP tests then passed (10 tests). The
first full source run found a missing final blank line in a new test file; after
correction, the 1,054-test source run passed. These were corrected test-command
or test-file formatting issues; no new production regression is established.
No target acceptance is claimed.

#### EXTERIOR-SURFACES independent plane and UV audit

Recorded 4 October 2026 02:06 EEST. An independent professional audit counted
57,009 plane rows / 52,817 unique in diagnostic 017: 4,192 exact duplicate
20-byte rows (83,840 serialized bytes). Diagnostics 021/022 counted 55,412 rows /
52,865 unique: 2,547 duplicates (50,940 bytes). This is duplication evidence,
not a geometry improvement or an applied saving; wait for a new output receipt
before claiming deduplication.

The audit found 1,520 terrain-quad pairs in 017, five over the 64-pixel UV gate;
021/022 have zero remaining under the same criterion. Inspector 018 corrects
role discovery and visibility classification but does not complete canonical
terrain clipping. Neither result accepts the hidden-surface pass or target output.

#### EXTERIOR-SURFACES receipt 023 and terrain/object A/B proposal

Recorded 4 October 2026 02:17 EEST. Receipt 023 applied exact duplicate-plane
record removal: 55,412 to 52,865 plane records, 2,547 rows / 50,940 serialized
bytes saved. BSP face count remained 32,209; file size changed 5,013,620 to
4,962,680 bytes. This does not establish geometry improvement, live-RAM savings
or native fit.

A separate bounded mesh experiment changed vertices/polygons/fan triangles from
616/578/864 to 675/590/919 (including 83 new vertices, net +59), removed 5.2179%
surface area, and had a 3.45e-10 relative above-ground area difference. Texinfo
was unchanged; no BSP or serialized-byte result was produced. A 021 reclip grew
675/590/919 to 704/594/948 through numeric fragmentation and was rejected as an
optimization. Physical terrain/object weld or Boolean union remains a proposal
separate from visibility clipping; a bounded actual example using canonical
clipping is in progress. Current house convex detection still makes zero cuts.
#### EXTERIOR-SURFACES independent 021/022 review and 023 peak projection

Recorded 4 October 2026 02:23 EEST. Independent byte comparison confirms 021 and
attempted 022 are identical. The 017→021 total reduction of 1,445 faces decomposes
into 1,597 fewer terrain faces and 152 more world-model faces; shared pool faces
(5,218) and other inline faces (19,862) are unchanged. This is count accounting,
not evidence that any interior-only surface was removed.

Correct loader accounting for 021: BSP-only peak 6,856,336 bytes; BSP resident
6,717,664 bytes. The separate sprite-residency and range-registry inputs are
600,256 and 11,536 bytes. The phase-ordered conservative combined estimate is
7,329,456 bytes, not a pure BSP peak, and exceeds the 6 MiB map allowance by
1,038,000 bytes. Receipt 023 models 50,928 bytes fewer plane-array allocations;
arithmetic projects 7,278,528 combined bytes, 987,072 over allowance. This is
not a new full-ABI measurement or memory-fit result. The reviewed BSP contains
zero sky render faces with shared-sky metadata present; production terrain spawn,
coarse-collision alignment and native visual verification remain blockers.

The one-house A/B now has a complete inspected receipt/summary: 616/578/864
(float local vertices/polygons/fan triangles) became 675/590/919; 83 new exact
local vertex positions were introduced for net +59 vertices, with no whole source
faces removed. Surface area decreased 12,360.891177 units (5.217138%). The
above-ground consistency error is 0.000077400473 (relative 3.45096033147e-10),
computed through the same clipper and therefore not independent proof. No BSP
variant or file-byte result exists. Texinfo mappings were reused without a
measured lightmap rebake. The already clipped 021 reclip grew to 704/594/948 via
numeric fragmentation. Treat it as a geometry experiment, not an optimization
or applied production saving.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- EFRAG-01 (no report page): Static foliage leaf links exhausted ('Too many efrags!')
- [ENGINE-ENTITY-TEXT-UNBOUNDED-35](ENGINE-ENTITY-TEXT-UNBOUNDED-35.md): Entity and QuakeC text was copied into fixed buffers without a bound
- [ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md): Sweep of every engine fatal path that data or a player can reach
- [ENGINE-FILEBASE-UNBOUNDED-35](ENGINE-FILEBASE-UNBOUNDED-35.md): COM_FileBase copied a name of any length into a 32-byte buffer and walked before the start of a name without a slash
- [ENGINE-LEAF-LIMIT-UNCHECKED-35](ENGINE-LEAF-LIMIT-UNCHECKED-35.md): A map with more leaves than MAX_MAP_LEAFS overflowed the PVS buffers silently
- [ENGINE-MODEL-NAME-SYSERROR-35](ENGINE-MODEL-NAME-SYSERROR-35.md): Model names of any length went into 64-byte model slots, and a missing model file stopped the program
- [ENGINE-SUBMODEL-LIMIT-32](ENGINE-SUBMODEL-LIMIT-32.md): Map loading does not check the submodel count against MAX_MODELS
- [ENGINE-UDP-ADDRESS-OVERFLOW-35](ENGINE-UDP-ADDRESS-OVERFLOW-35.md): A typed network connect address longer than 254 characters overflowed a stack buffer
- [ENGINE-VA-UNBOUNDED-35](ENGINE-VA-UNBOUNDED-35.md): va() formatted into its 1 KiB buffer without a bound
- ENTITY-DIAGNOSTIC-009 (no report page): Entity-exhaustion warning reports the high-water count as live slots
- [ERICW-TEXINFO-SIGNED-31](ERICW-TEXINFO-SIGNED-31.md): ericw vis crashes and ericw light leaves faces unlit above texinfo 32,767
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped
- FLORA-ENTITY-001 (no report page): Dense vegetation exceeds the per-map entity reserve
- FLORA-RESERVE-002 (no report page): Two world flora maps exceed storage and clipnode reserves
- GEO-04 (no report page): Canonical-terrain world rebuild fails VIS (too many portals)
- [IMPORT-DOORBANK-LIMIT-32](IMPORT-DOORBANK-LIMIT-32.md): Town importer did not check the engine's 128-row door bank limit
- [INTERIOR-COORDS-31](INTERIOR-COORDS-31.md): Some interiors place objects beyond the +/-4096 coordinate range
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

Related bugs in other categories:

- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
