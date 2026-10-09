# First-person geometry and sprite experiment

<!-- contents start -->
## Contents

- [Maximum-extension repair candidate: 2026-10-06T15:18:15+00:00](#maximum-extension-repair-candidate-2026-10-06t1518150000)
- [Projection follow-up: 2026-10-06T15:03:42+00:00](#projection-follow-up-2026-10-06t1503420000)
- [RC1 maximum-extension hand audit: 2026-10-06T14:46:55+00:00](#rc1-maximum-extension-hand-audit-2026-10-06t1446550000)
- [Combat inspection candidate: 6 October 2026](#combat-inspection-candidate-6-october-2026)
- [FPV combat action creation pipeline: RC1 baseline](#fpv-combat-action-creation-pipeline-rc1-baseline)
- [Unarmed right/left sequence request: 6 October 2026](#unarmed-rightleft-sequence-request-6-october-2026)
- [HAND-PUNCH-COVERAGE-29: exposed forearm during punching in RC1](#hand-punch-coverage-29-exposed-forearm-during-punching-in-rc1)
- [Coverage gate before adopting sprites generally](#coverage-gate-before-adopting-sprites-generally)
- [Race and sex catalogue candidate](#race-and-sex-catalogue-candidate)
- [Connected surfaces before a smaller triangle budget](#connected-surfaces-before-a-smaller-triangle-budget)
- [Detailed-model depth arithmetic candidate](#detailed-model-depth-arithmetic-candidate)
- [Investigation: first-person hands rendered as sprites](#investigation-first-person-hands-rendered-as-sprites)

<!-- contents end -->

## Maximum-extension repair candidate: 2026-10-06T15:18:15+00:00

The next source candidate now contains a fist-viewmodel-only clipping repair.
It preserves original models, UVs, animation, perspective and ordinary depth
bias; world entities, custom viewmodels and torch models keep their prior path.
The effective fist near distance becomes1.25 units without changing the world
near plane, and newly visible depth values saturate within the signed range.

Actual-C sanitized rendering passed20appearances x28frames x4pitches, totaling
2,240frames. Every sampled maximum-extension frame has zero uncovered near-cut
pixels. Four ambiguous female components occur offscreen; the separate existing
female wrist-seam issue remains open. The asset-free regression passes the
candidate and fails original code. Target build, combined suite and native visual
acceptance remain pending. First packaged/fixed release remains none.

## Projection follow-up: 2026-10-06T15:03:42+00:00

Actual-C alias projection of a sealed RC1 Nord male model at source frame25
shows 1,522 uncovered near-plane cross-section pixels at pitch0 and 2,641 at
pitch-39 in the diagnostic camera. The encoded mesh is closed. Small view-local
offsets did not eliminate the gap; lowering the near plane from5 to3.25 worsened
coverage, so neither is accepted as a repair. These measurements use a synthetic
camera, not an identified match to the owner's screenshot. Native confirmation
and a scoped repair remain pending; no first fixed version is assigned.

## RC1 maximum-extension hand audit: 2026-10-06T14:46:55+00:00

All 20 inspected fist models match the RC1 catalogue. At maximum right-hand
extension (source frame25 of28), encoded models have no unmatched boundary edges.
The apparent source boundary rings are paired wrist/forearm seams, not an
established open proximal arm. Some female models show quantization separation
in other frames; that is a separate possible seam issue.

At frame25 the standard five-unit near plane intersects 20 triangles in each
of six sampled appearances. The alias clipper trims triangles without creating
a cross-section cap. Camera/near-plane exposure is therefore a leading hypothesis
for the reported see-through forearm, not yet a proven visible cause or repair.
The owner's screenshot still does not identify an exact race, sex or frame.

Next compare actual renderer coverage at idle, adjacent and maximum poses using
small view-relative placement changes. Preserve hand proportions, torch grip and
ordinary clipping. A global near-plane reduction is not accepted: signed depth
storage has its own range constraints. Do not cap every source boundary or claim
the new combat inspection room repairs the defect. First fixed version remains
none; a visible target check is required.

## Combat inspection candidate: 6 October 2026

`dbg combattest` is implemented in the next source candidate, not published RC1.
It reuses the gallery's empty 4096-unit floor without loading its catalogue actor
or footprint. This is a large finite BSP floor; `dbg combattest center` resets
the inspection position. It is not an infinite-world generator.

Normal Attack punches into air; F draws/lowers the current race/sex hands.
`dbg combattest idle`, `draw`, `lower` and `punch` start the corresponding existing
action. F1 opens help; Ctrl+X or `dbg combattest exit` restores the captured game.
The HUD reports hand state/frame. Timing comes from the valid source scene;
missing timings or floor refuse entry instead of hiding unavailable hands.
Four focused Linux Docker checks pass, including actual gallery routines,
compiled hand rules and catalogue staging. Target visual acceptance is pending.
No punch-hole repair, left/right sequence, pose editor or sprite conversion is
claimed by this initial inspection mode.

## FPV combat action creation pipeline: RC1 baseline

Requested 6 October 2026; recorded 2026-10-06T13:34:07+00:00. Keep the RC1 race/sex fist models
as immutable inputs for an adjustable first-person action pipeline. This is
new conversion/preview work, not an implemented editor or a shipped correction.

The pipeline should retain original animation/mesh identity, expose bounded
camera-relative offsets and per-action/per-frame adjustments, and export a
fresh candidate plus a repeatable profile. Preview idle, draw, lower and the
entire punch sequence at the actual viewport/FOV/near plane, with exact frame
selection and contact sheets. Compare the unchanged baseline side by side.

The initial target is the exposed camera-near forearm at maximum extension.
Moving the arm toward the player's viewpoint is a requested framing candidate;
measure which axis/direction improves coverage before adopting it. Distinguish
UV loss, open geometry, face culling and near-plane clipping. Repositioning alone
must not be called a topology repair or accepted if another pose opens a hole.
Retain surface connectivity and validate any explicit cap/stitch separately.

Add right/left unarmed sequencing using verified source animations or an
explicit derived-animation profile. Preserve held equipment and race/sex
appearance. Reuse decoded source data and profiles to avoid repeated full
conversion; load only the selected runtime model. Record triangle/vertex count,
model/cache bytes and render cost alongside the coverage result. Preview tools
and profiles can be public; original/converted game assets remain locally owned.
The existing sprite baker's neutral projection is a framing aid, not acceptance
of the actual game renderer's clipping or lighting.

## Unarmed right/left sequence request: 6 October 2026

Recorded 2026-10-06T13:23:09+00:00. Successive accepted bare-knuckle attacks should alternate
**right, left, right, left**. The current converter samples only
`handtohand: chop start` through `handtohand: chop large follow stop` as one
ten-frame punch clip; alternating hands is not implemented in RC1.

Inspect the owned first-person animation catalogue for authored left/right
motions before choosing their conversion. Do not describe strict alternation
as verified original-Morrowind behaviour merely because it is requested here.
Add a second attack only when its appearance, timing and fallback contract are
explicit; count one accepted attack per input and avoid switching sides midway
through a punch or a cell handoff. This is an animation requirement, not a claim
of implemented combat damage or combo rules.

The owner further localizes HAND-PUNCH-COVERAGE-29 to **maximum arm extension**.
Inspect that pose and adjacent/interpolated frames on both arms. Fix visible
forearm coverage before accepting the new sequence. Preserve race/sex appearance,
held-item behavior and a bounded selected-model working set; measure any extra
frame/cache cost rather than retaining all race animations in RAM.

## HAND-PUNCH-COVERAGE-29: exposed forearm during punching in RC1

Recorded 2026-10-06T13:18:37+00:00. The playtester says RC1 fists are **substantially better**,
but reports visible background/open coverage in the punching arm. The marked
image identifies the camera-near forearm region, not the knuckles. Preserve the
improved appearance while repairing that defect. The race/sex and exact punch
frame are not established by this screenshot; do not inherit a race from an
earlier torch report.

**Open; final-release gate.** Check the delivered model's sampled punch frames,
interpolated poses, triangle winding/back-face culling, and near-plane clipping.
The source-topology audit deliberately retains authored open ends and reports
their boundary edges. Its zero-new-gap result proves source preservation, not
that every visible FPS surface is closed. This is a concrete inspection lead,
not attribution of the pictured defect to one particular boundary.

If an exposed attachment end is confirmed, generate a small explicitly labeled
cap or stitched continuation for that end, retaining the source surface audit
separately. Do not blindly cap every open loop, bridge fingers, reverse hidden
faces, or disable culling globally. Validate connectivity, orientation, animated
coverage, texture continuity and target cost across idle/draw/lower/punch for all
supported race/sex models and relevant camera pitches. Visual acceptance of the
fist shape does not close punching or the separate torch-grip issue. Model and
renderer maintenance own this investigation.

The existing 3D converter and model are retained. **3D remains the default.**
Select `build.sh --hands 3d` or `build.sh --hands sprites` at build time. The
engine and image builders accept the same flag and reject mismatched modes.
There is no in-game mode switch. The optional private `experimental/` HDF is
for comparison, not a replacement with complete equipment coverage.

Both routes use the same locally sampled Nord-male unarmed model: 311 triangles,
28 poses (8 idle, 6 draw, 4 lower, 10 punch). The 3D MDL is 252,612 bytes. The
sprite baker rasterizes each pose on the host at 160x100 and packs opaque row
spans into a 22,426-byte AWS1 file. Runtime checks bounds once and draws indexed
pixels without blending or world-depth tests; no per-frame disk read.

The compile-time sprite path uses the existing animation frame state, avoiding
the hand-model cache load. The 3D source asset remains on disk. Some sampled
draw/lower/punch poses move fully offscreen; those empty baked frames are recorded
in the report and need animation/framing refinement. This prototype is not a
complete fix for the owner's disappearance report.

First-person drawing now occurs after world fog; 3D hand ambient has a minimum
brightness floor. This prevents the world fog pass from obscuring the overlay,
but it does not prove the original flicker cause or eliminate all model/texture
issues. Native screenshots still warrant owner comparison. Sprite lighting is
a fixed neutral bake and does not yet follow the dim interior.

## Coverage gate before adopting sprites generally

Bake every required motion for the selected race/body, equipment, weapon/spell
and handedness before relying on a sprite set. Race stays fixed during play,
but armor/clothing/weapon appearance can change. Use a complete appearance key
for caching and invalidate affected frames on equipment change. Missing coverage
keeps that target on the 3D build until an explicit fallback policy exists.

Keep A/B cameras, heading, pitch, viewport, draw distance and emulator settings
identical. `hands_ms` is separately profiled; aggregate routes include hidden
hands and console time, so they are not per-visible-frame speedup measurements.
This checkpoint tests both builds functionally, not physical-Amiga performance.


## Race and sex catalogue candidate

The optional 3D catalogue selects owned skin BODY records for the player's race
and sex, rather than assigning Nord arms to every character. Selection prefers
first-person skin, then the same sex's third-person arm parts; female records
may fall back to the same race's male first/third-person arms. It never borrows
another race's records. This follows the arm fallback order in
[OpenMW's body-part selector](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwrender/npcanimation.cpp).
Authored records can legitimately share a mesh: the Nord male hand record uses
an Imperial hand mesh, with Nord wrists and arms. Distinct race IDs do not imply
that every underlying mesh is unique.

`tools/prepare_hand_catalog.py` generates male/female pairs for every playable
RACE record from locally owned data, including matching carried-torch arms.
Run conversion inside the documented Linux Docker builder. The data directory,
palette and fresh output directory must be outside this source checkout:

```sh
python3 tools/prepare_hand_catalog.py --data-files /owned \
  --palette /assets/id1/gfx/palette.lmp --out /output/hand-catalogue \
  --topology reduced
```

The builder runs the catalogue as its default `hand-catalog` stage with `--topology source
--runtime-palette` (the image's final palette) and the image step installs it after the sky
palette bank; that output is byte-identical to what v0.0.31 ships (BUILD-HANDS-NOT-BUILT-32).

The existing reduced profile remains the tool's own default. `--topology source` is an
explicit authored-topology candidate; it does not synthesize racial variants
by subdividing the Nord mesh. Converted models and textures remain local owned
assets and are never part of the public source export.

Install the paired `progs/hands/` models, `gfx/hand-models.awh` catalogue and
matching `gfx/hand-torch.awt` together. Keep the original `gfx/torch.awt` for
legacy models and guard emitters. Missing or malformed catalogue emitter data
disables the optional pairs; fallback always restores legacy model and emitter
timing/anchors together. AWH1 is bounded to 32 entries. The renderer
selects only the current pair, preserves the 28-fist/8-torch frame contract and
resets model pointers before map memory is released. Absent, malformed, missing
or wrong-frame-count pairs fall back together to `v_nord.mdl`/`v_torch.mdl`.
Keeping the catalogue absent retains the legacy path. Sprite hands still use
their existing baked appearance; this catalogue applies to 3D hands only.

Race selection, malformed-catalogue handling, frame preservation and paired
fallback have focused Linux Docker fixtures. Representative owned human/beast
conversion has been checked. All 20 playable race/sex pairs now complete with
matching fists and torch models. One bounded owned-data cache is shared during
catalogue generation; a representative cached conversion remains byte-identical
to its standalone output. A private native hand-only overlay selected visibly
distinct Argonian male fists through the actual character choice and ordinary
demo playback. The post-registration Nord character showed live punches and
torch on/off with matching arms. Live beast punching and torch use remain
unverified because that fresh character-creation scene correctly restricts
combat before registration. Source punch windup still moves below the viewport;
the general punch framing/self-occlusion report remains open. These candidates
do not change the default.

## Connected surfaces before a smaller triangle budget

Hands are the first implementation target. NPC conversion must later adopt the
same quality gates rather than generating another large asset set now.
`tools/hand_geometry.py` preserves authored face connectivity and sampled vertex
trajectories, baking repeated UV rectangles and any vertex colour gradients
without moving their geometry. Its automatic surface oracle ignores texture
vertex copies only when their complete animated trajectories coincide. It
rejects missing/reversed faces and seams that separate in any sampled pose.
Authored open sleeve ends are recorded, not filled with invented triangles.

`tools/hand_seam_reduction.py` is a conservative reduction prototype, separate
from the selectable conversion profiles. It locks all authored shape boundaries
(including material, UV and joint splits) and non-manifold edges. Interior edge
collapses must satisfy the manifold link condition; preserve boundary edges;
avoid duplicate faces; and preserve orientation, area, UV orientation and
bounded displacement across every exported animation sample. The surviving
endpoint keeps its exact source trajectory, UV and tint. No nearest-face motion
transfer, independent seam movement or hole filling is permitted. If the budget
cannot be reached safely, the report records the achieved count and refusal.

For the measured Nord fixture, the authored model has 1,092 triangles, 752
vertices and 245,736 bytes. The conservative 0.5-unit/0.125-UV trial retains
834 triangles, 623 vertices and 225,612 bytes; it does not meet the 480 goal.
Both retain the same 40 welded authored open boundary edges, with no new edges.
The 834-triangle trial subsequently failed the stricter all-pose coverage oracle:
several poses lost 2-7 interior pixels. It is rejected as a default candidate.
An optional projection-lock helper also protects sampled silhouette/near-plane
vertices and quantization extrema; its outputs still require the coverage gate.
The existing 311-triangle profile transforms 933 vertices because its texture
atlas duplicates vertices per face. Triangle count alone therefore does not
predict renderer cost.

Before adopting a reduced model, automatically compare all exported poses with
the authored reference: boundary trajectories, connected components, winding,
projected interior coverage, silhouette, texture seams and near-plane clipping.
Native idle/draw/lower/punch and torch toggles must then pass with a matching
engine, fixed camera and measured memory/rendering cost. Topology checks alone
do not prove absence of self-intersection or good appearance. Preserve the
legacy profile and reject any candidate with a newly visible opening, even if
its face-count target was met. Apply these same gates to future NPC reduction;
do not silently cap or stitch an intentional authored opening.


## Detailed-model depth arithmetic candidate

The authored-detail models exposed a thin-triangle inverse-depth gradient that
exceeds signed 32-bit range even when every covered pixel's depth is in range.
The C alias span path now converts and steps those intermediate values with
defined unsigned arithmetic, retaining its existing span layout and integer
pixel loop. This is supported by a wider-arithmetic reference, rather than
treating suppression of an overflow diagnostic as correctness.

The public synthetic fixture compares every framebuffer and depth-buffer byte
for 168 skinny-triangle and near/screen-clipping cases, including an occluding
surface. The owned catalogue check covers all 720 poses of the 40 models; the
reference reports no active pixel outside the representable depth range and
matches the candidate exactly. The original model's 28 outputs remain
byte-identical. The old span code fails the synthetic overflow regression.
AddressSanitizer, undefined-behavior and float-cast checks pass. The 68040/FPU
translation unit compiles without warnings; its object grows by 216 bytes.

On the unchanged earlier engine, a complete 4,447-frame replay completed at
49.1 emulated FPS with the authored Nord model and 49.9 with the original model,
with no surface or edge overflow. Session hand counters average 0.241 and
0.182 ms per frame respectively, but include differing console/live-map delays;
they are not isolated rendering costs. These capped emulator measurements do
not establish physical-Amiga performance. The corrected depth path subsequently
completed the same 4,447-frame demo from the title screen at 49.5 emulated FPS,
returned normally at EOF, and rendered the bounded race/punch/torch samples
above without surface or edge overflow. This is limited native acceptance,
not a complete integration or physical-Amiga performance claim. The reduction
and catalogue defaults remain unchanged; broader live beast and punch-quality
acceptance remains pending.


## Investigation: first-person hands rendered as sprites

Requested on 6 October 2026. Evaluate whether transparent, pre-rendered hand
frames can preserve the original fingers and torch grip better at the target
resolution and cost. This is an investigation, not a replacement selected for
RC1. Continue the current connected-mesh and animation acceptance checks.

- Build a reproducible conversion catalogue keyed by source identity, race,
  sex, left/right hand, equipment state, animation, frame and capture settings.
  Cover idle, draw, lower, punch and torch poses, including both beast races.
  Record source hashes, dimensions, crop bounds, pivot and timing per frame.
- Evaluate an OpenMW-based offline capture path using owned game data. First
  establish whether the chosen capture path provides a clean alpha channel;
  do not assume ordinary screenshots contain one. If necessary, investigate
  a separate mask pass or dedicated offscreen renderer using the same authored
  models and animation. Test edge halos and partial coverage after palette
  conversion. Ship the conversion tools and catalogue schema publicly, without
  original or derived game artwork.
- Convert captures into the runtime palette and transparency representation,
  with stable wrists, camera framing and frame-to-frame alignment. Keep the
  flame, embers and dynamic illumination separable from the baked hand image.
  Evaluate how local lighting, torch on/off, view bob, pitch and screen clipping
  behave; a baked image must not become permanently daylight-lit at night.
- Compare the current mesh against a bounded sprite prototype using matching
  poses. Measure visible silhouette and seams, frame timing, conversion cost,
  compressed disk size, decoded frame RAM, peak working set and read latency.
  Use a bounded cache and prefetch upcoming frames; reject visible stalls or
  audio interruptions. More animation/equipment variants must not imply loading
  the entire catalogue into Amiga RAM.
- Preserve the mesh profile for A/B and rollback. Choose a default only after
  native standing, walking, punching and torch tests across supported race/sex
  combinations. Sprite conversion has not yet been implemented or validated.
