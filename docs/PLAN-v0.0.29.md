# v0.0.29 immediate fixes and follow-up work

Recorded from owner playtesting on 4 October 2026, after the published
[v0.0.28 release](https://github.com/FlyingFathead/amiwind/releases/tag/v0.0.28).
The latest published development checkpoint is v0.0.29-dev4; the next is
v0.0.29-rc1, followed by final More Mushrooms after its release gates pass.
The original reports remain the baseline; current issue status is authoritative
in [BUGS.md](BUGS.md). Preserve all published artifacts unchanged. Retain rocks, joined giant mushrooms,
authored foliage placements and Balmora's mesh-foliage comparison area.

<!-- contents start -->
## Contents

- [Current release sequence — 6 October 2026](#current-release-sequence--6-october-2026)
- [Immediate bugfix queue](#immediate-bugfix-queue)
- [Torch and local-light regression gate](#torch-and-local-light-regression-gate)
- [Modal workload and Seyda Neen follow-up](#modal-workload-and-seyda-neen-follow-up)
- [Navigation, character state and optional sky work](#navigation-character-state-and-optional-sky-work)
- [Weather, storms and lava study](#weather-storms-and-lava-study)
- [Evidence and acceptance before a patch release](#evidence-and-acceptance-before-a-patch-release)
- [HUD source-candidate evidence, 4 October 2026](#hud-source-candidate-evidence-4-october-2026)
- [Distant terrain topology and occlusion study](#distant-terrain-topology-and-occlusion-study)
- [Bonus after the immediate fixes: Ghostgate and Ghostfence feasibility](#bonus-after-the-immediate-fixes-ghostgate-and-ghostfence-feasibility)
- [Additional source evidence, 4 October 2026](#additional-source-evidence-4-october-2026)
- [Protected sunrise and sunset baseline for v0.0.29](#protected-sunrise-and-sunset-baseline-for-v0029)
- [Later combat scope](#later-combat-scope)
  - [Horizon coordinate transcription correction](#horizon-coordinate-transcription-correction)
- [5 October afternoon owner follow-up](#5-october-afternoon-owner-follow-up)
  - [5 October radius and grip follow-up](#5-october-radius-and-grip-follow-up)
  - [Standing full-screen UI resource rule](#standing-full-screen-ui-resource-rule)
  - [5 October map interaction split](#5-october-map-interaction-split)
  - [Map controls: source implementation and focused checks](#map-controls-source-implementation-and-focused-checks)
  - [Combined source validation, 5 October 2026](#combined-source-validation-5-october-2026)
- [Conditional release milestone: More Mushrooms](#conditional-release-milestone-more-mushrooms)
- [Required More Mushrooms! debug checkpoint](#required-more-mushrooms-debug-checkpoint)
- [Final More Mushrooms! release blockers — 6 October 2026](#final-more-mushrooms-release-blockers--6-october-2026)
- [Next checkpoint: v0.0.29-rc1](#next-checkpoint-v0029-rc1)
- [Final-release gallery checklist](#final-release-gallery-checklist)
- [Mandatory issue and roadmap reconciliation](#mandatory-issue-and-roadmap-reconciliation)

<!-- contents end -->

## Current release sequence — 6 October 2026

| Milestone | Current state | Next action and completion evidence |
| --- | --- | --- |
| v0.0.29-rc1 playtest | Source integration in progress; no rc1 package released | Package the tested candidate, pin its contents and run targeted hand, torch, Enter-audio, debug-command and persistence checks. Carry unresolved IDs in its notes. |
| Audio options | Four independent slider controls pass source checks | Verify native appearance, uninterrupted playback, independent gains and saved settings in the RC1 package. |
| Worldwide mushrooms | Pilot picking verified; broader placement and admission incomplete | Resolve dense-map memory and interior access, then verify placement, empty visibility, pickup, travel and save/load on the exact package. Mapping counts alone do not complete this milestone. |
| Final More Mushrooms | Blocked by world coverage and the final-release issues below | Verify NPC lighting, connected race-specific hands, Enter-audio continuity and flame visibility; reconcile all required gates and publish the matched screenshot/GIF gallery. |
| Outdoor streaming | Performance / Needs work; no accepted speedup | Compare pinned outdoor crossings with frame and audio timing plus RAM peaks. Building entry/exit loading screens are acceptable. |
| Time to Fight! | Deferred until final More Mushrooms | Integrate the arena, then calm-to-aggro E activation, sword/shield combat, voices/SFX, combat music and player-death feedback. See [combat roadmap](ROADMAP.md). |

## Immediate bugfix queue

P1 means lost controls or major visual/gameplay failure; P2 means presentation
or fidelity work. Priority does not replace evidence or native acceptance.
Every bug remains **Fixed: N** until its own acceptance is supported.

| Priority / ID | Owner report and required result | Current evidence / next step |
| --- | --- | --- |
| P1 TERRAIN-TRAP-29 | v0.0.29-dev1: Player stuck on rocks beside structures. | Global -21794,-17467,545; reproduce movement and compare placement/collision/streaming evidence. Cause and correction pending. |
| P1 TORCH-INPUT-29 | F no longer raises hands in debug play; V prints torch on/off but no hands or working torch appear. Restore the full input-to-visible-equipment path. | Released-world metadata defect reproduced. All 2,532 corrected staged maps pass readback; source/VM tests and sampled native F/V checks in town, one world transition and a Hlaalu Council interior pass. One ordinary Council/Balmora roundtrip preserves the torch; after quickload, initially lowered hands can redraw/re-equip with F/V. Full state/save/light acceptance remains open. |
| P1 MAP-TELEPORT-28 | Both `dbg tp map` and `dbg map tp` intermittently fail; one retry worked. Keep both aliases and checked landing behavior. | Both share one handler; hidden-HUD coupling removed. Source checks and sampled native opening of both aliases pass. Checked landing and full owner-state acceptance remain open. |
| P1 MAP-VIEW-SWITCH-28 | Clicking DEBUG / IN-GAME fails to switch views. | Overlay/input-order fixes pass focused C tests and cross-host Amiga builds. One emulator replay sends oversized positive guest deltas; manual tab input remains unaccepted. |
| P2 MAP-RIGHT-DRAG-29 | Teleport picker advertises right-drag but only middle starts panning on Amiga. | Both secondary codes now accepted locally. Baseline failure, corrected fixture and Amiga build checks pass; manual native drag remains open. |
| P1 TREE-PILLAR-28 | Sprite-tree roots stretch into striped pillars on slopes. | Scale/authored-origin mismatch reproduced: 90 wrong pixels of 105 before repair; seven corrected raster cases pass. Three native views of one scale-2 tree on a roughly 20-degree slope show a tapered root without the broad pillar. Exact reported placement and broader sprite/slope coverage remain open. |
| P2 CONSOLE-CAPS-29 | FS-UAE F10 Caps Lock state sticks in v0.0.29-dev1. | Reproduce modifier/focus lifecycle; owner toggle-on/off workaround recorded, cause unknown. |
| P2 CONSOLE-WHEEL-29 | FS-UAE F10 scroll works initially then emits repeated unbound warnings in v0.0.29-dev1. | Recurring owner report; inspect console wheel consumption/binding fallback with preserved settings. No fix accepted. |
| P1 MODAL-WORLD-29 | Freeze world and optionally black out head/race, journal and modal backgrounds. | Source candidate: independent aw_modal_freeze/aw_modal_black defaults1; original name entry preserved. Soundtrack always serviced. Revised Linux tests and cross-host Amiga binary parity pass; native timing/lifecycle acceptance pending. |
| P1 SHACK-VISIBILITY-29 | Indrele Rathryon shack walls were missing in dev1. | Fixed in dev3: matched native restoration and playtester confirmation. Preserve the restored walls as a regression baseline; unrelated structures and horizon gaps remain separate. |
| P1 SEYDA-TRANSITION-29 | v0.0.29-dev1: Cell/sub-cell passage remains problematic; investigate fewer sub-cells. | Owner report, exact failing crossing unconfirmed. Capture region/hysteresis/collision and memory evidence; merging cells is not yet a verified remedy. |
| P2 INLAND-SHORE-29 | v0.0.29-dev1: Check angular inland-water shoreline topology. | Owner view at global -39785,-30636,379; cause unconfirmed. Compare source LAND/water intersection and converted topology without changing authored water placement or height. |
| P1 HORIZON-POP-29 | Distant terrain/features abruptly appear or become a mesh mess when turning. | Authored opaque terrain_rock_rm_18 is rejected by far culling. Exact diagnostic geometry visually restores one sample, but the latest lossless OFF baselines drift by 36.11%; controlled pose/view-angle replay is required before acceptance. |
| P2 MAP-SPOTS-28 | In-game map is covered with unintended white/yellow dots. | AWM1 palette-index data missed the sky remap; candidate corrects pixels/ocean without changing area metadata. Wide and closer native samples show clean terrain with labels/player marker retained; wheel zoom works. Explicit mode selection does not establish mouse-tab acceptance; exact owner view and broader coverage remain open. |
| P2 HUD-STATS-29 | Healthy character's red bar appears partly empty; all three bars need independent current/max values. | Independent current/max source and pixel fixtures pass. Native health fills match 55/55, 25/55 and controlled 5/55; quickload restores the 25-health frame exactly. Magicka/fatigue stayed full, so their independent depletion remains untested natively. Sampled heading/time is correct; broader state/damage/healing checks remain open. |
| P1 TORCH-LIGHT-29 | Guards carry torches but do not visibly illuminate nearby night surfaces. | Signed interpolation repair passes synthetic fixtures ([evidence](TORCH.md#light-gradient-29-unsigned-surface-light-interpolation-overflow)). One Balmora Hlaalu guard visibly lights pavement: 841/1,680 selected pixels brighten, restore exactly off and match automatic night. Earlier guard view still has identical off/on frames and no recognizable guard; diagnose it separately. General surface, actor and cost acceptance stays open ([incident](journals/BUG_JOURNAL-v0.0.29.md#torch-light-29-guard-torches-do-not-illuminate-nearby-night-surfaces-open)). |
| P2 INTERIOR-LIGHT-29 | Interiors look bleak, with no convincing local light sources. | One Hlaalu Council player-torch replay shows visible wall/floor response; lossless comparison finds 24,728 changed stable viewport pixels, 16,624 above the lower hand/torch band. This is not a depth-classified surface count. One ordinary door roundtrip preserves equipment; F/V restores the sampled light after quickload. Authored static lights, other rooms/save states and budgets remain open. |
| P2 SKY-NIGHT-COVER-29 | Night can look good in some regions, but near-constant dense cloud cover hides moons, stars and space. | Optional cloud-control V2 provides clear/partial/overcast deep nights and independent midday coverage. Legacy remains default; protected twilight and depth-order fixtures pass. Lossless indexed native frames at one frozen 23:00 dry-exterior pose show optional V2 coverage/night-layer changes confined to sky pixels with exact restores. Broader regions/Balmora, appearance/frame cost and original regional weather remain pending. Playtester accepted the night-sky appearance on 5 October; preserve that baseline. Exact active configuration and wider weather/region coverage remain open. |

Detailed incident records and evidence limits are in [BUG_JOURNAL.md](BUG_JOURNAL.md)
and the maintained [fix index](BUGS.md#fix-index). Passing a console handler or
showing a flame does not establish working hands, surface lighting or target FPS.

## Torch and local-light regression gate

The repeated F/V problem is an immediate regression-prevention obligation.
The test chain must include actual gameplay input, state transition, visible
equipment and rendered light, with explicit failures when any stage is absent.
Do not close it from the text "torch on", a successful command parser, or a
nonempty model alone. Keep the older periodic fist blink separate.

The [torch acceptance matrix](TORCH.md#v0029-required-hands-and-light-acceptance-matrix)
covers F, V during draw, V off/on, F lowering, debug on/off, normal/noclip,
map/console return, personal bindings, crossings, saves, night exteriors and
interiors. Record intentional story restrictions rather than removing them.
Test both supported hand presentations and preserve Shift+V's shortcut.

For local lights, compare identical cameras with the individual light off/on.
Show changed wall/floor/scenery pixels and bounded falloff; identify world versus
brush/alias surfaces and unavailable contributions honestly. Check source radius,
attachment, palette/lightmap behavior, ambient saturation, occlusion/contents,
cache invalidation and admitted light count. Measure frame time and memory in
the worst representative interior/guard scene. Do not add unlimited lights or
claim coloured lighting or shadows from the existing monochrome renderer.

## Modal workload and Seyda Neen follow-up

The source candidate exposes independent saved `aw_modal_freeze` and
`aw_modal_black`, both default1. Head/race and subsequent character pages,
journals and blocking overlays can freeze the world and hide it with black;
the original name-entry prompt retains its prior world context. UI/head/input,
presentation and the soundtrack continue. Music servicing has its own priority
and remains outside world-freeze gates; only explicit hard stop/shutdown stops it.
Preserve prior pause ownership, intentional waiting, nested overlays and fresh
redraw on close. Revised four-combination fixtures pass within78 Linux native-source checks.
Windows/Linux Amiga binaries match exactly. Native timings/acceptance remain
pending; no measured speedup is claimed.

Automatic streaming also has separate `TRANSITION-VIEW-29` and
`TRANSITION-VOICE-29` candidates: exact client view/drift restoration and bounded
detached voice tails. Focused Linux source tests pass; native crossings, audible
continuity and target allocation headroom remain required. Explicit travel keeps
authored facing. See the journal for causes, reproduction and refusal limits.

Investigate the new shack view and cell/sub-cell passage reports separately.
The owner also reports that horizon drawing looks better, but that observation
does not establish complete horizon acceptance or resolve streaming. Record
exact active and previous regions before attributing either issue to cell size.
Any reduction in sub-cell count must retain source geometry/collision/placement
coverage and meet existing resident/transition heap limits without reserve
relaxation. See the new open entries in [the journal](BUG_JOURNAL.md).

Add the angular inland shoreline to the topology checklist: compare source LAND
and water intersection against conversion at the reported pose, keeping water
placement/height unchanged. No specific triangulation or clipping fault is yet
established by the reported image.

## Navigation, character state and optional sky work

- **Debug HUD V2, default:** retain global/local coordinates; add N, NE, E, SE,
  S, SW, W, NW heading and saved-world-clock 24-hour `HH:MM`. Keep V1 available.
  Distinguish geographic bearing from raw engine yaw, preserve normal compass
  controls and verify readable layout at the supported native resolutions.
- **Character bars:** health, magicka and fatigue each use their own current/max
  values. A 55/55 health character is full, 27.5/55 is half; zero/invalid maxima
  are handled safely. Keep live gameplay health authoritative when applicable.
- **God-mode switch, later:** requested `dbg god on/off`, also `true/false` and
  `1/0`, with query/invalid-input behavior. Development is described by the owner
  as god mode; the future explicit switch still needs defined runtime/save
  semantics and tests. Do not silently refill stats to imitate god mode.
- **Optional veil clouds:** retain every existing sky/cloud type and current
  defaults. Add a selectable sparse, rasterized/ordered-transparent veil variant
  so more sky shows through. Bound CPU/memory, preserve sun/time/cloud-speed
  semantics, and verify the existing type remains byte-identical when selected.
- **Night coverage:** investigate the current preset/configuration and region
  policy. Capture clear, partly cloudy and overcast nights at comparable times
  and viewpoints, including Balmora. Do not remove every nighttime cloud. Moons
  and tiny distant stars must keep their established masks and depth ordering.

## Weather, storms and lava study

- Inspect original owned CELL/REGN data, scripts and relevant OpenMW code to
  determine ashstorm/blight onset and transitions, including settlements outside
  Ghostfence. Do not invent a radius or assume the fence is the weather boundary.
- Red Mountain's requested art direction is strongly red skies and dense,
  windblown ash: a storm-like visual, not snow. Separate the requested effect
  from proven original weather probabilities and colour settings.
- Study NPC hand-to-face storm reactions and their actor-state/animation rules;
  include direction, combat/equipment conflicts and transition behavior. The
  exact original trigger has not yet been established by the initial review.
- Survey source-authored lava activators, meshes, animation, scripts, placement,
  collision, damage and light separately. Prototype lava pools/fields from those
  records, preserving the ordinary water/terrain contract. Add a debug-world-map
  representation derived from actual surveyed lava references, with uncertainty
  shown rather than made-up coverage.
- Study original lantern/torch light records and attachment semantics alongside
  OpenMW and Quake/AmiQuake surface-lighting paths. Prefer a bounded nearest-light
  budget with measured visual benefit; source fixtures do not establish target
  performance or original-game parity.

The [pinned OpenMW weather and blight source study](WEATHER_AND_BLIGHT_STUDY.md)
records the verified regional selection and NPC storm-pose rules, their limits,
and staged acceptance. Weather and storm effects remain study/prototype scope;
the findings do not establish original regional chances or Ghostfence boundaries.
A historical official [lava design note](https://gitlab.com/OpenMW/openmw/-/blob/openmw-0.51.0/docs/openmw-stage1.md)
describes lava as activators, not a second water type; individual original lava
effects still require a source-data and runtime audit.

## Evidence and acceptance before a patch release

- Retain the owner's Ashlands horizon coordinates: global **38205, 29437, 1380**;
  local **335, 191, -294**. Screenshots show raw **DEG 263 / P -9** and
  **DEG 321 / P -23**. Pitch differs, so this is not a controlled yaw-only A/B.
- Preserve the reported tree root, map spots, health bar and navigation views
  as evidence; source fixtures and identical-camera target replays are separate.
- Current map candidate: 23 interpreted checks pass on Windows and Linux; two
  actual C world-UI/console fixtures pass on Linux, including UBSan coverage.
  Current sprite candidate: seven raster cases pass with undefined-behavior and
  float-cast checks. Neither result establishes a new playable-image acceptance.
- Run relevant Windows and Linux checks, actual Amiga compilation, staged-asset
  validation where required, and matched native gameplay/camera replay. Preserve
  public asset boundaries and report memory/music caveats truthfully.
- First release preflight remains raw LF/CR checks and no trailing whitespace
  on final source/scripts, including new files. Recheck after changed bytes.
- Do not change a bug's fixed flag or publish v0.0.29 until its stated closure
  evidence exists. Unfinished weather/lava studies remain explicitly deferred
  scope rather than silently advertised features.

The dedicated [Study lanterns and torch lighting more](LANTERNS_AND_TORCH_LIGHTING.md)
covers wall-mounted torches, lantern fixtures and carried lights; authored
placements/attachments; indoor static/dynamic lighting; the guard day/night
cycle; and measured local illumination rather than flame sprites alone.

## HUD source-candidate evidence, 4 October 2026

The source candidate now uses independent stat current/max values, with
live single-player health authoritative where applicable and safe invalid-max
handling. Actual UI pixel tests cover 55/55 full, independent half/quarter bars,
live health, zero, overheal and invalid maxima, without character-state mutation.
Default Debug HUD V2 now adds eight-point compass/numeric bearing, pitch and
saved-clock `HH:MM` (`--:--` when unavailable), retaining V1 raw DEG behavior.
Bounded 320-wide layout and the focused HUD/UI/sprite runner methods pass 3/3
on Linux.

**Bounded native update, 5 October:** lossless engine-generated captures and
independently decoded saves now support one controlled health/save sequence.
Health 55/55 fills all 71 inner bar columns; 25/55 fills 32. A deliberate
5-health display setting fills six, then quickload restores 25/55 and 32
columns. The before-change 25-health frame and quickload frame are byte-identical.
Magicka 30/30 and fatigue 180/180 remain full in the saved values and all four
captures; independent depletion of those stats is still untested natively.
The sampled HUD also shows N/000 at engine yaw 90 and retains 09:00 through
the ordinary door roundtrip, consistent with the source compass convention.
This does not test every heading or clock transition. Other current/max
combinations, broader save states, gameplay damage/healing and god mode remain
open; controlled health assignment does not validate those systems.

## Distant terrain topology and occlusion study

The controlled camera at global **51855 39125 3502**, local **-348 565 107**,
raw **DEG 265 / P 0**, exposes a taller peak formed by the authored opaque
`terrain_rock_rm_18` static. Its whole-model bounds fail the far-distance gate;
LAND-only fill cannot reproduce the missing rock silhouette. Other reported
angles still need their own attribution. See [HORIZON-POP-29](journals/BUG_JOURNAL-v0.0.29.md#horizon-pop-29-distant-scenery-pops-or-breaks-up-while-turning-open).

A bounded LAND/rock heightfield remesh is rejected: 44 of 48 sampled views fail
coverage, false-occlusion or conservative-depth checks, with a worst sampled
top-silhouette error of 13 pixels at 128x60. Preserve separate rock topology or
a source-checked proxy, near depth protection and seams; measure resource and
native frame cost. No complete horizon correction is accepted. These samples
neither prove all budgeted designs impossible nor justify reducing reserves.

An opt-in exact-geometry diagnostic restores the inspected silhouette visually;
it remains separate from accepted production behavior. A later seven-frame
320x200 lossless PCX run keeps the palette identical but changes 17,565/48,640
viewport pixels (36.11%) between its first and last OFF baselines. That run
cannot support exact A/B acceptance. The reported integer origin is unchanged;
endpoint view angles are absent, so broad drift has no established cause.

Next, set the existing mouse `sensitivity 0`, apply an explicit pose and record
measured endpoint view angles. Obtain two identical OFF baselines before any
LAND/exact/reference comparison. Keep authored LAND and opaque placed statics
separate when assessing silhouettes; do not infer rock topology from a top-down
height image alone. Preserve depth/occlusion, seams and measured cost limits.
These are diagnostic controls, not new production defaults or a closed bug.

## Bonus after the immediate fixes: Ghostgate and Ghostfence feasibility

Study the source-authored Ghostgate and Ghostfence after the immediate regression
queue is under control. Survey owned game placements, mesh/material references,
transforms and relationships to surrounding terrain; identify gates, visible
barriers and collision/gameplay behavior separately. Do not invent missing
geometry or assume a weather boundary from the visible fence alone.

Evaluate distant outdoor visibility, mountain occlusion and continuity through
adjacent converted regions. Any simplified representation must preserve the
recognizable authored silhouette, placements, gate access and intended collision,
with measured resident memory, loading and worst-view rendering costs. Prototype
one bounded representative section and compare it against owned source data
before widening coverage. Original game assets and inspection media are not
included in public source. This is bonus study scope for v0.0.29, not an
implemented feature, a publication promise or a reason to postpone bug fixes.

## Additional source evidence, 4 October 2026

The actual compiled QuakeC and torch fixture now reproduces the old missing-hand
timing failure and passes the candidate's state/model/light transitions. Correct
metadata still needs stamping and validation across the 2,532 affected world
regions; native-image acceptance is pending. Optional veil and retained sky
fixtures 1-13 pass; fixture 14 also passes for the separate, opt-in cloud-control
V2 prototype. Legacy remains the default. The new controller preserves protected
twilight, supports gentler daytime coverage and clear/partial/overcast deep
nights, and retains moon/star depth ordering. Native acceptance remains pending.

## Protected sunrise and sunset baseline for v0.0.29

The owner explicitly likes the v0.0.28 sunrise/sunset clouds and asks that they
remain unchanged, or change as little as possible. Preserve classic dawn, dusk,
golden-hour and twilight cloud appearance as the visual baseline. Night-coverage
changes must stay outside those protected windows and pass byte-identity
comparisons against the retained classic path. Do not let a global coverage
change quietly alter those skies.

Daytime clouds may be too dense. Keep the new daytime veil optional, preserving
existing types/defaults; do not silently replace the liked cloud art. Night
clear/partial/overcast policy remains a separate bounded change, with continuous
transitions that do not damage protected dawn/dusk or moon/star depth ordering.

## Later combat scope

[Time to Fight!](ROADMAP.md#future-combat-milestone-time-to-fight) follows the
More Mushrooms release: build the Nerevarine combat arena first, then NPC aggro
logic and a first sword-and-shield versus sword-and-shield encounter. The
original Vivec Arena Pit is the source candidate for an isolated `dbg arena`
prototype. Enter with a calm opponent, then target the NPC and press E to
trigger combat. Include appropriate NPC aggro lines, combat taunts and effects through
the imported audio lookups, and report missing assets. Prototype visible dodges
or deflections for failed hit rolls while preserving the resolved combat outcome.
Fight tests must switch combat music on/off with encounter state and include the
player death sound, death-camera movement and correct reset/retry behavior.
Minimal NPC state outside
loaded cells follows the combat baseline. These are planned tasks, not required
v0.0.29 features.

### Horizon coordinate transcription correction

The later Ashlands screenshot's global X was initially transcribed as51055.
Reinspection corrects it to **51855** (global51855 39125 3502, local-348 565107,
rawDEG265/P0), consistent with the scene transform. Preserve this transcription
correction when reproducing the view; it is not a changed player position.

## 5 October afternoon owner follow-up

- Preserve UI V1; default to `aw_ui_mode 2` with focused/clickable footer OK on
  appearance, class, birthsign and review. Native button acceptance remains open.
- Add named `dbg tpscene <scene>` entries, starting with headselection, to reduce
  repeated intro viewing and test setup. Normal New Game must remain available.
- Missing class illustrations and custom-class creation: see CHARACTER_CREATION.md;
  neither is implemented by the OK-button change.
- SHACK-VISIBILITY-29 remains open in the post-reboot target observation. New
  ROCK-FLORA-SURFACE-29 records recently appeared angular rock-like surfaces;
  identify the placed object, source mesh/material and camera before attribution.

- Immediate priority: TRANSITION-EQUIPMENT-29, preserving complete equipped
  and animation state before the first cell/sub-cell arrival frame. The owner
  confirms held-torch surface light works; guard illumination and
  TORCH-HAND-SEPARATION-29 remain separate open reports.
- Torch controls now implemented in source candidate: saved universal
  player/admitted-guard radius default 192, bounds 32–288, dbg torch radius X;
  saved flame style 1 classic/2 brightbase and dbg torch flame
  classic/brightbase. Amiga compilation passed; initial integration passed 78/79 checks,
  followed by a pass of the corrected radius assertion in the real-QC fixture. Current current development playtest and native
  acceptance remain pending. See TORCH.md.
- Cross-check current shack persistence and the separate angular rock-like
  ground-form report in BUG_JOURNAL.md. Object identity and both root causes
  remain open.


### 5 October radius and grip follow-up

Owner requests a universal player+guard radius control. Proposed source bounds
are 32–288 with a proposed default of 192 (prior value 144); current post-reboot
target is not assumed to contain this candidate. Keep native acceptance open.
Study the reported first-person torch hand/torso appearance against OpenMW and
OG part-visibility behavior without treating either as a proven cause.


### Standing full-screen UI resource rule

When a full-screen map, journal, letter, book or future inventory covers
gameplay, default to freezing the underlying 3D rendering and world simulation/
resource work. Keep UI, audio and music service active, then resume without
elapsed-time catch-up. Keep aw_modal_freeze and aw_modal_black as optional
legacy controls. Parent inspection confirms AW_WorldUI uses key_menu for J/M
and AWReader covers books; existing host-frame coverage keeps audio/music live.
Add integration checks for actual entry paths. Lower audio contention may help
headroom but does not guarantee resolution of music artifacts.


### 5 October map interaction split

Normal user-map left click sets/updates a marker without teleporting. With debug
HUD on, map opens in DEBUG mode. In DEBUG mode HUD right-click sets a red
teleport crosshair and exposes the bottom-right Teleport button; it never
teleports immediately. Keep existing dbg tp map independent of HUD visibility.
The marker feature follows the current torch state hotfix; parent has assigned
map implementation, native acceptance pending.


### Map controls: source implementation and focused checks

The requested saved cyan click marker, HUD-based default map view, and debug
right-click red destination plus explicit TELEPORT confirmation are implemented.
The real world-UI/save-codec fixture and input/focus compatibility checks pass
in offline Docker. The marker uses three bounded global entries and refuses
insufficient capacity atomically. Existing explicit teleport aliases remain
HUD-independent. Native acceptance is pending; see WORLD_MAP_AND_JOURNAL.md.


### Combined source validation, 5 October 2026

A fresh combined offline Docker run passed all 80 native-source test methods
and the Amiga 68040 build. It includes the UI V2/scene shortcut, full equipment
handoff, radius/flame controls, running-torch depth correction, and map marker/
debug selection changes. Native acceptance and delivery of these changes remain
pending. The smaller idle-grip defect and scene-specific light/geometry reports
remain open.

## Conditional release milestone: More Mushrooms

Recorded 2026-10-06T04:49:51Z from owner direction. The planned public release title is **AmiWind v0.0.29 -- More Mushrooms**. Shipping v0.0.29 is a conditional checkpoint after original mushrooms are placed worldwide, can be picked with persistent state behaving correctly, and the relevant release gates pass. This is a future target, not a claim that worldwide coverage or release readiness is complete. The current dev4 six-placement mushroom pilot may be photographed as progress evidence only and must be labeled as a six-placement pilot, not worldwide coverage. Take final release screenshots from the completed worldwide candidate. The later Caius quest milestone is separate and is not this release title.

## Required More Mushrooms! debug checkpoint

- Include `dbg shroompicker` in the upcoming v0.0.29 release, not as a deferred
  combat-update task. It reaches the confirmed Seyda Neen pickup cluster at
  global XY -10920, -75120 and sets yaw4/pitch64 after loading.
- Preserve inventory, equipment and collected/empty plant state. The shortcut
  must not silently reset or manufacture a mushroom for the test.
- Gate the command through its actual console, checked teleport and final-signon
  paths; verify the built command natively. Retain the two-command recipe for
  the already published dev4 binary.
- Dev4 picking has separate playtester confirmation dated 6 October 2026.
  Worldwide coverage and final release acceptance remain open.

## Final More Mushrooms! release blockers — 6 October 2026

These latest dev4 findings must be fixed and verified in the actual final
package before release:

- **TORCH-NPC-LIGHT-29:** torch illumination on nearby NPC bodies, while retaining
  working wall/floor illumination and bounded native frame cost.
- **TORCH-HAND-NORD-29:** detached-looking Nord torch-grip fragment; package the
  intended race-specific connected models and verify animation/camera coverage.
- **Music Enter regression:** brief cuts entering race/head selection and
  accepting guard-follow on the prison ship; preserve continuous OST while
  retaining world pause. Census-office negative controls remain in the matrix.

Keep the `sn012.bsp` below-2-MiB warning in the open memory/performance work.
Worldwide mushroom placement, persistent picking and exact-package regression
checks remain release requirements. This list does not turn candidates or
reported improvements into completed acceptance.

## Next checkpoint: v0.0.29-rc1

The next playtest checkpoint is **v0.0.29-rc1**, before the final More Mushrooms!
release. This is a planned release candidate, not a published artifact. Preserve
dev4 and its receipts. Include the complete current launchers and required debug
catalogues in rc1; verify exact-package playtests before declaring it ready.
The torch/NPC lighting, hand geometry and Enter-music blockers above still apply
to final release. A newly reported missing torch while testing flame variants
also needs equipment-versus-rendering reproduction before closure.

## Final-release gallery checklist

- Refresh the GitHub main README gallery for the final More Mushrooms release
  with representative screenshots and a few short GIFs from the verified build.
- Show several outdoor regions and mushroom close-ups; include crosshair name,
  `E: Pick`, disappearance and the pickup notification in a short sequence.
- Show torch illumination and hands only after their actual release fixes have
  passed visual checks. Include interiors only when those rooms are admitted.
- Bind each capture to its build/version and scenario. Progress images from
  the dev4 pilot must not imply worldwide release acceptance.
- Keep the active release blockers and roadmap reconciled with actual package
  contents before publication; source checks and conversion are distinct gates.

## Mandatory issue and roadmap reconciliation

Use [BUGS.md](BUGS.md) as the current issue-status index and [ROADMAP.md](ROADMAP.md) for planned scope. Carry open blocker IDs into every release review and record which exact package contains each fix. Source, package and native evidence are separate gates. The final gallery remains a required deliverable from the verified release build.
