# Bug register notes: v0.0.29 and earlier

Frozen history: dated notes moved from the bug register on 7 October 2026,
unchanged apart from link paths. Current status is in [the register](../BUGS.md).

## HARVEST-BITTERCOAST-29: one of three nearby mushrooms usable, 6 October 2026

Open RC2 playtest report in **Bitter Coast**: only one of three nearby mushrooms
could be eaten. The player tentatively identifies them as Luminous Russula but
also asks whether the other two are different types. Species and interaction
stage are unverified; do not assume that picking, harvesting and inventory
consumption are the same failure.

The original screenshot shows v0.0.29-rc2, global XYZ approximately
**-15287 -59485 735**, game time **02:39**. Obtain map and original reference IDs,
identify all three objects, and replay both pickup and inventory use. The cause
and fixed version are unknown. [Issue and reproduction](../bugs/HARVEST-BITTERCOAST-29.md).

## Latest scoped RC2 playtest confirmations: 6 October 2026

The RC2 playtest was released on 6 October. Its source and executable remain
the exact tested snapshot; later full-release preparation is tracked separately.

- **CENSUS-DOOR-STUCK-29:** the player confirms the Census door no longer traps
  them in the reported case and displays the obstruction message. This accepts
  that reproduction in RC2; other occupied/clear positions, save/reload, return
  paths and long-term door behavior remain to be exercised.
- **LIGHT-EXTERIOR-JUMP-29:** the player confirms the reported sudden brightness
  increase near the Seyda Neen shack is gone in RC2. The original reproduction
  and coordinates remain recorded. This does not establish all-world coverage.
- **HAND-PUNCH-COVERAGE-29:** a High Elf punch playtest reports no exposed gaps.
  Sex was not specified. This supports the maximum-extension aperture repair
  in that sampled appearance; brief idle-to-punch disappearance remains open.
- **Torch appearance:** the player reports that the torch is very good at the
  default settings. This does not close outdoor tuning, style-3 embers, dark-room
  floor, unlit/fuel-state or broader actor-lighting coverage.
- **INTERIOR-LIGHT-29:** the player describes the game's luminance as much more
  tolerable. Their exact factors were not supplied. Do not infer an exterior
  brightness change: defaults remain interior 1.2x and exterior 1.0x. Static-NPC
  sampling and broader performance checks remain separate.

WinUAE guard-follow, race-selection and heavy-load music continuity remain open,
including the reopened appearance-entry report below. Temple holes remain open.

## Latest v0.0.29-rc2 playtest report: 6 October 2026

- **AUDIO-APPEARANCE-29 is reopened:** the current WinUAE playtest reports
  background-music pauses on entering the rotating character race-selection
  screen. The earlier RC1 report that this entry was fixed remains historical
  evidence; it does not establish the current build's continuity.
- **AUDIO-ENTER-29 / AUDIO-LOAD-29 remain open:** the current WinUAE playtest
  still reports music crackle and pauses, including Enter to follow the guard.
  Heavy-load continuity also remains unresolved. Nonzero FS-UAE audio and
  synthetic streaming checks do not prove WinUAE continuity at these events.
- **INTERIOR-LIGHT-29:** the player reports that luma is much more tolerable
  with the current settings. The exact factor was not supplied. This is a
  subjective visual improvement, not a new default selection or a resolution
  of static-NPC sampling, broader performance, or Temple geometry. Defaults
  remain interior 1.2x and exterior 1.0x.

These reports supersede conflicting current-status claims below while retaining
their dated history. No audio repair or full-release readiness is claimed.

## Current RC2 issue status: 2026-10-06T19:08:08+00:00

[Implemented repairs, demonstrated cases and still-open issues](../RC2_ISSUE_CHECKPOINT.md).
This dated checkpoint supersedes older candidate status below. Delivery and
final extracted-package launch are still pending; Temple holes remain open.

## INTERIOR-LIGHT-29: RC2 measured checkpoint, 6 October 2026

Native menu changes and saved settings passed. Census renderer medians at
1.0x/1.2x were 1.175745/1.189845 s per128frames (+1.199%, +0.110 ms/render).
Only three alternating pairs; broader gameplay, enabled/disabled, night, RAM
and physical-Amiga performance remain open. Latest defaults are interior1.2
and exterior1.0; earlier dated debug-only plans are superseded.
[Full method, samples and remaining work](../bugs/INTERIOR-LIGHT-29.md).
These post-snapshot notes do not change the measured RC2 executable.

## Follow-up evidence and open reports: 2026-10-06T20:06:10+03:00

Delivered v0.0.29-rc1 remains unchanged. Candidate 004 passed 1,047 tests with
zero failures/errors and four skips, and the Amiga build. A fresh FS-UAE session
then demonstrated an actual Argonian Female punch at maximum extension, torch
off/on/off after appearance selection, and return to the ordinary story state.
The original maximum-extension aperture was absent in the sampled view. Normal
pre-Census restrictions were retained outside the explicit test rooms. Engine
and map readback matched the candidate; the session closed to AmigaDOS.

- HAND-PUNCH-TRANSITION-29: new owner report against the proposed-fix punch clip:
  hands briefly disappear when changing into the punch animation. Reproduce the
  idle-to-punch transition frame by frame, including first attack and repetition.
  Cause and repair are pending. This is separate from maximum-extension coverage.
- PUNCH-AUDIO-COVERAGE-29: inventory original punch swing/hit samples, converted
  equivalents and gameplay event wiring. Availability of every sample is not yet
  verified. Keep swing, hit and any material/target distinctions explicit.
- Torch appearance: owner approves the new appearance. This does not close the
  dark-room gray floor, outdoor surface strength or fuel/unlit-state reports.
- BALMORA-TEMPLE-GEOMETRY-29: exported planes are a confirmed contributing defect;
  the Temple-only candidate passes 23 focused checks. Rebuilt-map/native repair
  verification and the full geometry/collision issue remain open. See the
  [Temple issue](../bugs/BALMORA-TEMPLE-GEOMETRY-29.md) and
  [import guidance](../MESH_TIPS_AND_TRICKS.md).

First shipped fixed version for these follow-up candidates: none. The transition
and audio requests remain pending; a status answer does not complete them.

## Follow-up validation checkpoint: 2026-10-06T18:49:45+03:00

The post-RC1 repair candidate passes the full 1,047-test suite with zero failures
or errors and four documented skips, plus the Amiga build. It is not delivered.
The exact engine is `dfe02d4620766cbcf3449d41d48036b3fafcc7e4a35a89616ea38dc2195c53e2`.

- HAND-PUNCH-COVERAGE-29: bounded FS-UAE observation shows the default appearance
  at maximum extension, animation frame 25, without the previous proximal
  near-plane aperture. Additional captured appearances and final readback remain
  subject to review. First shipped fixed version remains none.
- DEBUG-GALLERY-TIMING-29: combat hands, punching and return to the ordinary map
  work in the observed native session. Torch-room hands now appear, but V did not
  equip/light a torch in that run. Full torch/state acceptance remains open.
- BALMORA-TEMPLE-GEOMETRY-29: lower-room missing regions reproduced in FS-UAE.
  Source placement/triangle preservation and loader checks pass, but the runtime
  defect remains. Changed surface ordering/culling did not restore structures;
  counters do not show surface/edge exhaustion. Cause and fixed version unknown.

These observations do not close the remaining WinUAE music/load issues, normal
walking acceptance of Seyda lighting boundaries, Temple collision, torch-room
darkness or incomplete content coverage. Delivered RC1 remains unchanged.

## Current RC1 regression checkpoint: 2026-10-06T15:03:42+00:00

Delivered playtest remains **v0.0.29-rc1**. The later combined source passed
1,046 checks (four documented skips) and its Amiga build, then underwent a
bounded FS-UAE check. Passing those gates did not close every reported bug.
No subsequent package or first shipped fixed version is established below.

| Issue | Current evidence and state | Next acceptance gate |
| --- | --- | --- |
| [BALMORA-TEMPLE-GEOMETRY-29](../bugs/BALMORA-TEMPLE-GEOMETRY-29.md) | Cause identified 7 October 2026: the scenery converter applied the NIF root node rotation, which Morrowind ignores, turning Velothi kit walls 90 degrees. Candidate converter repair and rebuilt Temple map (v0.0.30-dev) match OpenMW at the reported entrance views in FS-UAE. Not shipped or owner-accepted. | Walk and collide through the whole lower level; rebuild other affected maps (Tharys Ancestral Tomb, fireplace interiors); owner playtest. |
| [CENSUS-ENTITIES-30](../bugs/CENSUS-ENTITIES-30.md) | v0.0.30-dev5 Census office: upright rug (black hole seen in the ceiling below), tapestry inside a bookshelf. The dev5 lighting rebuild paired an older object list with the dev3 geometry; 67 of 140 objects used the neighbouring model. Fixed in v0.0.30-rc1 (dev4 object list plus dev5 flames). Not owner-accepted. | Owner playtest of the Census office in rc1. |
| [INTRO-ROLES-30](../bugs/INTRO-ROLES-30.md) | `NUM_FOR_EDICT: bad pointer` crash on a Seyda Neen region change: intro role pointers outlived a map reload. Repaired in v0.0.30-dev4 (stale roles dropped before use); scripted route crashed 2/2 on dev3, 0/3 repaired. Not owner-accepted. | Full opening played through with region changes; owner playtest. |
| [CONVERTER-ROOT-ROTATION-30](../bugs/CONVERTER-ROOT-ROTATION-30.md) | Converter applied NIF root-node rotations that Morrowind ignores. Rebuilt: Balmora Temple, Tharys Ancestral Tomb, five Seyda Neen fireplace interiors. Pending: one Balmora exterior placement. Not yet shipped. | Walk-through of rebuilt interiors; Balmora exterior rebuild; owner playtest. |
| LIGHT-EXTERIOR-JUMP-29 | Brightness discontinuity at the reported Seyda Neen shack | Y | v0.0.29-rc2 | Empty-versus-unused lightdata correction passes six focused checks. RC2 playtester confirms the reported shack brightness jump is gone. This is scoped to that reproduction; wider town/world traversal coverage remains. [Original boundary evidence](../BUGS-v0.0.29-RC1.md#repeated-boundary-evidence-6-october-2026). |
| HAND-PUNCH-COVERAGE-29 | Near-plane opening at maximum punch extension | Y | v0.0.29-rc2 | Sampled default and Argonian Female native views show no prior aperture; RC2 High Elf playtester also reports no exposed gaps, sex unspecified. Brief idle-to-punch disappearance and full race/pose coverage remain separate. |
| [DEBUG-GALLERY-TIMING-29](../bugs/DEBUG-GALLERY-TIMING-29.md) | New candidate defect reproduced natively in combat/torch rooms: hands unavailable due to invalid animation timing. Pre-activation callback incorrectly requires active server. Regression fails before repair; six focused checks pass after the narrow fix, with no skips. | Full candidate gates, then native hands/punch/torch/state-return checks. |
| TORCHTEST-DARKNESS-29 | Separate open candidate defect. Zero light samples still show dim gray floor because palette generation enforces a 15% minimum. | Room-scoped darkness policy and actual-palette native off/on comparison; preserve ordinary scenes. |
| INTERIOR-LIGHT-29 | Building-only default1.2 implemented. Native Census fixed-view gain observed; cave reports effective1.0 at both settings. Cave views differ by28 of158720 sampled pixels; no exact-image equality claim. | Next-package fresh/saved setting and broader building controls. Census static NPC sampling remains a separate open issue. |
| CENSUS-DOOR-STUCK-29 | Player stuck after opening Census Office hall door | Y | v0.0.29-rc2 | Occupied-door activation guard passes actual-map and five focused checks. RC2 playtester confirms the reported trap is gone and obstruction feedback appears. Other positions, save/reload and return paths remain coverage limits. [Issue](../bugs/CENSUS-DOOR-STUCK-29.md). |
| CONSOLE-WHEEL-29 / UI-OPTIONS-WRAP-29 | Five wheel and seven menu endpoint checks pass for candidate repairs. | Native boundary/reverse-scroll checks; not owner-accepted in a later package. |
| AUDIO-ENTER-29 / AUDIO-LOAD-29 | Both remain open. Nonzero native menu music is not continuity acceptance. Smaller read chunks help one synthetic load rate but not every rate. | Exact guard Enter and ship-to-deck capture with active music on target. |

Owner-confirmed RC1 positives remain scoped: appearance-screen entry music,
Go back/Choose borders, substantially improved fists, and tested torch-to-NPC
response. They do not close the separate reports above. Full coordinates,
reproduction notes and follow-up requests: [RC1 playtest ledger](../RC1_PLAYTEST_LEDGER.md).

Consolidated RC1 reports, coordinates and scoped positive observations: [RC1 playtest ledger](../RC1_PLAYTEST_LEDGER.md).

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

Temple scope update: some walls/ceilings are intact; upper area and stairs look usable on the owner-tested route. Broken lower/other sections remain a major geometry/collision defect. [Detailed evidence and pipeline audit](../bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

## Balmora Temple geometry/collision report: 6 October 2026

**[BALMORA-TEMPLE-GEOMETRY-29](../bugs/BALMORA-TEMPLE-GEOMETRY-29.md): open, major,
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

Current work is the [v0.0.29 immediate fixlist](../PLAN-v0.0.29.md), following
published v0.0.29-rc1. New owner reports and source candidates below remain open
until their own native acceptance; historical passes do not close later reports.
The published release and its immutable artifacts are not modified by this work.

Native Windows build: [WIN-01 — intermittent Python geometry-worker queue failure (open)](../journals/BUG_JOURNAL-v0.0.29.md#win-01-intermittent-geometry-worker-queue-failure--open-2-october-2026).

Keep reported symptoms separate from confirmed causes. A successful retry does
not close an intermittent report. Historical passing checks remain valid for
the runs they covered; they do not rule out these later incidents.

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
sideways containment and courtyard gates. See [journal J015](../IMPLEMENTATION_JOURNAL.md#j015--opening-invisible-barriers-crossed-the-plank-v0021-dev1)
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
UI dispositions and reproduction gates: [FEEDBACK-v0.0.23-dev2.md](../FEEDBACK-v0.0.23-dev2.md).

## dev3 feedback follow-up — 29 September 2026

The reported Vodunius-house visibility holes and the misrotated port rock are
addressed; see [terrain findings and workflow](../WHAT_ARE_ROCKS.md). Voice style 2
now defaults to aim-only identity, overriding voiced speaker headers.
NPC conversation-facing, deck/pier sideways containment and door squeaks remain
open in [the consolidated dev2 feedback](../FEEDBACK-v0.0.23-dev2.md).

## dev3 regression retest / dev4

Owner confirms the port rock is fixed. Newly reproduced and corrected: tree
sprite background-depth rejection; Darvame dropping under the platform before
static scenery spawns; uneven dialogue padding; ornamental caret/rotation glyphs;
startup theme/timing; missing optional opening quote overlay. See
[the full feedback table and trials](../FEEDBACK-v0.0.23-dev3.md).
These focused checks do not close unrelated open items above.

## RC1 remaining acceptance items — 30 September 2026

The coordinate-by-coordinate record is in
[INVESTIGATION-v0.0.24-rc1.md](../INVESTIGATION-v0.0.24-rc1.md). Keep these open:

- stairs10 at -685,+619,141: reported origin is inside terrain; do not silently
  substitute the older negative-Y report or call it a passed staircase.
- wedge1 at -225,348,131: exact trapped state not yet reproduced; nearby native
  retreat works only after lateral placement recovery.
- Full natural intro and owner city-roaming acceptance; physical Amiga, Windows
  and subjective audio checks have not been established by Linux null-audio runs.

NPC greetings, room population and entrance traversal are implemented; full
services, wandering/combat and quest behavior are not implied by their presence.
