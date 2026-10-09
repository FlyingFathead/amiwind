# Hidden in Dirt: Seyda Neen’s graphics performance bottlenecks

<!-- contents start -->
## Contents

- [Current implementation status: incomplete; acceptance remains open](#current-implementation-status-incomplete-acceptance-remains-open)
- [Mandatory Morrowind exterior map acceptance requirements](#mandatory-morrowind-exterior-map-acceptance-requirements)
- [The memory failure](#the-memory-failure)
- [Historical method 1: bounded local-LAND trial (incomplete)](#historical-method-1-bounded-local-land-trial-incomplete)
- [File savings versus allocation estimates](#file-savings-versus-allocation-estimates)
- [Door methods 1 and 2](#door-methods-1-and-2)
- [Rejected experiments still matter](#rejected-experiments-still-matter)
- [Inspection nominates geometry; it does not authorize deletion](#inspection-nominates-geometry-it-does-not-authorize-deletion)
- [Non-destructive acceptance sequence](#non-destructive-acceptance-sequence)
- [Remaining ground/closure questions](#remaining-groundclosure-questions)
- [Shared sky: renderer background and map geometry](#shared-sky-renderer-background-and-map-geometry)
  - [Historical inspector preview readings (not acceptance)](#historical-inspector-preview-readings-not-acceptance)
- [What we learned today: global topology is the compile basis](#what-we-learned-today-global-topology-is-the-compile-basis)
  - [World graphics acceptance: sediment, water and sky](#world-graphics-acceptance-sediment-water-and-sky)
- [Central Seyda Neen must remain continuously resident](#central-seyda-neen-must-remain-continuously-resident)
  - [Resident footprint and cost investigation](#resident-footprint-and-cost-investigation)

<!-- contents end -->

## Current implementation status: incomplete; acceptance remains open

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
[-2816, -17920, 0]. Inspection004 additionally reports 2,496 continuous source
cell-edge pairs but a rendered coarse/fine seam near Z=71/Z=80, plus a separate
canonical whole-face burial witness. A bounded source checkpoint reports the
boundary mismatches reduced from 23/26 to zero; it adds 69 source triangles, not
BSP faces, and does not complete object culling. See [the terrain boundary
measurements](TERRAIN_VISUAL_CULL.md#coarsefine-terrain-boundary-diagnosis-separate-from-object-culling).
The required terrain operation remains incomplete. Acceptance requires final
serialized output with all inspector hide/preview controls OFF and target sky
appearance/loading verified.

The method details below describe bounded implementation behavior and candidate
trials. They are historical implementation evidence, not acceptance policy or
proof that the required culling is complete.

## Mandatory Morrowind exterior map acceptance requirements

1. Remove EVERY local sky-enclosure render face: per-cell and per-subcell ceilings, walls, undersides and fragments, above or below ground. Subdivision does not make enclosure pieces legitimate scenery. Preserve current sky appearance through a separate shared/background rendering path, never another enclosure baked into each map.
2. Remove EVERY buried portion of static exterior render geometry using the actual, globally aligned canonical topomap surface and its varying slopes and seabed. Remove wholly buried faces and buried portions of crossing faces. Water level, flat planes, compiled local LAND proxies and finite-depth bands are not substitutes for the canonical global terrain input.

Keep the visible terrain surface intact. Preserve visible foundations, underwater structures above the seabed and visible water. Water is not terrain. Door-entered Morrowind caves and tombs load separate interior cells and are outside this exterior pass. Preserve required collision, contents and visibility behavior independently; they do not authorize retaining unwanted render faces.

Shared models and lightmaps require correct placement-specific clipping and deduplication/rebaking, with measured representation costs. They are not automatic exemptions. Missing terrain coverage, unsupported clipping, unresolved coordinate transforms or fragment-budget fallbacks must BLOCK ACCEPTANCE and be reported as incomplete. Do not report retained geometry as finished culling.

The serialized final BSP must satisfy both conditions with ALL inspector hiding and preview options OFF. Verify serialized geometry, render references, degeneracies, seams, shared placements and preserved collision/visibility, then matching-ABI memory and target appearance/loading. Attempted-face counts, collision checks alone and viewer-only hiding are insufficient.

These are required outcomes, not claims that the current implementation is complete. Candidate010 was rejected by owner visual review. It used compiled LAND proxies, not direct canonical NPZ evaluation. Direct NPZ alignment was subsequently checked at 288 source-grid corners with zero residual; that diagnosis is not a repaired BSP. The global packet exposed a continuous terrain surface where the compiled coarse/fine terrain had a height step.


Morrowind/AmiWind exterior culling uses the authoritative GLOBAL TOPOMAP as its
default surface reference. Door-entered caves and tombs teleport/load a separate
INTERIOR CELL: their underground geometry is not part of the exterior BSP and is
outside this exterior culling stage. Do not retain buried exterior graphics on
behalf of those separate interiors. Remove exterior graphics below actual varying
ground/seabed while preserving visible terrain, water placement and collision.
Only an opening or below-ground space verified in the actual EXTERIOR geometry
requires a documented conditional exception. This is specific to the AmiWind
conversion, not a universal 3D-engine rule.

A town costs more than its visible rooflines. Supports extend into the ground,
detailed source meshes also feed collision, texture boundaries split polygons,
and sprites remain resident even when not drawn. The v0.0.28 investigation
separates these costs before changing their representation. A viewer comparison,
host check or engine compilation is not a completed playable repair.

These aggregate results were recorded on 3 October 2026. Original/converted game
assets, inspection scenes and playable packages remain private.

## The memory failure

The last complete final-map gate inspected 2,723 maps: 2,694 passed and 29 Seyda
Neen maps failed. Assembly stopped before a new HDF. The worst map’s BSP-only
peak fit; sprites consumed the remaining room.

| Original worst-map allocation model | Bytes |
| --- | ---: |
| BSP resident data | 5,870,912 |
| BSP-only loading peak | 6,015,520 |
| Shared sprite residency | 600,256 |
| Sprite temporary input overlap | 148,592 |
| Combined loading peak | 6,619,760 |
| Map allowance | 6,291,456 |
| Excess | 328,304 |

The policy remains 11 MiB total: 3 MiB non-map baseline plus 2 MiB safety reserve
leaves 6 MiB for the map. The estimator compares phase peaks; it does not blindly
add the BSP temporary peak to the sprite phase. Hiding geometry, freeing an edict
and reducing resident memory are different operations.

## Historical method 1: bounded local-LAND trial (incomplete)

The [terrain visual-culling stage](TERRAIN_VISUAL_CULL.md) uses actual compiled
opaque LAND belonging to the cell/subcell, not screenshots or guessed sea level.
**Water is not terrain.** Ground/seabed underneath water is terrain; retain its
surface topology and collision.

Bounded triangular ground prisms follow the slope. Their lower bound is the
lowest LAND vertex: geometry below it remains. A configurable overlap skirt,
default **0.5 compiled units**, leaves material beneath the surface to prevent
cracks. Missing coverage, sky, water, interiors and uncertain cases are excluded.
Original collision and world terrain remain intact.

The stage is default ON, with independently configurable enabled/overlap values
by BSP, subcell and cell. Precedence is BSP, subcell, cell, global; explicit
compiler options override the corresponding setting. Invalid, negative and
nonfinite overlap is rejected. Receipts record the actual policy for each bounded
region/route. Preserve the unculled common source before partitioning: a later
OFF comparison cannot restore faces already deleted upstream.

Shared geometry is removed only when buried at **every** placement using it.
Crossing shared/lightmapped surfaces remain original. Unique unlightmapped faces
can be clipped under bounded fragment rules while preserving normals and affine
UVs; uncertain fragment growth retains the original.

| Bounded terrain trial | Result |
| --- | ---: |
| Original → candidate visual faces | 26,190 → 24,749 |
| Net removed faces | 1,441 |
| Clipped-face cases | 805 |
| Growth/budget retained cases | 298 |
| Shared/lightmapped retained cases | 1,432 |
| BSP file size | 4,550,392 → 4,440,184 bytes |
| Actual file saving | 110,208 bytes / 107.625 KiB |
| Inline collision checks | 960 passed |
| World terrain faces | 3,777 unchanged |

Classification counts are separate observations, not an invented equation for
net faces. These establish bounded file/preservation evidence, not target fit.

## File savings versus allocation estimates

A like-for-like model used the current streamed-sprite policy and cached target
ABI sizes in both columns:

| Current-source model | Original | Culled |
| --- | ---: | ---: |
| Combined resident/loading peak | 6,471,168 | 6,289,632 bytes |
| Margin against map allowance | −179,712 | +1,824 bytes |

The modeled saving is **181,536 bytes**, distinct from the actual 110,208-byte
file reduction. The old 6,619,760-byte peak included sprite input overlap: its
entire improvement cannot be credited to geometry removal. **1,824 bytes is a
very thin estimated margin.** A fresh matching Amiga engine compile has since
passed, but a new matching full-region/all-resource audit and target validation
remain pending. The cached estimate is not that final acceptance receipt.

Streaming removes input overlap, not resident pixels. Lossless anchored border
cropping is a separate candidate: preserve every nontransparent pixel, frame
origin, canvas reconstruction, animation timing and world footprint. Earlier
estimated cropping/streaming savings alone remained insufficient; rescaling or
silently shrinking trees is not lossless equivalence.

## Door methods 1 and 2

A selected door may not include its frame. Preserve immutable `original` and
number alternatives `<door_type>_optimization_method_1`, `_2`, `_3` and so on,
retaining old selector aliases explicitly.

| One bounded door comparison | Original | Method 1 | Method 2 |
| --- | ---: | ---: | ---: |
| Input visual triangles | 162 | 108 | 77 |
| Converted stored faces | 154 | 100 | 54 |
| Standalone allocation | 47,376 | 44,320 | 36,128 bytes |
| Standalone saving | — | 3,056 | 11,248 bytes |

Method 1 retains the corrugated shell and projecting fittings while baking
selected detail. Its compiled breakdown is **68 wood + 16 lock + 16 handle**;
source triangles are another stage. Method 2 uses
**16 front + 6 side + 16 lock + 16 handle**, with a source-baked front and darker
detail. Its new 5,520-byte
texture allocation is charged; old textures get no retirement credit. Repeated
placements share the stored mesh: do not multiply resident savings by instances.

Original 162-triangle collision remains exact. A frontal projected-outline check
lost/gained no samples, but oblique body depth changes reach 3.436 units and the
coarse texture alters appearance. Both are private candidates; production remains
original. Neither a frontal test nor a standalone estimate proves all-angle,
interaction, full-map or target acceptance.

## Rejected experiments still matter

Conservative collision containment removed no members and saved zero bytes.
Wood-only LOD estimated 17,052/35,244 standalone bytes but changed structural
appearance; no full-map saving was accepted. A direct roof panel reduced 578
faces to 549, yet displaced its boundary by 6.778 units and added 3.14845%
projected fill; it was rejected. A later boundary/crease-preserving fold remains
a separate visual candidate, not the memory fix. UV subdivision can increase
final faces after source reduction.

## Inspection nominates geometry; it does not authorize deletion

The [Polycount Inspector](POLYCOUNT_INSPECTOR.md) reads locally owned BSPs/scenes.
Spatial vertex-density hotspots are not object face counts, collision complexity
or memory. Isolate the placement, separate frame and terrain; compare components
and supplied source, merge, UV-split and final counts. Keep stored faces, repeated
placed faces, runtime submitted/drawn geometry and resident/loading bytes distinct.

Record source identity, XYZ, compass heading, projection, bin width and range.
Min/max filters change display/picking only. Above view is orthographic.
Polygon/box zones, where supported by the tool version, express planning intent,
not automatic removal or generated regions. Preserve exterior silhouettes,
openings, window views, collision and story consumers. Noclip/backface viewing
cannot prove a surface is never visible.

A central core with no town-square reloads and separate distant points of interest
needs coordinated planner/converter/runtime ownership, coverage, hysteresis and
actual budgets. An inline entity is not a resident region; a drawn outline does
not reclaim apron-loaded data.

## Non-destructive acceptance sequence

1. Preserve original source, pre-cull payload, configuration and identity receipts.
2. Generate one bounded candidate into fresh output; keep failures and no-op cases.
3. Compare content, UVs, lighting responsibilities, terrain and collision.
4. Run focused checks, full Linux suite and matching asset-free Amiga compile.
5. Audit actual final regions, sprites, actors/transport and source-bound ABI
   phase peaks with unchanged reserves; stop if any required map fails.
6. Only then assemble/read back a private HDF and test views, transitions,
   interactions, save/load and responsiveness on target/emulator.

Host checks and fresh compilation have progressed; the new whole-region gate,
image and gameplay acceptance decide whether this becomes a repair. **Mitigation
is not a fix.** Real synthetic-only inspector screenshots remain blocked/pending
approved capture; no recreated or proprietary screenshot is substituted here.

## Remaining ground/closure questions

The measured trial is not a claim that all buried geometry disappears. The
current retained-BSP preview includes bounded crossing-face clipping but remains
partial and differs from the compiler trial; the compiler separately retains shared,
lightmapped and growth-limited cases. The 3,777 world faces remain unchanged,
including generated LAND closure responsibilities. Classify any underground
side/casing work separately from top terrain and original collision.

An initial missing-global-LAND hypothesis is not supported by the checked camera
location: compiled LAND covers it. Nearby geometry may be above that ground,
not wholly buried. Further coverage/closure audits must use actual source faces,
not a noclip impression. Water surfaces remain excluded; only actual ground or
seabed can support terrain-based clipping. No missing-topography or solved-town
claim is established by the screenshots or this measured candidate.

## Shared sky: renderer background and map geometry

Sky appearance and the polygons that enclose an exterior BSP have different
roles. The renderer already draws a sky background into uncovered spans; the
selection still depends on the loaded map's sky texture, so this does not yet
prove a shared cross-map resource or target behavior after sky-face removal.
Candidate010's independent binary audit reports zero serialized sky render
faces, while replacement appearance and loading remain unverified. Structural
BSP closure, PVS/content boundaries and collision may have separate requirements;
validate them independently and do not use them to justify sky render faces.

The current renderer background path is documented in [Day/night and sky](DAY_NIGHT_AND_SKY.md#shared-exterior-background-sky-implementation-candidate); source-to-compiled terrain alignment is documented in [Terrain visual culling](TERRAIN_VISUAL_CULL.md#canonical-source-to-compiled-terrain-mapping). No particular sky plane or dome is selected. Weather and time-of-day behavior remain future design work.

### Historical inspector preview readings (not acceptance)

The version006 inspector preview reports 1,445 stored / 1,755 placed faces removed
and 696 clipped, with 1,432 shared/lightmapped, 402 fragment-growth and 30 budget
retentions. These are preview measurements, distinct from compiler trial001 and
its 1,441 net stored-face reduction. Preview clipping is partial and does not
prove all buried geometry was removed from the serialized BSP.

## What we learned today: global topology is the compile basis

The requested default is the authoritative existing GLOBAL LAND/topology packet,
with a recorded source hash, version, coordinate transform and covered tiles.
Local BSP ground and generated enclosure faces are not substitutes for that
whole-map reference. Ground and seabed count as terrain; water surfaces do not.
The initial local object-face trial remained partial: deep world closure faces
and uncertain shared crossings were retained. Preserve visible terrain and
collision independently, and verify above-surface/below-contact views with
identical-camera A/B as well as numeric receipts. Missing or uncertain global
coverage must fail closed and be reported. This global-basis requirement is
pending implementation, not a claim that the partial pass completed it.

A later fresh-ABI, source-selected streaming estimate compares all 67 Seyda
candidate maps: original50/67 pass, candidates67/67 pass; worst clearance remains
1,824 B. This is a source-bound estimate gate, not emulator gameplay acceptance,
whole-world image acceptance or a shipped HDF. Shared crossing and world closure
responsibilities remain unchanged by that comparison.
### World graphics acceptance: sediment, water and sky

For this Morrowind/AmiWind exterior conversion, consult the authoritative global
topomap before building each cell/subcell. See [Terrain visual culling](TERRAIN_VISUAL_CULL.md#canonical-source-to-compiled-terrain-mapping) for the source-to-compiled mapping and [Day/night and sky](DAY_NIGHT_AND_SKY.md#shared-exterior-background-sky-implementation-candidate) for the current renderer background path.
The requested default is essentially no graphics underneath the varying actual
terrain surface. Door-entered caves/tombs load separate interior cells and are
outside this exterior stage. Only verified actual exterior openings need exceptions. Ground includes actual source sediment,
bedrock and seabed; an ocean fallback height is not evidence of any of them.
Compiler coordinates are XY horizontal with Z height: this is not a flat Z=0 cut.
Visible terrain and collision remain independently protected. Manual exclusion
zones are separate versioned plans, not automatic visibility proofs.

Preserve every existing water placement, including water on land. Do not move or
flatten water, and never use its surface as the terrain-culling occluder.

The required result keeps the CURRENT sky appearance while removing local
per-cell/per-subcell sky-enclosure render faces. Candidate010 has a reported zero
serialized sky-face count; the existing background path's appearance, map
selection, closure/PVS/collision equivalence and target cost still need
verification. Existing background buffers alone do not prove correct behavior
when a map's sky material is absent.
This exterior policy does not apply to separately loaded interior cells. Actual
exterior openings must be evidenced rather than assumed from underground interiors.

## Central Seyda Neen must remain continuously resident

The central square and its ordinary walking routes must form one continuously
resident exterior area. Crossing old cell or subcell ownership boundaries inside
that area must not reload the map, reset actors or cause repeated pauses. Separate
door-loaded interiors retain their own loading transitions. Distant exterior
areas may have separate residency, with boundaries outside the central walking
area and verified coverage of views and approach routes.

Acceptance requires walking the marked central area in both directions, including
its former ownership boundaries, while recording map-load events. The expected
count is zero after the initial central-area load. Preserve visible scenery,
water, collision, interaction, actor state and save/load behavior. Polygon export
alone does not establish resident ownership or change runtime transitions.

### Resident footprint and cost investigation

A read-only footprint probe proposes the owner-marked central polygon as the
resident core, surrounded by the existing visibility apron. The original plan
needs explicit closure and polygon validation before it can become a runtime
region. The present small rectangular ownership cores do not meet the central
residency requirement merely because their loaded coverage overlaps.

| Inspected artifact or selection | Disk bytes | Stored visual faces | Scope |
| --- | ---: | ---: | --- |
| Original complete town source | 8,724,276 | 36,757 | Entire source town; 127 BSP models |
| Original inspected subcell | 4,550,392 | 26,190 | Existing local resident payload |
| Proposed central polygon plus current apron | Not compiled | 23,988 inline faces | 114 selected inline models; world terrain and other costs still required |

The complete unculled source town does not fit the existing budget. Using the
historical target ABI profile, its BSP-only loader peak is 11,059,568 bytes,
exceeding the 6 MiB map allowance by 4,768,112 bytes before additional sprite,
actor and render-range registry costs. This is an allocation estimate, not a
measured target run. A smaller central payload must be compiled and measured
after canonical terrain culling and representation changes. Disk size is not
runtime memory. A bounded boot map can share the town filename; its size must
not be mistaken for the complete source town.

No runtime ownership layout was changed by this investigation. A fresh final
BSP, matching-ABI phase peaks and target walking/load-event checks are still
required before reporting a continuous central area as implemented.
