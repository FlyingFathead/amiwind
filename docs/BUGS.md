# Bug register

Current work is the [v0.0.29 immediate fixlist](PLAN-v0.0.29.md), following
published v0.0.28. New owner reports and source candidates below remain open
until their own native acceptance; historical passes do not close later reports.
The published release and its immutable artifacts are not modified by this work.

Native Windows build: [WIN-01 — intermittent Python geometry-worker queue failure (open)](BUG_JOURNAL.md#win-01-intermittent-geometry-worker-queue-failure--open-2-october-2026).

Keep reported symptoms separate from confirmed causes. A successful retry does
not close an intermittent report. Historical passing checks remain valid for
the runs they covered; they do not rule out these later incidents.

## Fix index

`Yes` means a shipped correction has supporting verification. `No` includes
unverified candidates. Record owner acceptance separately; never infer a freeze
fix from an unrelated memory correction. Every new report needs an ID, fixed
flag, first fixed version (or an em dash), and evidence/status below.

| ID | Issue | Fixed (Y/N) | First fixed version | Verification / current status |
| --- | --- | --- | --- | --- |
| PERF-READAHEAD-29 | Performance: cell crossing pauses and premature read-ahead cancellation | N | — | Source candidate now predicts the first crossed region; 4 focused source fixtures, target object compile, and integration suite pass. The 1.070–1.149s baseline is a ready/presentation-callback estimate, not proven first-world-frame time. Patched native timing and improvement remain unverified. See [report](performance/CELL-TRANSITION-INVESTIGATION-v0.0.29-dev4.md) and [journal](BUG_JOURNAL.md#perf-readahead-29-cell-crossing-pauses-and-premature-prefetch-cancellation). |
| CHAR-CONFIRM-BORDER-29 | In-game Go back / Choose actions lack OK-style frames | N | — | Dev4 source candidate adds mode2 frames and inset focus to shared character confirmations and travel choices; legacy UI and main/Esc menus preserved. Native appearance pending. |
| TRANSITION-VIEW-29 | Automatic cell handoff forgets mouse orientation | N | — | Exact live view/drift restore candidate passes focused Linux cases; native route/input acceptance pending. |
| VIEW-AUTOCENTER-29 | Walking recenters pitch during free-look; reported orientation reset persists | N | — | An original-engine walk trial showed HUD pitch P:0 after a -10 aim command while still before the next sub-cell threshold; no immediate pre-walk angle readback exists. The default-off option, explicit-centerview path, and no-event guard pass focused Docker fixtures; candidate native acceptance and the yaw cause remain open. See [journal](BUG_JOURNAL.md#view-autocenter-29-forward-motion-recenters-free-look-open). |
| TRANSITION-VOICE-29 | Automatic cell handoff cuts active speech | N | — | Bounded detached PCM candidate passes sanitized actual mixer tests; memory/audible native acceptance pending. |
| TERRAIN-TRAP-29 | v0.0.29-dev1: Player reportedly stuck on rocks beside structures | N | — | Global -21794,-17467,545; screenshot reviewed, exact map/collision/transition cause and runtime reproduction pending. |
| TORCH-INPUT-29 | F cannot raise hands; V only prints torch state | N | — | P1 metadata cause reproduced; all 2,532 corrected world maps pass readback and sampled native F/V checks pass. Full state/save/light matrix remains open. |
| LIGHT-GRADIENT-29 | Unsigned light gradients overflow during surface interpolation | N | — | Source arithmetic repair passes sanitized final-pixel tests across all four mips; native acceptance pending. |
| TORCH-LIGHT-29 | Torch flames look weak and provide little immediate light | N | — | Owner reports torches look weak/dying and night darkness swallows the scene; requests a brighter near-white/yellow core and stronger immediate light while preserving dark unlit nights. AW_FogDraw is a candidate contributor, not a confirmed cause. No fix/acceptance; distinct from intermittent guard-torch visibility. |
| GUARD-TORCH-CYCLE-29 | Guard torch intermittently absent during night-cycle observation | N | — | Owner first observed a nearby guard without a visible torch, then saw the same guard carrying one after reapproaching during the same night. Trigger and cause unverified; do not treat as a confirmed lost cycle. |
| INTERIOR-LIGHT-29 | Interiors lack convincing local illumination | N | — | P2 source-light and bounded renderer study requested; cause/coverage not yet audited. |
| SKY-NIGHT-COVER-29 | Dense night clouds rarely reveal moons/stars | N | — | Owner accepted the current night-sky appearance on 5 October 2026. Preserve that look as the visual regression baseline; exact active config and broader weather/region/performance coverage remain unrecorded or pending. See [journal](BUG_JOURNAL.md#sky-night-cover-29-owner-appearance-acceptance-5-october-2026). |
| HUD-STATS-29 | Health uses fixed 100; other bars hardcoded full | N | — | P2 independent current/max candidate passes actual pixel checks; native acceptance pending. |
| CONSOLE-CAPS-29 | FS-UAE F10 Caps Lock appears stuck | N | — | v0.0.29-dev1 owner report; toggling on/off is an observed workaround. Modifier/focus cause unconfirmed. |
| CONSOLE-WHEEL-29 | FS-UAE console wheel starts working then reports unbound | N | — | v0.0.29-dev1 recurring owner report; preserve initial success then MWHEELUP fallback. Event-routing cause and fix unconfirmed. |
| MODAL-WORLD-29 | Head/race and journal backgrounds consume world work | N | — | Independent saved aw_modal_freeze/aw_modal_black defaults1; original name entry excluded. Soundtrack/UI stay live; revised Linux fixtures and cross-host Amiga binary parity pass; native acceptance pending. |
| SHACK-VISIBILITY-29 | v0.0.29-dev1: Shack near Seyda Neen no longer renders as before | N | — | Owner-reported development regression at global -12917,-71290,98; active chunk, matched baseline and cause unconfirmed. |
| SEYDA-TRANSITION-29 | v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen | N | — | Owner report; reproduce exact crossing and residency/collision state. Fewer sub-cells requested for study, not an established fix. |
| INLAND-SHORE-29 | v0.0.29-dev1: Angular/jagged inland shoreline | N | — | Owner-reported view at global -39785,-30636,379; compare authored LAND/water intersection with conversion. Cause unknown; preserve water placement/height. |
| HORIZON-POP-29 | Ashlands horizon pops or breaks up while turning | N | — | Owner qualitatively reports distant outlines load better in dev3; preserve that as a comparison baseline; occasional fill gaps remain. Opaque-rock far-culling is attributed and an exact probe helps one sample, but OFF baselines differ in 17,565/48,640 pixels (36.11%). Horizon gaps, popping, matched-view replay, and performance remain open. |
| MAP-TELEPORT-28 | F10 map teleport intermittently fails | N | — | Shared handler and hidden-HUD correction pass C checks; both aliases open the same picker in sampled native replay. Landing/full-state acceptance pending. |
| MAP-SPOTS-28 | In-game map screen has white/yellow spots | N | — | AWM1 palette remap omission found; pixel/ocean remap candidate passes focused Windows/Linux checks. Target map pending. |
| MAP-VIEW-SWITCH-28 | Mouse cannot switch DEBUG / IN-GAME map views | N | — | Overlay and event-order fixes pass focused C checks/Amiga builds. Emulator replay shows oversized guest deltas; manual mouse acceptance pending. |
| MAP-RIGHT-DRAG-29 | Advertised right-drag does not pan teleport map | N | — | Amiga right/middle mismatch reproduced; local two-button fix passes fixtures and builds. Manual native acceptance pending. |
| TREE-PILLAR-28 | Sprite-tree roots extend into unintended striped pillars | N | — | Scaled/authored-origin sampling mismatch reproduced: 90/105 bad pixels before; seven raster cases pass after. Native tree acceptance pending. |
| SKY-GROUND-28 | Rebuilt LAND faces invisible; clouds scroll too fast | N | — | Native winding repair restores ground in bounded town views; current cloud multiplier is 0.00333333333. Final route/motion acceptance pending; [journal](BUG_JOURNAL.md#sky-ground-28-pale-ground-and-excessive-cloud-speed-open). |
| SKY-STARS-28 | Enlarged stars cover original night artwork | N | — | AWN2 point roles limit stars to one pixel behind nebula and full moon masks. Focused fixtures pass; native views pending; [journal](BUG_JOURNAL.md#sky-stars-28-enlarged-stars-and-night-layer-ordering-open). |
| ARRIVAL-CEILING-28 | Coordinate arrivals start inside solid ceiling shell | N | — | Bounded clear-start search passes four actual owned hull cases; dynamic/native routes pending; [journal](BUG_JOURNAL.md#arrival-ceiling-28-coordinate-arrivals-blocked-by-solid-ceiling-shell-open). |
| DOC-STATE-01 | Published release documentation retained stale candidate/current-version claims | N | Main-branch correction pending | Local editorial repair; published v0.0.27 tag/assets preserved. See [journal](BUG_JOURNAL.md#doc-state-01-published-v0027-described-as-an-unpublished-candidate-documentation-bug). |
| CI-01 | Windows short aliases mismatch resolved discovery paths in tests | Y | v0.0.26-rc1 | Assertions corrected; local short-alias regression and subsequent hosted Windows parity passed. See [journal](BUG_JOURNAL.md#ci-01-windows-short-path-aliases-fail-host-discovery-assertions). |
| WIN-03 | Windows image-packing command exceeds process limit | Y | v0.0.26-rc1 | Windows batching passed 1,100-file readback, four regressions and complete image readback/WinUAE game entry; [journal](BUG_JOURNAL.md#win-03-windows-image-packing-command-exceeds-process-limit--validation-pending-2-october-2026) |
| WIN-02 | Cancelled Windows stage leaves child workers alive | N | — | Process-tree cleanup candidate tested separately; integration pending; [journal](BUG_JOURNAL.md#win-02-cancelled-windows-stage-leaves-worker-descendants--open-2-october-2026) |
| WIN-01 | Native Windows Python geometry-worker queue failure | N | — | Intermittent invalid semaphore handle; cause unknown; [journal](BUG_JOURNAL.md#win-01-intermittent-geometry-worker-queue-failure--open-2-october-2026) |
| AW-20260928-01 | Ship-exit intermittent freeze | N | — | Open; retry succeeded, cause unknown |
| AW-20260928-02 | Dock/menu freeze and looping audio | N | — | Open; third run remained stable |
| AW-20260928-03 | Silt Strider landing geometry | N | — | Expanded bounds and missing rock restored; Strider/Darvame now present; exact-view acceptance pending |
| AW-20260928-04 | Invisible barriers across plank | Y | v0.0.21-dev2 | Focused native passage/containment passed; owner acceptance pending; pier escape below remains separate |
| AW-20260928-05 | Dock guard misses approach interception | Y | v0.0.21-dev3 | Feet-anchor regression and focused FS-UAE automatic approach/race passed; full escort route remains open |
| AW-20260928-06 | Player can leave pier and become stranded | N | — | Owner report; join/edge coverage under investigation |
| AW-20260928-07 | Slow opening exterior / excessive residency | N | — | Profile rendering and memory; reduced opening exterior planned |
| AW-20260928-08 | Census wall/hanging texture quality or mapping | Y | v0.0.21-dev3 | Confirmed class-art downsampling loss corrected; source art verified and native view inspected; other mapping faults not ruled out |
| AW-20260928-09 | Papers unreadable | Y | v0.0.21-dev3 | Native reading/paging: black text on a plain light page; current world palette maps requested white to warm off-white |
| AW-20260928-10 | Interior door animation and sound missing | N | — | Hall door snaps open; source motion/sound sequence pending |
| AW-20260928-11 | Census missing floor and wall / falling into void | Y | v0.0.21-dev3 | Original room172861 restored; 306-sample scan and native standing at reported hole pass; separate out-of-bounds report remains open |
| AW-20260928-12 | Downstairs interior doors cannot open | N | — | Ordinary hinged-door interaction not implemented; only opening hall special case exists |
| AW-20260928-13 | New Game confirmation defaults to Cancel | Y | v0.0.21-dev3 | Main/pause host checks and native confirmation/start passed |
| AW-20260928-14 | Master debug toggle omits coordinates | Y | v0.0.20 | Host regression checks on/off and explicit coordinate override |
| AW-20260928-15 | Prison wave ambience masks dialogue | Y | v0.0.20 | Historical -5 dB correction; superseded by dev2 authored gain after new quiet-wave report |
| AW-20260928-16 | Two compiler-reported array bounds violations | Y | v0.0.20 | Sanitizer reproductions and corrected production routines |
| AW-20260928-17 | FS-UAE 24-bit-addressing option rejected | Y | v0.0.20 | Preset corrected against FS-UAE parser; unrelated freezes remain open |
| AW-20260928-18 | Punch blocked after Census office exit | N | — | Candidate: hall fighting gate separated from opening enclosure; post-exit native check pending |
| AW-20260928-19 | Courtyard barrel incorrectly says empty | Y | v0.0.21-dev3 | Final native build: Take ring, inventory ring present, then Empty; host checks persisted depletion and no refill after losing the ring |
| AW-20260928-20 | Census clipped outside room near captain wing | N | — | Owner screenshot XYZ201,-210,0; route/cause unconfirmed; separate from restored room172861 |
| AW-20260928-21 | Exterior Census door/wall overlap | N | — | Owner screenshot XYZ396,-171,39, heading170, pitch-3; cause and FPS impact unmeasured |
| AW-20260929-01 | Player passes through town NPCs | Y | v0.0.23-dev2 | Shared solid-body spawn path; real engine swept-box checks and native Fargoth approach stop |
| AW-20260929-02 | NPCs missing from expanded town render | Y | v0.0.23-dev2 | 256-entry draw list exhausted; full bounded list and 8,192 visibility links; Darvame/Fargoth captured |
| AW-20260929-03 | Music cuts during loading | Y | v0.0.23-dev2 | Buffer-clear protection, bounded loader servicing; repeated transitions keep track open with no post-startup underruns in tested runs |
| AW-20260929-04 | Loading artwork flashes after intro movie | Y | v0.0.23-dev2 | One-shot blank style; native transition sequence contains all-black loading frames, then ship |
| AW-20260929-05 | Ship waves too quiet | N | — | Loop confirmed running; extra -5 dB reduction removed in dev2; owner listening acceptance pending |
| AW-20260929-06 | Expanded scene exhausts 9 MiB heap | Y | v0.0.23-dev2 | Removed redundant plane allocation; 11 MiB heap inside unchanged 16 MiB Fast RAM profile |

## 29 September dev2 notes

The expanded footprint retains rock reference 309452 (`terrain_rock_bc_18`). Its
origin lay outside the previous selection cutoff while the rock geometry crossed
into the playable area. Full-bounds selection now retains it. The exact reported
view is XYZ 211,447,47 / heading 4 / pitch 0; the candidate has been captured, but
owner acceptance is still required before closing AW-20260928-03.

A further port viewpoint exceeded the 10,240-surface buffer. The final image
raises the bounded surface/edge pools to 12,288 / 24,576 within the same reference
hardware profile. This is distinct from missing terrain assets and entity links.

The quieter wave report supersedes the earlier balance request: the two original
placed loops were active, but carried an extra hardcoded -5 dB reduction. Dev2
removes only that additional gain reduction, retaining the source sound volume,
script multiplier and spatial falloff. `soundinfo` now lists live channels and
their mixed volumes/positions for diagnosis. User listening feedback remains the
acceptance criterion; an active loop alone does not prove the desired balance.

The loading fixes apply to common map, restart/changelevel, file, BSP/model and
entity-spawn work. They do not prove that every future blocking operation is
bounded, or resolve the older intermittent freeze reports.

## AW-20260928-01: potential prison-ship exit freeze during intro

**Status:** Open; intermittent owner report; cause unknown.

- Reported on 28 September 2026, initially at 15:21 Helsinki, against the
  current v0.0.19 work, using **FS-UAE 3.1.66**.
- During the introductory prison-ship sequence, attempting to exit through the
  hatch froze the game. The supplied screenshot shows the interior hatch with
  the **Seyda Neen / E: Enter** prompt.
- At 15:28 Helsinki, the owner reported that the second attempt worked normally.
  The exact restart/retry procedure and how long the first freeze lasted were
  not recorded. Reproducibility and frequency are not established.
- The owner's exact HDF/executable hashes and full emulator settings were not
  supplied with this report. Do not infer a cause from the emulator version.

**Next investigation:** Repeat New Game, intro, hatch exit and return cycles;
record speech/escort state, transition progress and elapsed load time. Check
whether input and the emulator remain responsive during the reported stall.

## AW-20260928-02: potential dock/menu freeze with looping music

**Status:** Open; owner report; cause unknown; relationship to the hatch incident
is unconfirmed.

- Reported on 28 September 2026 at 15:33 Helsinki, during the same v0.0.19
  investigation. The owner reports the same machine and **FS-UAE 3.1.66**.
- After successfully reaching the dock, the owner opened the menu and remained
  there for a while. It then froze and the music began looping.
- At 15:34 Helsinki, the owner clarified the audio symptom: a short fragment
  kept repeating like a stuck vinyl record, possibly what remained in the audio
  buffer. Buffer repetition is the owner's inference, not a verified diagnosis;
  this was not described as normal whole-track repeat.
- The exact menu/submenu, idle duration and repeatability were not recorded.
  Whether the game alone or the emulator stopped responding remains unknown.
- Keep this incident distinct from ordinary music playback while a menu is open.
  The reported fault is the freeze together with the looping audio.

- At 15:40 Helsinki, the owner reported a third attempt on the same machine
  and emulator setup: reached town and running normally so far. This is an
  ongoing successful run, not a completed stability test or closure. At 15:42,
  the owner added that town exploration had continued for some time without
  issues. At 15:44 the owner reported continued successful roaming, including
  render-heavy town views. This weakens a simple rendering-load explanation,
  without excluding a transition-triggered fault or emulator issue.

**Next investigation:** Leave the menu open after ship exit for repeated timed
runs, including a natural music-track change; record the current track, menu
state, input responsiveness and audio-buffer/clock progress.

## Emulator launch evidence (28 September, 15:44 Helsinki)

The owner launched `AmiWind-v0.0.19-FS-UAE.fs-uae` using FS-UAE 3.1.66 on Linux
x86-64. The log reports a WinUAE 3300b2-derived core and Kickstart 3.1 A1200
revision 40.68. Full settings and image hashes remain unconfirmed.

- `schedutil` CPU governor warning: possible emulation frame-rate impact;
  insufficient evidence for a hard-freeze diagnosis.
- `Option failed: address_space_24 = false`: confirmed preset typo. The FS-UAE
  3.1.66 `src/cfgfile.cpp` parser accepts `cpu_24bit_addressing`, so the v0.0.20
  preset uses `uae_cpu_24bit_addressing = false`. The launcher reads that preset.
  Historical version presets remain unchanged. This correction is not evidence
  that the ignored option caused either incident.
- `my_resolvesoftlink` stub and `res_initcode context = (nil)` were also present;
  the supplied startup excerpt does not locate the later freeze.
- FS-UAE's official site lists 3.2.35 as the current release on this date. A
  comparison run with the same HDF/settings is useful, but upgrading is not a
  demonstrated fix. Keep the older-version reports open.

Primary references: [FS-UAE 3.1.66 configuration parser](https://github.com/FrodeSolheim/fs-uae/blob/v3.1.66/src/cfgfile.cpp)
and [official releases](https://fs-uae.net/).

## Debug overlay coordinates

Owner report at 15:45 and requested behavior at 15:46 Helsinki: `debug overlay
on` should also enable `debug coords on`. Version 0.0.20 makes every valid explicit
master enable restore coordinates, including all existing aliases. Queries and
invalid input do not reset the coordinate selection. Every valid master-off also
sets coordinates off (owner clarification at 15:54); a subsequent
`debug coords off` still works. Startup overlays remain off. Host HUD regression
coverage checks the default and explicit override behavior.

## Memory-lifetime hypothesis (unconfirmed)

At 15:36 Helsinki, the owner suggested that the prison interior might not be
properly released after leaving the ship. This is a valid investigation lead,
not an established diagnosis.

The native C engine uses explicit memory management. `SV_SpawnServer()` calls
`Host_ClearMemory()`, which flushes renderer caches, calls `Mod_ClearAll()` and
frees the old level's low hunk to `host_hunklevel`; it also clears server/client
state. Some alias models remain in the reusable model cache by design. These
source paths establish the intended cleanup, not proof that every retained
reference or failure path is correct. Check stale map/actor pointers, cache
ownership, allocation failures and memory totals across repeated transitions.

The short repeating audio fragment is consistent with the update/mixing loop
stalling while buffered audio continues. It does not distinguish memory
corruption, a deadlock, an I/O stall or an emulator problem. Do not label either
incident a garbage-collection failure or blame FS-UAE without reproduction.

## Ship ambience / dialogue balance

Owner report, 28 September 2026 at 15:37 Helsinki: wave/hull ambience inside the
ship overwhelms dialogue. Requested reduction: at least approximately 4-5 dB.
Version 0.0.20 applies **-5 dB** (amplitude factor 0.5623413) to both authored
hull-loop channels **in the runtime mixer, only in the prison interior**.
The original audio file, converted samples and authored emitter values are
unchanged. The same sample elsewhere, other effects, dialogue and music retain
their existing gain. This follows the owner's explicit scope correction at
15:39 Helsinki; no source-file or converter attenuation is applied.
The owner should assess dialogue clarity in a listening playtest. This audio
balance adjustment is separate from the unresolved freeze incidents.

## Compiler-warning findings

The v0.0.19 reference build emitted 95 compiler warnings with the recovered
GCC 16.2-rc11 toolchain. Review found two confirmed C array-row bounds violations:
`Mod_LoadTexinfo()` indexed `[0][0..7]` in a `[2][4]` array, and
`R_EntityParticles()` indexed `[0][0..485]` in a `[162][3]` array.
Bounds-sanitized execution reproduced both violations. Version 0.0.20 accesses
each declared row correctly and preserves the intended texture values and
particle random-number sequence. Regression coverage exercises the production
routines under the sanitizer. Neither correction is a proven cause/fix for the
reported intermittent freezes. Remaining warnings are documented in the handoff.

## AW-20260928-03: persistent Silt Strider-port geometry and missing occupants

**Status:** Open; owner confirms persistence in v0.0.19 at 15:50 Helsinki.

Screenshot `image(7).png` shows an arch-like textured surface with large exposed
space beneath it near the Seyda Neen Silt Strider landing. Camera is **XYZ 260,
417, 30; DEG 11; P -19**. The owner describes missing ground-texture portions
and is unsure whether boulders or other geometry should fill the area. The Silt
Strider and driver are also absent. This follows earlier viewpoints documented
in SEYDA_NEEN_NEXT_STEPS.md; it is not a new confirmed regression.

The source selection audit already established that ACTI `a_siltstrider` is
omitted by the scenery selector. `tools/scenery_selection.py` selects ordinary
STAT/DOOR plus explicitly grouped ship ACTI. Town actors are explicitly limited
to Fargoth and two Imperial guards by `tools/prepare_npcs.py`; the intro pass does
not add the strider operator. The owner clarified at15:52 that the strider and driver have simply not been
implemented; treat them as planned content, not a disappearing-actor bug. This
does not explain the malformed surface. Do not claim that adding the strider will repair the landing.

**Next investigation:** Compare original LAND and placed STAT/ACTI meshes at the
reported camera, including adjacent cells, visibility, face winding and
simplification. Identify the surface by source record/reference before changing
geometry. Convert the strider and operator as separate source-backed candidates;
travel-service scripting remains separate. The v0.0.20 maintenance image retains
the existing scene assets and does not resolve these visual omissions.

## Investigation baseline and limits

- Live repository inspected at commit
  `3305c9861718553acdbec76f825bfad884e0bb94` (v0.0.19).
- Recovered the matching v0.0.19 private playable, source, handoff and prior
  emulator harness. Current `engine/` files match that recovered source byte
  for byte; the current source also compiles for 68040/FPU.
- Prior v0.0.19 native acceptance focused on music-notice toggling. Hatch/menu
  evidence was inherited from earlier checkpoints, not an extended soak test.
- Neither reported freeze has been locally reproduced or diagnosed at the time
  of this documentation update. No fix for the reported freezes or stability clearance is claimed.

## AW-20260928-04: opening plank blocked by incorrectly rotated barriers

**Status:** Confirmed converter defect; v0.0.21-dev2 correction passed focused
local native plank passage/containment checks; owner confirmation pending. Reported against v0.0.21-dev1.

The invisible opening enclosure obstructed the plank and could redirect the
player into the sea. Compound reference rotations were applied in the wrong
order. Keep the original references and their `CharGenState` condition; correct
world-space orientation. Passage to the dock guard and office must coexist with
sideways containment and courtyard gates. See [journal J015](IMPLEMENTATION_JOURNAL.md#j015--opening-invisible-barriers-crossed-the-plank-v0021-dev1)
for failed coverage, candidate change and verification status.

## AW-20260928-05 through 13: opening playtest, 28 September

- **05 — Dock interception:** owner reports the guard does not catch the player
  as in the original. The source `GetDistance Player < 108` requires automatic
  interception, followed by controls disabled, speech and race selection. Native
  NPC origins are feet; the player origin is body centre. The old mixed-anchor
  distance incorrectly reduced the effective approach radius. The candidate
  compares feet positions in full 3-D and retains the original quarter-scale 27
  unit threshold. Regression fails against dev2, passes candidate. Owner reports
  the character-selection functionality itself otherwise works reasonably well.
- **06 — Pier escape:** player can fall off and cannot climb back. Do not close
  this based on the earlier plank fix or centre-of-pier samples. Check seams,
  ends and diagonal movement, before/after race selection, with normal walking.
- **07 — Performance:** owner reports poor dock frame rate and requests a
  physically smaller, radius-bounded opening exterior. Measure frame-stage time,
  resident map/model/texture memory and transition peaks. Fog is not unloading.
- **08 — Textures:** screenshot `image(9).png` shows indistinct wall hangings.
  Source NIF materials resolve to owned DDS files with matching source hashes.
  256x512 tapestry inputs were reduced to 16x32 before the BSP conversion;
  plaster was reduced from 256x256 to 32x32. Check final UV/texture association,
  palette and lightmap output as well as resolution before closing.
- **09 — Reading:** screenshot `image(10).png` shows text overlapping curled
  parchment edges and low-contrast glyph edges. Candidate uses a clear white
  surface, black text and grayscale antialiasing; preserves existing font assets.
- **10 — Door feedback:** interior doors lack an opening animation/audio sequence.
  Implement authored hinge/pivot, angular travel, collision while moving and
  source open/close sounds; retain locked/scripted conditions.
- **11 — Floor/wall:** owner fell below the Census floor after a door, at
  XYZ166/171/0, DEG61, P-61; later localized the missing area with
  XYZ127/206/0, DEG349, P-70. A third view at XYZ46/192/65, DEG39, P8
  shows the missing wall behind a cupboard. Images were inspected directly;
  supplied OCR misread several coordinates. The converter excluded source
  reference172861, ACTI `chargen stuff room`, using a normal room mesh. Its
  script supplies item/tutorial messages and does not make its architecture
  optional. Restore source floor/walls and collision; do not paste a guessed
  platform over the gap. This geometry must remain after chargen completion.
- **12 — Downstairs doors:** owner cannot open the downstairs doors. This is
  separate from animation and from the missing architectural room section.
- **13 — New Game default:** owner requests affirmative selection when opening
  the New Game confirmation. Candidate also aligns its initial mouse anchor.

NPC idle vocalizations/whistling are requested future behavior, not a confirmed
regression. Preserve silence/voice cooldown and dialogue/intro priority when the
ambient NPC scheduler is implemented.


## AW-20260928-18: fists can be drawn but punches are blocked

Owner reports no punching even after exiting the Census office, not only during
registration. Confirmed code cause for pre-release exit: `AW_IntroButtons`
returned zero whenever `CharGenState` was still active, even though the original
hall-guard script enables fighting after accepting papers. Drawing used a
different, less restrictive gate. Candidate correction gives both the same
persistent fighting permission and retains temporary menu locks. Test office,
courtyard and final release separately; a pre-release fix alone is not proof of
the owner's complete post-release report. Actual combat damage remains absent. The owner's later console capture also
reports `MOUSE3 is unbound`: this native port maps MOUSE3 to the right button,
while MOUSE1/left is the default attack binding. Keep that input observation
separate from a claim that every post-release punch failure has been reproduced.

Dev3 focused native checks pass after hall paper acceptance and in demo state:
F draws hands and left click enters the punch state. The host regression also
checks released-state inputs. Keep this report open until the natural
post-captain exit is reproduced and tested on the owner's route.

## AW-20260928-19: false empty courtyard barrel

Owner reports the outside barrel says empty although it should hold Fargoth's
ring. Prior code treated a mismatched tutorial stage as empty and inferred
contents from current player possession. Corrected candidate uses a persisted
placed-container depletion fact and atomic item transfer. It works outside the
courtyard UI stage and cannot refill when the ring leaves player inventory.
Full loot UI and the later return-to-Fargoth dialogue are still unimplemented.

Final dev3 native check on FS-UAE 3.1.66, demo state: player in WALK mode at
117,-78,56; hint offers Take ring; E reports the Engraved Ring of Healing taken,
the state diagnostic reports ring present, and a second E reports Empty.
This verifies the stage-independent pickup; it does not certify the natural
tutorial route or the unimplemented Fargoth return dialogue.

Additional room evidence: owner screenshot at XYZ45,220,65, heading1, pitch8
(v0.0.21-dev2) shows the missing wall behind the left bookcase. This accompanies
AW-20260928-11, not a new independently diagnosed geometry fault.


## AW-20260928-20: clipped Census captain-wing view

Owner screenshot v0.0.21-dev2: XYZ201,-210,0, heading118, pitch-25. The view is
outside/below room geometry. The immediately preceding movement and noclip state
are not recorded, so do not attribute this second location to omitted room172861
without checking. Retain it as a separate reproduction point. Requested runtime
out-of-bounds poller/last-safe-position recovery is a safeguard roadmap item;
source collision and door-arrival faults must still be repaired directly.


## AW-20260928-21: overlapping Census exterior door geometry

Owner v0.0.21-dev2 screenshot shows a horizontal opaque strip over the central
part of the exterior door at XYZ396,-171,39, heading170, pitch-3. Visible fault
confirmed from the supplied image; duplicate/coplanar faces, an overfilled
simplified wall/recess, depth ordering and source placement remain candidate
causes. The owner suspects a frame-rate cost, which is not yet benchmarked.

Requested experiment: host conversion `door_priority` boolean, planned default
true after implementation/validation, with false preserving the baseline. Audit the
door, frame and adjoining architecture as an assembly; preserve real apertures
and remove only proven duplicate/fully covered faces or overfilled proxies.
Do not implement unconditional draw-on-top, flatten unrelated geometry, or
remove collision needed for walls and moving doors. Preserve the baseline recipe
and compare face/edge counts, identical-camera timing, visible opening/closing,
wall occlusion and walkability. The flag is planned, not an implemented switch.


AW-20260928-21 owner clarification: the same protruding-wall defect occurs at the
other Census exterior exit. Desired conversion tool performs an oriented,
door-shaped cut in intruding wall geometry, leaving the door in its proper
aperture. This is a reusable assembly operation with a changed-face report,
not just a visual priority flag. Both exits must be checked before closure.


## 29 September 2026 owner report: intro sea ambience

The owner reports the splash/wave sound in the starting ship scene is almost
inaudible or absent in recent builds, including the supplied v0.0.22 source line.
The earlier intentional 5 dB ship-only reduction is present, but is not yet
proven to explain the reported silence. v0.0.23-dev1 preserves the audio runtime.
Next: verify the converted wave sample and loop cue, placed emitter records,
spatial attenuation and mixer channels during the actual New Game path. Restore
audibility without drowning dialogue or global music. Owner acceptance pending.


## Owner dev2 feedback — 29 September 2026

Deck/pier sideways escape during creation and missing interior door open/close
squeaks remain open in dev3. The owner confirms improved pier guard orientation
and working ship-to-Census progression; preserve those behaviours. Full report,
UI dispositions and reproduction gates: [FEEDBACK-v0.0.23-dev2.md](FEEDBACK-v0.0.23-dev2.md).

## dev3 feedback follow-up — 29 September 2026

The reported Vodunius-house visibility holes and the misrotated port rock are
addressed; see [terrain findings and workflow](WHAT_ARE_ROCKS.md). Voice style 2
now defaults to aim-only identity, overriding voiced speaker headers.
NPC conversation-facing, deck/pier sideways containment and door squeaks remain
open in [the consolidated dev2 feedback](FEEDBACK-v0.0.23-dev2.md).

## dev3 regression retest / dev4

Owner confirms the port rock is fixed. Newly reproduced and corrected: tree
sprite background-depth rejection; Darvame dropping under the platform before
static scenery spawns; uneven dialogue padding; ornamental caret/rotation glyphs;
startup theme/timing; missing optional opening quote overlay. See
[the full feedback table and trials](FEEDBACK-v0.0.23-dev3.md).
These focused checks do not close unrelated open items above.

## RC1 remaining acceptance items — 30 September 2026

The coordinate-by-coordinate record is in
[INVESTIGATION-v0.0.24-rc1.md](INVESTIGATION-v0.0.24-rc1.md). Keep these open:

- stairs10 at -685,+619,141: reported origin is inside terrain; do not silently
  substitute the older negative-Y report or call it a passed staircase.
- wedge1 at -225,348,131: exact trapped state not yet reproduced; nearby native
  retreat works only after lateral placement recovery.
- Full natural intro and owner city-roaming acceptance; physical Amiga, Windows
  and subjective audio checks have not been established by Linux null-audio runs.

NPC greetings, room population and entrance traversal are implemented; full
services, wandering/combat and quest behavior are not implied by their presence.
