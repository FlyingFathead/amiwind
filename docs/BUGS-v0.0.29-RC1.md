# v0.0.29-rc1 playtest issues

## Current RC1 regression checkpoint: 2026-10-06T15:03:42+00:00

Delivered playtest remains **v0.0.29-rc1**. The later combined source passed
1,046 checks (four documented skips) and its Amiga build, then underwent a
bounded FS-UAE check. Passing those gates did not close every reported bug.
No subsequent package or first shipped fixed version is established below.

| Issue | Current evidence and state | Next acceptance gate |
| --- | --- | --- |
| [BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) | Open, major partial interior geometry/collision failure. 31 audited source meshes retain all 12,913 visible triangles in export; 62 structural placements retain area/bounds in the BSP. No cause or fix proven. | Trace BSP/runtime visibility and collision at damaged poses and intact upper route. Apply any repair only to Temple. |
| LIGHT-EXTERIOR-JUMP-29 | Empty versus unused lightdata cause isolated; candidate passes six focused checks. Native fixed-engine arrivals to sn037/sn031 were captured. | Ordinary walking across the boundary both ways at fixed clock remains pending. Arrival captures do not close traversal. |
| HAND-PUNCH-COVERAGE-29 | Open maximum-extension forearm hole. Closed encoded meshes can expose an uncapped near-plane cross-section in actual-C projection. Small offsets and lower near plane did not solve it. | Scoped repair across punch/adjacent poses, then native visual acceptance; preserve improved fists and torch grip. |
| [DEBUG-GALLERY-TIMING-29](bugs/DEBUG-GALLERY-TIMING-29.md) | New candidate defect reproduced natively in combat/torch rooms: hands unavailable due to invalid animation timing. Pre-activation callback incorrectly requires active server. Regression fails before repair; six focused checks pass after the narrow fix, with no skips. | Full candidate gates, then native hands/punch/torch/state-return checks. |
| TORCHTEST-DARKNESS-29 | Separate open candidate defect. Zero light samples still show dim gray floor because palette generation enforces a 15% minimum. | Room-scoped darkness policy and actual-palette native off/on comparison; preserve ordinary scenes. |
| INTERIOR-LIGHT-29 | Building-only default1.2 implemented. Native Census fixed-view gain observed; cave reports effective1.0 at both settings. Cave views differ by28 of158720 sampled pixels; no exact-image equality claim. | Next-package fresh/saved setting and broader building controls. Census static NPC sampling remains a separate open issue. |
| CENSUS-DOOR-STUCK-29 | Opening hull overlaps reported local65,52,65. Source reproduction and five guard tests pass. | Native blocked/clear activation and return/save cases; no shipped fix. |
| CONSOLE-WHEEL-29 / UI-OPTIONS-WRAP-29 | Five wheel and seven menu endpoint checks pass for candidate repairs. | Native boundary/reverse-scroll checks; not owner-accepted in a later package. |
| AUDIO-ENTER-29 / AUDIO-LOAD-29 | Both remain open. Nonzero native menu music is not continuity acceptance. Smaller read chunks help one synthetic load rate but not every rate. | Exact guard Enter and ship-to-deck capture with active music on target. |

Owner-confirmed RC1 positives remain scoped: appearance-screen entry music,
Go back/Choose borders, substantially improved fists, and tested torch-to-NPC
response. They do not close the separate reports above. Full coordinates,
reproduction notes and follow-up requests: [RC1 playtest ledger](RC1_PLAYTEST_LEDGER.md).

Consolidated RC1 reports, coordinates and scoped positive observations: [RC1 playtest ledger](RC1_PLAYTEST_LEDGER.md).

## Post-RC1 combined gate: 2026-10-06T14:38:14+00:00

The next candidate passes **1,046 Linux Docker checks**, zero failures/errors,
and four documented skips: three Windows-only checks and the JavaScript inspector
check requiring Node.js. The actual procedural torch-room compiler/hull check ran.
The Amiga 68040 build, binary checks and source/ABI binding also pass. Engine
SHA-256: `3c86b014ad7fadcf3636b34567b2cc63ddd1a6674916387f08eb9f0df6f9aba4`.

The first combined run failed three tests and one source-binding check. Two
older isolated loader fixtures omitted the new loading-music state declaration;
the memory-policy validator still pinned the old loader source; new default-config
comments contained semicolons, which the command buffer splits before stripping
comments. Added the missing fixture globals, reviewed the loader diff, updated its
binding and replaced comment semicolons. The reviewed loader change only bounds
music-active read sizes; edge allocation/rendering code remains unchanged.
The Amiga binary had linked on the first attempt, but its final binding validation
failed and was not counted as an accepted build. The rerun passes both gates.

This candidate includes the effects75% default, nonwrapping option selection,
console-wheel dispatch correction, Census door guard, exterior lightdata fallback,
building-only interior brightness, torch style2/strength and combat/dark-torch
inspection scenes. Individual target/owner acceptance remains separate. Native
validation uses fresh private copies; **published v0.0.29-rc1 remains unchanged**.
No shipped fixed version is assigned by these source/build results. Temple geometry,
maximum-punch hole, torch fuel, full audio and wider world acceptance remain open.

## RC1 follow-up: building brightness and isolated inspection scenes

Recorded 2026-10-06T14:29:39+00:00; next candidate after v0.0.29-rc1, not in the published RC1.

- `dbg interiorluma [factor]`: archived `aw_interiorluma`, default 1.2, bounded
  0..4. An explicit reviewed list of 55 buildings is eligible; caves, tombs,
  the ship, unknown maps, exteriors and the dark torch room remain at 1.0.
  The command without a value reports configured and effective values. Scale
  static surface/actor samples before dynamic light; invalidate cached surfaces
  immediately. Existing palette/clamps limit the visible change. Saved overrides
  remain. Eight focused Docker checks pass with the actual cvar parser/writer,
  finite/invalid values, exclusions and unchanged dynamic-light contribution.
- `dbg combattest`: isolated empty gallery floor, current character's hands,
  ordinary attacks plus idle/draw/lower/punch/center/help/exit controls. The
  existing floor is bounded, not literally infinite. This tool does not repair
  the maximum-extension forearm hole or introduce an alternating punch combo.
- `dbg torchtest`: separate dark enclosed room, empty or one fitting existing
  NPC, normal torch controls and captured-game return. Seven focused Docker
  checks pass, including the actual compiled room's zero lightmaps and standing
  collision hull. Ambient/baked room light is zero; existing hand/UI visibility
  is separate. A target-palette room and native off/on acceptance remain required.

Validation incidents are retained: initial minlight1 compilation omitted the
lighting lump and was correctly rejected; compile with allocation-level minlight
then zero every lighting byte and metadata, checking valid nonempty samples.
A copy made during renderer integration lacked the new policy header; the final
focused run used a complete immutable snapshot. Two luma fixture linkage errors
were repaired; final review also replaced a substitute parser with the real
Quake parser and corrected invalid raw-cvar text handling. Source preflight
exposed inherited whitespace in newly touched renderer code; whitespace-only
cleanup passed the rerun. No published artifact was changed by these attempts.

Combined full-suite, Amiga-link and FS-UAE acceptance are tracked separately.
Do not close Temple geometry, Census static character sampling, torch fuel or
hand topology based on these inspection tools. **First shipped version: none.**

## RC1 Seyda Neen brightness discontinuity: cause isolated

Recorded 2026-10-06T14:18:00+00:00; affected build v0.0.29-rc1; introducing version unknown.
Walking between some Seyda Neen regions causes an abrupt brightness change
without a torch. The owner did not observe it on the later open-country route.
The first reported bright region is **sn031**, not sn039. Retain the corrected
identity when comparing geometry or attempting the original reproduction.

The sealed sn037 map contains an unused lighting lump; sn031 omits the lump.
Their overlapping geometry/material evidence matches across 29,834 referenced
polygons and 626 world polygons. The renderer nevertheless took different
paths: absent world lightdata selected full brightness, whereas an unused lump
selected the ambient path. This affects world surfaces and actor light samples.

A bounded FS-UAE-in-Docker diagnostic confirmed ambient128 versus actor sample
255 on the empty-lump map, with the same clock, palette, fog state and gamma,
and no active torch/dynamic lights. These observations used different cameras;
they are not a same-camera pixel test or an accepted walking-boundary repair.

The next-candidate correction makes both lump cases follow ambient/dynamic
lighting on validated AmiWind exteriors. Explicit fullbright and legacy-map
fallback remain. Six focused Docker checks pass, including 32 actual-renderer
empty/unused-lump pixel pairs, alias samples and dynamic/baked/legacy controls.
The narrow change is integrated with the separate torch-strength work; the
combined candidate still requires its complete checks and native traversal.
The guard uses the existing validated exterior sky state; missing/invalid sky
assets retain the compatibility path and are outside this tested configuration.

Retest the reported shack crossings in both directions with fixed clock,
torch off/on and ordinary walking, then check other affected Seyda regions and
the open-country control. This correction does not change map subdivision,
geometry, texture brightness or interior lighting. **First fixed version: none;
status: source-tested repair candidate, target acceptance pending.**

Temple scope update: some walls/ceilings are intact; upper area and stairs look usable on the owner-tested route. Broken lower/other sections remain a major geometry/collision defect. [Detailed evidence and pipeline audit](bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

## Balmora Temple geometry/collision report: 6 October 2026

**[BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md): open, major,
final-release blocker.** RC1 WinUAE playtesting found multiple missing walls,
floors and structural connections; the player can accidentally pass through.
Primary reported local position: **1063,1048,3700**, heading E076, pitch65;
additional captures span game05:22 to06:11. Cause and introducing version are
unknown. No repair candidate or shipped fixed version exists yet. Preserve
visual and collision regressions together and verify the repair in FS-UAE/Docker.

## CONSOLE-WHEEL-29: scroll limits trigger unbound-message feedback

Recorded 2026-10-06T13:48:58+00:00; owner report: v0.0.29-rc1 and earlier versions, WinUAE,
F10 debug console. Earlier introducing version is unknown. Scroll DOWN to the
newest line and continue: repeated MWHEELDOWN/MWHEELUP unbound warnings appear
and usable scrolling breaks down. The lower boundary is owner-reproduced;
the upper boundary was suspected and is covered by the source regression.

Cause: `Key_Event` prints an unbound-device-key warning before deciding whether
the console or another UI consumes that key. Every wheel tick can append output
even though `Key_Console` already clamps both ends correctly. At the newest line
those new messages are immediately visible. This is input dispatch/output feedback,
not evidence of wheel hardware failing or an exhausted scrollback allocation.

Next-candidate correction moves the warning into the actual game-binding path.
The existing keymap fixture exercises both limits, reverse scrolling, forced
console, empty/null/bound keys, game bindings and release events. Five focused
Linux Docker checks pass; the expanded regression fails against the unchanged
RC1 source on the unwanted warning. No WinUAE acceptance or shipped fix yet.
**Fixed: N; first fixed version: none; candidate: next build after RC1.**

## RC1 owner torch follow-up: 6 October 2026

Recorded 2026-10-06T13:48:58+00:00. Owner reports NPC illumination from a carried torch now
looks reasonably good on the tested route. Preserve this scoped positive
result; it does not close Census static interior lighting or every NPC case.
The remaining request is stronger useful light on nearby ground/walls, farther
forward and around player/NPC torch holders, with bounded falloff and light count.

The owner prefers flame type **2, brightbase**, and explicitly requests type 2
or 3 as the new default. The next candidate will use 2; existing saved preferences
should remain effective. Type 3's sparks/embers were not visible to the owner,
so spark visibility remains unaccepted. In RC1 the bright flame core is shared
by player and supported guard torches; the extra spark pass is player-only.
`dbg torch flame` without a value already reports the current setting. It does
not change illumination radius or all stationary world-fire effects.

Implement a separate archived local-light strength control and console query/set
alias. The requested initial candidate is 0.7 on a normalized 0..1 control, not
a verified photometric equivalence to daylight. Preserve the accepted default
NPC response and test surface contribution separately. Radius, flame appearance,
light strength and admitted light count must remain independently understandable.

**TORCH-FUEL-29: missing unlit/fuel state.** RC1 draws a lit torch and does not
consume fuel or burn out. Track held/equipped state separately from burning state;
retain original item identity and only a compact fuel/state override for changed
items. Prototype bounded integer remaining-time units plus packed flags, then
measure alignment, inventory/save overhead and update cost before choosing a
format. Source light duration and zero/negative semantics still need verification;
do not invent duration from appearance or implement one full entity per item.
Test equip, extinguish, relight if supported, burnout, save/reload and area changes.
Pending design/implementation; first fixed release none.

**Dark torch inspection requested:** `dbg torchtest` should use an absolutely
dark, separate space with no daylight or ambient contribution, nearby surfaces
and an optional catalogue NPC. Reuse gallery entry/return machinery, not its
daylit environment. Compare fixed pose/time with torch off/on, radius and strength;
preserve the player's previous equipment, game state and scene on exit.
This is requested next-candidate work, not a command shipped in RC1.

## RC1 comparative traversal feedback: Balmora and Seyda Neen

Owner playtest, 6 October 2026; recorded 2026-10-06T13:48:58+00:00: Balmora feels smoother than
Seyda Neen, with very short loads even when running through its streets. More
open fields also felt acceptable on the owner's tested route. Preserve these
as subjective route-specific results, not measured timing or whole-world approval.

The owner suspects Seyda Neen's sub-cell count/partitioning. Compare equivalent
routes for crossing frequency, resident/transition RAM, geometry, entities,
load duration, audio continuity and frame time before attributing the difference.
Roadmap follow-up: review town partitioning **after LIGHT-EXTERIOR-JUMP-29**.
Fewer cells must not sacrifice Amiga reserve or hide the brightness discontinuity.

## HAND-PUNCH-COVERAGE-29: exposed forearm during punching in RC1

Recorded 2026-10-06T13:18:37+00:00. The playtester says RC1 fists are **substantially better**,
but reports visible background/open coverage in the punching arm. The defect is reported at maximum punch extension. The marked
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

## RC1 door snag and outdoor brightness reports: 6 October 2026

Recorded 2026-10-06T13:13:00+00:00; reported against the delivered v0.0.29-rc1 on WinUAE.

**CENSUS-DOOR-STUCK-29: open.** The player became stuck immediately after
opening the Census Office interior door. The captured pose and image are retained
with the playtest evidence. The door-open handler rotates and relinks the door;
whether the reported player hull overlaps that door, its frame, or other geometry
is not yet established. Reproduce from the closed side and both approach offsets;
inspect start-solid/contact entity before and after opening, then verify passage
in both directions and restored door state. Collision maintenance owns the case.
Do not remove room collision or add a coordinate-specific teleport as a workaround.

**LIGHT-EXTERIOR-JUMP-29: open.** The playtester reports an abrupt change from
dark to strongly lit scenery around the shack area with no carried torch. Two
screenshots show different positions and clocks of 11:11 and 11:41, so the images
alone are not a fixed-time, fixed-pose comparison or proof of a cell crossing.
Record the exact route, map identity, world light/style state, fog/daylight state,
and all active dynamic emitters. Replay with time held fixed, then repeat the same
pose while advancing time. Compare per-map initialization and cache invalidation.
Rendering maintenance owns the investigation; cause and introducing change are
unconfirmed. Preserve normal unlit scenery instead of masking the discontinuity
with a global brightness change. This report is distinct from interior NPC light.

### Repeated boundary evidence: 6 October 2026

Recorded 2026-10-06T13:16:13+00:00. The owner can repeatedly trigger the brightness change by
walking around the shack and reports it at other Seyda Neen traversal points.
Further screenshots show first-presented map diagnostics during the route.
The owner then reports that **the jumps stop after leaving the Seyda Neen area**.
Treat this as a reproducible owner-reported sub-cell passage defect, not merely
two unrelated stills. The underlying cause is still unconfirmed; the last report
is a negative observation on that route, not acceptance of the entire world.

Prioritize comparisons between the detailed town/sub-cell maps and surrounding
world maps: baked surface samples, world light-data presence, light styles,
daylight/fog state, and cached surfaces before/after handoff. Retain fixed-time
and reverse-route checks to distinguish inconsistent map data from initialization.
The earlier NPC torch report occurred in the same vicinity but is not proof of
a shared cause. **LIGHT-EXTERIOR-JUMP-29 remains open and is a release gate.**

## RC1 owner playtest follow-up: 6 October 2026

Recorded 2026-10-06T13:09:20+00:00. These are observations of the delivered **v0.0.29-rc1**
private playtest; the new default/navigation edits below are an unpublished
source candidate and do not change that package.

| Area | Observation / current status | Next evidence |
| --- | --- | --- |
| Appearance entry music | **AUDIO-APPEARANCE-29: fixed in RC1, owner-confirmed on WinUAE.** Entering the character appearance screen no longer produces the reported jump. | Preserve this exact entry as a regression case; this does not certify other transitions. |
| Follow-guard Enter | **AUDIO-ENTER-29: open.** A small soundtrack jump still occurs when pressing Enter to follow the prison-ship guard in RC1. | Reproduce the exact prompt and correlate audio service/queue and event timings. |
| Heavy-load music | **AUDIO-LOAD-29: open.** OST crackles on WinUAE during heavy loading, specifically prison ship to deck. Related to the earlier WIN-05 load-in report; a shared cause is unconfirmed. | Capture the load with nonzero music, service gaps, queued frames and read timings; compare with normal playback and the guard prompt. |
| Character confirmation buttons | **CHAR-CONFIRM-BORDER-29: fixed in RC1, owner rates Go back / Choose borders 5/5.** | Preserve both outlines/focus. Other travel/menu variants retain their separate acceptance scope. |
| Setup list / scrollbar | Owner confirms both work. **UI-OPTIONS-WRAP-29: open in delivered RC1.** Down wraps from bottom to top, making the scroll position confusing. | Candidate clamps Options, Interface and Audio at both ends for arrows, W/S, wheel and forward Tab. Seven focused Docker checks pass; target playtest pending. |
| Mixing default | Requested Effects default is **75%**; other category defaults and saved user overrides stay unchanged. | Eight default-only focused Docker checks pass. Verify fresh settings and retained saved overrides in the next target package. |
| Interior NPC light | **INTERIOR-NPC-LIGHT-29: open.** Census Office characters appear insufficiently lit by room lights. | Compare room surfaces and NPCs at the same pose with static interior light and player torch independently. Audit light samples, light data and actor representation before attributing it to TORCH-NPC-LIGHT-29. |

Audio work must preserve smooth playback during paused-world menus and map loads.
Do not mask a gap with a fade, mute, or an unmeasured global latency increase.
The interior report does not establish that the torch correction failed or that
both symptoms share one cause. Renderer and audio maintainers own their respective
investigations; UI maintenance owns boundary navigation and regression checks.

These reports were observed in dev4 and are tracked toward the next rc1
checkpoint. **NPC illumination, the detached hand fragment and Enter-music cuts
remain final-release blockers.** No resolution is implied by documenting them.
Music's detailed positive/negative matrix remains in [AUDIO.md](AUDIO.md).

## TORCH-NPC-LIGHT-29: nearby NPCs do not respond to torchlight (OPEN)

- **Affected / report date:** v0.0.29-dev4, 6 October 2026. Introducing version
  and last-known-good version are unknown. This refines the earlier weak-torch
  report; it does not imply that wall/floor lighting is absent.
- **Playtest evidence:** five screenshots compare a nearby exterior NPC with
  the player's torch off/on, a downward ground view off/on, and a dawn view.
  The reporter sees walls and floors respond but no visible illumination of
  the NPC. The ground comparison changes visibly. Night samples are around
  02:20–02:42 near original global XYZ **-14643, -71613, 95**; the dawn sample is
  at 05:58. They are useful visual evidence, not a fixed-time pixel test.
- **Expected:** an admitted nearby player or guard torch visibly lights an
  NPC within its effective range, with falloff and without globally brightening
  unlit actors. Expired/off/distant lights must stop contributing.
- **Source leads:** the alias-model branch in `R_DrawEntitiesOnList` already
  adds dynamic lights before clamping ambient light to 128. `R_LightPoint`
  returns 255 when world light data is absent, which can saturate that clamp
  before a torch contributes. The exterior fog/night palette is applied after
  entity drawing. Sprite actors use a different rendering branch. Establish
  the actual actor representation, map light data and final palette response
  before selecting a correction; these are leads, not a confirmed diagnosis.
- **Next checks:** reproduce at a fixed clock, pose and build; capture the NPC
  body separately from the flame/hands and ground. Trace base light, each live
  light contribution, final clamping and post-render night shading. Compare
  player/guard emitters, close/far/off/expired cases, interiors, dawn/daylight,
  ordinary NPCs and supported guard bodies. Check the reference appearance and
  native frame cost. Preserve existing floor/wall lighting and gallery behavior.
- **Current status:** source correction and bounded native night/day torch
  off/on acceptance at one guard are recorded below. Final-package replay,
  broader coverage and frame cost remain open. **Fixed: N; first shipped
  verified fixed version: none.**

See [the torch acceptance matrix](TORCH.md#npc-illumination-dev4-report).


## TORCH-HAND-NORD-29: detached-looking grip fragment in dev4 (OPEN)

On 6 October 2026 a Nord playtest in **v0.0.29-dev4** supplied a full view,
close-up and marked close-up of a skin-coloured fragment separated from the
left torch-bearing hand near the shaft/grip. Global **22572,-68571,2001**,
heading340/pitch-39, clock07:13 is the full-view reproduction vicinity.
This continues the earlier hand seam/clipping reports; a still image does not
establish whether the visible part is skin, grip geometry, an animation transform
or clipping. It must remain open rather than being closed by a geometry-only test.

The sealed dev4 payload catalogue contains the legacy `progs/v_torch.mdl` and
does not contain `gfx/hand-models.awh` or the proposed Nord-specific hand models.
The optional original-topology replacement was not shipped in that package.
Therefore source-candidate geometry results are not acceptance of the user's
actual model. Inspect the packaged model over idle, walk/run and punching frames,
torch on/off and pitched cameras; compare clipping and connected components with
the owned original model. Verify the race-specific catalogue and correct model
binding in the next image, then replay the visible seam checks. Apply the same
closed-seam requirement to every supported race. **Fixed: N; final-release blocker.**

## HUNK-RESERVE-SN012-29: dev4 warning below 2 MiB (OPEN)

On 6 October 2026 the playtest console reports `maps/sn012.bsp first-presented`:
low/peak **9,593,856 B**, high0, allowance **11,534,336 B**, gap/peak gap
**1,940,480 B**, cache **1,788,496 B**, cache peak **2,635,056 B**, largest zone
block **19,860 B**. It warns that hunk-operation safety is below2 MiB and the
region requires memory review. This is a first-presented diagnostic, not proof
of worst-frame memory use or a crash.

The playtester supplied a current reproduction vicinity: global
**-11510,-73406,123**, local **-61,-481,30**, heading273/pitch28, clock10:47.
Movement between screenshots means it is not established as the original
warning-frame pose. Retain the scene warning and location together; measure the
exact build and first-presented/steady/transition peaks before admission.
Continue the exterior residency/allocation investigation without lowering the
target reserve merely to silence the warning. **Unresolved.**

## Debug flame feedback and renderer-metadata warning: dev4 follow-up

A playtest console screenshot confirms `Torch flame style 2 (1 classic,
2 brightbase, 3 sparks)`. Brightbase selection works in that session; the
setter's lack of a success message confused the check. The next source candidate
adds explicit style confirmation. This does not establish NPC lighting or
hand-seam correction. Keep `dbg torch flame sparks`, `brightbase`, `classic`
and the direct query `aw_torch_flame_set` available.

The same console shows `'aw_render_ranges' is not a field`. The engine's native
render-range reader does recognize that key, while the separate generic entity
field parser warns about undeclared QuakeC fields. Investigate that metadata
handoff and improve the warning only after verifying consumption; do not infer
missing geometry or associate it with flame-mode selection from this line alone.

### Dev4 torch disappearance reported while trying flame variants

The playtester reports no visible torch after experimenting with flame styles1–3.
A preceding query confirmed style2. The supplied follow-up screenshot is a console
view and does not establish whether the model, flame, or equipment state is absent.
Changing style is not intended to change equipped state. Capture read-only
`aw_hands`, current style and the actual viewport; distinguish lowered hands,
lost torch state, invalid model/frame and missing flame pixels before a fix.
Keep this open alongside the grip/illumination issues; do not declare it solved
by a successful configuration query.

### Equipped-state evidence for the flame-visibility report

The follow-up console sample reads `hands state 2 goal 1 frame 5 torch 1 /
time 25711`. The viewport beneath the console shows the torch shaft and grip.
Thus equipment is retained at this sampled instant; actual flame visibility,
emitter projection and console occlusion still need a full-viewport comparison.
The separate render-range field warning appears again in the same capture.

### Rc1 candidate: native range metadata handoff verified

The QuakeC entity parser now recognizes `aw_render_pool` and `aw_render_ranges`
as native renderer metadata and leaves the original BSP text for the renderer.
It skips their bounded values without copying long lists through the legacy
1-KiB token buffer. The renderer still validates the model and range bounds;
other unknown fields still warn. No additional QuakeC fields or per-entity RAM
are added. This fixes the misleading field warning in the source candidate; it
does not establish a torch-flame or geometry repair.

Two focused Docker checks pass, including the real entity parser and native
range consumer under AddressSanitizer/UndefinedBehaviorSanitizer: a 3,999-byte
range list survives unchanged, normal fields still parse, malformed/oversized
metadata is rejected, and invalid renderer ranges still fail. Source checks
passed; the integrated 1,023-test candidate and Amiga engine build also passed.
Exact package inclusion and native playtest remain pending.

## Let there be (some more) light — NPC torch-light correction

The candidate establishes the unchanged static actor-light baseline before adding
finite positive dynamic light, then caps total brightness at255. The previous
order erased local light on maps where `R_LightPoint` returned255 for absent
lightdata. Actual alias transform/clip/span and day/night-palette checks show
torch response while all256 unlit inputs, off/far/expired lights and gallery
controls retain their prior output. The 68040 change adds68 code bytes and no
static RAM. It changes neither torch radius nor world/floor/viewmodel lighting.
The integrated candidate passes its Amiga build and 1,024-test run with zero
failures/errors and four skips. These are source/build and synthetic raster
checks. Exact package inclusion and actual NPC off/on visual acceptance remain
required; the issue stays open.


## 6 October: current candidate and regression evidence

The integrated packed-edge candidate ran **1,028 tests**, with zero failures or
errors and four existing skips, and passed the Amiga target build. The subsequent
combined edge/surface candidate also passed: 1,029 tests, zero failures or
errors, four existing skips, and the Amiga target build.
Neither result establishes a released RC1 package.

- NPC torch lighting has bounded native night/day off/on evidence at one sampled
  guard. All three flame styles are visible in the tested full viewport. Wider
  appearance coverage, frame cost and exact final-package checks remain open.
- The playtester observed no blinking in the latest delivered dev4. Preserve
  that regression baseline while treating the paw-like silhouette and grip
  fragment as separate unresolved appearance reports. Source-topology and
  per-vertex lighting-normal candidates still need ordinary motion acceptance.
- World admission now models 347 of 390 exterior maps within budget; 43 remain
  withheld. Original-placement route counts are 897 of 934 primary and 886 of 934
  complete overlaps. This does not change packaged or native-accepted totals.
- Enter-music remains open. The prior timed native attempt did not establish
  soundtrack continuity or a cause. Head-preview reads are being checked
  separately from the prison-ship follow-guard event; no blanket pause/fade
  workaround or global audio-latency increase is accepted.

Keep NPC lighting, connected hands, music continuity and flame visibility in
the final-release gate. A source pass does not close a reported regression.


### Head-preview audio: controlled loader result

The head loader now services the existing audio mixer around reads capped at
4,096 bytes, retaining its fixed buffers and same-ID cache. With an injected
100 KiB/s disk delay, the original two large reads miss 7,369 mixer samples;
the chunked loader misses none under the same fixture. The actual C loader and
mixer are exercised. Its isolated full suite passes 1,029 tests with zero
failures/errors and four existing skips. This establishes a starvation mechanism
under the controlled delay, not native acceptance or the cause of the separate
prison-ship Enter report. Native traces for both events remain under review.
