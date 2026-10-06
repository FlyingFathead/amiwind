# v0.0.29-rc1 owner playtest ledger

## HARVEST-BITTERCOAST-29: one of three nearby mushrooms usable, 6 October 2026

Open RC2 playtest report in **Bitter Coast**: only one of three nearby mushrooms
could be eaten. The player tentatively identifies them as Luminous Russula but
also asks whether the other two are different types. Species and interaction
stage are unverified; do not assume that picking, harvesting and inventory
consumption are the same failure.

The original screenshot shows v0.0.29-rc2, global XYZ approximately
**-15287 -59485 735**, game time **02:39**. Obtain map and original reference IDs,
identify all three objects, and replay both pickup and inventory use. The cause
and fixed version are unknown. [Issue and reproduction](bugs/HARVEST-BITTERCOAST-29.md).

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

[Implemented repairs, demonstrated cases and still-open issues](RC2_ISSUE_CHECKPOINT.md).
This dated checkpoint supersedes older candidate status below. Delivery and
final extracted-package launch are still pending; Temple holes remain open.

## INTERIOR-LIGHT-29: RC2 measured checkpoint, 6 October 2026

Native menu changes and saved settings passed. Census renderer medians at
1.0x/1.2x were 1.175745/1.189845 s per128frames (+1.199%, +0.110 ms/render).
Only three alternating pairs; broader gameplay, enabled/disabled, night, RAM
and physical-Amiga performance remain open. Latest defaults are interior1.2
and exterior1.0; earlier dated debug-only plans are superseded.
[Full method, samples and remaining work](bugs/INTERIOR-LIGHT-29.md).
These post-snapshot notes do not change the measured RC2 executable.

## v0.0.29-rc2: Let There Be (Just a Bit More) Light

Recorded 2026-10-06T21:23:03+03:00. Release candidate preparation, not yet published.
Interior brightness defaults to1.2x; independent exterior control defaults
to1.0x. Six-step Options > Graphics controls and saved settings are included,
with both build opt-out flags and explanatory disabled console commands.
The owner approved the latest torch off/on/off test5/5 for this candidate.
Balmora Temple remains a major partial geometry/collision defect. Its shipped
map stays unchanged; the scoped converter plane correction does not resolve
the broad holes. WinUAE Enter/load audio, brief hand-transition disappearance,
modeled memory warnings and incomplete content coverage remain open.
Native performance comparison is pending. First shipped fixed version remains
none until exact delivery and acceptance are recorded.


## Live-console comparison completed: 2026-10-06T20:52:21+03:00

A single `--debug-luma` executable was used for all four values: 1.0, 1.1,
1.2 and 1.3. Each value was applied live using `dbg interior luma <factor>`
and confirmed by the console in the same FS-UAE session. No separate
brightness-specific builds were required. Matched original-map views were
captured in Balmora Temple and the Census Office with fixed pose and clock
(10:21), and the player torch off. Temple local XYZ was 931 1052 3701;
Census local XYZ was 3 -33 64. Temple used diagnostic noclip placement.

Returning the Temple factor from 1.3 to 1.0 reproduced the baseline PNG
byte for byte. Native console logs confirmed all eight effective values.
The session exited to AmigaDOS, the emulator preset was restored, and
engine/map readback and filesystem ownership checks passed. Played disks
remain diagnostic evidence only. This does not establish collision repair
or target performance; no new production brightness or bake was chosen.

Candidate 005 passed 1,055 tests, zero failures/errors and four documented
skips, plus separate production and debug engine builds. The normal build
excludes this optional feature. First shipped version remains none.

## Debug-only luminosity checkpoint: 2026-10-06T20:30:20+03:00

The latest setting supersedes the earlier 1.2 default: normal builds omit the
preview feature; `--debug-luma` builds include all gameplay-interior previews,
starting at 1.0. Both `dbg indoor luma [factor]` and `dbg interior luma [factor]`
are available, with the original alias retained. Engine-bound image staging
omits unsupported commands/configuration in production. Twelve focused checks
pass, including real renderer paths, saved/default values, compiled-out mode
and existing exterior/torch controls. Four matched native brightness views are
still pending. No bake or new production brightness is selected. First shipped
fixed version remains none. See [interior lighting](INTERIOR_LIGHTING.md).

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
  [Temple issue](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) and
  [import guidance](MESH_TIPS_AND_TRICKS.md).

First shipped fixed version for these follow-up candidates: none. The transition
and audio requests remain pending; a status answer does not complete them.

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

Recorded 6 October 2026. This ledger consolidates owner reports and scoped positive observations for the exact private RC1 playtest. Next-source work is separate from RC1 and does not constitute a shipped fix. Local original game inputs and captures are not included.

## Package identity and status

This record applies to the v0.0.29-rc1 owner playtest on WinUAE. Exact private package and capture receipts are retained in the development evidence ledger.

Track owner-reported, source-checked, candidate-tested, packaged, target-observed and owner-accepted separately. Only an explicit owner acceptance in this exact package is marked fixed below.

## Balmora Temple geometry/collision - BALMORA-TEMPLE-GEOMETRY-29

**Open, major, release blocker.** RC1 shows partial structural loss: absent wall/floor/ceiling spans, thin horizontal remnants and pass-through gaps. Some other walls and ceilings remain; the upper route and stairs are the intact control. This is neither a wholly absent Temple nor a texture-only report.

| Owner local runtime XYZ | Heading / pitch | Time | Observation |
| --- | --- | --- | --- |
| 1063,1048,3700 | E076 / 65 | ~05:28 | Primary report; broad gaps, pass-through concern |
| 1072,1063,3701 | E089 / 8 | 05:22 | Damaged area |
| 975,1026,3701 | S169 / 7 | 05:50 | Damaged area |
| 1071,870,3700 | SW234 / 50 | 06:11 | Damaged area |
| 1033,885,3701 | NE050 / 7 | 06:50 | Thin horizontal remnant |
| 1035,882,3701 | NE046 / -49 | 07:13 | Missing ceiling sections |
| 1170,1036,3700 | S183 / -5 | 08:29 | Intact upper-route/stairs control |
| 1016,1033,3701 | SW204 / 13 | 08:56 | Thin remnant/open lower structure |
| 1061,1056,3700 | E072 / 31 | 09:24 | Thin remnant/open lower structure |
| 1062,888,3697 | SW207 / 46 | 09:50 | Largely open damaged section |
| 931,1052,3701 | SE131 / 8 | 10:21 | Latest owner view; continuing damage report |

These are approximate local HUD poses from owner WinUAE playtesting; headings and integer positions are not precision measurements. Independent FS-UAE reproduction is pending.

**Pipeline findings:** source interior contains 286 references; 185 explicit selected references and all 185 reference IDs survive in sealed RC1. The prior RC1/RC4 cache has 185 converted placements and 41,816 placed source triangles. Assembled BSP has 35,242 faces, 186 models and 39,864 clipnodes. Exact packaged BSP matches its private catalogue; RC1 and RC4 cached assembled BSP hashes match each other. This rules out wholesale placement omission and a simple post-append face-count drop; it does not prove required transformed surfaces or collision at the gaps.

101 references are omitted: 46 fine dressing (including one rope placement), 45 small items/actors, six records without a static model, three unsupported activators and one editor marker. The deferred rope may resemble a thin line, but an omitted object cannot directly account for a visible RC1 strip without a separate included source; identity and relationship remain unconfirmed. It cannot explain broad open lower structures. The `.map` compiles an enclosure before original mesh appending, so its brush totals do not count architecture.

The classic signed-short coordinate wire has an upper limit of 4095.875 and lower limit of -4096. Source-transformed structural vertices sampled near the reported poses and upper control fall within this limit, making straightforward coordinate wrap less likely at those views. The exact RC1 static brush entity protocol/runtime still needs checking. Curved/hollow meshes, source transforms, BSP surfaces/visibility and collision remain leads, not established causes.

**Additional structural check:** all 62 architectural placements retain the exported packet surface area in the sealed BSP within 0.1%, with transformed bounding differences no larger than 0.000031 runtime units. This rules out large packet-to-BSP placement offsets or widespread surface-area collapse in those pieces. A subsequent original-mesh audit retains all 12,913 visible triangles across 31 structural model sources. Face normals, runtime visibility and collision remain unverified.

**Next:** audit final BSP normals/visibility and actual runtime culling at broken poses and the upper control; source-to-packet and packet-to-BSP structural completeness now have scoped evidence above. Trace collision hull/rays at matching points. Identify each strip's placement before labeling it a wall. Build a regression for selected structural IDs, transformed visual coverage and matching collision at broken/intact locations, plus translated synthetic interiors with door arrivals/collision across large positive/negative offsets. Any eventual geometry change is limited to Balmora Temple. Require packaged target walk/look coverage at every listed point, both passage directions, torch off/on, entry/exit and upper-route control. No repair or fixed release is established.

Detailed record: [BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

## Rendering and traversal

| Issue | RC1 report | State and next evidence |
| --- | --- | --- |
| LIGHT-EXTERIOR-JUMP-29 | Owner repeatedly sees dark-to-bright changes around Seyda Neen shacks/sub-cell crossings without torch; says it stops after leaving the area. Pair: dark global `-13037,-70679,113`, local `-443,251,28`, heading165/pitch7, 13:14; bright global `-12659,-71562,90`, local `-348,29,22`, heading122/pitch-5, 13:18. Correct maps: dark `sn037`, bright `sn031` (not `sn039`); later `sn061`/`vf0846` pair adds evidence. | Open; owner-reproduced traversal symptom. Source audit isolates empty/unused lighting-lump path; candidate ambient/dynamic fix has six focused Docker checks, not package/owner acceptance. Replay both ways at fixed clock, torch off/on, both pairs and open-country control. |
| CONSOLE-WHEEL-29 | F10 console down at newest output triggers repeated MWHEELDOWN/MWHEELUP unbound warnings and degrades scroll. Lower boundary owner-reproduced; source regression tests both ends. | Cause source-checked: warning prints before console consumes key. Candidate moves warning into game-binding path; five focused checks, not target accepted or shipped. Verify both limits/directions and ordinary game-binding negative control. |
| INTERIOR-NPC-LIGHT-29 | Census Office NPCs look too dark under static interior lighting. | Open, distinct from surface light and player torch. Compare same-pose room light and torch off/on on actor and adjacent surfaces; inspect actor path/light data/sample/final shading. |
| INTERIOR-LIGHT-29 / `dbg interiorluma` | Owner requests archived `aw_interiorluma`, query on no argument, default 1.2 vs baseline 1.0 for built interiors. | Candidate applies to 55 explicitly reviewed buildings, bounded 0..4; natural caves/tombs and unknown maps remain 1.0, as do ship/exteriors/dark torch room. Eight focused checks plus bounded native Census gain and Addamasartus effective-baseline evidence. Cave images were near-identical, not exactly identical. No later package delivered. |
| Traversal feel | Balmora streets feel smoother/shorter loads than Seyda Neen; tested open fields acceptable. | Subjective scoped positive, not timings or world approval. Compare equivalent crossings, RAM, entities, geometry, loading, audio and frame time. Defer coarser town-cell study until LIGHT-EXTERIOR-JUMP-29 is addressed. |

## Audio and interface

| Issue | RC1 report | State and next evidence |
| --- | --- | --- |
| AUDIO-APPEARANCE-29 | Appearance-screen entry no longer jumps. | Owner accepts in RC1; fixed within this entry behavior. Preserve regression; full confirmation exit separate. |
| AUDIO-ENTER-29 | Small music jump still occurs on Enter at prison-ship “follow the guard” prompt. | Open, separate from appearance entry and load crackle. Replay exact event with music, mixer/service/queue/read timings and listen. |
| AUDIO-LOAD-29 | OST crackles on prison-ship-to-deck heavy load. | Open. 4 KiB candidate servicing removes misses in synthetic test at 32 KiB/s but still misses 53,312 at 25 KiB/s and increases load duration. Target replay with active music, service gaps, queue and reads required. |
| UI-OPTIONS-WRAP-29 | Setup list and scrollbar work; Options wraps bottom to top. | Open in RC1. Candidate clamps Options/Interface/Audio endpoints; seven focused checks, target pending. Check arrows, W/S, wheel, Tab and reverse with focus/scroll. |
| Effects default | Owner requests 75%; saved overrides and other defaults preserved. | Candidate defaults Effects at 75%; eight focused checks. Next-package fresh settings and override persistence pending. |
| CHAR-CONFIRM-BORDER-29 | Go back and Choose have OK-style borders. | Owner rates both 5/5 in RC1; fixed for those two controls. Preserve regression; other menus separate. |

## Hands and combat

| Issue/request | RC1 report | State and next evidence |
| --- | --- | --- |
| HAND-PUNCH-COVERAGE-29 | Fists substantially improved; camera-near forearm shows background/open coverage at maximum extension. Race/sex/frame not identified by screenshot. | Open. Inspect exact packaged punch and adjacent frames, both arms, viewport/FOV/near plane, winding/interpolation/clipping. All 20 inspected encoded models are closed at maximum extension; actual-C projection exposes a near-plane cross-section. Simple offsets and plane reduction did not solve it. A later diagnostic viewmodel-only camera-depth scale closes the sampled maximum-extension gap without deforming geometry; depth-bias and world-entity controls, full pose coverage and native acceptance remain pending. Any repair remains explicit and separately tested. |
| Alternating attacks | Owner requests bare-knuckle right/left/right/left. | Not in RC1; current source samples one 10-frame punch. Inspect owned animation catalogue and define fallback; do not claim original behavior from request. Forearm coverage first. |
| FPV action pipeline | Owner requests adjustable preview/conversion pipeline retaining immutable RC1 input with per-action/frame offsets. | Not an RC1 editor. Produce repeatable full-viewport previews/contact sheets for idle/draw/lower/full punch; measure selected model/cache and render cost. Framing change is not topology repair. |
| `dbg combattest` | Isolated attack inspection requested. | Next candidate uses finite 4096-unit empty gallery floor/current hands; four focused Docker checks. Native room entry passed but hands failed due to DEBUG-GALLERY-TIMING-29. Does not repair forearm or add combo. |
| Scoped positive | Latest tested movement had no observed blinking; held-torch NPC response is “pretty okay” on tested route. | Preserve as scoped owner observations. Paw/grip, broad race coverage, punch and Census static NPC light remain open. |

## Torch and local light

| Issue/request | RC1 report | State and next evidence |
| --- | --- | --- |
| Flame style | Owner prefers brightbase type 2 and requests 2 or 3 as new default. | RC1 style query/control exists; next candidate defaults 2, saved preference retained. Verify fresh/saved settings on target. |
| Sparks | Owner did not see type 3 sparks/embers. | Extra spark pass is player-only; not owner-accepted. Full viewport fixed-pose/time type 1/2/3 off/on, player/guard distinction pending. |
| Surface reach/strength | Stronger near ground/walls, farther forward/around player and NPC torch holders requested. Indoor torch is twice described as more useful than outdoors. | Keep radius, light strength, flame appearance and admitted-light count distinct. Candidate 0.7 normalized strength is not photometric/daylight equivalence. Matched indoor/outdoor surfaces/NPC, falloff and cost pending. |
| TORCH-FUEL-29 | RC1 torch is drawn but does not consume fuel/burn out. | Open design; source duration and zero/negative semantics unknown. Compact changed-item state proposal only; no implementation/fixed release. Verify equip/off/relight/burnout/save-load/area transitions and memory. |
| `dbg torchtest` | Absolutely dark isolated surface room with optional NPC and exact state-preserving return requested. | Candidate zero-lightmap enclosure/standing collision and seven focused checks; native entry/return observed, but invalid hand timing blocks torch-on, and dim gray floor leaves absolute darkness open. Full state-return acceptance pending. Not in RC1. |

## CENSUS-DOOR-STUCK-29

Reported after opening Census Office hall door at game 10:16, local HUD `65,52,65`, heading N008/pitch20. Integer HUD truncates; valid standing z is 65.549949646. Actual RC1 hull replay and `SV_ClipMoveToEntity` find ref172860/model `*2` rotates from yaw -180 to -90 and creates player overlap. This reproduces the source collision cause, not a fresh emulator run. Activation guard candidate passes five focused Docker checks for occupied refusal and clear opening; saved-open restore, already-trapped saves, package and native passage remain open. Fixed N; first shipped fixed version none. See [CENSUS-DOOR-STUCK-29](bugs/CENSUS-DOOR-STUCK-29.md).

## Latest candidate gates and exact scope

The combined next-source candidate ran 1,046 tests with zero failures/errors and four documented skips, and passed Amiga target gates. A bounded FS-UAE check observed building gain and cave effective baseline, but exposed invalid hand timing in both inspection rooms. Their repair and normal walking across the Seyda boundary remain pending. These do not close reports above. `dbg interiorluma` (eight focused checks), `dbg combattest` (four), `dbg torchtest` (seven), wheel (five), Options clamp (seven), Effects default (eight), and audio read servicing are source evidence only unless separately stated. No Temple repair is claimed; any geometry correction must remain Temple-only.

Issue index: [BUGS](BUGS.md); dated record: [BUG_JOURNAL](BUG_JOURNAL.md); [Temple](bugs/BALMORA-TEMPLE-GEOMETRY-29.md), [Census door](bugs/CENSUS-DOOR-STUCK-29.md), [audio](AUDIO.md), [torch](TORCH.md), [hands](FIRST_PERSON_HANDS.md), [release checkpoint](RELEASE-v0.0.29-rc1.md). Maintain this ledger together with the issue index and roadmap.
