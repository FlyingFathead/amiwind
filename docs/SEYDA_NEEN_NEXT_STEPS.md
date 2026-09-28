# Seyda Neen follow-up register

Owner reports and requests recovered on 27 September 2026, 22:17–22:27 Helsinki.
Keep this register with the roadmap so interrupted chat messages do not lose work.
Runtime baseline: v0.0.15-dev1 / checkpoint-016.
Additional reports: 27 September 2026, 22:32–22:35 Helsinki.

## Immediate correctness and diagnosis

- [x] ~~Hammocks obstructing the ship interior route.~~ Fixed. Lower-hull structural repair delivered in checkpoint-017; owner confirmed the hammock obstruction is gone on 28 September.
- **Remaining interior defects:** minor hull flicker/glitches remain open. Preserve structural source surfaces/UVs and check the continuous lower-to-upper route. The resolved hammock obstruction is not a claim that every hull view is correct.

- **Debug camera:** already delivered XYZ + DEG horizontal yaw + P vertical pitch.
  Enable `dbg coords on`; include version, area, position and both angles.
- **Missing town-edge formation:** the owner suspects the Silt Strider port.
  Treat as a hypothesis, not a confirmed identity. Owned source audit finds the
  strider as a visible ACTI, excluded by the ordinary STAT/DOOR renderer filter.
  Compare source bounds/terrain and fixed cameras before conflating that omission
  with the separately reported formation near (235,596,29).
- **Other disappearing structures:** distinguish missing conversion coverage,
  geometry reduction, bounds, depth order and render-capacity overflow. Do not
  assume a culling-priority fix without reproducing the camera.
- **Exterior ship preservation:** v0.0.14-dev1 is `method_001`, an immutable
  appearance/conversion baseline. Keep its source, recipe and image hashes;
  new methods need separate outputs and comparisons. See SHIP_RENDERING_METHODS.md.
- **Music clicks/pops:** still reported in WinUAE. Local native counters already
  show mixer deadline misses despite zero file-read errors. Distinguish asset
  prefetch, DMA/mix-ahead, blocked game-loop work and host audio buffering.

## Local gameplay slice

1. Catalogue the complete exterior cast and directly linked interior cast. Load
   only the active scene's actors. Keep distinct placed identities for guards
   sharing one base definition. Preserve opening-state/script dependencies.
2. Add missing actors incrementally with measured geometry/cache/voice budgets.
   Existing male-human conversion is not support for all female or beast outfits.
   Prioritize ordinary exterior actors and the third town guard, then opening
   actors with the required script state. Native NPC collision is still pending.
3. Compile authored action packages and speech conditions on the host. Separate
   Hello, idle, combat/alarm and interactive dialogue. Guards have multiple source
   candidates, not one fixed line; candidates are not an unconditional shuffle pool.
   Use bounded polling, visibility/state tests, cooldowns and anti-overlap behavior.
4. Import CONT placements (barrels/boxes/etc.), then their interaction and state.
   Store contents per placed reference; scene loads must not regenerate inventory.
   Audit original respawn settings and scripts before deciding a default policy.
   Safer storage/nonrespawn overrides, if wanted, must be explicit and save-bound.
5. Load houses/offices as separate scenes. Host door tables retain source reference,
   display destination, target scene, destination pose, locks/traps/ownership and
   script dependencies. Multiple entrances require explicit reverse-link matching.
6. Opening sequence: correct lower hold, stairs, hatch, Jiub/guards, then Census
   and Excise office. The current build is a location preview, not character creation.
7. **Hatch state:** E currently loads the next scene but leaves the mesh static.
   Add open/closed visual and collision state keyed to the placed hatch; opening
   on exit must give safe deck placement beside the hole. Preserve state through
   scene reloads. Audit the source animation/pivot before choosing a baked open
   pose; a missing hatch mesh is not a completed open-state implementation.

## Shared world systems

- One game clock for dawn/day/evening/dusk/night, waiting, schedules and quests.
- Locally converted low-resolution night sky; dawn/dusk horizon gradients track
  audited sun direction. Add the cheap sun disc/blob and later moons/clouds.
- Planned `dbg sky on/off`, `true/false`, `1/0`: off restores the current starter
  sky presentation. It does not stop time, disable schedules or remove night
  gameplay. Define appearance/clock independence and test identical frozen times.
- Night guards' torches: audit source equipment/scripts and light records. Track
  ownership, equip state and ignition separately. Prototype a bounded emissive
  flame/light radius or limited dynamic-light budget, with costs measured.
  No global illumination; no global palette trick that recolors the whole world.
- Keep audio deadline work active during NPC, lighting and scene-load additions.

## Current host audit, not added native residents

The base-master 3x3 exterior audit around (-2,-9) finds 15 exterior NPC references
and 28 NPC references in directly linked interiors (including peripheral caves).
Twelve exterior references belong to the named Seyda Neen cell. The generated
private cast separates them from peripheral/dead/scripted actors and interiors.
It also preserves door, container, actor-package and ordered voice records.
These counts describe the audit footprint, not a new runtime population.

Use `tools/audit_vicinity.py --data-files ... --out /external/new-audit` to repeat.
Output is private derived game data; public source contains only the reader/tests.

## Latest playtest reports and debug request

- Implemented in checkpoint-017: `dbg scene change`, `debug scene change` and `amiwind debug scene change`:
  a popup with the available compiled scenes, arrows/Enter or mouse selection,
  Escape/Cancel back to the console. Keep direct ship/town commands.
- Owner camera **XYZ 211 447 47 / DEG 4 / P 0**, exterior v0.0.15-dev1:
  malformed arched formation near the suspected Silt Strider approach. Screenshot
  received and inspected. Identity remains unconfirmed; compare source geometry
  at this exact view instead of assuming it is the missing ACTI strider itself.
- Owner notices a performance drop since the preceding update. Reproduce with
  identical emulator settings, scene, camera, hands and fog before attributing it
  to geometry or raising requirements. Keep old checkpoint as the baseline.
- **Underwater presentation:** ordinary immersion should have a blueish tint,
  without a red damage flash. Drowning or attacks such as slaughterfish bites
  should trigger a separate red flash scaled to actual damage and the appropriate
  source-defined hurt sound. Inspect current contents tint vs damage feedback
  before diagnosing; a red water palette alone does not prove health loss.
  Test entering/leaving water without damage, submerged damage, recovery, and
  tint restoration after surfacing. This is a requested fix, not implemented yet.
- Audit the original hatch/character-generation scripts for re-entry restrictions;
  debug scene travel remains available independently of eventual story gates.

## Opening residency and lighting (owner follow-up, 22:40 Helsinki)

- Audit the authored opening script sequence before implementing it. Record each
  stage's controls, NPCs, dialogue waits, door permissions, menu handoffs and
  disabled references. Do not execute arbitrary source scripts as host commands.
- The current scene loader already releases the old world before loading the next.
  The prison interior does not keep Seyda Neen geometry resident. Retain compact
  player/quest/music state; later add inventory, object and dialogue state.
- Plan a bounded arrival exterior only if its visible shoreline dependencies can
  be preserved. A smaller intro map is not implemented; town currently loads whole.
- After the Census script's removal state, omit the exterior ship assembly from
  rendering, collision and activation on subsequent loads. This needs state-aware
  conversion/residency, not merely drawing the ship invisible. Keep debug access.
- Study the existing Quake/AmiQuake lightmap and dynamic-light paths for dim
  interiors and torches. Current ship lamps are baked static scalar lightmaps.
  Try a small measured dynamic-light budget; preserve static fallback and record
  surface-cache rebuild cost, palette visibility, frame times and audio deadlines.

## Variable exterior frame cost (owner report, 22:50 Helsinki)

v0.0.15-dev1, **XYZ -44 259 75 / DEG 328 / P -14**: owner reports heavy
slowdown in this view, while other views run smoothly. Preserve its current
geometry/textures as an exterior `method_001` reference (checkpoint-016 immutable
image/source); ship-specific method_001 remains the checkpoint-015 archive.
Use separate candidate outputs for texture/poly-count optimization. Measure
visible edges/surfaces, world time, lightmap/surface-cache churn, overdraw and
audio deadlines before concluding polygon count alone causes the choke.
Try closer coupled fog/culling first, then source-aware LOD/texture reductions.
Missing geometry cannot count as a successful performance improvement.

Silt Strider: prepare a separate low-poly ACTI conversion candidate with a retained
source silhouette and suitable texture bake. The model is not native-loaded yet.

Live visibility controls: current default remains 700 local units. Owner requested
fine adjustment: normal Left/Right steps are 10, Shift+Left/Right steps are 1;
console accepts exact whole-number values. Keep the fog table and cull distance
coupled. Low-poly/texture candidates remain separate from this runtime control.

Owner follow-up, 22:54 Helsinki: the (-44,259,75), yaw328/pitch-14 view was not
previously expensive; suspect the ship behind town. Treat as regression, not
simply a fundamentally dense view. Required diagnostic: same-camera/same-engine
ship-present vs ship-omitted visual candidate, same fog, hands, audio and hardware.
Hidden/occluded geometry can still cost traversal/transformation/raster work.
Record whether the ship contributes before simplifying unrelated town buildings.
Keep the ship/no-ship candidate separate from the deliverable and method_001.

Owner follow-up, 22:55 Helsinki: emulator may be running at a 1440p host display
size. Compare the same camera in a small window vs that output size before
blaming converted geometry. AmiWind's internal 320x200 render size is separate
from host scaling/filter/display costs. Record window/fullscreen mode, filters,
sync, host load and CPU/JIT settings with each performance report.

Owner aft-deck report, 22:56 Helsinki: **XYZ 790 -364 81 / DEG39 / P25**,
v0.0.15-dev1. Aft/deck opening still visible. Compare full source exterior
geometry and reduced output at this view before declaring it an authored hole.
Keep separate from the lower-hold structural repair and intended hatch opening.

Second reported slow view, 22:57 Helsinki: **XYZ 692 -455 66 / DEG132 / P-8**,
looking from the boat toward the same town building. Keep both approach angles
in performance acceptance; an expensive building/material path is another lead.
The exact responsible reference, surface-cache behavior and ship contribution
remain unconfirmed. Owner screenshots retained privately.

Owner narrows slow geometry to overhang/details, 22:59 Helsinki, camera
**XYZ 435 -248 37 / DEG140 / P-26**. Preserve screenshot and compare constituent
model/material surfaces, especially roof/overhang undersides and balcony details.
Do not flatten the whole building before determining whether a subset dominates.
Keep per-camera performance baselines and visual acceptance alongside counters.

Ship diagnostic now sampled at the first slow camera: 10.52 vs 12.44 FPS
with hull faces drawn/suppressed. Allocations/collision/attachments retained.
Some contribution indicated; no complete regression diagnosis. See checkpoint-017.

## Post-checkpoint-017 building reports (27 September, 23:06–23:13 Helsinki)

These reports arrived after v0.0.15-dev2 ZIP freeze. They are preserved in this
working follow-up, not claimed fixed or included in those frozen ZIPs. Exterior
geometry remains unchanged in checkpoint-017.

### Exact reproductions

Coordinates below were read from the images, rather than their imperfect OCR.

| Screenshot suffix | XYZ | DEG / P | Report |
| --- | --- | --- | --- |
| 200638 | 256 34 152 | 323 / 7 | Thin dark lines protrude left from overhead timber/wall edge. |
| 200802 | 288 42 171 | 332 / 12 | Closer view of the same protruding edges. |
| 200847 | 202 16 191 | 287 / 21 | Coordinate-only crop; no geometry evidence in this image. |
| 201024 | 267 32 181 | 347 / -14 | Upward roof/skywalk view; investigate visible structure and cost. |
| 201201 | 301 -9 257 | 23 / 39 | Elevated roof view; distinguish authored joins from conversion artifacts. |
| 201319 | 181 125 251 | 313 / 13 | Owner localizes expensive view to this building/spot, not adjacent tower. |

Keep these separate from the prior ground-level slowdown cameras. Noclip inside
an authored one-sided shell can expose its backfaces; that alone does not imply
corrupt solid geometry. Above-roof exterior views should still work, especially
for eventual levitation. Do not dismiss a normal external view as an invalid test.
Do not yet label these lines z-fighting, excessive source polygons or the cause
of the slowdown. A screenshot alone cannot discriminate those possibilities.

### Narrow host diagnostic actually completed

At player origin (288,42,171), eye offset16.4338215, yaw332/pitch12, projected six
nearby placed references from the existing owned-data export: 113826, 113827,
113883, 113825, 113824, 113829. Source-centre (-11264,-71680), scale0.25. Compared
full source triangles against the production coplanar merge plus 64-pixel UV
surface splitting. Both use a separate host triangle/depth rasterizer and the
same textures/camera. Images show the timber end without the thin protruding
lines visible in the native screenshot. At 320x200, coverage differs at zero
pixels; maximum shared depth difference is 0.00001715 local units, with no
shared pixel differing by more than0.001.

This is a bounded diagnostic, not an OpenMW screenshot, native acceptance or
proof that the complete converter is correct. It draws both face orientations,
omits BSP serialization/native edge rasterization, and includes only those six
references; palette, lighting, viewport and quantized native angles differ.
It did not reproduce the defect in the early merge/split stage at this view.
Next compare serialized BSP geometry and native face/edge clipping, including
one-sided surfaces and camera proximity. Capture stable model/reference and
surface IDs before suppressing components. Source silhouette, holes and material
boundaries remain acceptance constraints. No renderer change was made for this
new report.

Private evidence: building017-source-audit.py, source.png, merged-split.png,
comparison.json and the owner screenshots. Retain outside the public source.

### Local model counts, not a diagnosed offending model

These components are near the reported view according to placed-reference
bounds. Bounds proximity is not a crosshair hit test. Source vertex counts
include the exported mesh's split vertices; compiled faces are renderer polygons,
not original triangles.

| Source model | Vertices | Triangles | Compiled renderer faces |
| --- | ---: | ---: | ---: |
| ex_common_skywalk_01 | 396 | 236 | 192 |
| ex_common_house_tall_02 | 1338 | 958 | 546 |
| ex_common_house_tall_01 | 824 | 652 | 578 |
| ex_common_house_addon | 894 | 747 | 589 |
| ex_common_tower_thatch | 886 | 848 | 741 |
| ex_nord_house_03 | 730 | 682 | 572 |

Counts alone do not prove the frame-time culprit. Record bounded per-model
render time, submitted/visible surfaces and edges, clipped surfaces, overflow,
surface-cache churn and audio deadlines at the fixed cameras. Compare suspect
components enabled/disabled without changing CPU, fog, hands or output scaling.
Keep geometry correctness separate from the performance trial: hiding a broken
surface does not fix it.

### Reusable conversion policy to develop

1. Preserve the original recipe as method_001. Generate each candidate in a new
   directory with source hashes, parameters and a per-model change report.
2. Classify structural surfaces separately from trim. Preserve openings, walkable
   surfaces, visible silhouettes, material/UV boundaries and interaction anchors.
   Use geometry/metadata rules with recorded exceptions, not only mesh-name lists.
3. Merge only compatible coplanar connected surfaces. Bake fine planks, shallow
   beams and trim into textures where the silhouette and close inspection allow
   it; keep collision proxies independent. Never fill a doorway to meet a budget.
4. Build offline LOD candidates against geometric/screen-space error and target
   surface/edge/cache budgets. A universal percentage is not a quality guarantee:
   the ship interior already demonstrated how blanket reduction breaks structure.
   Runtime selects prebuilt levels using cheap distance bands and hysteresis;
   no mesh simplification runs on the Amiga. This selection policy is planned,
   not currently implemented.
5. Keep render and collision bounds conservative so reduced meshes do not vanish
   prematurely. Check triangle winding, degenerate faces, non-finite coordinates,
   material assignments, UV extents and unexpected face multiplication after
   export. Open source meshes are not automatically invalid solids.
6. Compare source, converted mesh and native screenshots at fixed close/far,
   doorway, underside and above-roof views. Accept only measured improvements in
   matched conditions with memory, audio and frame-time regressions checked.
   Tune budgets from those measurements; do not invent a universal safe poly cap.

### FPS follow-up

Checkpoint-017 already implements default-off `dbg fps on/off`, also accepting
true/false and1/0; `debug` and `amiwind debug` prefixes work. Bare `dbg fps` prints
its state. It uses the existing profiler time sample and about a one-second
average. It is internal game FPS, not the emulator's output refresh rate.
The frozen build draws it at the upper right; `dbg overlay off` hides it.
Owner's new preference: move it to the left (avoid overwriting coordinates), and
add `dbg show fps` as an enabling alias with optional validated toggle argument.
Those placement/alias changes are queued, not included in the frozen dev2 binary.

## Roof inspector follow-up (27 September, 23:14–23:15 Helsinki)

- Exact filenames are image(20260927-201431).png and
  image(20260927-201533).png; private owner screenshots, not public source assets.
- First camera: XYZ269 12 214, DEG341, P8. Second: XYZ292 22 214, DEG345, P7.
  Both show pointed/slender roof-edge projections near the adjacent taller roof.
  Owner suspects these details explain the localized slowdown. Hypothesis remains
  unconfirmed; test the named surface group at these cameras as well as street level.
- Working idea: **Jagged Edge Reducer (TM)**, an offline detail-cleanup candidate.
  First establish whether a spike exists in the source or arises during BSP/native
  rendering. Repair conversion/raster defects where introduced; do not disguise
  them by blindly shaving geometry. For authored decorative jagged trim, compare
  an intact-silhouette low-detail replacement with detail baked into its texture.
  Preserve door openings, roof boundaries/joins, collision and method_001. Thinness
  alone is not a deletion rule: rails, doorframes and structural beams can be thin.
- Candidate rule should depend on projected error at designated near/far views,
  not a fixed world-space triangle area. Keep source and rejected candidates,
  report face/edge/cache changes, and accept only measured native frame-time gains.
  This is a proposed host-side optimization pass, not anti-aliasing or an added
  per-frame Amiga workload. Not implemented in checkpoint-017.

## Building culling investigation 001 (after checkpoint-017)

Owner report at XYZ249 40 227 / DEG315 P25 linked roof-edge popping to culling
cost. Native fixed-camera A/B with `dbg cull 1` and0 reproduces the lines in both
states, also at XYZ288 42 171 / DEG332 P12. HUD-excluded scene crops are identical
(zero changed pixels of166352 at each pair). This rules out the added fog-distance
cutoff as the cause of the observed lines at those sampled poses; it does not
rule out frustum/backface/BSP clipping or depth-ordering defects. No new fix yet.
Buildings remain resident: this culling path performs no asset unload/reload.
Zero renderer edge/surface overflow in the completed run. Read-only BSP audit
found no broken edge loops, non-finite vertices/planes or reversed winding under
its checks. Next isolate native clipping/sorting and separately measure per-model
rendering/cache costs. Do not turn off useful culling globally or assume the
visual artifact proves the performance culprit. Details and private evidence:
AmiWind-building-culling-audit-001; this is not a new playable checkpoint.

## Owner checkpoint-017 playtest, 27 September 23:28 Helsinki

v0.0.15-dev2 prison-ship interior: owner reports improved appearance, but lower
hull flicker from the pictured angle and performance dips. Screenshot:
image(20260927-202651).png; coordinates are not enabled, so no exact pose is
claimed. Preserve it privately and reproduce after restoring the workspace.
Structural shape repair did not certify all depth/clipping or performance issues.
Intro/UI/font work remains the next planned milestone; recovery ZIPs take priority.

## Latest owner playtest and default decision, 27 September 23:29–23:31 Helsinki

Owner says the previously slow town-building view no longer lags in dev2.
Screenshot image(20260927-202925).png has no coordinates. Record this as an
owner-reported improvement with unconfirmed cause, not a proven targeted fix;
checkpoint-017 exterior BSP is byte-identical to checkpoint-016. The fog table
rebuild was optimized, but that runs on distance changes, not every frame.

Owner chooses450 local units as the default fog/cull distance from the NEXT
build onward. Released dev2 still defaults to700; `dbg fog distance 450` works
now. Next implementation must update renderer/config/UI reset/docs/tests together;
keep700 available as a selectable value and preserve existing frozen packages.
Do not falsely describe the currently shipped binary as already defaulting to450.

## Final recovery handover update, 27 September 23:32–23:35 Helsinki

The latest chosen NEXT-build fog/culling default is **540**, superseding the450
proposal above. Current frozen dev2 still starts at700; live command:
`dbg fog distance 540`. Update config/runtime/menu reset/tests/docs together in
the next build, preserving the old packages and selectable distances.

New persistent rock/Silt Strider-port report: XYZ337 643 34, DEG304, P-16,
v0.0.15-dev2, image(20260927-203433).png. Owner screenshot shows a projecting
terrain/rock section with missing-looking lower geometry; exact source identity
and cause still require comparison. HUD reads28.4FPS in that one screenshot,
not a benchmark. Do not conflate the already-known omitted Silt Strider ACTI
with proof of this formation's geometry cause. Backup first; keep this open.
