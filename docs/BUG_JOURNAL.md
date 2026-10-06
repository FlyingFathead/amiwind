# Bug journal

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

## Packaged interior plane audit: 2026-10-06T20:11:15+03:00

Read-only check of the sealed v0.0.29-rc1 package completed: all 58 gameplay
interiors, 880,244 faces. Every scanned map matched its packaged SHA-256.
There were 44 faces with vertex-to-stored-plane distance above 0.05 BSP units:

| Map | Flagged faces | Maximum distance |
| --- | ---: | ---: |
| Balmora Temple | 13 | 31.4870 |
| Prison ship interior | 23 | 0.72159 |
| Census Office | 3 | 0.93969 |
| Tradehouse | 4 | 0.93969 |
| Warehouse | 1 | 0.93969 |

The remaining 53 interiors had no failures of this specific threshold check.
The auxiliary character plane was checked separately: 464 faces, no failures.
All 2,723 packaged map names were accounted for: 58 interiors, 2,664 exterior
maps outside this audit scope and one separately scanned auxiliary map. Two
optional section names were absent from the package and were recorded as such.

These additional 31 flagged faces are import-risk findings, not proof of the
same root cause, visible holes or broken collision. Passing this plane check
does not certify an entire interior. No map was modified. The repair remains
limited to Balmora Temple. Future imports should retain this check alongside
source coverage, native rendering and ordinary collision-route validation.

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

## Explicit test-room input restriction, 2026-10-06T18:59:52+03:00

Native follow-up identified a separate control failure: after appearance
selection returns to the pre-Census story stage, normal fighting restrictions
also mask combat-test attack and torch-test impulse202. The female capture
shows idle hands, not a successful punch. The default post-demo punch check
remains valid. This is unrelated to the torch-room gray lighting floor.

The narrow source repair grants input only during a captured, active explicit
combat/torch test session on its matching map. Character-modal blocking stays;
ordinary NPC gallery, raw test-map loads and normal story restrictions remain.
Permission ends immediately when return begins, without changing story state.
The actual gallery/story regression fails before repair; five focused Docker
checks pass after repair with no skips. Full combined gates and new native
pre-Census punch/torch/exit acceptance are pending. No shipped fixed version.

## RC1 follow-up evidence, 2026-10-06T18:49:45+03:00

Combined repair candidate: 1,047 tests, zero failures/errors, four documented
skips; Amiga build passed. A missing client-state global in one test fixture
caused the preceding candidate's link failure; the fixture-only correction
passed the full suite. It was not evidence of a game regression.

HAND-PUNCH-COVERAGE-29: native default appearance frame25 shows no prior
proximal near-plane aperture; actual game-audio video captured. Full appearance
review and delivered-version acceptance remain pending. DEBUG-GALLERY-TIMING-29:
hands/punching and scene return work; torch-room V equip/light failed this
control and remains open. Session closed cleanly at18:47:31+03:00.

BALMORA-TEMPLE-GEOMETRY-29: native missing-region reproduction confirmed; loader,
transport-origin and render-face plane-index checks do not explain the failure.
No render surface/edge exhaustion observed. Diagnostic noclip was not ordinary
walking acceptance. No cause, repair or first shipped fixed version established.

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

## Structural packet/BSP comparison: 2026-10-06T14:46:55+00:00

A read-only comparison of all 62 architectural instances in the exact packaged
Temple found no missing architectural entity, surface-area differences below
0.1%, and transformed bounds agreeing within 0.000031 runtime units. This checks
the exported MWG geometry against sealed BSP polygons after applying the actual
entity `angles` field. An initial diagnostic read only `angle`; that comparison
was corrected before attributing any placement error to the game.

This narrows the loss search: there is no evidence of large architectural offsets
or widespread surface collapse in the packet-to-BSP stages. Original NIF export
completeness, normals/winding, runtime visibility/culling and collision still need
independent checks. Preserve the damaged lower areas and intact upper/stair route
as separate controls. An omitted rope placement does not identify a visible strip.
Cause remains unproven; no Temple repair or fixed version is claimed. Geometry
changes, once justified, remain explicitly limited to Balmora Temple.

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

## 6 October 2026 activation guard candidate

The proposed overlap guard is now implemented in the next source candidate.
Actual RC1 map hulls plus actual `AW_OpeningUse` verify refusal for the player
and a solid NPC, unchanged actor pose/closed yaw/story flag, no false sound or
relink, and successful opening once both bodies are clear. Five focused existing
checks pass in Linux Docker. The open door remains SOLID_BSP.

This checks the final pose of the existing instant rotation. Saved-open restore,
already-trapped saves, native passage acceptance and packaged integration remain
pending. First shipped fixed version remains **none**.

## Loading-audio candidate evidence: 6 October 2026

The next candidate limits loading-only asset reads to 4 KiB and services audio
between reads. Steady gameplay reads retain their prior policy; no new audio
buffer or global latency increase was added. Nine focused Linux Docker checks
and a target compile/link passed before the subsequent door/test-scene changes.

Actual loader/mixer/absolute-clock routines under deterministic synthetic I/O
showed missed samples drop from 49,568 to zero at 32 KiB/s. At 25 KiB/s the
candidate still missed 53,312 samples; keeping playback serviced also increased
total load duration. These are synthetic source experiments, not WinUAE timings.
Treat this as a mitigation candidate. Ship-to-deck crackle and guard-follow Enter
jump remain open until target replay; appearance-selection entry already has
separate owner RC1 acceptance.

## RC1 door and brightness follow-up: 6 October 2026

New open reports: **CENSUS-DOOR-STUCK-29**, trapped after opening the Census
Office interior door; **LIGHT-EXTERIOR-JUMP-29**, abrupt outdoor brightening near
shacks without a carried torch. [Reproduction and next checks](BUGS-v0.0.29-RC1.md#rc1-door-snag-and-outdoor-brightness-reports-6-october-2026)
retain uncertainty about both causes. Earlier accepted appearance-entry audio
and character-button borders remain accepted within their stated scope.

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

## TORCH-NPC-LIGHT-29: nearby NPCs do not respond to torchlight (OPEN)

Dev4 playtesting reports lit walls/floors but dark NPC bodies. Five screenshots,
the night/day poses, source leads and required acceptance matrix are retained in
[the rc1 issue report](BUGS-v0.0.29-RC1.md#torch-npc-light-29-nearby-npcs-do-not-respond-to-torchlight-open).
**Fixed: N; final-release blocker.**

## CONFIG-COMMENT-29: semicolon splits a default comment (repair candidate)

First observed in the v0.0.29-dev2 Linux source suite on 5 October 2026 at
17:36 EEST. Five modal, UI and torch-default comments exist in preceding dev1 development
source; affected delivered builds and the introducing change are not established.
`Cbuf_Execute` splits unquoted semicolons before comment parsing, so the second
clauses can become unintended commands while loading defaults (`original`
from the modal comment is one example).
The existing `test_archived_default_and_config_seconds` regression rejects this
comment and reproduced the source failure. Native startup symptoms were not tested.

The first correction removed only the first reported semicolon. A repeated
full suite exposed the next one, so the dev2 correction now replaces semicolons
in all five affected comments with commas. It changes no setting
or parser behavior. The existing source regression and full Linux suite gate this
repair candidate; target startup acceptance remains separate. No target-verified
fixed version is claimed.

## TERRAIN-TRAP-29: player reported stuck on rocks beside structures (OPEN)

- **Affected/first observed:** v0.0.29-dev1, 5 October 2026; owner playtest
  report. Introducing change and last-known-good build are not established.
- **Observed pose:** global -21794,-17467,545; local -328,-1294,136;
  heading NW295, pitch0, game clock12:11. The exact active region is unknown.
- **Symptom/evidence:** owner reports being stuck on rocks. The supplied view
  shows obstructing rock geometry beside structures; a still image does not
  establish movement failure, collision hull correctness or a streaming cause.
- **Reproduction pending:** bind the exact map and build, approach the pictured
  gap from a known valid position, then capture attempted directions, player
  bounds, ground/solid state, trace hits and any cell transition. Compare visible
  geometry with owned-source placement and collision before choosing a remedy.
- **Proposed work:** determine whether placement, collision hulls, step limits
  or a crossing causes the trap. Preserve intended rock collision and terrain.
  Do not remove collision globally or assume this is the separate transition
  orientation defect.
- **Tried/results:** report and screenshot reviewed; pose recorded. No runtime
  reproduction or correction yet. **Fixed: N; first verified fixed version: none.**


## TORCH-INPUT-29: F cannot raise hands and V only reports torch state (OPEN)

**Confirmed converted-world hand metadata defect, 4 October 2026**

The released-map audit found missing hand draw/idle/lower/punch timing and eye
height metadata in **all 2,532 checked world-region BSPs**. All **190 checked
town/interior maps** contain the required metadata; the character gallery also
lacks it. This establishes a conversion coverage defect, not a personal-binding
diagnosis. No runtime restoration supplies the absent values.

The failure chain explains the reported behavior: missing/nonpositive draw
duration can leave QuakeC in drawing state 1 with the weapon model cleared.
V still accepts that state and prints its selected on/off goal, but actual
torch equipment requires raised state 2. Consequently the console can report
on while no hands, held model or equipped light appear. The exact owner-session
replay still needs acceptance, distinct from this source/payload diagnosis.

The v0.0.29-dev1 source candidate now stamps validated authored hand-conversion
metadata into staged worldspawn before optimization/fingerprinting and verifies
hand-model topology/frame provenance. Non-entity lumps and unrelated entity
bytes remain unchanged. Invalid metadata causes explicit safe QuakeC refusal
and clear state rather than invented fallback timing or repeated console spam.

Seven metadata tests pass on Windows and Linux. The actual compiled QuakeC plus
runtime torch fixture reproduces the missing-timing failure and passes corrected
draw/idle/model/light, lower, punch and death transitions under sanitizers. The
Amiga target compiles.

The corrected hand fields have now been stamped into all **2,532 staged
world-region BSPs**, with complete staged-image file readback and independent
metadata preservation checks passing. Sampled native F/V checks pass in Seyda
Neen and after a town-to-world transition into `vf1463`: hands lower/redraw,
the held torch appears, and equipped-state diagnostics agree. A subsequent
Hlaalu Council interior replay also shows F raising hands and V toggling the
held torch, with a broad response in the scoped native lighting checks. These samples
now include a normal Hlaalu Council/Balmora door roundtrip with the torch
preserved, plus successful F/V re-equipping after a quickload that initially
lowered the hands. They do not establish the full owner-state matrix, every map,
all save/load states or general lighting acceptance. **Fixed: N; first verified
fixed release: none.**


**Historical initial lead (superseded by the completed census and source tests):** the inspected released
`vf1340` worldspawn lacks the hand draw/idle/lower/punch timing fields. The
QuakeC path can remain in drawing state 1 when duration is nonpositive and
clear the weapon model. V accepts that state and reports its goal toggle, while
the equipped-light path requires raised state 2. This mechanism matches the
reported no-hands/no-light symptoms, but the affected conversion/map census and
actual owner-state/native reproduction remain pending. Do not close the report
or claim a repaired image from this inspection alone.


- **Priority/type:** P1, recurring owner-reported regression. First observed in
  this record: 4 October 2026, post-release v0.0.28 playtest, with debug mode
  enabled. The owner says this has recurred across older versions. Exact current
  executable, HDF, keymap and last-known-good revision are not yet bound.
- **Symptom:** F does not raise hands. V prints torch on/off, but hands never
  appear and no working player torch is visible. A text toggle is not success.
  Keep this distinct from guard illumination and the older periodic fist blink.
- **Reproduction to verify:** return from F10/map to gameplay, press F then V;
  capture input destination, bindings, impulse, hand goal/state/frame, viewmodel,
  torch goal/metadata and admitted light. Repeat with debug on/off, normal/noclip
  and both hand presentations. Do not infer that debug is the cause.
- **Cause established for the audited world maps:** missing authored hand timing
  stalls the draw state, as reproduced by the compiled QuakeC fixture above.
  The older [intermittent hand report](#intermittent-inability-to-ready-hands-unknown-state-open)
  still lacks its exact owner-session state; do not assume every older occurrence
  has the same cause without replay evidence.
- **Proposed correction:** identify the first failed stage and repair that path;
  add regression coverage spanning binding, game state, visible held model/flame
  and final local illumination. Preserve personal bindings and intended story
  restrictions. See the [mandatory torch matrix](TORCH.md#v0029-required-hands-and-light-acceptance-matrix).
- **Tried/results:** owner report, complete metadata census, failing/passing real
  QuakeC/runtime fixture, seven cross-host metadata tests and Amiga compilation.
  All 2,532 world-region maps have corrected staged metadata and passed complete
  staged-image file readback. Sampled native F/V and held-torch checks pass in one
  town-to-world sequence and one Hlaalu Council interior. The interior view also
  responds to the player torch. An ordinary Council/Balmora door roundtrip
  preserves the equipped torch, and F/V works after quickload and after travel.
  Quickload initially lowers the hands; it does not preserve equipped appearance.
  The complete state, save/load and surface-light matrix remains open.
  **Fixed: N. Repair candidate: v0.0.29-dev1 source.
  First verified fixed version: none.**

## TORCH-LIGHT-29: guard torches do not illuminate nearby night surfaces (OPEN)

- **Priority/type:** P1 visual/gameplay issue, reported 4 October 2026 in the
  post-release v0.0.28 playtest. Owner sees carried guard torches but no local
  night illumination. Exact guard/location/build and introducing revision are
  unconfirmed; this is not proof all dynamic lighting is absent.
- **Reproduction to verify:** at the same night time/camera, compare nearby
  wall/floor/scenery with a supported Imperial or Hlaalu guard torch off/on.
  Inspect actual surface contrast, not only flame particles or registry state.
- **Cause:** unknown. Source already contains a capped guard-light path, so
  inspect admission, radius/anchor, contents and trace rejection, lightmap/cache
  contribution, ambient/palette response and surface type before choosing a fix.
- **Proposed correction:** bounded local illumination using the existing
  Quake/AmiQuake renderer where possible; retain measured light-count limits and
  placement rules. OpenMW/source-light research informs fidelity, not a promise
  of RGB lights or full shadow casting.
- **Tried/results, 5 October:** a separate signed surface-light interpolation
  defect has a tested source correction ([details](TORCH.md#light-gradient-29-unsigned-surface-light-interpolation-overflow)).
  A native night replay now shows a visible pavement light pool beside one
  standing Hlaalu guard in Balmora. Lossless engine-generated captures show
  **841 of 1,680 selected pavement pixels brighten**, excluding the central
  guard/flame strip. Both off captures match exactly in those strips; automatic
  night lighting matches forced-on there too. These are visually selected
  screen regions at one pose, not a general surface classifier or performance
  result. Other pixels differ, so no full-frame identity is claimed.
  An earlier attempted guard view still has byte-identical off/on captures and
  no recognizable guard in view. Its cause remains unresolved: registry/proxy
  admission alone does not establish actual dynamic-light allocation. Preserve
  that failed view and inspect actor visibility, emitter/rejection and allocated
  light contribution before closing the report. Both samples used the default
  night palette path. **Fixed: N. Candidate: v0.0.29-dev1.
  First verified fixed version: none.**

- **Owner request, 5 October 2026:** all torches look weak, “like they are
  dying,” and night darkness swallows up everything. The requested target is a
  brighter near-white/yellow flame core with stronger immediate light around
  torches, while preserving the current profile as the baseline and keeping
  unlit night dark. Both flame appearance and local surface illumination need
  review; no fix or acceptance is claimed. A source study identified the
  AW_FogDraw night transform after dynamic lighting as one candidate contributor,
  not a confirmed cause of the owner screenshot. Verify with a controlled
  local-light-preserving night comparison. Keep this visual/light request
  separate from intermittent guard-torch visibility under GUARD-TORCH-CYCLE-29.

- **Dev4 source correction, guard-light eviction isolation:** eviction of one
  guard's optional torch model previously cleared every admitted guard light.
  The candidate tracks each guard's selected light key and clears only that
  light. A negative control fails on the original source; the candidate passes
  the guard and final-pixel fixtures under UBSan. A 68040 object compiles with
  unchanged existing warnings and 128 additional static bytes. This callback
  runs during alias-entity drawing, after world/brush drawing: the repair can
  preserve lights for later actors, but cannot retroactively brighten world
  pixels. It is not a verified fix for the reported dim ground or intermittent
  torch appearance. Native acceptance remains pending; Fixed: N. The previous
  916-test integration snapshot predates this separate source correction.

## INTERIOR-LIGHT-29: interiors lack convincing local light (OPEN)

- **Priority/type:** P2 fidelity/visual issue. Reported 4 October 2026 during the
  post-release v0.0.28 playtest: interiors look bleak, with no apparent light
  sources. Exact rooms/build/last good comparison are not established. The
  owner-visible symptom does not prove every source light record is missing.
- **Reproduction to verify:** identify representative lantern/torch-lit rooms,
  record source light/placement and compare a fixed camera with the local light
  enabled/disabled. Audit conversion, emitter, surface response and palette.
- **Cause:** unknown. **Proposed work:** study owned original light records,
  OpenMW behavior and AmiQuake/Quake local-lighting paths; prototype a capped
  nearest-light/visibility policy with measured indoor frame and memory cost.
  Do not substitute a uniform ambient increase for verified local lighting.
- **Tried/results, 5 October:** one native Hlaalu Council interior replay shows
  F raising hands, V equipping the torch and visible wall/floor illumination;
  V off restores the darker view. Lossless off/on/off captures contain **24,728
  changed viewport pixels stable between the two off frames**, including 16,624
  above the lower hand/torch band. The change extends beyond the held sprite,
  but without an independent depth mask these are not exact world-surface
  counts. The default night palette path was used. Source-light census, authored
  static lantern/torch coverage, other interiors and frame/memory budgets remain
  pending. A later ordinary Council/Balmora door roundtrip retains the equipped
  torch; quickload initially lowers hands, after which F/V restores equipment
  and the sampled interior lighting. Other transitions/save states remain open. **Fixed: N. Candidate: v0.0.29-dev1.
  First verified fixed version: none.** Track separately from player F/V input.

## SKY-NIGHT-COVER-29: frequent dense night clouds hide celestial views (OPEN)

- **Priority/type:** P2 presentation/policy issue. Reported 4 October 2026 during
  the post-release v0.0.28 playtest. Night looks good in some regions, but the
  owner sees dense cloud coverage on nearly every night and rarely sees the
  moons, stars and space. Exact configuration/time/region sampling is pending.
- **Cause:** the legacy shared cloud-role validator accepts roles below 225,
  while the night layer also needs valid role index 254. That rejected night
  role left the overlay unavailable when night clouds were enabled. The
  source candidate uses a separately validated night-role map, preserving the
  legacy cloud-role mask, scaling and tint behavior.
- **Reproduction/proposal:** with cloud control V2, compare clear, partial and
  overcast deep-night views and the adjusted daytime window. Check moon/star
  visibility and depth ordering against identical-clock reference captures;
  keep the retained legacy controller and protected sunrise/sunset path.
- **Tried/results:** synthetic rendered-sky fixtures pass candidate modes
  0-14 and 75 protected parity comparisons; the pre-fix baseline fails the
  expected new night-role case. A bounded native check now uses lossless,
  engine-generated indexed frames at frozen 23:00 in one dry exterior view.
  With optional V2/classic clouds, clear-to-partial, clear-to-overcast and
  night-layer-off comparisons change 9,232, 13,774 and 10,867 sky pixels,
  respectively. The matching depth classification has 32,614 sky pixels;
  all 16,017 geometry pixels and nine crosshair pixels remain unchanged.
  Clear-frame and depth-mask restores are byte-identical. This result is
  limited to those controls and that view; broader regions, Balmora, moving
  views, water and native performance remain acceptance gates. Optional veil
  clouds remain a separate selectable experiment. **Fixed: N. Candidate:
  v0.0.29. First verified fixed version: none.**

## HUD-STATS-29: healthy character appears partly depleted (OPEN)

**Source-candidate update:** The source candidate now uses independent stat current/max values, with
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


- **Priority/type:** P2 confirmed source defect with owner screenshot, reported
  4 October 2026 in the post-release v0.0.28 playtest. The red health bar is
  partly empty although no depletion is expected; introducing revision unknown.
- **Cause:** `AW_UIHud` divides live health by fixed 100 rather than the
  character's maximum. A character at 55/55 therefore looks partly depleted.
  Magicka/fatigue display fractions are hardcoded to one rather than their own
  current/max values. This does not establish any actual unwanted damage.
- **Proposed correction:** use independent stat current/max pairs and live
  gameplay health where authoritative. Handle invalid/zero maxima safely;
  do not heal the player or mask damage. The requested later god-mode switch is
  a separate gameplay policy, not the health-bar fix.
- **Required checks:** 55/55 full, 27.5/55 half, independent depleted magicka and
  fatigue, fallback/invalid bounds, save/load and native display. **Tried/results:**
  source fixtures and the bounded native health/save replay above pass; other
  current/max combinations and gameplay-state acceptance remain open. **Fixed: N.
  Repair candidate: v0.0.29, not yet accepted. First verified fixed version: none.**

## CONSOLE-CAPS-29: FS-UAE console Caps Lock state reported (OPEN)

Reported 5 October 2026 at 12:07:08 Europe/Helsinki in v0.0.29-dev1 on
FS-UAE. The owner reports Caps Lock appears stuck in the F10 debug console;
toggling Caps Lock on and off is the observed workaround. Exact emulator
version/configuration and the triggering focus/state sequence remain unknown.
Reproduce normal entry/exit, host focus changes and modifier press/release,
preserving current bindings. Inspect host-to-guest and console modifier state
before attributing the cause. **Fixed: N.** No correction is implemented.

## CONSOLE-WHEEL-29: FS-UAE wheel stops scrolling console (OPEN)

Reported 5 October 2026 at 12:08:51 Europe/Helsinki in v0.0.29-dev1 on
FS-UAE; screenshot at 12:08:55 shows repeated
`MWHEELUP is unbound, hit F4 to set.` The owner reports scrolling initially
works, then falls through to the unbound notice after scrolling up and down.
At 12:09:03 the owner identifies this as a recurring regression; the introducing
revision and earlier fix are not yet established. Preserve that intermittent
sequence rather than treating it as a permanently missing user binding.
Reproduce with exact emulator configuration, key bindings, console/focus state
and wheel event sequence. Inspect console event consumption and binding fallback;
no root cause, rebind remedy or fixed version is established. **Fixed: N.**

## MODAL-WORLD-29: world work continues behind character creation (OPEN)

Observed version: **v0.0.29-dev1**. Reported 5 October 2026, 11:44:38-11:53:11
Europe/Helsinki.

Reported on 5 October 2026 during development playtesting: appearance/head
rotation is slow at the docks and water moves in uncovered space around the
panel. Source confirms that `SCR_UpdateScreen` still calls `V_RenderView`
before character UI drawing. Character creation retains `key_game`, so normal
server physics is not excluded by the existing menu pause condition. Intro
progression and normal calendar advancement already stop; water animation uses
the independently advancing client clock. The opaque 316x196 panel at (2,2)
leaves 2,064 pixels uncovered in a 320x200 framebuffer.

Owner clarification on 5 October: this request concerns **head/race selection**
and subsequent character pages, journals and other blocking overlays, not the
original name-entry prompt. Preserve that original prompt's world context.

The source candidate adds two independent saved booleans, both default **1**:
`aw_modal_freeze` suspends background simulation/client world clocks;
`aw_modal_black` covers the modal background in black and skips hidden world
drawing. Setting either to0 restores that aspect independently. Character pages
cover the full draw area when black is enabled, including appearance, class,
birthsign, review and confirmations. No saved framebuffer or new heap cache is
required. UI/head animation, input and presentation remain live.

**Soundtrack priority is independent of world simulation.** Modal freezing,
blackout, journals and character selection must never pause, restart or starve
the background music. Continue mixer and music service calls; only an explicit
music hard stop or shutdown may intentionally stop playback. This contract is
documented next to the host audio service, not implemented as a whole-loop pause.
Existing intermittent load/heavy-scene music artifacts remain a separate issue.

Simulation pause and render suppression do not change ownership of `sv.paused`.
Closing or changing flags requests a fresh world frame, clears held gameplay
input and prevents accumulated-time catch-up. Explicit wait confirmation still
advances the intended calendar interval. Map/journal/menu, reader and modal
gallery are classified; HUD/subtitles, the original name prompt, follow-guard
prompt, movie presentation and nonmodal sky gallery retain their own semantics.

The first focused Linux source run passed host/client policy and character
coverage cases. It included a name-entry expansion which was subsequently
removed after the owner's clarification. That earlier pass does not verify the
revised two-flag behavior. The revised host fixture exercises all four settings
and checks continued mixer, extra audio service, soundtrack, network and UI work.
The revised integration passes all78 Linux native-source tests, including all
four combinations, and Windows/Linux Amiga builds produce identical binaries.
Audible native continuity, measured head/world cost split and lifecycle acceptance
remain pending. **Fixed: N.**
This report does not establish the cause of earlier dock freezes.

## UI-ACCEPT-29: character selection lacks a visible OK button (OPEN)

Reported 5 October 2026 in the post-reboot v0.0.29-dev1-based target session.
Appearance and class selection work, but their footer exposes only keyboard
instructions, without a distinct bottom-right OK button. Existing code treats
a broad footer strip as an invisible accept target. Reproduce by opening either
selection page and looking/clicking at the bottom right; repeat for birthsign
and review. Appearance Enter advances rows, but its final focus is not a button.

Candidate fix: saved `aw_ui_mode 2` default adds one shared draw/hit rectangle,
keyboard focus after Hair, and the same validation/confirmation as Enter. V1
preserves the old layout and hit strip. Native confirmation of this new change
is pending. The owner's successful preceding blackout/head/class checks are
recorded separately and do not close this report. **Fixed: N (target pending).**

## ROCK-FLORA-SURFACE-29: newly appeared angular rock-like surfaces (OPEN)

Owner screenshot/report, 5 October 2026, current v0.0.29-dev1-based target session,
Bitter Coast. Large angular/coarsely textured surfaces appear near the ground;
the owner asks whether these might be mushrooms and reports recent onset. The
image alone does not identify the object or establish texture versus geometry,
placement, sprite transform or culling as the cause. Do not relabel it as a
confirmed mushroom/rock conversion fault without source-bound evidence.

HUD transcription: global XYZ -10940,-74750,81; local XYZ 78,-767,20; heading192,
pitch22; game time12:23. These rounded HUD values are a reproduction lead, not
the exact streamed region or full-precision camera. Obtain active chunk and
matching-pose captures, identify contributing placed references/materials, and
compare source geometry and earlier output. Keep separate from the tree-root
and shack reports until evidence connects them. No fix accepted. **Fixed: N.**

## SHACK-VISIBILITY-29: Indrele shack missing front walls (FIXED in v0.0.29-dev3; owner-confirmed)

Observed version: **v0.0.29-dev1**. Reported 5 October 2026, 11:55:31-11:55:56
Europe/Helsinki.

On 5 October 2026 the owner reports a shack near Seyda Neen no longer renders
as it previously did. The development view records global XYZ -12917,-71290,98,
local XYZ -413,97,24, heading104, pitch-3 and game time10:17. Integer HUD values
do not provide a full-precision camera or identify the active streamed chunk.
No matched earlier-version view or root cause is established. Identify active
region and transition history, then compare source-bound placement/geometry,
visibility and stable same-pose output before attributing absent surfaces.
**Fixed: N.** No geometry or renderer correction is accepted.

5 October follow-up: the owner reports the same shack still fails in the current
post-reboot target session. Screenshot shows large sky-coloured gaps through and
beneath the structure. HUD transcription: global -12418,-71193,35; local -208,121,8;
heading233/pitch-15; game time11:35. Confirm exact camera/region from runtime before
diagnosis; neither the modal overlay fix nor this observation establishes a cause.


5 October dev3 investigation: the owner identified the building as Indrele
Rathryon's Shack. The missing front wall polygons are present in the placement's
auxiliary render range. Its authored yaw is -153.735168 degrees, but the actual
legacy `MSG_WriteAngle` truncates whole degrees before integer scaling; the real
`MSG_ReadAngle` returns -151.875 degrees. Their 1.860168-degree difference exceeds
the registry lookup's former 1.5-degree window, so the auxiliary walls are omitted.

An earlier private parser fixture incorrectly used `(int)(angle*256/360)` and
therefore did not reproduce the real writer. Its earlier passing result did not
rule out this cause. The replacement regression links the actual `common.c`
writer and reader and fails against the previous range lookup at this placement.

The dev3 candidate matches the exact authored or actual wire-quantized orientation,
including signed 360-degree wrap. It rejects ambiguous placements rather than
expanding the tolerance or choosing the first match. Shared model bounds,
collision, surface storage, network identity and packet encoding remain intact.
Docker tests cover the shack, 2,560 signed boundary cases, nearby distinct
placements, ambiguous quantization, duplicate outputs and nonfinite input.
Three focused tests pass; the 68040/FPU module compiles without warnings.
Full combined build and matched native before/after wall views are still pending.
**Fixed: N; source correction verified, native acceptance pending.**


5 October native acceptance: the dev3 engine restores both missing wooden wall
panels in an isolated FS-UAE comparison at global (-12285,-71178,103), displayed
heading000/pitch-1 and frozen09:10. The prior engine shows sky through these same
panels. Both images use the same teleport route and original BSP assets. This is
a matching diagnostic view, not an exact reproduction of the owner's heading319.
Combined source tests passed (853 methods, four environment skips), followed by
the target build and actual native comparison. **Fixed: Y for this reported
missing-front-wall defect; first verified development version: v0.0.29-dev3.**
Other terrain, flora and unrelated geometry reports remain open independently.

5 October owner acceptance: the owner now confirms that the reported shack is
fixed in v0.0.29-dev3. This corroborates the isolated native wall restoration and
the actual-writer/reader angle-quantization regression proof above. Acceptance
is specific to Indrele Rathryon's Shack's missing front wall panels; it does not
close unrelated buildings, rock/flora surfaces or distant terrain reports.
**Fixed: Y; owner-confirmed development version: v0.0.29-dev3.**

## TRANSITION-VIEW-29: mouse view changes during automatic cell handoff (OPEN)

Observed version: **v0.0.29-dev1**, owner report on 5 October 2026. Walk across
an implicit cell or sub-cell boundary while looking at a fractional yaw/pitch;
compare the exact view before loading and after final signon, without new input.

Source inspection found the handoff used the server's wire-rounded view, while
client reset also cleared pitch-drift state. The candidate captures the live
`cl.viewangles` and pitch-drift fields before teardown and restores exact local
view once after signon. Server facing is restored too. Explicit doors and named
teleports keep authored destination facing; failed/mismatched arrivals cancel
the pending restoration. No permanent per-frame orientation override is added.

Focused Linux fixtures pass using the real client-clear/signon and pitch-drift
paths: fractional/wrapped headings, reverse crossings, rebasing, movement modes,
one-shot restoration and explicit/failing travel. Native mouse feel and route
acceptance are pending. Keep separate from collision/residency reports below.
**Fixed: N; first verified fixed version: none.**

## TRANSITION-VOICE-29: active speech stops during automatic cell handoff (OPEN)

Observed version: **v0.0.29-dev1**, owner report on 5 October 2026. Start an NPC
line, cross an implicit cell/sub-cell boundary before it ends, and listen through
loading and arrival. The expected result is continuous speech without restarting
the line or attaching it to a newly reused actor number.

The existing map handoff clears channels and map-owned sound-cache storage;
loading also skips normal world-channel mixing. The source candidate copies the
remaining PCM of active, nonlooping NPC/intro voices before that teardown and
mixes those tails independently through loading and arrival. It preserves sample
position and stereo gains, keeps no stale cache/entity/lip pointers and does not
duplicate tails on repeated crossings. Speech-duration gates include queued
audio after the detached PCM is freed. Explicit stop/disconnect, failed handoff,
shutdown and clock reset cancel as appropriate.

Limits: four tails, **128KiB aggregate allocation including sample headers**,
plus fixed descriptors and allocator overhead. Over-budget, unsupported-format
or allocation failures print explicit refusals. This allocation is outside the
engine hunk; worst-case target memory/headroom still needs acceptance. The change
does not alter guard gain or background-music buffering.

Target allocator review found an additional failure path: the linked SDK
malloc can trap before returning NULL, making an ordinary null-result guard
insufficient. The candidate now uses Amiga Exec AllocMem with FAST|PUBLIC and
matching-size FreeMem for detached tails; the host fixture retains malloc/free.
The corrected Amiga build and 78 focused Linux source tests pass. Target
allocation refusal and measured Fast-RAM headroom remain unverified.

The sanitized Linux fixture passes actual mixer sample comparisons after the
old cache is poisoned/freed, for8/16-bit data, repeated handoffs, underrun,
cancellation and refusal paths. These are source tests, not audible native
acceptance. **Fixed: N; first verified fixed version: none.**

## SEYDA-TRANSITION-29: cell and sub-cell passage problems reported (OPEN)

Observed version: **v0.0.29-dev1**. Reported 5 October 2026, 11:56:33 and12:00:01
Europe/Helsinki.

On 5 October 2026 the owner reports continuing cell/sub-cell passage problems
around Seyda Neen and requests investigation of fewer sub-cells. Exact failing
boundary, route and mechanism remain unconfirmed. Record normal-walk crossings,
active/previous region and hysteresis, loading state, collision and placement
coverage. A larger resident region is a proposal requiring measured heap,
transition peaks and complete coverage; fewer cells are not an established fix.
Keep this report separate from the shack view and distant-horizon attribution.
Later positive owner feedback on horizon drawing does not close the passage
report or replace controlled horizon acceptance. **Fixed: N.**

## INLAND-SHORE-29: angular inland shoreline reported (OPEN)

Observed version: **v0.0.29-dev1**. Reported 5 October 2026, 12:01:13-12:01:22
Europe/Helsinki.

On 5 October 2026 the owner requests a topology/jagged-inland-water check after
a development view at global XYZ -39785,-30636,379, local XYZ -218,20,-161,
heading154, pitch30 and game time12:45. The visible angular shoreline is a
reported symptom; the cause is unconfirmed. Compare authored LAND topology,
water coverage and their intersection with the converted result at matched
pose/region. Preserve all authored water placements and heights; do not flatten
or move water based on the image. **Fixed: N.** Investigation is pending.

## HORIZON-POP-29: distant scenery pops or breaks up while turning (OPEN)

- **Priority/type:** P1 rendering issue reported in the v0.0.28 Ashlands playtest.
  Introducing revision and a correction for every reported view remain unknown.
- **Evidence/reproduction:** retain global **38205 29437 1380**, local
  **335 191 -294**, with raw **DEG 263 / P -9** and **DEG 321 / P -23**. Those
  captures change pitch as well as yaw. A later controlled case uses global
  **51855 39125 3502**, local **-348 565 107**, raw **DEG 265 / P 0**. At fixed
  pose/time, disabling far culling restores distant coverage; restoring it
  restores the original viewport. Sweep nearby yaw at unchanged pitch and time.
- **Cause established for the inspected central peak, 5 October:** the missing
  silhouette belongs to the authored opaque static `terrain_rock_rm_18`, not
  LAND alone. Source placement/transform and ray intersections identify it.
  The whole rock's bounding sphere fails the forward-distance visibility gate
  at this camera. A LAND-only horizon fill therefore cannot reproduce its
  taller silhouette. This attribution does not establish every horizon report's
  cause; the earlier bounds/PVS checks remain limited to their sampled scene.
- **Rejected correction:** a bounded heightfield remesh combining LAND with
  large rocks fails coverage, false-sky-occlusion or conservative-depth gates in
  **44 of 48 sampled views**. Its worst top-silhouette error is **13 pixels at
  128x60**. This rejects that approximation, not every possible representation
  within the budget, and is not a global error bound or native acceptance.
- **Latest diagnostic evidence, 5 October:** an opt-in exact-geometry probe
  visually restores the inspected rock silhouette, but is not an accepted
  production correction. Seven lossless 320x200 PCX captures use the same
  palette. The first and last OFF baselines differ in **17,565 of 48,640
  viewport pixels (36.11%)**, invalidating exact A/B acceptance for this run.
  The reported integer origin stayed fixed, but endpoint view angles were not
  captured. Recovered per-frame telemetry proves yaw changed from264.37 to
  268.33 degrees during the fixed-position session. Exact capture-to-sample
  alignment and pitch/render-eye data are still missing, so this does not
  establish the cause of every differing pixel or a matched endpoint camera.
- **Next controlled replay:** use the existing mouse `sensitivity 0`, set an
  explicit pose, and record measured view angles at each endpoint. Require two
  identical OFF baselines before comparing the opt-in geometry probe, LAND-only
  path and full reference. Preserve near-depth/occlusion and resource gates.
  Diagnostic switches remain opt-in and are not production defaults.
- **Next correction/gates:** preserve the opaque rock geometry or use a
  source-checked proxy that retains its silhouette and separate topology,
  including overhangs. Keep near geometry/depth protection, footprint seams and
  measured triangle/RAM limits. Repeat controlled camera sweeps and depth/
  coverage tests before native frame-cost and visual acceptance. Do not treat
  a larger draw distance or reduced reserves as the fix.
- **Status:** source attribution established; the latest exact comparison
  fails baseline stability, so no complete horizon correction is accepted. **Fixed: N. Candidate: study for
  v0.0.29. First verified fixed version: none.**

## MAP-TELEPORT-28: map teleport commands fail from F10 (OPEN)

**4 October v0.0.29 source-candidate update:** inspection found that
`map_debug_enabled()` incorrectly required visible debug HUD overlays. Hidden
overlays therefore silently disabled teleport-map access. Both aliases already
dispatch to the same utility and remain unchanged. The candidate removes that
presentation coupling while retaining explicit map availability and story/modal
gates, with explanatory refusal messages. Actual C world-UI/console fixtures
pass, including both aliases and overlay-off paths. Sampled native replay now
confirms that `dbg tp map` and `dbg map tp` each open the same teleport picker
with the HUD hidden. Checked destination/arrival and exact owner-state coverage
remain separate pending gates. **Fixed: N; first verified fixed version: none.**
The initial unknown-cause report
below is retained as history, superseded by this source diagnosis.

- **Reported:** 4 October 2026, owner playtest after v0.0.28 release. Both
  `dbg tp map` and its alias `dbg map tp` no longer work from the F10 debug
  menu/console. A subsequent owner retry of `dbg tp map` suddenly worked.
  Treat this as intermittent, not continuously failing or resolved.
  This is an owner-reported regression; the last working build,
  introducing change, exact executable/HDF identity and emulator configuration
  have not yet been established for this report.
- **Reproduction to verify:** open F10 during play and try each alias separately.
  Expected: map-point selection with a red crosshair, followed by explicit
  TELEPORT/Enter confirmation. The failing stage (opening the map, selection,
  confirmation or arrival) and any console error are not yet known.
- **Cause:** unknown. **Proposed investigation:** reproduce both routes in the
  matched target build and trace command dispatch, map/input state and checked
  arrival handling before choosing a correction. Do not bypass arrival checks.
- **Tried/results:** owner retry of `dbg tp map` succeeded. Read-only source
  inspection confirms both aliases route to `aw_teleport_map` in `aw_console.c`,
  registered to the same `open_teleport_map` handler in `aw_worldui.c`. This does
  not establish the failing UI state or runtime acceptance. No code change,
  mitigation or fix attempted. A successful retry does not close this report.
  **Fixed: N. Repair candidate: none. First verified fixed version: none.**

## MAP-SPOTS-28: white/yellow spots on the default map (OPEN)

**4 October v0.0.29 source-candidate update:** the map is generated before
sky palette reassignments, but `.awm` was incorrectly treated as opaque data.
AWM1 stores palette indices, so old terrain pixels could display newly bright
sky colours. The candidate remaps map pixels and ocean index while preserving
area metadata, rebinds the conversion receipt and validates the final staged
world-UI payload after overlay application. The combined focused map/sky suites
pass 23 interpreted checks on both Windows and Linux. Native wide and closer
map samples now show terrain, town labels and the player marker without the
reported widespread bright spots. Mouse-wheel zoom works; the closer IN-GAME
sample was selected through the explicit mode command, so it does not establish
mouse-tab acceptance. The exact owner view and broader map coverage remain open.
**Fixed: N; first verified fixed version: none.** The initial report below is retained as
history; its unknown-cause/no-attempt wording is superseded by this update.

- **Reported:** 4 October 2026, owner playtest after v0.0.28 release: the default
  in-game map screen has many white/yellow spots. A follow-up screenshot confirms
  the IN-GAME MAP PROTOTYPE view, with Balmora and Seyda Neen labels and dense
  yellow/orange dots over several land areas. The owner questions whether the
  dots are POIs; their meaning has not been established. Exact build identity
  and settings remain unconfirmed.
  Introducing revision and last known good version are unknown.
- **Reproduction to verify:** capture the reported default map/view with location,
  display mode, zoom and build identity; compare against the matching source
  and a known-good view. Expected: no unintended white/yellow spots.
- **Cause:** unknown; no palette, transparency, terrain or marker cause is inferred.
  **Proposed investigation:** identify the affected rendering layer from matching
  captures before choosing a correction.
- **Tried/results:** owner screenshot inspected; no engine reproduction, attempted correction
  or validated mitigation. **Fixed: N. Repair candidate: none. First verified
  fixed version: none.** Track separately from the earlier pale-ground defect.

## MAP-RIGHT-DRAG-29: advertised right-drag does not pan the teleport map (OPEN)

- **Priority/type:** P2 input defect identified during 5 October 2026 source
  review. The teleport picker advertises `R-drag`, but the Amiga input backend
  sends the right button as `K_MOUSE3` while the panel accepted only `K_MOUSE2`,
  which is the middle button on that backend.
- **Reproduction:** open the teleport picker, place its in-game cursor over the
  map and hold right while moving. Expected: map pans without selecting or
  confirming a destination. The baseline source fixture fails to move the map;
  the corresponding middle-button gesture works.
- **Candidate correction:** accept both secondary button codes in the teleport
  picker and end right-button dragging on release. Preserve existing middle
  behavior and global bindings. Ordinary map left-drag, left target selection,
  two clicks without implicit teleport, explicit confirmation and modal exits
  retain their existing behavior.
- **Tried/results:** the focused Linux UBSan comparison reproduces the baseline
  right-drag failure; its five preservation cases pass. All six corrected cases
  pass, including release and close/reopen state, with the existing map/journal
  checks retained. The extended public world-UI fixture and input-event suite
  pass their two focused Linux methods. Windows and Linux Amiga builds produce
  identical engine bytes. Manual native right-drag acceptance remains pending.
  It does not resolve the separate emulator cursor
  positioning or map-tab click report. **Fixed: N. Candidate: v0.0.29 source.
  First verified fixed version: none.**

## MAP-FOCUS-DRAG-29: map or journal keeps dragging after focus returns (OPEN)

- **Priority/type:** P2 input-lifecycle defect identified and reproduced in a
  source fixture on 5 October 2026. This is separate from the original map-tab
  report and the host-to-guest pointer mismatch described below.
- **Reproduction:** begin an ordinary map left-drag, teleport-map right/middle
  drag, or journal scrollbar drag; lose window focus and release the button
  outside the game; return and move without pressing a button. Expected: the
  panel stays open but the old drag has ended. The baseline host fixture instead
  continues panning or invoking scrollbar hit testing after the focus reset.
- **Cause:** both native focus events clear gameplay buttons, pending mouse
  movement and key arrays, but did not clear the world-UI drag flag. Clearing
  key arrays does not dispatch the mouse-up event that the panel was awaiting.
- **Candidate correction:** explicitly cancel that drag on focus loss and gain,
  alongside the existing input resets. Preserve the open panel, cursor, map view,
  selected destination and persistent mouse-look setting. No per-frame work,
  allocation, global sensitivity or button-binding changes are added.
- **Tried/results:** a Linux sanitizer fixture compiles the actual map, mouse,
  gameplay-button and key-reset routines, using the statement sequence extracted
  from the native focus branch. The four baseline lost-release cases fail; all
  eleven candidate cases pass. Preservation checks cover normal left/right/middle
  dragging and release, close/reopen, selection and cursor retention, and clearing
  pending gameplay motion without an extra move. Actual native focus dispatch
  and capture transitions remain pending. This result does not close map-tab or
  physical right-drag acceptance. **Fixed: N. Candidate: v0.0.29-dev1 source.
  First verified fixed version: none.**

## MAP-VIEW-SWITCH-28: mouse cannot switch map views (OPEN)

**5 October v0.0.29-dev1 input-path candidate:** the native event loop
overwrote earlier relative mouse deltas and deferred their delivery until
`IN_Move`, while mouse buttons were delivered immediately. Two movements and
a click in one event batch could therefore test the previous cursor position.
Gameplay also lost earlier movement, and pending/filter state could survive
modal boundaries. This source mechanism is distinct from the earlier hidden-HUD
gate and does not establish that every reported emulator cursor issue shares it.

The candidate dispatches each UI delta before the next button, preserving
per-event clamping, and accumulates bounded gameplay motion until consumption.
Existing modal/focus button clearing now clears pending/filter motion while
preserving the intended mouse-look toggle. Bounded multiplication replaces
negative signed shifts without adding allocations or changing sensitivity.

Synthetic Linux C checks exercise actual input, map hit testing and modal code:
eight corrected cases pass; the baseline reproduces six specific failures and
preserves the two ordinary signed/filter behaviors. Separate C99 UBSan checks
reject baseline signed shifts and pass the candidate for all three tested paths.
Existing gallery behavior passes with mouse events delivered through the real
entry point. The public regression suite includes these corrected cases.
Windows and Linux Amiga compilation now produces identical engine bytes; the
integrated world-UI and mouse-event methods also pass their focused Linux run.

A controlled emulator input trace requested a six-pixel upward host movement
but delivered two guest deltas of **(+122,+122)**. From the reset cursor, these
deltas are consistent with reaching the footer, whose click branch closes the
map; the trace does not log button dispatch or hit-test coordinates. This
identifies a mismatch in that input replay; it is neither a successful tab hit
nor proof that ordinary manual input has the same defect. Native tab/right-drag
acceptance stays open:
observe the guest cursor, then test a button without assuming host absolute
coordinates equal the game's relative coordinates. **Fixed: N; first verified
fixed version: none.**

**4 October v0.0.29 source-candidate update:** the DEBUG tab shared the
incorrect visible-overlay gate found in teleport-map access. The candidate
decouples map controls from HUD visibility and preserves explicit availability
and story restrictions. Actual C tests cover DEBUG to IN-GAME and back with
overlays off, plus disabled/story refusals; world-UI and console fixtures pass.
Input event batching was inspected but not changed. Native mouse acceptance is
pending. **Fixed: N; source candidate only; first verified fixed version: none.**
The original unknown-cause/no-repair account below is historical.

- **Reported:** 4 October 2026, owner playtest after v0.0.28 release. Clicking
  the map controls does not switch between DEBUG and IN-GAME views. The supplied
  screenshot shows both controls, with IN-GAME highlighted. Exact build and
  emulator configuration are pending; the introducing revision is unknown.
- **Reproduction to verify:** open the map and click DEBUG, then IN-GAME; record
  pointer position and whether the active view/highlight changes. Expected:
  mouse selection switches between the two views. Keyboard switching was not
  reported tested and must be checked separately.
- **Cause:** unknown. **Proposed investigation:** trace mouse event delivery,
  control hit regions and view-state changes in the matching target build;
  do not assume a shared cause with the F10 teleport commands.
- **Tried/results:** owner tried mouse clicks and reported failure; screenshot
  inspected, but no independent runtime reproduction or repair attempted.
  **Fixed: N. Repair candidate: none. First verified fixed version: none.**

## TREE-PILLAR-28: unintended pillar beneath sprite-tree roots (OPEN)

**4 October v0.0.29 source-candidate update:** the owner's transform lead
was investigated. Geometry projection uses sprite scale and authored frame
origins, while `D_SpriteCalculateGradients` sampled at unit scale with a centred
origin assumption. The actual old rasterizer produced 90 incorrect pixels of
105 checked in the authored-origin reproduction, including clamped edge-row
stretching. Corrected gradients respect the same scale/origin contract. Seven
actual projection/raster cases pass undefined-behavior/float-cast checks,
covering legacy centring, fractional/large scales, authored anchors, pitch and
clipping, transparent roots and foreground occlusion. Assets/placements and
collision are unchanged. Three native views of one representative tree sprite,
at authored scale 2 on a roughly 20-degree slope, now show a tapered root and
terrain contact without the broad striped pillar. A nearby straight base is a
separate authored tree and must not be mistaken for stretching of this sprite.
The owner's exact pictured placement, other sprite types and broader slope/
occlusion coverage remain unaccepted. **Fixed: N; first verified fixed version:
none.** The earlier unknown-cause/no-attempt report below is retained as history.

- **Reported:** 4 October 2026, owner playtest after v0.0.28 release. Some trees
  converted to sprites have an unintended pillar-like root. The supplied image
  shows the broad trunk base extending into a tall, vertically striped block
  exposed on sloping ground. Exact cell, tree model/reference, transform and
  executable/HDF identity are pending; the introducing change is unconfirmed.
- **Reproduction to verify:** locate the pictured tree and inspect its base from
  several angles on the slope. Compare its original model and source placement
  with the sprite bake, alpha/bounds/origin and final runtime representation.
  Expected: the intended trunk/root silhouette and placement, without a stretched
  vertical pillar beneath it. Preserve intended roots and terrain contact.
- **Cause:** unknown. **Proposed investigation:** distinguish bake/alpha or edge
  sampling artifacts from origin/scale/placement and retained geometry issues
  using matched evidence; none is established by the screenshot alone.
- **Tried/results:** owner screenshot inspected and retained as evidence; no
  engine reproduction, code change or mitigation attempted. **Fixed: N. Repair
  candidate: none. First verified fixed version: none.** Recheck sloped and flat
  placements and retained mesh trees when a correction is available.

## SKY-GROUND-28: pale ground and excessive cloud speed (OPEN)

- **Observed:** 4 October 2026, native WinUAE playtest of the assembled V3
  v0.0.28 candidate. The registered Seyda Neen street view displays flat pale
  ground under textured buildings and the guard. The owner also observes cloud
  motion far too fast. The scripted lighting/camera sequence is a diagnostic,
  not a normal-gameplay speed or appearance pass.
- **Reproduction:** enter the registered town, view the guard and adjacent
  street in daylight; compare the same camera with fog/cloud rendering disabled.
  Host geometry, collision and file-readback checks did not expose this defect.
- **Cause:** the reconstructed LAND writer emits edge loops with the opposite
  winding to the native Quake BSP convention. Stored faces and collision remain
  present, but visible span rendering fails. All 5,597 new LAND faces in the
  inspected town map differ from the original face orientation. The reconstruction
  introduced this defect; host checks did not enforce the native winding contract.
  The earlier zero-winding-change checks proved that clipping preserved input
  orientation, including the incorrectly authored loops. The new regression
  checks the native convention separately.
  Cloud phase combines the persistent 30-times clock with Quake's scroll rate.
- **Correction:** reverse 442,861 LAND loops across the bounded 64-map batch;
  all other BSP lumps and file sizes remain identical. Correct the reconstruction
  writer and add a winding regression. Cloud speed gains `dbg skyspeed`, default
  approximately 1/300 of the old rate (`0.00333333333`), without changing
  sun/color timing or the approved sunset palette. This is one third of the
  preceding `0.01` candidate. Native motion acceptance remains pending.
  A same-camera native comparison with only the town map repaired and the
  original engine restores brown textured ground and stone foreground. Fog-off,
  clouds-off and V1/V3 comparisons retain the ground. The initial combined-engine
  town replay also shows restored brown ground. Broader native routes and cloud
  motion acceptance remain pending. Gallery preview is implemented
  as `dbg daycycle gallery`, separately from normal play. The correction is
  verified in bounded native town views so far; release still requires the
  remaining combined-image routes and accepted normal cloud motion.

## SKY-STARS-28: enlarged stars and night-layer ordering (OPEN)

- **Observed:** 4 October 2026, native WinUAE v0.0.28 night views. Bright stars
  became large slanted diamond-shaped patches over the original night artwork.
  Disabling `dbg starsky` removed them. Opaque foliage appeared to cover the
  layer, but fine sprite transparency and both moon silhouettes still require
  explicit native verification; their failure is not inferred from the report.
- **Cause:** the first reduced 128 by 128 composite preserved maximum bright
  source-star samples and projected each atlas texel over a visible sky area.
  A bright texel therefore grew to several screen pixels. Combining stars into
  that atlas also placed them over visible nebulosity. This was introduced with
  the first combined original-night layer in the v0.0.28 development candidate.
- **Correction:** AWN2 adds an explicit 2,048-byte point-role mask; each marked
  star projects to at most one native screen pixel. The first AWN2 revision
  removed large diamonds in native views but did not show the intended tiny
  stars. Of its 136 points, only 20 lay in the sampled upper hemisphere, and
  doubling the original nebula alpha hid further source stars.
  The corrected conversion maps the full source square into the valid upper-sky
  domain and preserves original nebula alpha. Its 163 original-source points
  all occupy valid upper-sky directions, including overhead, in dark nebula gaps.
  Black background gaps remain transparent; full moon discs, including unlit
  areas, cover the field. All sixteen original moon tiles remain byte-identical.
  Semantic sky depth retains the layer behind terrain, actors and opaque foliage.
- **Evidence/status:** fifteen focused Linux fixtures pass, including two
  viewport sizes, the full dark moon mask, transparency, sky/world depth and
  legacy-atlas upgrades. Seven further converter checks cover upper-sky mapping
  and the revised conversion receipt. Corrected matching target builds and image
  image015 passed scoped native sky inspection in selected actual-map views. All-map routes and unrestricted world acceptance remain outside scope; stable v0.0.28 is accepted locally within its declared image015 scope.

## ARRIVAL-CEILING-28: coordinate arrivals blocked by solid ceiling shell (OPEN)

- **Observed:** 4 October 2026, native v0.0.28 coordinate arrivals to the dock
  guard, Erene and two pressure routes reported `arrival blocked` and preserved
  the previous scene. Standard town/Balmora/ship transitions still worked.
- **Cause:** the full-height floor search began inside the solid map ceiling
  shell because render bounds included that shell. The standing-hull trace
  consequently returned `startsolid`. The introducing source revision is not
  established; no missing terrain or collision-tolerance defect is inferred.
- **Correction:** `AW_MapPlace` searches downward at the same XY, at most 128
  units, for a clear full-standing-hull trace start. The existing strict floor,
  water, walkability and final standing-clearance checks remain unchanged. No
  BSP geometry, collision data, player size or allocation policy was relaxed.
- **Evidence/status:** all four failures reproduced using the actual engine
  traces and exact packaged owned hulls; all four then reached valid clear
  placements. Two compiled spawn/walking regression methods also pass. The
  selected `sn012` coordinate lands on a roof, so that result is not proof of
  ground walking. Dynamic actors/doors and new native route replay remain
  pending. Verified fixed version: pending.

## PACKAGE-PORTABILITY-28: source ZIP modes and Windows path aliases

- **Observed:** 4 October 2026, v0.0.28 preparation-helper review on Windows.
  Rebundling a source tree recreated ZIP entries with mode 0600, losing
  executable modes. Paths containing alternate-stream colons, reserved
  device names or trailing dots/spaces also passed lexical validation.
  No delivered release is known to be affected; the introducing revision
  is not established.
- **Reproduction/cause:** rebundle a synthetic mode-0755 shell entry and
  inspect its ZIP metadata; submit device/stream/alias names to the path
  validator. Entry recreation discarded metadata, and the validator
  checked traversal without excluding Windows filename aliases.
- **Correction and evidence:** preserve each source entry's Unix origin
  and permission metadata; reject nonportable path components and compare
  case-folded ZIP names on every host. Five interpreted preparation-helper
  checks pass, including byte/mode preservation, path rejection and the
  checksum-inclusive size boundary. Actual final-package extraction and
  audit remain required. Status: preparation-helper correction validated
  with synthetic inputs; no new game-engine fix or native acceptance claim.

## Current v0.0.28 validation status — 4 October 2026

The latest source gate, finalization011, passed at 17:45 EEST on 4 October 2026.
It ran 824 tests per host: Linux 820 passed / 4 skipped and Windows 732 passed /
92 skipped, with no failures or errors. Fresh actual Amiga cross-compiles on
Windows and Linux Docker used the same 206 runtime sources and produced identical
744,860-byte executables (SHA-256
`a5aa451e297b517cd0d2e072c4e5ccc4eb39bf09e93c67eed72586b55265955b`). The 1,096
frozen source files match across hosts, with no source drift. The target ABI was
measured in Linux Docker, not with a Windows size probe.

These gates include the full upper-sky star conversion, `dbg nightgallery`,
the ceiling-start arrival correction, the latest cloud-speed change and
64 KiB of music-only source read-ahead. Shared mixer timing, speech and
guard voices are unchanged. The current WinUAE listening report still notes
intermittent artifacts, mostly at load-ins and in heavy scenes. The audio issue
remains open; publication proceeds with this known limitation, with further
audio investigation deferred until after publication. See [WIN-05](BUG_JOURNAL.md#win-05-intermittent-winuae-background-music-snapping---investigation-open).
The compiler retains 86 warnings; these are successful builds, not warning-free
builds. The earlier 816-test/739,156-byte result is
superseded for this source. Compilation and host fixtures do not establish
native image appearance, gameplay or performance acceptance.

Image015 assembly uses the exact matching engine and passes 10,766 payload
readbacks plus three partition-ownership checks. The audit records 59 modeled
reserve warnings and no modeled hard allocation-ceiling failures. These are
estimates and file-verification results, not a production-memory pass. Earlier
native startup, restored town ground and clock checks apply to a preceding image.

Independent actual WinUAE acceptance of engine011/image015 passed within its
declared scope. Two fresh cold-cache sessions exercised Imperial and Hlaalu
guards: each admitted all three eligible actors with no frame/model skips or
evictions, and boundary checks showed torches on at 20:01/05:59 and off at
06:00/20:00. Bounded close captures confirmed subtle moving gold/ember particles.
Five pressure maps completed without crashes or renderer overflow. All eight day
and four night gallery stages were captured, independently caption-reviewed and
restored. The 137 fresh native captures were preserved, alongside image014's
historical captures and saves. All 10,766 image files and three partition
ownership checks passed. This is a scoped native pass, not all-map, unrestricted
world, or physical-hardware certification. The minimum logged peak clearance
was 1,812,304 bytes at sn012, 284,848 bytes below the unchanged 2 MiB safety
reference. That remains a reserve warning; the production memory gate did not
pass. Intermittent music artifacts remain an owner-deferred known issue, and no
clean-audio pass is claimed. Stable v0.0.28 is accepted locally within this
scope; hosted CI, tag and public publication remain pending the owner's Linux
publication step.

The coherent 049/050 terrain batch passes all 64 strict serialized repeats over
2,129,800 placed polygons. The seven-map float32 correction replaces 13 faces
and adds 1,776 bytes without changing collision/PVS/actor bindings. Its 12 NPC
identity/support checks and 1,696 standing probes pass. Historical isolated-map
034/039 failures and 29 outside-coverage diagnostic probes remain historical,
not a current target defect or acceptance claim. Native ground/routes, clock,
profile/travel, appearance and lifecycle checks remain pending. Mitigation is
still distinct from a fixed version; neither host success nor image readback
alone closes a target incident. See [terrain evidence](CANONICAL_TERRAIN_CULLING.md).

## Required incident record

Always document every bug, issue and regression with:

1. **What and where:** symptoms, full affected version/build and environment, location or subsystem,
   reproduction steps and impact.
2. **Cause:** the established failure mechanism and introducing update/change.
   Record the introducing version/change when known. State explicitly when
   diagnosis or the first introducing version is unknown or suspected.
3. **Fix:** the actual correction, any temporary mitigation, regression coverage,
   validation results and remaining limits. Name the repair candidate version
   and verified fixed version separately. Unverified corrections remain open;
   use pending for the fixed version until acceptance is established.

Update the relevant subsystem guide and current release state when needed.
A passing retry or estimate alone does not close a confirmed incident.

## Producer's rule: mitigation is NOT a fix

Mitigation is a bandage. Record workarounds and partial corrections separately
from the actual verified fix. Do not close a bug because it can be avoided or
because one contributing allocation was removed. Every report must identify
(1) version, bug, location and circumstances; (2) how to replicate; (3) how to
fix, with evidence and verified fixed version. Unknown/pending facts stay explicit.

Current release: [published stable v0.0.27](RELEASE-v0.0.27.md), 3 October 2026.
Its hosted CI, source publication and downloaded-asset checks are complete.
The repaired private image passed assembly/readback and the complete static map
gate. [CRASH-01](HEAP_CRASH_v0.0.27-rc3.md) remains an open target-validation
incident; publication does not certify its exact route or a heap lifecycle.
Earlier rc build records below retain their historical status and evidence.

## DOC-STATE-01: published v0.0.27 described as an unpublished candidate (DOCUMENTATION BUG)

- **Observed/version/environment:** 3 October 2026, after stable v0.0.27 was
  published. The root README introduced v0.0.27 but still named v0.0.26 as latest
  and offered v0.0.26-rc1 emulator setup. Current-state, release and subsystem
  pages retained completed publication/build/fixture checks as pending.
- **Reproduction and impact:** read the README release link, emulator table and
  release-status paragraphs together. They disagree with the published tag and
  cause readers to select old setup files or mistake completed checks for open
  gates. No runtime or playable payload defect is implied.
- **Cause:** new summaries were prepended without reconciling the rest of the
  landing page and related status records. The inconsistent content is present
  in the published v0.0.27 source; the first earlier introduction is unproven.
- **Correction:** a documentation-only follow-up updates the full README,
  current release/state/roadmap, changelog and related guides against publication
  and validation receipts. Historical screenshots and dated evidence remain;
  genuine target-playtest limits remain open. Existing tags/assets are unchanged.
- **Status:** local editorial correction for the main branch, following v0.0.27.
  Source/link/encoding review and the separate handoff validation must precede
  publication of this follow-up. Verified published correction: pending.


## v0.0.27-rc3: terrain and held-input candidate assembled

Seyda Neen real-ground apron/shared world sampling and automatic-transition
held-input preservation are assembled. The rc3 engine, strict actor contact,
full gallery, filesystem readbacks, HDF checksums and emulator mount lists
passed. Actual outer subdivision core/coverage records were checked against
the runtime contract. Owner terrain/Shift/Ctrl/focus and character-state
playtesting remains pending. See [rc3 notes](RELEASE-v0.0.27-rc3.md) and the
[growing cell-change checklist](CELL_CHANGING.md).


## v0.0.27-rc2: Rocks and Mushrooms - mushroom correction accepted; town handoff open

This candidate separates the mushroom seam correction and `dbg map tp` alias
from the original rc1 playtest. All five mushroom models retain exact source
geometry and UVs on joined sections. All 2,526 corrected world regions passed
existing storage, face and collision limits in 303.469 seconds. New image assembly, strict actor contact (zero unresolved), full gallery,
filesystem readback, independent HDF hashes and both configuration disk lists
passed. The owner accepted the corrected mushroom caps in the rc2 WinUAE
playtest. The Seyda Neen terrain handover blocked that rc2 candidate; its later
correction is included in v0.0.27 with target boundary acceptance still open.

## INPUT-01: held flight modifiers reset on cell changes - rc3 correction awaiting playtest

The owner reports held Ctrl/Shift noclip speed modifiers resetting when a cell
or sub-cell loads. Release and press again is a temporary workaround. Audit
held input and persistent gameplay state separately from coordinate rebasing;
future NPC pursuit must continue across residency boundaries. The rc3 scene loader retains held input at automatic crossings; doors and
teleports retain deliberate clearing. The real transition harness passes in
both variants and checks health, hands, torch, noclip, velocity and view state.
Owner Shift/Ctrl release/focus playtesting remains pending. Pursuit is not
implemented by this correction. See [cell changing](CELL_CHANGING.md).

## GEO-02: Seyda Neen ground disappears before the world handoff

The owner reproduced a sharp landscape change near the eastern town boundary
in rc2. The town remains resident to local X=1600, but its converted ground ends
at X=1664, leaving only 64 units of landscape ahead of a 540-unit draw distance.
The world map then supplies terrain that the town never rendered. The town and
world also used different coarse material selection and shoreline sampling.

Correction introduced in rc3 and carried into v0.0.27: retain the town handoff,
provide the authored LAND apron, and share world terrain sampling, triangulation
and material selection outside the detailed port approach. Later bounded town
subdivision and final image assembly passed their static gates/readbacks. Exact
boundary playtesting remains required; no emulator acceptance is claimed yet.

## GEO-01: giant mushroom cap gaps after material-wise reduction - 2 October 2026

Symptoms: repeated open cap rims in Ascadian Isles during the local v0.0.27-rc1
playtest. All five giant-mushroom models were checked against exported original
geometry. Their material sections share source positions; independent reduction
moves or removes these joining vertices (parasol rim displacement up to roughly
199 source units). This is not evidence of a missing filler texture.

Correction: mushroom profiles preserve material sections that share source
vertices, including their original UVs. Rock reduction is unchanged. A synthetic
shared-rim regression checks exact geometry and UV retention. This conservative
correction increases mushroom triangles. Rebuilt BSP budget checks passed, and
the owner accepted the closed caps in the rc2 WinUAE playtest. Boundary-constrained
reduction remains a possible future optimization.

## v0.0.27-rc1: Rocks and Mushrooms - local playtest checkpoint

The complete world overlay covers 37,960 original exterior rock references and
816 giant-mushroom references across 2,526 retained world regions. Original
placements, transformed collision and original texture sources are used; visual
meshes and textures are reduced for the renderer. Small collectible mushrooms
are excluded. Town sub-cell divisions remain deliberate FPS controls.

Local assembly passed strict actor contact with zero unresolved cases, the
required 2,935-record / 3,551-model NPC gallery, complete filesystem readback,
and independent HDF checksum checks. Storage uses two simultaneously mounted
HDFs (approximately 3.75 GiB and 1 GiB); it is not disk swapping.

Owner playtesting reports rock geometry looks reasonable, Red Mountain gains
its missing formations, and giant mushrooms are visibly rendering in the
Ascadian Isles (owner screenshot confirmation). Rock texture
correctness is not yet accepted. This does not establish complete town coverage,
Linux/FS-UAE gameplay acceptance, real-hardware performance, or release readiness.
The original master places giant parasols northeast of Seyda Neen in Ascadian
Isles cells (0, -9) and (-1, -8), not just distant mushroom regions. Region vf1019
contains an original giant parasol close to its core centre for testing.

The builder now generates FS-UAE and WinUAE configuration files beside full and
asset-free images. Both FS-UAE launch paths read the complete verified HDF list;
missing world disks stop configuration. The terminal-width final footer lists
all HDFs and both runner paths, also retained in the build summary. Docker exports
receive separate host-local configurations rather than container filesystem paths.
Configuration, summary and Docker boundary regressions passed locally; the new
Docker export path still needs an actual container integration test.

## WIN-05: intermittent WinUAE background-music snapping - investigation open

**4 October 2026 follow-up — OPEN, audible artifacts persist.** During the
current v0.0.28 WinUAE opening playtest, the owner initially rated the audio
5/5 and described the music glitch as fixed for now, then immediately qualified
that verdict: some audible trouble remains, mostly at load-ins and in heavy
scenes. The later report supersedes the initial positive impression. This is human listening evidence for the current
session, not an uninterrupted-audio acceptance or a completed release gate.

**What failed and what was tried.** Background OST crackle/snapping was reported
particularly under WinUAE; no general guard-voice defect was established. The
earlier separate host-buffer proposal was 16,384 to 32,768 bytes and remained
an unverified experiment. During this candidate's investigation, increasing
shared `_snd_mixahead` from 0.1 to 0.25 seconds was initially proposed. The owner
restricted the change to music, so the shared-mixer source was restored byte
for byte before compilation. No build or listening result belongs to that
abandoned mix-ahead proposal; speech and guard-voice code were unchanged.

**Implemented mitigation.** The OST source queue grew from two to four
16,384-byte stereo PCM blocks: 32 KiB to 64 KiB, with the existing bounded
4 KiB refill slices. Music status/profile diagnostics expose buffer size.
The shared mixer schedule, DMA buffer, speech and guard voices remain unchanged.
The PCM queue adds 32,768 static bytes. Separately, the complete executable's
BSS increased from 1,395,360 to 1,428,156 bytes (+32,796), and total CODE/DATA/BSS
from 2,055,256 to 2,088,920 bytes (+33,664). These whole-executable totals are
not the PCM payload alone or the fixed 11 MiB game heap; they do not establish
native peak-memory clearance.

**Checks and attempted-test correction.** The new buffered fixture initially
had two reversed left/right expected-sample assertions. Correcting that oracle
did not change runtime code. The resulting fixture preloads all four blocks,
then verifies 30,000 stereo sample frames with exact left/right values, no
additional file reads, zero synchronous fills and zero read errors. Existing
full-track, partial-tail, playlist/history and bad-file checks also pass. Full
host gates run 822 tests each: Linux 818 passed/4 skipped, Windows 731 passed/
91 skipped. Matching Amiga builds produce the same 742,884-byte executable.
These checks establish functional streaming behavior, not a cure for crackle.

**Current conclusion.** More source read-ahead should reduce the risk of OST
source starvation; that is an engineering explanation of the mitigation, not
proof of the original hardware, emulator/backend or mixer-deadline cause.
The owner's qualified listening report leaves the audible issue unresolved.
The owner prioritizes publication with this known issue and defers further
audio investigation until after publication. Do not add another audio
investigation as a gate for this release. Matched-route listening, captured
output and guest/host timing diagnostics remain follow-up work. Status:
functional mitigation validated; audible fix and fixed version remain
unverified. Preserve both owner observations in that order.

1. **Symptoms, impact and cause.** During v0.0.27-rc1 WinUAE playtesting, the
   owner reported recurring background-music glitches, resembling underruns, in
   v0.0.27-rc1 and earlier WinUAE sessions. Earlier Linux FS-UAE runs did not
   exhibit the same reported symptom. The report concerns background music;
   sound-effect snapping has not been reported. Root cause is unknown; this observation
   does not isolate game streaming, emulator scheduling, backend buffering or
   the host audio driver.
2. **Reproduction.** Reported while playing the current image; no deterministic
   minimal reproduction yet. Compare the same scene and track, recording whether
   snaps coincide with map loading or occur during steady playback. Repeat with
   host conversion/build tasks stopped. Compare music streaming diagnostics
   (`music-profile.txt` after normal game shutdown: `read_errors` and
   `synchronous_fills`) alongside WinUAE buffering. Synchronous fills include
   expected startup/track changes, so their count alone does not prove underruns.
3. **Experiment, not a fix.** Keep the reference `sound_max_buff=16384` and test
   a separate private WinUAE configuration with `32768`. It mounts the same two
   HDFs and changes only the audio buffer. Crackle reduction and latency have not
   been verified. Linux presets and game audio code are unchanged by this test.

   Frame-rate distinction: the WinUAE status-bar ~49.9 value measures emulator
   display/vsync frames, not game renders. AmiWind `Host_FilterTime` already
   limits ordinary game frames to 72 per second. `dbg show fps on` exposes the
   game counter. `host_framerate` changes simulation timing and must not be used
   as an FPS-cap workaround. A 25/50 game-cap experiment needs a separate real
   limiter; do not change PAL chipset timing as a substitute. Inspect
   `frame-profile.txt` after normal shutdown for `audio_late_updates`,
   `missed_audio_frames` and the separately counted startup warmup; these
   counters can distinguish late guest mixing from a host-backend symptom.

## WIN-04: gallery allowance receipt differs after Windows staging

1. **Cause, symptoms and impact.** During v0.0.27-rc1 local assembly, the
   complete retained NPC gallery validated, but staging regenerated
   `model-budgets.txt` using the host default newline translation. Windows
   produced CRLF while the gallery receipt described LF bytes. The strict
   required-gallery check stopped assembly with a changed-payload error.
   This was a text-writer portability defect; converted models were intact.
2. **Reproduction.** Stage a gallery generated on Linux on a Windows host,
   then validate the staged allowance file against its original receipt.
3. **Correction and verification.** `write_allowances` now writes explicit
   UTF-8 and LF. A byte-level regression verifies the header, record separators,
   and absence of carriage returns. The fresh local assembly retry validated
   2,935 gallery records and 3,551 models, including the inspection map.
   Final disk readback and gameplay remain separate acceptance checks.

## CI-01: Windows short-path aliases fail host-discovery assertions

1. **Cause, symptoms and impact.** In AmiWind v0.0.26-rc1, the Windows 2022
   host-parity job failed two tests: managed-font discovery and SDK discovery.
   The runner supplied an 8.3 short alias in its temporary-directory path.
   Discovery correctly returned resolved long paths, while assertions compared
   unresolved fixture paths. Both names referred to the same files. Linux source
   checks, the asset-free Amiga build and Ubuntu host parity passed. The release
   gate stopped before tagging. This failure does not establish a compiler or
   asset-conversion defect.
2. **Reproduction.** On Windows, create a temporary directory with a distinct
   8.3 alias, set TEMP and TMP to that alias in a child process, then run
   unittest discovery for test_build_host.py. Both failures reproduced locally.
   An ordinary long-path temporary directory passed, masking this CI difference.
3. **Correction and verification.** Resolve expected SDK, map-tool, QCC and font
   paths before comparison. Keep short-path inputs in the fixtures to exercise
   discovery. This also exposed a later setup-preview fixture passing an invalid
   MSYS2 tools path containing a short alias or spaces. Preview now uses a unique
   nonexistent path on the same drive with supported characters; it creates no
   files there. No production or Linux launcher code changes. All four CI test
   groups passed locally with short-path TEMP/TMP after correction (30 tests,
   two POSIX-only skips). An explicit Windows 8.3 regression retains this case
   in the suite; it skips only where the volume supplies no distinct short alias.
   The corrected v0.0.26-rc1 subsequently passed hosted Windows parity before
   publication; v0.0.26 and v0.0.27 also passed their required hosted parity jobs.
   The fix is verified in published v0.0.26-rc1; local evidence alone was not the
   publication gate.

<a id="win-03-windows-image-packing-command-exceeds-process-limit--validation-pending-2-october-2026"></a>
## WIN-03: Windows image-packing command exceeds process limit â€” fixed in working tree, 2 October 2026

1. **Type, cause, symptoms and impact.** Deterministic Windows host packaging
   defect in the v0.0.25 Windows port. All 25 pre-image stages passed, including
   all 3,551 NPC gallery models and 2,526 world regions. Image assembly reached
   `tools/world_volumes.py:pack` and failed launching `xdftool.exe` with
   `[WinError 206] The filename or extension is too long`. The generated terrain
   partition command contained 6,618 arguments / 165,293 UTF-16 code units,
   including its terminator, to write 1,651 files. This exceeds Windows'
   32,767-unit CreateProcess command-line limit; the message does not mean an
   individual game filename is too long. The boot-volume command has the same
   scaling problem. This is separate from WIN-01's intermittent queue handles.

2. **Reproduction and evidence.** A full native Windows build using normal game
   content reaches this oversized partition command. Capturing its argument list
   reproduced the size above; a harmless child-Python invocation with a 40,000
   character argument independently reproduced WinError 206. The failed run and
   completed conversions are retained. Its 1,925 instrumented worker lifecycles
   reported no invalid handles; that single run does not close WIN-01.

3. **Correction and validation.** `tools/build_windows_xdftool.py` splits the
   command queue only between complete `+`-delimited operations, preserving file
   order and paths. Each invocation is bounded to 24,000 UTF-16 units including
   Windows quoting and the terminator. A failed batch stops assembly immediately;
   an individually oversized operation is rejected before any image writes.
   Only Windows world/boot packaging selects this helper. Linux's original
   invocations, image contents and validation gates remain unchanged.
   A real 1,100-file image test passed all byte-for-byte readbacks across five
   commands; its original command was 116,774 units. Four regression tests cover
   queue preservation, quoting/UTF-16 length, oversize rejection and failure
   propagation. Full retained-conversion image assembly was retried into a
   fresh output directory with all normal gates. The image retry passed in
   433.078 seconds; both partitions passed complete readback, the actor gate had
   zero unresolved findings, and WinUAE entered the prison scene. WIN-03's
   correction is verified and included in v0.0.26-rc1.

The image-only retry is a bounded local recovery after checking source changes
and all retained terrain hashes. It is not general pipeline resume support and
does not rewrite the failed full-run receipt as successful.

<a id="win-01-intermittent-geometry-worker-queue-failure--open-2-october-2026"></a>
## WIN-01: intermittent geometry worker queue failure â€” open, 2 October 2026

1. **Type, symptoms, cause and impact.** Host-side parallel asset conversion
   on Windows 11, official CPython 3.12.10, in the Windows port based on cloned
   v0.0.25 commit `3433922c40a48ffd20a0362ed58407298221686a`.
   Interior, Balmora and Census conversion have failed in geometry work
   dispatched by `tools/prepare_mesh_bsp.py` through
   `tools/build_parallel.py:ordered_map`. A worker raises
   `OSError: [WinError 6] The handle is invalid` inside Python's
   `multiprocessing/queues.py`, at `self._sem.release()` in `Queue.get`.
   The queue's semaphore handle is invalid when released; why it became invalid
   is **unknown**. The pool reports `BrokenProcessPool`, the stage fails, and
   the builder cancels sibling work. The Amiga engine compiler passed in these
   runs. This does not establish a compiler defect, memory exhaustion, or an
   excessive worker count. Windows cancellation also left orphan workers;
   process-tree cleanup needs a separate verified correction.

2. **Reproduction and evidence.** Complete native conversion via `build.cmd`
   with owned game inputs and `--jobs 24`. Three retained full-run attempts failed:
   interior with 17 effective pool workers under a 24-worker total budget,
   Balmora with 12 while the gallery had 12, and Census with 12 while a
   separate 12-worker gallery was active.
   Keep run receipts and the corresponding stage logs. Reproduction is
   intermittent: an isolated 24-worker interior pass, eight rounds of a
   24-worker synthetic geometry probe, and five repetitions of the first two
   Balmora regions with 12 workers passed. The complete 64-region Balmora diagnostic, ten instrumented Census geometry
   repetitions and three exact Census stage-command replays also passed.
   The independent gallery completed all 3,551 models and payload validation
   (790 reused, 2,761 freshly converted, zero failures). An instrumented full
   run then passed every conversion stage with 1,925 worker lifecycles and no bad
   handles, before failing separately at image packaging (WIN-03). Root cause
   remains open; this passing conversion does not establish full-build reliability.

3. **Fix or mitigation and validation.** No confirmed fix or reliable workaround
   yet. Retain validated conversion caches and diagnose with separate output
   directories. Close only identified orphan descendants of a failed build.
   These are recovery measures, **not a fix**. Do not disable required content,
   lower quality or waive validation gates. A future process-management fix
   must be scoped to Windows, preserve Linux worker behavior, and be validated
   under the failing workload and a complete build before closing this entry.

See [Windows build and known issues](WINDOWS_BUILD.md#windows-build-and-known-issues).

**Review findings.** The observed `Queue.get()` failure occurs after receiving
the next task's serialized bytes and before decoding that task. The earlier
tracebacks do not show whether the worker had already processed any tasks.
Each Windows worker owns a duplicated semaphore handle: ordinary parent-side
garbage collection, slow result consumption, or another pool closing its own
handles does not by itself explain an invalid worker-local handle. Code review
has not identified an executor-lifetime error in `ordered_map`.

Instrumented full-run diagnostics now record handle type during deserialization,
before/after worker standard-input cleanup, at worker entry, and on queue errors,
with the number and identity of previously received work items. These records
are private diagnostic artifacts, not release assets. Interpret a failure at
startup separately from a handle becoming invalid after geometry work. A handle
number reused for another kernel-object type would support a local close/reuse
problem; that has not yet been observed. Standard-input cleanup was considered,
but the tested interpreter's initial stdin uses `closefd=False`; it remains a
low-confidence hypothesis, not an established cause.

No automatic retry, alternate multiprocessing backend or reduced-content build
has been adopted as a fix. If the failing handle was initially valid, a scoped
[Windows native handle trace](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-htrace)
can identify handle-open/close/invalid-reference call stacks. A passing run with
different concurrency and cache state cannot alone identify the cause.

<a id="win-02-cancelled-windows-stage-leaves-worker-descendants--open-2-october-2026"></a>
## WIN-02: cancelled Windows stage leaves worker descendants â€” open, 2 October 2026

1. **Type, cause, symptoms and impact.** Host process cleanup. Windows stage
   cancellation currently calls `Popen.terminate()`/`kill()` on the immediate
   process. Unlike the Linux process-group path, that does not terminate the
   entire descendant tree. A cancelled gallery left twelve Python workers alive
   after its parent exited, consuming resources or waiting indefinitely.
   This is separate from WIN-01; it is not evidence of the semaphore root cause.
2. **Reproduction.** Run independent conversion stages concurrently and cause
   one to fail while another owns a worker pool. Inspect the cancelled stage's
   descendants after its parent exits. A synthetic Windows parent/child fixture
   can test this without game data or disrupting an active build.
3. **Fix status.** A Windows-only process-tree termination candidate passed the
   isolated parent/child test, including the virtual-environment launcher. It is
   not integrated into the public scheduler. A separate candidate also passed a
   synthetic scheduler forced-failure test; production integration and a full
   failure-path build remain pending, so this issue remains unfixed. Linux process-group handling must remain unchanged.
   Until integration, explicitly close only verified orphan build descendants.



## Intermittent inability to ready hands: unknown state (open)

The owner reported F temporarily ceasing to raise/lower the hands. Debug mode
and the map were initial suspicions, but repeating both did not reproduce it.
Do not label either as the cause. No reliable trigger or state capture exists
yet. Track separately from the repeated visible-fist disappearance; the latter
is the persistent and more immediately distracting visual defect.

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Record every reported regression here or in its linked version record. Include
affected version, symptom, reproduction, established cause (or explicitly unknown),
exact implementation, native validation and unresolved limits. Host tests,
cross-compilation and native playtesting are separate evidence. Preserve older
records when a diagnosis changes.

## Torch grip and periodic fist disappearance â€” open, 2 October 2026

Owner screenshots show the placeholder torch beside the fist, and the owner
reports that the fists stay visible, blink completely off very briefly, and
return immediately. This brief blink repeats roughly every 1â€“2 seconds;
1â€“2 seconds is the interval between blinks, not the duration of invisibility.
The symptom has been present since hands were first implemented. This is a longstanding
bug, not a new torch regression; its period is not established as the
2.67-second animation loop. The rc7/rc8 torch overlay was positioned independently of the animated hand.
rc9 replaces it with the original torch mesh, authored grip and emitter-aligned
flame. Emulator acceptance of that replacement remains pending. The eight baked idle frames are
nonempty and a repeated actual QuakeC VM test retains the model across loop
boundaries; the reported 3D rendering disappearance remains unreproduced.
See [torch source findings and next checks](TORCH.md#original-model-replacement-and-reported-hand-flicker).
Neither the grip nor flicker is declared fixed by the rc8 crash correction.

## Scaled Seyda Neen flora omitted â€” open, 2 October 2026

The retained rc3 regional maps contain only five of sixteen large Bitter Coast
tree placements from the two named Seyda Neen cells. All sixteen reached the
scenery index and their sprite files exist. The other eleven have non-unit
source scales and are skipped by `prepare_quake.py`; that filter remains in rc8.
The Seyda brush pass excludes flora, so it supplies no replacement. This is a
placement omission, not merely delayed runtime loading. No fix is included in
the delivered rc8 torch package. See the evidence and planned repair in
[asset coverage](ASSET_CATALOGUE_AND_GALLERY.md#confirmed-omission-scaled-bitter-coast-trees).

## rc7 torch activation crash (rc8 source correction)

Reproduction reported by owner: raise fists with F, then press V; game crashes.
The successful rc7 native/image build and CI did not detect it. Host reproduction
calls the actual brush-render entry point with one active dynamic light and a
converted-style model whose collision root is -5. rc7 faults in R_MarkLights
while reading node contents before the node array. The retained bm015 fixture
contains 42 negative-root brush models; this is valid generated geometry.

Positive mesh collision trees can also contain no face references. rc8 therefore
lights the model's own visible surface range instead of following either kind
of collision root. Surface bounds, local light transforms, model-box rejection,
plane distance and tiled-surface exclusion are retained or checked explicitly.
The unsigned last-slot mask also avoids signed-shift undefined behavior.

The new address/undefined-sanitized regression fails on rc7 and passes on the
correction. It exercises R_DrawBEntitiesOnList, not just the standalone lighting
helper. Emulator retest remains open. No geometry regeneration, actor waiver,
water change or removal of the torch feature is used to bypass the fault.

## rc7: contact fitting, fog-off sky and cave lighting

The 23 rc3 contact findings cover 15 placed references, including one outdoor
Balmora Dreamer; they are not missing actors. Origin-only support differs from
contact of the quantized idle mesh. rc7 fits the mesh within bounded placement
constraints and preserves that certified point at runtime. The strict checker
is unchanged. See [contact method and evidence](NPC_GROUND_CONTACT.md).

The reported fog-off pale outdoor background matches the solid clear-colour
path where far-culling leaves uncovered pixels. rc7 uses the existing sky for
those pixels and restores normal solid background indoors. Native pixel tests
cover this path; the precise Red Mountain camera still needs replay, and terrain
holes are not declared fixed solely by changing their background.

The F/V temporary torch uses existing dynamic lighting. A related renderer
problem was exposed by translated/rotated cave models: light origins were in
world coordinates where surface calculations required model-local coordinates.
Both dynamic marking and accumulation now use the same model transform. Tests
exercise actual surface lighting. No water-rendering code is changed; cave
appearance and Amiga performance remain playtest tasks.

## AW25-09: image rejects world/journal receipt after terrain â€” v0.0.25-rc3

The reported workstation run completed world-terrain in 4232.5 seconds, then
image assembly failed with `Incomplete world/journal conversion receipt`.
The world-UI writer swept `regions.awr` into a receipt whose validator correctly
requires exactly four UI-owned files. rc6 enumerates only those four files;
the terrain directory is preserved and strict hash/palette validation remains.
A synthetic mixed-directory regression reproduces the condition and checks
repeat generation and corrupted-journal rejection.

New runs validate world UI before terrain. Checked rc3 image recovery verifies
the retained terrain and rebuilds only engine/image into new staging. This
does not waive actor-contact or filesystem gates, and no final game HDF has
passed here. See [image recovery](IMAGE_RECOVERY.md). The Daedric font fallback
warning preceding the error is separate from this receipt failure.

## AW25-08: area build aborts on window mounting â€” v0.0.25-rc2

The full local build stopped in `prepare_area.py` with
`ValueError: No supporting faÃ§ade geometry`. The same failure was reproduced
from the uploaded rc2 source using the original Census and Excise Warehouse
cell. The Tradehouse also contains affected Nord window assets without an
exterior house supporting mesh.

The flattening profiles were selected by model name alone. Those exterior-named
assets are reused inside rooms, where their exterior mounting plane and wall
normal test do not apply. Profiles now explicitly select scene kinds; the
shipped profiles approve exteriors only. The BSP converter uses the named-cell
metadata supplied by every interior exporter and retains original interior
window visuals and collision. The exterior support guard still rejects missing
or incorrectly facing walls. Archive handles close on both success and failure.

Regression coverage assembles a complete synthetic interior BSP with a window
and no house. Its output must equal the explicitly unflattened conversion,
including collision. The same unsupported exterior must still fail. The real
Warehouse conversion passes with the fix. Full checkpoint verification is
recorded separately; this result alone is not complete build acceptance.

## 1 October 2026: dev1 to rc1 recovery

Detailed records and chronological validation:
[v0.0.25-rc1 recovery journal](RECOVERY-v0.0.25-rc1.md).

| ID | Issue / reproduction | Cause and implementation | Current validation / limits |
| --- | --- | --- | --- |
| AW25-01 | Seyda walking reaches water before island handoff | Backdrop bounds exceeded authored ground; derive handoff from actual LAND bounds with clearance | Host bounds/rebasing checked; fresh native walking both ways pending |
| AW25-02 | Dry valleys/rises flooded; local 9,484,102, yaw 298, pitch 50, region unknown | Coarse terrain loses wet/dry identity; recover adaptive source samples and aligned shared edges | Zero mesh wet/dry errors in 8.27M comparisons; original camera and native visuals pending |
| AW25-03 | Map marker reported stale; HUD lacks universal/local positions | Unify exterior transform and refresh marker each draw; add global/local HUD and compass | Host live-position tests pass; original user cause not conclusively isolated |
| AW25-04 | M/N switch to desktop, including console, with debug/noclip | OS qualifier shortcut; front-game input filter, remove Amiga-to-Ctrl alias, debug Alt+M | Fresh native M/N console and intentional desktop pass; return-path regression found, corrected and repeated successfully |
| AW25-05 | Console always uppercase; digits become Shift symbols | Stale transition-based Shift can survive missed release; refresh event qualifiers, separate Caps Lock letters, correct raw 0x30 | Compiled regression types literal dbg 1 after lost release; owner reproduction still pending |
| AW25-06 | Quicksave shown empty / ordering confusing | One quick slot, two generations; menu conflates absent/corrupt/incompatible; exact ordering cause unknown | Inspected; menu/generation display TODO; original affected saves needed for incident diagnosis |
| AW25-07 | Python FS-UAE launcher cannot execute directly after extraction | Archive mode forced 0644; preserve/validate 0755 on public and private copies | Archive mode and extraction checked; private HDF packaging pending |

Requested changes tracked alongside regressions: Ctrl noclip at twice Shift
speed on all axes; separate keymap; autosave history configurable in Options and
game config, default five. Existing saved autosave choices override the default.
Map occlusion is a future TODO and is not implemented in rc1.

Checkpoint 006 is source for an incomplete prerelease. The strict actor-contact
gate still has 23 known findings; these remain in historical reports and may stop
local final HDF assembly. No private image is represented as production validated.

## Input preflight rejects personal transfer ZIPs â€” v0.0.25-rc1

Reproduction: put Morrowind_Video.zip and Morrowind_video.zip beside the normal
Data Files/Video directory. The scanner previously inventoried every loose file
and rejected the case-folded ZIP collision before distinguishing game assets.
These are transfer archives, not required game inputs.

Fix: positively select Morrowind.esm/Morrowind.bsa by name and supported asset
types inside known game folders before path checks, inventory and build hashes.
Ignore unrelated directories, root files and transfer archives. Audio inventory
counts WAV/MP3 files only. Reference checks use the same game-input selection.
Keep normal ESM/BSA checks and ambiguity checks for actual assets. Intro conversion
already reads loose Video/mw_intro.bik and never requires a ZIP. Do not modify or
rename the owner's archives. Synthetic regression covers both differently cased
ZIPs, an actual loose video, archive-free input receipts and a real video conflict.
No proprietary game files are needed for this host regression.


## AW25-10 â€” actor contact blocks image assembly after terrain

**Status: placement bugs unresolved; earlier detection and explicit private-test
acceptance implemented in rc6.** The receipt fix exposed the existing 23 strict
contact failures at the next image gate. Scheduling that gate only after the
reported 4232.5-second world-terrain pass wasted time before a deterministic
failure. A new actor-contact stage prepares an isolated copied payload and
checks it before world-terrain. The final image still repeats the audit.

The retained scene reproduces the same 23 findings, including one Balmora outdoor
Dreamer, two Balmora interior residents, four Addamasartus actors, and eight
Seyda references repeated across scenes. See [the contact record](NPC_GROUND_CONTACT.md).
The owner's earlier Balmora floating reports were unintended placement bugs,
which motivated this gate; intentional levitation is not their explanation.

A narrow optional reviewed-report acceptance permits diagnostic HDF assembly.
It compares the entire report and recorded geometry/model hashes, rejects
changed findings and invalid metadata, retains the failed raw audit, labels the
HDF `-private-test`, and records production_gate_passed=false. The owner reported
a successful rc3 diagnostic assembly in 144.664 seconds, 3,221,258,240 bytes.
This is not resolution of the 23 contact defects or proof of an rc6 game build.

## rc9: NPC gallery absent from normal images

Owner reported `Gallery catalogue missing` on rc8. The standalone conversion and
staging tools existed, but the normal builder never called them or compiled the
inspection map. This was a build integration omission, not evidence that the
original NPC records were absent. Add a default gallery stage and required payload
checks before image success; expose only the explicit `--no-npc-gallery` opt-out.
The full-world terrain remains reusable. Target gallery entry, browsing, selected
models and return-to-game remain part of the rc9 playtest.

## AUDIO-03: WinUAE video-to-Jiub loading spike

The owner reports repeatable audio glitches during the heaviest scene-loading
spike immediately after the intro movie, when entering the Jiub opening scene.
This is additional to intermittent background-music snapping; the exact audio
source and cause at this transition remain unverified. Reproduce a new game
with the movie enabled and listen across movie completion and ship entry.

Proposed rc4 investigation: finish video audio before blocking scene I/O, then
resume background music with about a one-second fade after loading completes.
A delay while the audio device continues consuming an empty buffer is not a
fix. Check natural movie completion and skipping, preserve Jiub speech timing,
and compare WinUAE with FS-UAE. No mitigation or fix is claimed yet.

## CRASH-01: rc3 Hors restart from Jiub name entry

- First observed / affected: **v0.0.27-rc3** local playtest, image-002 in WinUAE.
- Reproduction: start New Game, reach Jiub's name-entry scene and enter
  `dbg aw hors 0` to travel to Seyda Neen. The game returns to AmigaDOS while
  WinUAE remains open. The recovered detached-filesystem `ERROR.TXT` says:
  `Hunk_Alloc sn012: need 2767120 bytes, free 1682208 of 11534336`.
- Introducing content change: the rc3 terrain-handoff correction added a
  768-unit real-LAND apron without moving the existing FPS residency cores.
  sn012 grew from 5,507,736 to 8,395,232 BSP bytes and its visibility lump from
  473,407 to 2,767,103 bytes. The visibility double-buffer behavior predates
  rc3; its first introducing version is unverified.
- Established cause: the streaming loader held visibility in temporary high
  Hunk memory, then allocated a second full resident copy in low Hunk. The
  allocations overlapped and the next request failed. Held-input/state
  preservation did not cause this BSP allocation failure.
- Repair source introduced during rc3/rc4 and included in published v0.0.27 reads byte-only visibility,
  lighting and entities directly into final storage. The real-loader regression
  passes byte-identity, temporary-copy, pack-member-offset and malformed-input
  checks. An Amiga compile and host tests are evidence for the source change,
  not a playable-map acceptance. The then-current unbounded sn012 candidate
  exceeded the unchanged 6 MiB map ceiling after 3 MiB non-map and 2 MiB safety
  reserves. A later normal bounded Seyda conversion passes static per-map
  estimates; see the dated follow-up below. Neither static result closes the
  target crash incident. Fatal-exit diagnostics are a separate improvement.
- Verified fixed version: **pending**. The final static map gate passed for all
  2,717 packaged maps; the original trip, packaged loader route and target
  lifecycle must still pass before closure.

This blocked the original rc3 candidate and remains an open target incident. Keep the original image as the reproduction target;
do not substitute a repaired candidate and call it a reproduction. Older minimal
images lack the AmigaDOS `Type` command; detach the HDF and inspect its files
with host tools. Mitigation is not a fix, and a passing loader regression does
not establish that later nodes, hulls, actors or renderer allocations fit.

### CRASH-01 diagnosis and exit diagnostics

The detached playtest image contains the fatal report: `Hunk_Alloc sn012:
need 2767120 bytes, free 1682208 of 11534336`. This is engine heap exhaustion
loading Seyda Neen visibility data, not termination of WinUAE. The expanded
terrain candidate increased this subdivision visibility lump to 2767103 bytes.
Basic lightmap/PVS byte deduplication alone does not recover enough memory;
the later bounded-map/loader repair is packaged, but target closure is pending.

Fatal exits now print their reason to AmigaDOS after closing the game screen,
as well as attempting the existing ERROR.TXT file. This adds no per-frame work.
The original failing rc3 playtest disk predates that diagnostic change. The minimal boot
image does not contain the AmigaDOS Type command; inspect ERROR.TXT using
filesystem tools with the disk detached when using older candidates.

### CRASH-01 bounded-world static follow-up — 3 October 2026

The normal bounded Seyda converter generated 67 BSP entries (64 cores plus
docks, court and fallback); all 67 pass the saved target-ABI estimate. The worst
modeled peak is 5,884,944 B, with 406,512 B minimum growth margin after the
unchanged 3 MiB non-map allowance and 2 MiB safety reserve. A separate Balmora
layout's 65-entry audit also passes statically and covers 1,488/1,488 source
placements; its worst fallback is 6,155,504 B with 135,952 B margin. Full details
and the 128-unit-core hysteresis caveat are in
[memory allocation](MEMORY_ALLOCATION.md#normal-converter-bounded-town-audit--3-october-2026).

These are map estimates using saved ABI sizes, not runtime allocation. The
subsequent complete optimizer, actor/contact and heap gates passed all 2,717 maps;
final private HDF assembly and both filesystem readbacks passed. Target cold/warm
transitions remain pending. Static/package results do not prove the original
`sn012` crash fixed and do not close CRASH-01. No FPS improvement is claimed.

## MEM-EXTRA-HDF — map search path bypasses section streaming

- Issue: direct com_gamedir fopen cannot find BSPs placed only on additional
  world-volume search paths; whole-file fallback can add an unexpected BSP-sized
  temporary allocation. A section-only memory estimate is then insufficient.
- Affected/observed: path confirmed by inspection of v0.0.27-rc3 loader and world
  volume wiring; no target crash reproduction claimed for this distinct issue.
  First introducing version: unverified.
- Cause: custom streaming loader bypassed the engine filesystem lookup; normal
  search paths include AW_WORLDn:id1 without changing com_gamedir.
- Repair source introduced during rc3 and included in v0.0.27 opens through COM_FOpenFile, records
  the returned member base/length and seeks relative to it. This also respects
  pack-member offsets. No heap increase or reserve reduction.
- Verified target-fixed version: pending. Loader direct-byte/offset regressions
  and the Amiga compile passed; actual multi-HDF gameplay and load-boundary
  behavior remain to be verified on target.
- Prevention: audit the actual loader path for every storage layout and retain
  final-map estimates plus runtime load evidence. See
  [the separate loader trap](MEMORY_ALLOCATION.md#separate-loader-trap-extra-hdf-search-paths).


## CRASH-REPORT-02 — visible fatal-exit report

- Affected: v0.0.27-rc3 playtests returned to AmigaDOS after a fatal engine
  error with no visible reason. The first rc4 source diagnostic was terse,
  omitted the version/restart hint and did not verify whether logging succeeded.
- Reproduce: trigger an engine `Sys_Error`, such as the recorded rc3 sn012
  allocation failure; observe the shell after the game screen closes.
- Source change: v0.0.27-rc4 now prints a versioned crash banner, the supplied
  reason, the resolved ERROR.TXT path when saved, and the `amiwind` restart hint.
  DOS Open/Write/Close results and a byte-for-byte readback through EOF are
  checked; failed/partial writes or unverifiable contents instead request
  copying the displayed cause. No stdio file buffer is allocated for this write.
- Validation: the diagnostic source is included in the compiled v0.0.27 engine.
  Target fatal-exit checks remain pending; compilation does not prove the report
  is visible or saved correctly on every error path. Test both writable and full/read-only launch directories.
  This improves diagnostics, not the underlying crash cause. CPU traps, emulator
  termination and failures before this handler cannot be guaranteed a report.
- ERROR.TXT is a text error report, not a complete memory crash dump. Existing
  separate heap-audit telemetry remains separate. No per-frame polling is added.


## MEM-GEOMETRY-01: transactional geometry/light sharing candidates

- Scope: an exact-representation optimization trial for `bmmages`, `bmtemple`
  and `addamasartus`; it is separate from CRASH-01 and does not close that
  incident or establish that all over-budget maps are fixed.
- First failed candidate: Mages Guild face 285, light-data offset 11,723. The
  earlier light-range deduplicator used wide intermediate UV arithmetic and
  derived a 30-byte referenced span. Per-operation binary32 arithmetic derived
  36 bytes, so copying the shorter range would have changed the next 6 bytes.
  The actual Amiga target FPU intermediate precision has not been established.
- Safe handling: the first optimizer attempt failed before replacing any map;
  original maps and the failed receipt were retained. `deduplicate_bsp.py` now
  preserves the longest original referenced byte span required under both
  precision policies. It does not change UVs, extents or runtime geometry.
- Candidate and transaction: exact vertex/inline-edge/edge-reference sharing,
  followed by independent light/PVS byte deduplication. The normal build hook
  stages all candidates after actor annotation/baking and before independent
  actor contact, the final heap gate and content fingerprinting. Every candidate
  is checked before replacement; replacement failures roll back prior maps;
  output hashes are rechecked before the heap gate and fingerprint.
- Source/data evidence: all three geometry-only maps passed independent Python
  render-input checks. Vertex order/coordinates and face winding match; affected
  visible/render inputs, lighting samples and decoded visibility were checked;
  collision, models and other protected lumps remain unchanged. Five optimizer,
  five render-input oracle, two deduplication and ten engine-receipt regressions
  passed.
- Native C comparison: inside the owner-authorized Linux Docker environment,
  one synthetic before/after pair (3 faces) and three real map pairs passed
  (Mages 40,530; Temple 35,242; Addamasartus 23,426; 99,198 real faces total).
  This is Linux C loader evidence, not Amiga FPU/rendering or target gameplay
  evidence. The earlier Windows Application Control block remains historical;
  the local helper was removed and Windows runners skip native binary tests.
- Reused-ABI static estimates: Addamasartus peak 5,812,864 B, margin 478,592 B;
  Mages peak 5,688,464 B, margin 602,992 B; Temple peak 5,905,872 B, margin
  385,584 B. All three pass the current 6 MiB map ceiling with the unchanged
  3 MiB non-map reserve and 2 MiB safety margin. These are estimate-only values,
  not a fresh ABI probe or gameplay result.
- Status: the optimizer and transactional protection are included in v0.0.27.
  The three-map comparisons passed, followed by the complete 2,717-map optimizer,
  actor/contact and static heap gates, matching engine/image and HDF readbacks.
  Target renderer/FPU behavior, seams/state and lifecycle playtesting remain
  pending. No FPS improvement or target closure is claimed. Mitigation is not a fix.


### WIN-04 follow-up: retained CRLF allowance receipt in rc4 assembly

- **Version and circumstances:** v0.0.27-rc4 image assembly rejected
  `model-budgets.txt` when reusing a complete retained gallery whose receipt
  authenticated CRLF bytes. No missing or changed NPC model was established.
- **Reproduction:** stage a valid CRLF gallery allowance table with the current
  explicit-LF writer, then validate staged bytes against the retained receipt.
- **Cause:** the earlier LF writer correction fixed future output but did not
  handle legacy CRLF receipts; regenerating LF changed the byte size and hash.
- **Repair:** authenticate the entire source package, regenerate/audit allowances,
  require identical contents after CRLF-to-LF comparison, then copy the verified
  original allowance bytes. Substantive differences remain fatal.
- **Verification:** seven gallery build tests pass on Windows, including retained
  CRLF acceptance and authenticated-but-inconsistent allowance rejection. The
  next image retry verified 2,935 records and 3,551 models. Subsequent v0.0.27
  Linux suite and final private-image readbacks passed; target gameplay acceptance
  remains a separate check.
## MEM-TOWN-02: Balmora bounded-layout estimate candidate

- **Scope and symptom:** earlier Balmora candidate maps exceeded the modeled BSP
  limit. This was a static heap-policy failure, not a separately reproduced
  Balmora crash. It is independent of the reproduced rc3 `sn012` crash in
  CRASH-01; neither static repair closes that target incident by itself.
- **Candidate change:** the normal Balmora layout path merges inexpensive outer
  regions to retain the 64-core format and divides the previous oversized area
  into three measured regions. It preserves the existing 896-unit visual
  coverage apron, 224-unit physical collision apron, 96-unit hysteresis,
  540-unit draw policy and unchanged 3 MiB non-map plus 2 MiB safety reserves.
- **Static evidence:** the whole audit covers 1,488/1,488 source placements with
  zero lost references and validates 64 non-overlapping cores; 65 map entries
  including the fallback pass using saved target-ABI sizes. Peaks: merged
  `bm000` 3,087,760 B; upper `bm001` 5,971,920 B; lower `bm027` 5,615,520 B;
  worst `bm019` / `balmora` fallback 6,155,504 B, leaving 135,952 B after both
  reserves. All are within the 6 MiB modeled ceiling; the 5 MiB figure remains a
  planning target, not a gate.
- **Transition caveat:** the 128-unit lower `bm027` core is shorter than the
  96-unit hysteresis band. The adjacent map can remain active through the core
  center within hysteresis; half-open core ownership remains unique and switch
  thresholds were not changed. Test seams, scenery and collision both ways at
  the split/merge, including rapid noclip and held controls.
- **Status:** the saved-ABI audit, subsequent complete actor/heap gates and
  final private image assembly/readbacks passed for the layout carried into
  v0.0.27. Target cold/warm lifecycle, both-direction crossing, collision and
  gameplay-state acceptance remain pending. No FPS improvement is claimed. This
  does not establish that the original `sn012` crash is fixed. See
  [bounded-town memory audit](MEMORY_ALLOCATION.md#normal-converter-bounded-town-audit--3-october-2026).

## BSP-LIGHT-01: pre-existing Vodunius lightmap range exceeds its lump

- **When discovered:** 3 October 2026, during the v0.0.27-rc4 image-005 continuation's whole-map optimizer pass. The pass failed at `vodunius.bsp` with `ValueError: Light sample range outside lump`. Its receipt records status `failed`, no committed maps, `rollback: originals preserved/restored`, and zero rollback errors. This is a build-data validation failure, not the earlier runtime heap crash.
- **Version provenance:** the offending map bytes were already present in retained v0.0.27-rc1 assembly/seam and v0.0.27-rc2 seam/town-handoff artifacts, and in rc4 image-001 through image-004. Their `vodunius.bsp` SHA-256 is `e92f82fb6793aa427f12fddd3901abfacb6ac984368ba6310f37fa5d074044a9`; the introducing version is not established, and the defect is known present by the retained rc1 artifact. The rc4 image-005 source copy has a different SHA-256 (`984639b9d02259504de9adde0fe7e2edabb0d1921d1e61a65958005326531f0e`); therefore this incident does not assert that every image-005 byte sequence is identical to the earlier retained map. The bad face/light-range condition was exposed by optimizing this map, not introduced by the optimizer.
- **Reproduction and cause:** run the receipt-bound v0.0.27-rc4 map optimizer over the staged image; it stops on `vodunius.bsp`. Face 4859 has `lightofs=64277`; the lighting lump is 64,355 bytes, leaving 78 bytes, while the final serialized face extents require 14×6 = 84 samples. The source lightmap was baked as 13×6 before final float32/canonical geometry values were used. Both narrow and wide extent policies identify the out-of-lump range. This is malformed/inconsistent baked map data, not a heap-budget failure.
- Repair applied as a verified candidate: regenerated only face 4859 from final serialized/canonical geometry and texinfo, retained lamp inputs, and inline transform. Narrow and wide arithmetic policies agreed on a 14×6 grid. The candidate appends 84 bytes and changes only that face's light offset; all other lumps, valid faces, and original light bytes were preserved.
- Verification and status: 15 focused tests passed, and an independent check covered all 4,860 faces under both narrow and wide policies. The initial whole-map optimizer attempt failed at this pre-existing defect after more than 2,700 of 2,717 map checks; it committed no maps and restored originals. After repair and manifest rebind, the complete optimizer verified 2,717/2,717 maps with no failures; the actor/contact gate passed with zero unresolved items; and the receipt-bound target-ABI heap estimate passed 2,717/2,717 maps. Worst modeled map is Balmora at 6,155,504 B, leaving 135,952 B after the unchanged 3 MiB non-map and 2 MiB safety reserves. These are static build gates, not target runtime validation. Both final HDFs now pass filesystem readback; target runtime acceptance is pending. The optimizer exposed this defect; it did not cause it. The one-face repair does not resolve broader narrow/wide precision differences or prove the producer is generally corrected.
- Long-term producer work: derive bake grids from canonical stored values and retain the minimum grid dimension of 16. This is separate from the verified single-face candidate.

## MAP-REG-01: rc4 In-Game selector hides retained settlement markers (BUG / REGRESSION)

- **When and affected version:** reported from owner playtesting of the v0.0.27-rc4 map-panel prototype. The screenshot shows the In-Game Map Prototype heading, a Debug button at left and an unreadable pale active button at right; the user sees Debug mode and no settlement names/markers.
- **Introducing change and reproduction:** the rc4 two-mode selector put settlement-landmark rendering behind a Debug-only mode condition. Open the map panel and choose In-Game to reproduce: the In-Game terrain view opens but converted town markers disappear, even though the retained map asset contains two town landmarks.
- **Cause:** the renderer incorrectly treated settlement landmarks as diagnostic overlays and skipped the full landmark loop in In-Game mode. The active-button fill was pale while console glyphs remained light, reducing the active label's contrast. This is a map UI rendering regression, not missing map records or evidence that a full original-game world map is implemented.
- **Source correction:** the v0.0.27-rc5 source removes the mode restriction for settlement landmarks so both views share those markers. The active selector uses a dark text interior with a contrasting gold border, keeping the light label readable. The rc4 HDF is unchanged.
- **Status and validation:** the v0.0.27-rc5 correction compiled in engine-002 and is included in the private candidate whose HDF files passed readback. Nine focused source checks passed; the repaired Linux native world-UI fixture subsequently passed in the full 558-test Docker suite. The correction is included in stable v0.0.27; owner target validation remains pending. Confirm town-marker visibility and both button labels/states in both modes. Preserve the In-Game heading arrow and Debug teleport crosshair. In-Game remains a terrain-overview prototype; local map content and full-map parity are incomplete. See [world map and journal](WORLD_MAP_AND_JOURNAL.md).

## BUILD-REPAIR-01: ownership files omitted by rc5 retry extractor (BUG / BUILD TOOL)

- **When and affected version:** found during the v0.0.27-rc5 private image-repair retry. The helper extraction omitted authenticated numeric Seyda Neen and Balmora region-ownership text files; actor validation then reported 1,950 missing-owner-directory errors.
- **Cause and impact:** the retry extractor failed to copy the authenticated ownership table. This was a staging-helper defect, not a map ownership regression or a change in game data. It was detected before any HDF patch.
- **Correction and validation:** the helper now copies the authenticated ownership files, and the failed report/log are preserved. The retry was rerun through strict gates; the final rc5 candidate records actor/contact passed with zero unresolved items, all 2,717 map heap estimates passing, and successful HDF readbacks. The earlier failed extraction did not mutate the rc4 HDF or the retry clone.

## BUILD-REPAIR-02: retry assertion misread an empty failure list (BUG / BUILD TOOL)

- **When and affected version:** found during the same v0.0.27-rc5 retry, before HDF patching. The optimizer had verified all 2,717 maps, but a continuation assertion stopped.
- **Cause and impact:** the helper expected failing_maps to be numeric zero, while the receipt schema represents success with an empty list. This guard rejected a successful result; no map failed and no HDF was patched.
- **Correction and validation:** the assertion now checks the schema's empty-list representation. The final rc5 candidate was built after the correction; optimizer, actor/contact, static heap and HDF readback gates passed. These are build/package checks, not target gameplay acceptance.

## TEST-PORT-01: focused suite depends on repository root and Windows UTF-8 mode (TEST PORTABILITY ISSUE)

- **When and affected version:** discovered during final v0.0.27 release validation on Windows, 3 October 2026. Invoking the same 75 tests from the external working directory with default Windows cp1252 decoding produced nine missing-source-path failures in loading-delay tests and two UnicodeDecodeErrors in emulator-configuration tests.
- **Cause and impact:** running outside the repository selected an unrelated working-copy test module before the intended repository test, causing its source paths to resolve incorrectly. Separately, emulator-configuration tests used platform-default text decoding for UTF-8 configuration data. This is a test invocation/portability defect, not production behavior or an rc5 runtime regression.
- **What worked:** rerunning the exact 75 tests from the repository root with PYTHONUTF8=1 passed all 75. The first failure log is retained privately; no product or HDF change was needed for the rerun.
- **Correction/status:** explicitly decode UTF-8 in the emulator-configuration test and keep test invocation rooted/anchored to the repository. The test now explicitly decodes UTF-8; all 11 emulator-configuration checks passed under the default Windows encoding without PYTHONUTF8. Repository-root execution keeps the intended source tests selected. No runtime impact has been established; the owner-approved stable release is not reopened by this test-only issue.

## ACTOR-RECEIPT-01: Windows audit receipt hashed different line endings

- **Version, when and where:** discovered on 3 October 2026 during stable v0.0.27 private assembly preflight; present in retained rc4/rc5 actor reports. Introducing version is not established. No target gameplay regression is implied.
- **Reproduction:** on Windows, call `check_actor_ground.require`, then hash the saved output bytes and compare with `acceptance.report_sha256`. The former writer used implicit text-mode newline translation; its hash used the original LF string.
- **Cause:** the saved file gained CRLF endings, so its recorded SHA-256 did not describe the exact file. Stable assembly correctly refused it before cloning. Audit findings and payload hashes were unchanged.
- **Proposed and actual correction:** write explicit UTF-8 bytes, and hash those same bytes. A focused regression verifies LF output and equality between the saved-file hash and the acceptance receipt.
- **Legacy evidence:** the preserved rc5 report contains 5,915 CRLF sequences. Its actual SHA-256 is `ba619481de654d89d5cb6c5d99c7229c3c449b93c48d769ae5d7467afd47536c`; changing only CRLF to LF produces exactly the recorded `e691027c4fc7d50e3e6e5ae72391247b19ab14ac07938383fb5fde6e237c3adb`. Stable assembly preserves both hashes and the original receipt as provenance and normalizes its new copy only after that exact comparison.
- **Status:** writer correction in v0.0.27; all 15 interpreted actor-ground checks, including exact saved-file hash/LF validation, passed on Windows. The subsequent complete Linux Docker suite and exact-release hosted CI passed. This fixes receipt serialization, not geometry or heap exhaustion. Legacy normalization is narrowly authenticated compatibility handling, not permission to rewrite mismatched content.

## LINUX-VALID-02: Linux test-fixture link failures repaired (VALIDATION ISSUE)

- **When/version/environment:** first reported 3 October 2026 during v0.0.27
  validation on Linux. The initial suite recorded 558 tests, 2 failures and
  5 skips. The first Docker rerun isolated a movie-fixture failure; the repaired
  full Docker rerun and matching asset-free compile are now verified.
- **Initial symptoms and cause:** `tests/aga_worldui_test.c` lacked stubs for
  `AW_DebugOverlaysEnabled`, `Cvar_SetValue` and `Cvar_RegisterVariable` used by
  linked world-UI code. `tests/aga_movie_test.c` lacked `CDAudio_Resume`,
  `Key_ClearStates` and `V_UpdatePalette` stubs used by movie code. These were
  test-fixture linkage omissions; they did not establish runtime/HDF defects.
  The cause of the second failure in the initial 2-failure result was not
  individually established from that run; the first Docker rerun identified the
  movie fixture issue. Do not retroactively claim a one-to-one match without the
  preserved failure logs.
- **Correction and verification:** both fixtures now provide the needed stubs;
  the world-UI fixture also exercises the relevant behavior. Native Windows C
  fixture execution is explicitly skipped under the interpreter-first policy.
  In the owner-reported Docker rerun, the complete Linux suite reported
  `558 tests, OK (skipped=3)`. The matching asset-free build exited 0 and emitted
  both emulator configurations. These checks repair/validate test linkage and
  compile configuration; they do not alter runtime or HDF content.
- **Status and limits:** Linux Docker suite and asset-free compile gates pass for
  the exact repaired release package. Archive validation completed, then
  v0.0.27 was published at `8da838784efa619a12da39d29095be4c0fe6e44d`; all four
  jobs in CI run 37113138642 passed and the Linux publisher verified downloaded
  assets. The fixture correction is verified in the published v0.0.27 source.
  This does not establish gameplay, target or runtime acceptance. Keep Windows
  fixture skips distinct from Linux pass evidence.

## HANDOFF-WRAPPER-01: direct-unzip wrapper collided with an existing extraction (HANDOFF TOOL BUG)

- **When/version:** first observed 3 October 2026 in the v0.0.27 repair-001
  Linux handoff wrapper. This was a transfer-wrapper defect; no public source,
  runtime or HDF change is implicated.
- **Reproduction:** extract the single transfer archive directly into the
  established `~/NeuralNetwork` handoff root while an older generic extracted-kit
  directory is present, then run the included entry point. The wrapper reused
  that extraction location and stopped after finding modified `APPLY.py`.
  Repository source remained unchanged.
- **Cause:** extraction reused a generic kit-directory name instead of isolating
  each authenticated archive. Requiring a separate transfer directory would only
  avoid the collision by changing the owner's required workflow; that mitigation
  was not the correction.
- **Correction:** repair-002 derives an extraction namespace from the verified
  archive checksum, verifies the ZIP and every extracted member before apply,
  preserves old kits/backups, and keeps the apply target fixed at
  `~/NeuralNetwork/amiwind`. Delivery is one outer ZIP and one Bash entry point;
  the owner unzips directly into `~/NeuralNetwork` and runs it there.
- **Validation and status:** the exact-layout Docker test passed with the old
  extraction present: initial apply, repeat extraction/apply, unrelated-edit and
  kit-tamper refusal without mutation, and parent-shell errexit safety. This
  validates wrapper behavior, not archive delivery or publication. The inner
  source kit is unchanged from repair-001 and retains its separate Linux suite /
  asset-free compile results. The frozen public source ZIP was not regenerated.
  These results describe repair-002. The later repair-003 package passed its
  own exact-package checks; its public source was published as v0.0.27, with
  hosted CI and downloaded assets verified. Earlier kits remain unchanged;
  target gameplay acceptance is separate.

## TREE-SCALE-001 — non-unit tree sprites and conservative bounds

- **Status/version:** open investigation in v0.0.27 source, observed 3 October
  2026; introducing version unknown. No verified fixed version yet.
- **Where/how:** world tree expansion reuses the bounded-town sprite converter.
  `prepare_quake.py` omits scales outside 1 +/- 0.02; current static sprite messages
  carry no instance scale. Sprite header bounds can also differ from asymmetric
  frame extents. Source tracing established these limits; target visual symptoms
  have not been reproduced.
- **Reproduce:** provide a tree reference at scale 0.5 or 2 to the existing town
  converter and inspect emitted entities; trace SPR frame origins against loader
  bounds and leaf linkage. Do not mistake generated image count for placement count.
- **Proposed fix:** shared per-model pixels, validated per-placement scale through
  static loading, quad extents and conservative leaf/culling bounds. Preserve
  source transforms, collision and interactive object state.
- **Tried/results:** base-source census and private five-model sprite bakes
  completed; seven synthetic selection-policy checks passed on Windows Python.
  Policy is staged, runtime activation false; renderer/converter integration and
  target tests remain pending. A metadata-only exclusion is not a runtime fix.
- See [tree sprite work](WORLD_TREE_SPRITES.md). Mitigation is NOT a fix.

## FLORA-ENTITY-001: dense vegetation exceeds the entity reserve

- **Version/when:** observed 3 October 2026 during unreleased Trees and Grass
  development after v0.0.27; no verified fixed version.
- **Where/reproduction:** convert dense region vf2098 with the staged world
  flora overlay and unchanged reserve checks. Its 301 entries before adding 266
  sprite placements yield 567 entities, exceeding the 550 build reserve.
- **Cause:** retained scenery plus separate collision entities and new sprite
  placements exceed the entity-count allowance. An initial model-slot suspicion
  was corrected; this result does not establish model-slot exhaustion.
- **Correction candidate/tried:** explicit adaptive collision packing tries the
  original per-instance representation first. Only entity or model-slot reserve
  failures permit a transformed collision aggregation retry. Every content and
  reserve check must pass; both failed candidates remain preserved.
- **Measured results:** vf2098 aggregate passes host reserves with 112 BSP models,
  504 entities, 266 sprite instances, 13,369 clipnodes, 9,173 nodes and 1,908,024
  bytes. vf0634 retains its passing per-instance candidate: 208 BSP models,
  387 entities, 57 sprites, 30,691 clipnodes, 14,564 nodes and 3,608,112 bytes.
  Forced aggregation there exceeds clipnodes (34,102), so it is rejected.
- **Validation/limits:** interpreted source-convex transform equivalence and
  synthetic adaptive choice/failure-both checks pass. No scenery was removed or
  reserve lowered. Complete signon/heap and target collision/traversal/gameplay
  checks remain separate gates. Verified fixed release: pending.
- **Status:** measured host build correction candidate; target acceptance open.

## TREES-BUILD-001: first rc1 validation found missing integration inputs

- **When/version:** 3 October 2026, first offline Linux Docker validation of
  unreleased v0.0.28-rc1. No v0.0.27 release or private image was changed.
- **Reproduction:** run the full Python suite against the first rc1 source
  checkpoint. Emulator configuration tests require presets named for VERSION;
  a synthetic source-root provenance test also exercises vegetation disabled.
- **Cause:** the rc1 version bump preceded creation of its two emulator presets;
  new build provenance unconditionally hashed the vegetation policy even when
  vegetation was not requested. These are build integration defects.
- **Proposed correction/tried:** supply both versioned source presets and make
  the optional policy dependency conditional on opting into vegetation. Preserve
  failed logs and validate a new source checkpoint through the full suite and
  matching Amiga compile. Do not weaken tests or change unrelated fixtures.
- **Result/status:** first run's scale protocol native fixture passed. Full suite
  failed (587 tests, one failure, 16 errors, three skips), so that run did not
  perform the subsequent Amiga compile. Corrections require rerun; no verified
  fixed release or playable image is claimed. Mitigation is NOT a fix.

## FLORA-RESERVE-002: two full-world rc1 flora candidates exceed reserves

- **Observed/version/reproduction:** 3 October 2026, unreleased v0.0.28-rc1.
  Full owner-source world flora conversion with adaptive collision packing
  completed 2,524 of 2,526 regions. Reconvert vf0698 and vf0791 with the same
  original source, palette and retained terrain/rock/mushroom scenery.
- **Established cause:** vf0698 default has 237 BSP + 17 sprite models (254/240),
  504 entities, 125 statics, 16,730 nodes, 28,579 clipnodes and 4,241,364 bytes.
  Aggregate collision passes model slots (210 + 17 = 227) and entities (445),
  but has 18,279 nodes, 31,173 clipnodes and 4,371,204 bytes: 176,900 over the
  unchanged 4,194,304-byte reserve. Its retained base is 3,896,076 bytes.
  vf0791 default has 182 + 9 models, 313 entities, 36 statics, 16,388 nodes,
  33,541 clipnodes and 3,626,900 bytes: 774 over the 32,767 clipnode reserve.
  These are measured storage/collision failures, not a heap or target diagnosis.
- **Representation audit:** exact table sharing offers insufficient savings.
  Numeric standing-plane redundancy audit found four strictly implied new planes
  in vf0698 (at most 112 bytes) and none in vf0791. No collision was changed;
  this numeric audit is not an exact geometry certificate or target test.
- **Correction candidate:** retain the other 2,524 map IDs and subdivide each
  failed cell into four cores of 1,024 units, each with the same 896-unit apron.
  The first child replaces its parent slot; six siblings append as vf2526–vf2531.
  AWR2 indices stay sequential. Normal terrain planning consumes explicit
  source-cell refinement configuration; no source survey is rewritten.
  All eight scenery children passed host conversion checks with unchanged rock
  and mushroom profiles. Original unique references must remain equal after
  merging overlap copies. The complete refined flora retry passed 2,532 regions,
  reusing 2,524 verified candidates and covering all 19,984 original references.
  All eight children retain per-instance collision; none require aggregation.
  Their peak counters are 167 model slots, 335 entities, 92 statics, 10,911 nodes,
  19,816 clipnodes and 2,541,584 bytes (peaks can belong to different children).
  Full-world measured maxima are 227 model slots, 532 entities, 266 statics,
  18,815 nodes, 32,614 clipnodes and 4,157,712 bytes. All reserves remain intact.
  Final image, runtime memory and target acceptance remain pending.
- **Validation/status:** 34 focused interpreted checks pass (seven region-layout, thirteen
  flora integration, four town, seven policy and three sprite checks), including append-only map IDs, tiled cores,
  unchanged apron and refusal to reuse changed palettes/assets/source references.
  Failed candidates and completed receipts are preserved. No reserve was lowered,
  original scenery removed, or visual LOD changed. Verified fixed version: pending.

## TOWN-ARRIVAL-002: flora installation selected the wrong Balmora fallback

- **Observed/version/location:** local v0.0.28-rc1 image integration, 3 October
  2026; build_aga town flora fallback selection. Candidate not shipped.
- **Cause/reproduction:** selecting local (0,0) picks the central region instead
  of the actual configured arrival. Compare that choice with the AWBR1 arrival
  fields and retained Balmora region table.
- **Source correction:** use AWBR1 header arrival fields [4:6], matching existing
  prepare/repair behavior. Root's actual table check selects unique bm019 for
  arrival (-209.68310546875, -1486.1015625). Unused default_region import removed.
- **Status/limits:** source corrected and actual table checked; assembled image
  and target arrival acceptance pending. Verified fixed version: pending.

## TOWN-FLORA-BINDING-003: valid legacy source copy outside rotated source bounds

- **Observed/version:** unreleased v0.0.28-rc1 image001 assembly, 3 October 2026.
  Town flora staging stopped at sn001 after sn000, before committing town maps.
- **Reproduction/cause:** original FRMR 267004, flora_bc_grass_01, cell (-2,-10),
  source f/flora_bc_grass_01.nif has a valid legacy progs/m009.spr binding.
  Its old upright yaw-only sprite intersects the town apron, while its fully
  tilted source-model bounds lie outside sn001's coverage. Source identity,
  model hash and legacy pose were correct; the new bounds-only selection omitted
  an existing bound copy, then rejected that binding as unavailable.
- **Correction candidate:** union normal original-bounds membership with exact
  existing bound source keys. Validate the complete master/cell/reference key,
  retain original transforms, deduplicate normal/existing copies, and report
  copies outside source bounds. Do not change terrain coverage, fabricate bounds,
  infer identity from pose alone or touch unrelated legacy sprites.
- **Validation:** six interpreted town tests and thirteen flora integration tests
  pass. All 66 actual Seyda source-binding checks pass, including intro_docks and
  sncourt. Boundary copies and ordinary selected copies produce one new instance;
  unrelated sprites remain and forged master keys are rejected. Collision is
  unchanged for retained geometry and follows the existing original-transform
  pipeline for new resident copies. Target collision/gameplay not tested.
- **Status:** source correction validated on host; assembled/target fixed version
  pending. Balmora mesh exclusion is unchanged.

## TOWN-FLORA-BUDGET-004: world file-budget gate applied to existing town profile

- **Observed/version/reproduction:** subsequent private full 66-map Seyda trial
  with the corrected bindings, v0.0.28-rc1. All bindings pass; 27 flora candidates
  pass the world-style reserve gate and 39 fail only its 4,194,304-byte file limit.
  sn007 is 4,279,864 bytes (85,560 over), with 98 model slots, 261 entities,
  84 statics, 16,247 nodes and 25,286 clipnodes. Largest candidate sn045 is
  4,553,004 bytes; its original retained town BSP is already 4,427,656 bytes.
- **Established cause:** the reusable flora helper inherits the world converter's
  4 MiB storage budget. Existing town generation specifies final actor/ABI heap
  gates and has no such file limit. This is a gate-scope mismatch; it is not proof
  that these candidates pass runtime memory or that a reserve may be weakened.
- **Tried/results:** existing lossless geometry and sample sharing was tested on
  all 39 failed candidates with independent render/sample oracles. It saved
  992–4,416 bytes; none fell below 4 MiB. Models, entities, planes and collision
  nodes were byte-identical. Candidates and exact counters are retained privately.
- **Correction candidate:** typed town admission omits the unrelated world-only
  file budget, keeps every other capacity constraint, and requires the existing
  final actual-ABI gate: 6 MiB map allowance, unchanged 3 MiB baseline reserve
  and 2 MiB headroom, plus complete transport checks. Receipts explicitly mark
  final heap verification false until the final hash-bound gate runs. World
  admission still enforces its unchanged 4 MiB budget.
- **Validation/status:** seven town tests and thirteen flora integration tests
  pass, including world-cap enforcement, town static-cap rejection and refusal
  to label staged candidates heap-verified. All 66 actual Seyda town maps pass
  typed host staging on independent copies. Final ABI gate/image/target pending.
  Balmora capacity failures below remain blockers. No original content removed.
  Verified fixed version pending.

## BALMORA-CAPACITY-005: retained town maps exceed entity admission

- **Observed/version:** private v0.0.28-rc1 image001 bounded Balmora output,
  3 October 2026, while validating flora without changing existing town meshes.
  First introducing version unknown; these failures are present before flora.
- **Reproduction/measured cause:** original bm001 contains 634 func_wall and
  18 aw_npc entities, plus worldspawn/start (654 blocks). Its original BSP has
  170 models, 18,426 nodes, 53,119 clipnodes and 4,643,376 bytes. The flora
  candidate adds no models or sprites and retains these original counters.
  Original bm020 has 658 blocks, bm028 674 and the bm019 arrival 610.
  Quakedef MAX_EDICTS is 600; func_wall QC retains a solid persistent edict.
  This is a capacity failure, not just a world-file-budget mismatch. Separately,
  the unsigned engine clipnode loader accepts up to 65,520 nodes; the stricter
  world build clip reserve is 32,767 and remains unchanged in this candidate.
- **Established introducing mechanism:** the existing immutable scenery catalogue
  in aw_scenery.c admits only the balmora alias in Begin/Capture/Link. Bounded
  bmNNN maps therefore bypass capture and retain func_wall edicts. ED_LoadFromFile
  already captures scenery before QC spawn and frees each captured edict; its
  catalogue retains each original BSP model, full pose, rotated bounds and
  collision through SV_ClipMoveToEntity. No new placement architecture is needed.
  First version introducing bounded-name mismatch remains unproven.
- **Source correction candidate:** one strict predicate accepts balmora and only
  bm000 through bm063 in all three guards. Names such as bm064, bm100, bm01,
  bm000x and unrelated maps remain excluded. No instances are collapsed (the
  all-map audit found zero exact duplicates), models converted, or caps raised.
  Worst catalogue is 654 walls against its existing 1,000-placement capacity;
  every map retains 20 non-wall blocks before player/helper accounting.
- **Regression/limits:** existing native scenery fixture source now covers the
  alias and bm000/bm019/bm063, rotated standing collision and world proxy, clear
  and reload lifecycle, and nine rejected names. Root's authorized Linux native validation passed the
  extended rotated-collision fixture and the late-NPC visibility fixture (two
  tests). These host native results do not certify target gameplay.
  Final visibility must include catalogue plus actors/statics; target ABI heap
  accounting must add capacity*sizeof(aw_scenery_t), including entity_t, two
  bounds vectors, model index and padding. Final live-slot, heap and transport
  gates remain mandatory. Assembled/target fixed version pending.

## TELEPORT-XY-006: explicit global coordinates and water-safe debug arrival

- **Request/version:** Harry requested `dbg tp X Y` during unreleased v0.0.28-rc1
  development on 3 October 2026. Existing console supported named destinations
  and the two map-picker aliases, but no explicit global XY form.
- **Source correction candidate:** exactly two coordinate tokens, strict finite
  decimal/exponent parsing with full-token/length/range validation, route through
  existing AW_MapTeleport/AW_WorldMapTarget, using original Morrowind global XY
  and existing .25 conversion. Named destinations, no-argument menu, `dbg tp map`
  and `dbg map tp` remain. Invalid inputs/unavailable destinations do not reset
  character or world state; extra arguments are rejected.
- **Water cause/correction:** old checked map placement landed on submerged
  terrain. Detect actual water at the standing feet, locate its air boundary
  with a bounded 20-step search in the loaded local BSP, raise the feet by .25
  and recheck the complete standing hull. No assumed zero height or unchecked
  underwater point. If no air/clear hull exists, placement fails without changing
  the player pose and the existing checked scene-spawn fallback reports it.
- **Regression/limits:** native fixture sources cover both map aliases, coordinate
  dispatch, malformed/nonfinite/overflow/underflow/out-of-range/extra arguments,
  unavailable destination/state preservation, actual water-surface placement and
  all-water no-solution preservation. Root's authorized Docker native rerun passes
  all four checks: console dispatch, real-world-resolver scene links, standing
  spawn/water and Strider available destinations (4 tests, 4.952 seconds).
  The initial fixture rerun found duplicate resolver linking; the corrected
  fixture supplies synthetic AWR2 data to the real resolver. Its optional empty
  Hors preset also required an explicit alive-player precondition, with a new
  dead-player rejection assertion. No production check was weakened.
  No emulator screenshot or target gameplay result is claimed.
  Verified fixed version pending.

## ENTITY-EXHAUSTION-007: interactive entity exhaustion recovery

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### Balmora catalogue admission and heap accounting addendum

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### BUILD-QCC-PATH-008: assembly received a source directory as its compiler

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### ENTITY-DIAGNOSTIC-009: allocation high-water count described as live slots

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### WORLD-FLORA-HEAP-010: Seyda sprite payload exceeds final headroom

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### WORLD-FLORA-HEAP-010 inspection addendum

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### WORLD-FLORA-HEAP-010 geometry/collision investigation

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### WORLD-FLORA-HEAP-010: contained-collision experiment and refreshed diagnostics

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### WORLD-FLORA-HEAP-010 bounded wood-detail trial and lifecycle audit

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### Development inspection follow-up: Blender mesh views (3 October 2026)

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### SPRITE-STREAM-VALIDATION: development wrapper and legacy alignment failures

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### POLYCOUNT-INSPECTOR: initial empty-scene render stops animation

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### Sprite validation follow-up: bounded native and full suite results

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### WORLD-FLORA-HEAP-010: unresolved fallback diagnostic accounting

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### Geometry investigation method: heatmap, inspection and recipe identity

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### POLYCOUNT-INSPECTOR release admission and current estimate follow-up

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### TERRAIN-CULL: global topology and local sky enclosure remain unaccepted

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### POLYCOUNT-INSPECTOR: fly navigation and repeated-count regressions open

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### TERRAIN-CULL audit follow-up 002: sky geometry removed; global terrain still pending

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### TERRAIN-CULL inspection004: source join repair is separate from buried-object removal

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### SKY-FOG v0.0.28: shared resource and reserved depth validated natively; target pending

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### EXTERIOR-SURFACES v0.0.28: no checked interior-cell leak; storage exclusion remains open

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

### EXTERIOR-VISIBILITY v0.0.28: source policy metadata and bounded selector added

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES follow-up: default hidden-surface cull contract

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES source review: appended static faces bypass brush CSG

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES diagnostic 022: bounded containment found no house faces

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES build integration and validation follow-up

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES independent plane and UV audit

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES receipt 023 and terrain/object A/B proposal

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

#### EXTERIOR-SURFACES independent 021/022 review and 023 peak projection

Detailed history is retained in [the entity exhaustion record](bugs/ENTITY-EXHAUSTION-007.md).

## GEO-03: canonical clipping stores reversed-winding fragments in diagnostic 023

**Status:** The bounded source-winding defect is corrected and validated on the exact-linked one-house fixture. Diagnostic 023 itself remains unchanged; a full-scene corrected BSP, product integration and native consequence are not established.

**Observed/version/environment:** recorded 4 October 2026, 03:22 EEST, in an
independent read-only inspection of diagnostic BSP 023 and its supplied
one-house fixture. Ten emitted fragments across eight source faces have loop
orientation reversed relative to the matching fixture faces. Their normalized
area-vector dot products are near `-1`, not near-zero numerical ambiguity. All
ten output loops match face records in the actual 023 BSP at model 22, entity 73,
placement reference 113824. A plane-only comparison confirms the same winding
defect was already present in 021 and is carried unchanged into 023; exact plane
deduplication did not cause it.

| Fixture face | BSP 023 face records |
|---|---|
| 13212 | 8685, 8686 |
| 13214 | 8693 |
| 13215 | 8694, 8696 |
| 13228 | 8711 |
| 13234 | 8718 |
| 13274 | 8758 |
| 13276 | 8761 |
| 13277 | 8762 |

**Impact and reproduction:** this is a stored-orientation preservation failure;
it may affect backface or normal handling, but native visual/gameplay consequences
have not been measured. Compare each emitted fragment's directed loop/area vector
with its source-face orientation, then verify the same BSP records after write and
reload. Confirm all fragments, not only aggregate polygon counts. A stable repeat
does not prove the orientation is correct.

**Cause and introducing change:** the defect is known to predate plane-only 023
because 021 already contains the same non-plane geometry. The first introducing
version or pass is unknown. Projected convex-hull ordering in the merge/coalesce
path is a concrete source area to investigate, not yet a proven cause. The
independent fixture's derivation from the immutable original BSP was not verified
in that review, so this finding is scoped to the matching supplied source fixture
and actual 023 records.

**Correction and verification (4 October 2026, 03:35 EEST):** the source fixture is now proven to match the
immutable original's ordered points. The bounded fix is in `canonical_face_clip.py`
(source hash recorded in receipt `canonical-winding-fix-001`): projection-hull
coalescing preserves the source directed winding, and clipping/coalescing
normalizes against the original area vector. On the exact-linked house fixture it
emits 590 polygons / 919 fan triangles with zero reversed loops; source positions,
UVs, material/style/light fields are preserved. The actual-BSP numeric fixture
checks ordered loop, resolved plane bytes and side, and passes ten repeated
float32 recuts with zero geometry changes. The focused suite passes 27 tests.
This supersedes the earlier uncertainty about whether the fixture corresponded
to original source geometry. The earlier independent review remains accurate for
its package scope: 023-002 held the unchanged 023 BSP and omitted the corrected
helper/tests/repeat runner, so the reviewer could not reproduce the fix there.

This is a validated bounded source fix, not a rebuilt full-scene BSP: the actual
023 file and reviewed ZIP remain unchanged. Full-scene integration/repeat,
production serialization, native rendering and release acceptance are pending.
The receipt proves loop/plane-side agreement in its numeric fixture; it does not
establish Amiga visual consequences or close the production-map issue.

#### GEO-03 addendum: canonical writers also reversed valid source loops — 4 October 2026, 04:23 EEST

A later source comparison found the same class of defect in both
`tools/canonical_bsp_cull.py` and `tools/canonical_world_cull.py`: the writers
forced clipped loops to the orientation of the BSP plane, which could reverse a
valid loop inherited from its source polygon. This was a serializer-level gap;
the clip-helper winding proof alone did not cover the emitted BSP records. Both
writers are now corrected. Three regressions were reproduced against the old
source, and 30 current focused tests pass across world writing, placement writing
and water-top preservation.

Current water policy preserves visible upward-facing water surfaces and allows
terrain clipping of buried closure sides and bottoms; water is neither a terrain
receiver nor a barrier. An original-based combined candidate using aligned
canonical terrain, clipped objects and shared-sky conversion is being rebuilt.
It has not yet produced or validated a final BSP, and is not accepted. A bounded
stump sample reported 67 removals, 24 crossing cases, 27 unchanged cases and
3,421 above-ground survivors; local rendered LAND differed from canonical terrain
by up to 9.29443 compiled units in that sample. These bounded results do not prove
whole-world correctness or savings. Validate directed loops after actual BSP
write/reload, and keep historical receipts unchanged.

An eleven-map exact PVS deduplication probe produced byte-identical files and
zero savings; no optimization is claimed from it.

## TEST-PORTABILITY-01: pre-release fixture dependencies and host assumptions

Observed in the v0.0.28-rc1 worktree on 4 October 2026; introducing revisions are
not established. Linux full discovery initially failed one torch-brush fixture
because its ad hoc link list omitted `aw_render_ranges.c`, although the production
Makefile already linked that source. The fixture now links the actual implementation.

Windows full discovery additionally exposed POSIX API mocks without `create=True`,
path-separator assumptions in generated cgroup data, tests needing case-sensitive
names or symlink privileges, and POSIX shebang execution assumptions. Fixtures now
mock the intended platform explicitly, retain portable assertions in separate
methods and report unsupported capabilities as skips. The Python inspector entry
also retained an obsolete duplicated JavaScript fixture; it now executes the same
maintained standalone JavaScript suite as the direct Node check. No inspector or
engine runtime correction is claimed for these test-fixture repairs.

Historical verification on 4 October 2026, before the EFRAG-01 correction:
Linux discovery 749 tests, 745 passed and four explicit skips; Windows discovery
749 tests, 663 passed and 86 explicit skips; zero
failures/errors on either host. Both Amiga cross-compiles passed and matched all
205 engine source files. Windows used the existing Python build entry after the
PowerShell script entry was rejected by local execution policy; the policy was
not changed. Before/failure/after evidence is preserved privately. These local
results do not establish a published fixed version, an emulator playtest or hosted
CI for a future commit.

## EFRAG-01: static foliage leaf links exhausted in image004

Recorded 4 October 2026 from the 06:26:57 EEST final verification.
**Status:** bounded source correction, cross-host gates and native capacity/map-reset
route passed. Image006 verified that route and filesystem write/exit/reboot behavior
at 07:30 EEST on 4 October 2026. Image005 remains rejected for HDF-WRITER-01;
image004 remains the original efrag-failure reference. All-world and real-hardware
acceptance are not established, and SKY-VISUAL-01 remains open.

- **Observed/version/environment and reproduction:** v0.0.28-rc1 private
  image004 in WinUAE boots the prison. Open the console and run `map sn045`;
  repeated `Too many efrags!` messages appear during exterior static linking.
  The engine was matched to all 205 recorded source files. This warning identifies
  lost visibility links and omitted foliage, even though the map loads. It cannot
  be downgraded to an acceptable modeled memory-margin warning.
- **Cause and extent:** `R_SplitEntityOnNode` exhausted the fixed 8,192-link pool
  and returned without linking subsequent leaves. `sn045` needs 8,612 links for
  77 static entities: 420 missing links affect two entities, one wholly unlinked.
  Across all 2,664 authenticated packaged exterior maps, 762 exceed the old pool;
  the maximum is 52,176 links in `vf0538`. Maximum static count is 266 against the
  separate unchanged limit of 512. Sprite bounds were checked against actual
  frame corners, camera-facing rendering and scale applied once; no coordinate
  or duplicate-scale defect was established. First introducing revision is
  unknown; this demand failure is confirmed in image004.
- **Correction candidate:** retain the existing 8,192-link base pool and grow
  in 1,024-link map-owned low-Hunk pages, with a 65,536-link hard cap. Allocation
  occurs only during static linking. Client resets clear/reuse the pages; map
  clear drops leaf/static and allocator references before Hunk release. Exhausting
  the hard cap raises an explicit load error; actual allocation failure remains
  an error. Geometry, placements and the static-entity limit are unchanged.
- **Memory accounting:** the fresh Amiga ABI probe measures 16 bytes per link
  and 16,388 bytes per page payload, including its next pointer. Twelve alignment
  bytes plus a 16-byte Hunk header produce **16,416 bytes per allocated page**.
  `sn045` needs one page; the measured maximum needs 43 pages / **705,888 bytes**.
  The absolute cap is 56 pages / **919,296 bytes**. Maps fitting the original pool
  allocate no extra pages. These are additional map-Hunk costs, not executable
  size, whole-process RAM or observed free Fast RAM. The earlier image004 native
  heap peak of 8,810,640 / 11,534,336 bytes establishes one measured old-image
  heap state, not all-map fit or total-system memory availability. The estimator
  charges pages after model loading and records header/alignment separately;
  engine receipts now bind `client.h`, `r_efrag.c`, `cl_main.c` and `host.c`.
- **Verification:** all 2,664 new estimator results matched the independent
  demand audit with the fresh target ABI. The native regression reaches 65,536
  links, checks last-entity visibility, explicit exhaustion, removed-link reuse,
  client reset and freeing/reloading pages under ASan and UBSan. All 63 native
  engine methods and 26 focused Python heap/receipt fixtures passed. Fresh full
  discovery found 753 tests: Linux 749 passed / four explicit skips; Windows
  667 passed / 86 explicit skips; zero failures or errors. Both matching Amiga
  cross-compiles passed with all 205 engine sources matched. Both executables
  are 718,032 bytes, differing only in six bytes within two embedded compile-time
  strings. Both retain the same 84 compiler warning lines as the preceding
  day/night build; no warning was added or removed. Existing warning debt remains.
  Linux source/asset-free packaging and UBSan render-range checks passed; Windows
  covers its native launcher and Node checks. The native follow-up below supersedes
  the earlier pending route/memory checks, within its explicitly bounded scope.

**Native follow-up, recorded 4 October 2026:** the validation run used the same
production image005 engine (SHA-256
`9d1e24a2ce04e388cb27aa53c0325dc12395e9f0f20a78da3d919e841616fd50`) and loaded
`sn045` → `vf0538` → prison → `sn045`. Its 11,346-frame profile recorded a peak of
52,176 efrags and final allocated capacity of 9,216 against the 65,536 limit,
with zero edge-overflow or surface-overflow frames. The first `sn045` heap peak
was 8,827,056 bytes, exactly the previous 8,810,640 plus one 16,416-byte page.
Its low-Hunk use was 8,814,288 bytes on both the first and repeat visits; the
repeat transient peak was 9,084,960 bytes. The `vf0538` peak was 5,922,896 bytes.
This supports bounded growth and map-reset behavior on the tested route within
the 11,534,336-byte heap, not total Fast RAM or every-map visibility/memory proof.
The separate private image005 filesystem rejection does not erase the recorded
engine measurements; it prevents accepting that playable image.

**Image006 verification, 4 October 2026, 07:30 EEST:** an authenticated copy with
the same engine loaded `sn045` → `vf0538` → ship/prison → `sn045`, exited cleanly
to AmigaDOS, then restarted the same test HDF, loaded `sn045` and exited cleanly
again. The first route recorded 7,495 frames, 52,176 peak efrags, final capacity
9,216 and zero edge/surface-overflow frames. All heap figures repeated the earlier
route: `sn045` first peak 8,827,056, repeat peak 9,084,960 and settled low Hunk
8,814,288 bytes; `vf0538` peak 5,922,896 bytes. Post-exit and post-reboot content
and ownership checks both passed as detailed in HDF-WRITER-01. This is bounded
WinUAE/JIT evidence with 16 MiB Fast RAM, not all-world or real-hardware proof.

The repair preserves private checkpoints and source hashes. Public source and
this record contain no original game artwork, private paths or screenshots.
See [day/night and sky](DAY_NIGHT_AND_SKY.md#static-foliage-links-image004-incident-and-image005-correction-candidate)
for the current host gate and presentation scope.

## SKY-VISUAL-01: sky-only day/night remap conflicts with gray fog

Recorded 4 October 2026 during the bounded native route for the earlier
v0.0.28-rc1 candidate. The first sky-only remap left distance fog gray, producing
contrasting distant silhouettes; the ordered dawn pattern also showed moiré.
Frozen-time comparisons reproduced both defects. Image006's route/filesystem
pass did not establish a visual fix. The first introducing development snapshot
is the sky-only v0.0.28-rc1 milestone; no earlier published version is implicated.

The current repair replaces the ordered pattern with uniform cached remaps and
coordinates independently selected Clear-profile sky and far-fog RGB targets.
Direction-based horizon haze follows camera pitch/roll. Nearby geometry,
interiors and UI retain their separate behavior. Focused sanitized fixtures and
both full host gates passed; both normalized-source Amiga compiles produced the
same executable. Image007's complete payload and allocation checks passed.

**Status: implemented correction, native visual acceptance pending.** The
independent image007 playtest must check matched dawn/day/dusk/night views and
occlusion before this visual issue can be closed. Sun/moon layers, night-sky
artwork, regional weather and nearby-world relighting remain separate unfinished
features. See [sky and fog implementation](DAY_NIGHT_AND_SKY.md).

## HDF-WRITER-01: private image005 refresh left owned blocks free

Recorded 4 October 2026. **Status:** image005 remains rejected; image006's corrected
private assembly and bounded native write/exit/reboot checks passed at 07:30 EEST.

- **Version/environment, reproduction and impact:** the private host image005
  engine/checker refresh produced a filesystem whose owned blocks were not all
  marked allocated. Native writes then overwrote test-header blocks, producing
  AmigaDOS checksum error at block 1,233,646 and directory loss. This is an image
  assembly failure independent of EFRAG-01's public engine correction and the
  remaining day/night visual gap.
- **Established cause:** the private editor called `device.close()` without
  first calling `volume.close()`, leaving the allocation bitmap unflushed. Eight
  blocks owned by the engine/checker files were still marked free. The image004
  baseline passes the owned-block check; the failure is established in the
  image005 refresh path. No public engine or public image-writer defect is claimed.
- **Correction and verified result:** image006 was refreshed from image004 with
  the volume closed/flushed before the device and every owned block checked as
  allocated. Test copies were authenticated to the assembled boot-image SHA-256
  `145e04c8de783a0a49b525f8612b92a18b152d985c770eb30932c1bdd317a629`
  and matching world image before three recorded test controls were applied.
  The observed route, clean AmigaDOS exit, restart of the same test HDF, second
  `sn045` load and clean exit are recorded in EFRAG-01 above.
- **Filesystem evidence and scope:** both the 07:27:36 EEST post-exit and
  07:30:07 EEST post-reboot checks passed: 8,788 original files checked, none
  missing or unexpectedly changed, and zero free-owned blocks, duplicate ownership
  or invalid nodes. Twelve new native files were recorded. Verification used
  Amiga filename case folding; the earlier case-sensitive verifier's false
  `S/startup-sequence` mismatch remains preserved in private diagnostic evidence.
  This establishes the recorded image006 write/exit/reboot case in WinUAE/JIT
  with 16 MiB Fast RAM. It does not establish all-world gameplay, real-hardware
  behavior or resolution of SKY-VISUAL-01.

Source and image checkpoints remain private. No runtime code was changed for
this incident record, and no game artwork or private filesystem paths are included.

## CFG-01: startup comments split into console commands

Recorded 4 October 2026 during the v0.0.28-rc1 native playtest review.
The packaged gameplay defaults contained semicolons inside `//` comments.
The engine command buffer separates commands at unquoted semicolons before
the token parser discards comments. Text following them therefore produced
nonfatal unknown-command messages including `range`, `console`, `2` and
`negative/NaN`. Default settings themselves still loaded. A separate private
test comment caused the same symptom and is not part of the public defaults.

The bounded repair replaces comment separators with periods, preserving actual
commands and avoiding a change to the engine command grammar. The correction
is part of the next cycle candidate. The first full Windows and Linux runs each found one outdated
test assertion requiring the old semicolon wording. That assertion now checks
the documented meanings separately and rejects semicolons in default comments.
Both actual Amiga compiles and full-suite retries passed (Linux 753 passed /
four expected skips; Windows 671 passed / 86 expected skips). Image007 contains
the corrected defaults and passed packaged readback. Actual default-startup
validation remains pending; image006's prior route pass does not establish it.

## GEO-04: canonical terrain world hits the VIS portal limit

Recorded 4 October 2026 in the v0.0.28-rc1 terrain repair trial025.
The prior diagnostic displayed canonical LAND while retaining coarse world
collision, so it could not establish matched visible ground and walkability.
Rebuilding a world from all 8,192 authored triangle prisms reached QBSP but
failed VIS with `Leaf with too many portals`. The intermediate world alone had
19,136 faces and 38,425 stock clipnodes, before scenery. This is a rejected
repair trial, not an accepted optimization or playable map.

The next experiment merges only exactly coplanar, same-material canonical
patches before rebuilding both world rendering and collision. It must preserve
the actual terrain surface, placement bindings, visible water and required
collision behavior, and report storage and memory against the untouched map.
Neither the rebuild nor full-world canonical culling is accepted yet.

## CLOCK-01: automatic clock discarded fractional milliseconds

Recorded 4 October 2026. The pre-correction v0.0.28-rc1 automatic tick path
truncated sub-millisecond time every frame, allowing frame-rate-dependent drift.
The first historical introducing version has not been established. The current
repair retains a bounded fractional remainder and clears it on explicit clock
changes, waits and inactive-server transitions. The saved calendar remains the
single clock; no second time system or retroactive catch-up was introduced.

The default-on `dbg daynightcycle` control pauses only automatic advancement;
explicit time setting and T waits still operate. Host fixtures cover fractional
accumulation, pause/resume, invalid values, explicit changes, rollover and saved
milliseconds. All 63 native engine methods and both full host suites passed.
The later image009 established bounded historical clock/profile restoration.
The previously frozen V3 source gate and image014 readback passed. Independent
image014 native acceptance completed with a failed aggregate result because of
cold guard admission; the sub-2-MiB logged clearance is a reserve warning, not a separate hard native gate (see GUARD-COLD-28).
The cache correction is host-validated and incorporated in finalization011, which passed the updated-source freeze and target compilation gates. Image015 passed its declared native gallery, guard and pressure scope. Broader routes and physical-hardware performance are not established. Gallery stages and guard clock boundaries passed; this does not certify every saved-clock lifecycle. **Status: stable v0.0.28 accepted locally within scope; hosted CI/tag/publication pending.**

## GUARD-COLD-28: automatic guard torch admission failed on cold visits (CLOSED WITH BOUNDED NATIVE VERIFICATION)

Recorded 4 October 2026 from the independent native acceptance of image014.
Cold Imperial and Hlaalu visits failed the automatic night-guard torch check:
the close Imperial follow-up logged three eligible companions, zero admitted and
three evictions, with repeated model lookup activity for minutes; the Hlaalu
follow-up logged three eligible, zero admitted and three model skips, with the
guard visibly bare-handed. The initial failures were also present in the
99-capture run. Later warm boundary observations used different poses/lighting,
and the distant 320-by-200 frames cannot certify the visible flame. Command
parsing and invalid-input checks passed but do not imply a visual pass.

The established failure mechanism is in low-Hunk alias decoding: staging calls
`Cache_FreeLow`, which evicts the hot actor before the later `malloccopy`. The
`gt_b` guard and Vodunius alias alternation reaches this path. A `model.c`
correction now stages decoded alias data separately before cache expansion, so
the hot cache working set can survive. Focused source regressions pass for
actor/body/held-item residency and grouped alias formats, including UBSan,
allocation failure, 16-bit skin conversion, the greater-than-512-KiB fallback,
and malformed/truncated-input rejection. A first test compile exposed a
duplicate test declaration; the test harness was corrected to keep production
translation units separate. This is host-validated source evidence only. Finalization011 incorporated the correction and passed its freeze and target-compilation gates. Image015 passed fresh cold admission for both factions with three eligible guards admitted, zero frame/model skips and zero evictions. Boundary checks showed torches on at 20:01 and 05:59, off at 06:00 and 20:00; moving gold/ember pixels were visible in bounded close captures.

Image014 logged minimum peak clearance of 1,689,040 bytes below the unchanged 2 MiB safety reference, a reserve warning rather than a separate hard native gate. Image015 pressure checks across five maps completed without crash or renderer overflow; minimum logged clearance was 1,812,304 bytes at sn012, 284,848 bytes below the same reference. The production memory gate did not pass. The controlled malformed-map fatal-report check passed within its scope. Audio artifacts remain an owner-deferred open issue, mostly at load-ins and heavy scenes.

Correction recorded 4 October 2026: earlier wording in this entry called the 2 MiB comparison a failed native reserve criterion. That overstated the gate. The unchanged 2 MiB value is a safety/admission reference; a clearance below it is a reserve warning, not an independent hard native gate. Image015 remains below it, so no production-memory pass is claimed.

The same review found a case-sensitive guard memory-cost lookup while runtime
IDs match case-insensitively. Mixed-case Imperial IDs therefore omitted three
placements from one tested town map. The corrected estimator case-folds source
IDs only and preserves exact model paths. That map now counts five placements
instead of two and charges an additional 352,144 bytes; the checked Hlaalu map
is unchanged. A mixed-case regression fails before and all five focused ledger
tests pass after correction. Finalization011 regenerated the estimates, and its Linux Docker target-ABI gate passed after the correction. This estimator check does not reduce reserves or establish a production-memory pass.

### Horizon coordinate transcription correction

The later Ashlands screenshot's global X was initially transcribed as51055.
Reinspection corrects it to **51855** (global51855 39125 3502, local-348 565107,
rawDEG265/P0), consistent with the scene transform. Preserve this transcription
correction when reproducing the view; it is not a changed player position.

## LIGHT-GRADIENT-29: unsigned surface-light interpolation overflow

During the v0.0.29 guard-light investigation, a synthetic fixture using the
actual guard allocator, surface marking, rotated-brush transform, surface cache
and palette lookup triggered signed overflow in `R_DrawSurfaceBlock8_mip0`.
The surface light samples are unsigned. Subtracting them before the shift made
negative slopes wrap into huge positive steps and overflow during interpolation.
This is an inherited renderer arithmetic defect; its introducing revision is
not established. It is not yet proven to explain the owner's entire guard-light
report.

The v0.0.29-dev1 candidate converts the bounded samples before subtraction and
uses explicit floor rounding for negative steps in all four active 8-bit mip
paths. The unchanged 16-bit path already loads signed endpoints before doing
its differences. No light count, radius or global brightness was increased.

Before repair, the final-pixel fixture failed under undefined-behavior checking.
After repair, all four mip levels brighten world and translated/rotated brush
pixels at representative ambient/static levels (0/12, 128/12 and 128/50);
extinguishing restores every original pixel. Missing-lightdata, fullbright and
saturation controls correctly show no change. Existing player-torch and brush
fixtures also pass, and the Amiga target compiles. The fixture is
[`aga_guard_light_surface_test.c`](../tests/aga_guard_light_surface_test.c).

This establishes the arithmetic repair and a working synthetic surface-light
path. The bounded native interior and guard checks documented above add visible
view/pavement responses, but do not isolate this arithmetic change as the cause
of those results or establish general appearance/frame cost. **Source repair
tested; Fixed: N pending complete matching native acceptance. First verified
fixed release: none.** TORCH-LIGHT-29 and INTERIOR-LIGHT-29 remain open for
scene-specific diagnosis.

## TRANSITION-EQUIPMENT-29: carried torch blinks out during cell handoff (OPEN)

Owner reports 5 October 2026 in Seyda Neen automatic cell/sub-cell travel: hands
remain visible, but an equipped torch disappears briefly on arrival. Reproduce
with F-raised hands plus V torch, cross a boundary without toggling either, and
inspect the first visible arrival frames. Compare unarmed, fists, fists+torch,
raising/lowering and attack phases. Future weapons plus torch must use the same
complete state-transfer contract, not a fists-only presence check.

Source diagnosis: the current load path carries aw_hand_goal and aw_torch but
not aw_hand_state, animation timer age, attack latch or ready weapon presentation.
The newly spawned player begins in state0; game rules restart drawing. Torch
rendering/lighting requires ready state2, so the saved torch bit alone cannot
prevent the blink. Transfer field-by-field values and timer age across the new
server clock, rebind new-world model names instead of carrying VM pointers, and
restore before the first visible client state. Native acceptance remains pending.
**Fixed: N.** The separate owner observation that player torch lights surfaces
does not establish transfer continuity.

## TORCH-HAND-SEPARATION-29: grip appears to break during idle animation (OPEN)

Owner supplied two frames on 5 October 2026 showing the torch-side hand/grip
changing/separating while standing. He associates it with breathing/idle motion;
this is a reproduction hypothesis, not a confirmed geometry or skinning cause.
Visible HUD: global -14208,-66080,170; local -736,1399,42; heading282/pitch0;
game times22:24 and22:25. Exact animation phase and active streamed chunk still
need capture. Compare the owned torch model's successive frames, grip/hand
topology, interpolation, clipping and shared pose transforms at a fixed camera.
Keep distinct from the map-handoff blink until evidence links them. **Fixed: N.**

### 5 October torch-light acceptance follow-up

Owner confirms the held/player torch now visibly illuminates surroundings.
He separately reports the guard torches still appear to illuminate little or
nothing. A nighttime guard screenshot records global -11281,-70292,315;
local -4,346,78; heading330/pitch13; game time21:12. Reproduce there, distinguish
visible flame proxies from admitted point lights, and measure actual surface
pixels. The guard-light path is capped at two admitted lights; visible flames
alone do not prove a corresponding light was selected. Root cause of this
specific screenshot remains unverified; retain the guard-light bug as open.

Requested control: saved torch light-radius configuration plus a debug-console
command to adjust lit area. Preserve bounded radius, light count and defaults;
this tuning control is separate from fixing missing transfer/equipped state.

## 5 October playtest scribe cross-check

The owner confirms that the head/appearance and class overlays in the current
playtest work and head rotation is faster. Keep that positive result attached
to MODAL-WORLD-29; it does not establish music continuity or acceptance of the
new OK controls. Freeze+black defaults apply to head/race and later blocking
pages; original name entry retains its prior behavior. Music servicing stays
live.

The requested aw_ui_mode 2 default retains mode 1 and adds visible bottom-right
OK on the same hint row, clickable by mouse and focused after Hair for Enter.
Keep the existing confirmation step. Native button acceptance remains pending.
Class-selection illustrations and a custom-class path are separate missing
components. See CHARACTER_CREATION.md.

tpscene means transport/teleport to a named scene, initially headselection, so
repeat tests do not require replaying the intro and future playtests save time.
Keep ordinary New Game intact. The command is for disposable state because it
resets unsaved character/story progress. Source usage is documented in
DEBUG_OVERLAYS.md; target acceptance is pending.

SHACK-VISIBILITY-29 persists in the post-reboot owner view. ROCK-FLORA-SURFACE-29
is a separate recent angular/coarsely textured ground-form report; object
identity and cause are unknown. Do not label it mushroom or merge it with
shack/tree incidents without source evidence. The owner confirms the
carried/player torch now lights surroundings. Guard torches still appear weak;
TORCH-LIGHT-29 stays open. TRANSITION-EQUIPMENT-29 is P1: preserve complete
equipment/animation state across cell/sub-cell arrival so the torch is present
on the first visible frame. TORCH-HAND-SEPARATION-29 is separate suspected
grip/model deformation correlated by the owner with idle/breathing animation;
mesh causality is unconfirmed.

The owner requested bounded saved torch-radius control plus console adjustment,
and an optional bright-base flame style with classic selectable. The newer
source candidate now implements these controls; they remain source-only and
separate from urgent equipment handoff. See TORCH.md for exact commands and
pending target acceptance.

The private scribe checklist records the complete same-day report crosswalk and
preserves the latest torch-grip screenshot. Earlier reports remain in the
existing journal and plan. Source fixtures, earlier native samples, current
post-reboot playtest observations, and the parent’s newer source candidate are
distinct evidence classes. No report is closed by this audit.

### Later 5 October grip and radius follow-up

A further traversal screenshot shows the first-person torch-grip glitch with a
view resembling the hand/torso seen from the opposite side. Keep this under
TORCH-HAND-SEPARATION-29 pending evidence that it is a distinct defect; the
rendered-part visibility/geometry explanation remains a hypothesis. The owner
asks that investigation include OpenMW and OG first-person part-visibility
behavior. The new screenshot is retained in the private same-day checklist
receipt. Do not claim an OpenMW/OG cause or parity result before source study.

## 5 October torch underfoot and SHIFT+RUN acceptance

The owner identifies dim ground directly beneath the player as the main torch
illumination problem, not only insufficient reach. Compare torch OFF/ON at the
same nighttime position while looking down from a normal held pose; inspect
ground immediately beneath the player. Test held-player and guard torches
independently. A farther-wall response or guard pavement sample does not close
this near-field gap or the other emitter.

The owner reports the hand/torso part glitch most strongly during SHIFT+RUN:
left-side geometry appears and disappears. This strengthens the reproduction
for TORCH-HAND-SEPARATION-29 but does not prove a part-visibility or mesh cause.
The owner requests study of OpenMW and OG first-person part visibility. Keep
this under the existing report unless evidence establishes a distinct issue.
The traversal screenshot remains private; its hash is in the private scribe
receipt.


## MAP-MARKER-29: click to place a user map marker (REQUESTED)

Owner requests that clicking a location on the user map place/update a user
map marker. This marker is distinct from teleporting the player and from the
Debug map's teleport control. Expected behavior: map click sets the marker and
does not change player position; show the marker clearly on the user map and
preserve/update it according to the existing user-marker/save policy. Exact
persistence semantics need to follow the current map design. This feature is
queued after the urgent torch state handoff repair. No implementation or target
acceptance is claimed.


### Owner clarification: freeze J/M/map backgrounds

The owner explicitly asks that journal (J), books/readers (M/AWReader) and map
screens freeze the 3D world behind them to avoid wasted world work. Keep UI and
soundtrack servicing live. The parent reports aw_modal_freeze=1 currently
covers key_menu and AWReader; actual J/M entry paths are being verified. Do not
close MODAL-WORLD-29 from the general head-selection overlay observation alone.


### Torch-control source status

The newer source candidate adds saved aw_torch_radius (default 192, bounded
32–288) for player and admitted guard lights, with dbg torch radius X; it adds
saved aw_torch_flame_style (1 classic default, 2 brightbase) and
dbg torch flame classic/brightbase. The Amiga build passed. Initial integration passed 78/79 checks; the
remaining old-radius assertion was corrected and its real-QC fixture passed
separately. A fresh combined run follows the map/stride changes. These changes are not
deployed to current development playtest and lack native acceptance. Direct-underfoot
night illumination remains an acceptance gate.


### Map interaction requests

The owner requests two distinct click behaviors. In normal user-map mode, left
click sets/updates a user map marker without moving the player. With debug HUD
on, the map should default to DEBUG; in DEBUG map mode, HUD right-click sets
the red teleport crosshair and shows the bottom-right Teleport button, with no
instant travel. Existing dbg tp map remains available independently of HUD
visibility. A debug teleport action must stay separate from a normal user
marker. These changes are requested/in progress; native acceptance is pending.


### Running torch arm: tested source mitigation, target acceptance pending

The current first-person model contains arm parts and the torch, with no torso.
Inspection and projection comparisons identify forward stride bob exposing
near-clipped arm geometry as a reproducible running contribution. The source
adds saved `aw_torch_depth_bob 0`: torch-equipped depth remains stable while
camera and lateral/vertical motion continue; `1` restores the legacy behavior.
A fixture using the actual camera and alias-transform routines passes 324
stride/speed/pitch/yaw combinations with sanitizers; restoring the old depth
behavior causes the relevant assertion to fail. This is a tested source
mitigation, not native acceptance or a claim that all grip fragmentation is
resolved. Standing/idle fragmentation remains OPEN.


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


### Idle torch investigation: clipped fourth vertex (source candidate)

TORCH-HAND-SEPARATION-29 remains OPEN. A separate renderer defect is now
reproduced: near-plane clipping can turn a triangle into four vertices, but
the alias clipper checked only the first three when deciding which screen
edges to clip. If only the fourth vertex crossed an edge, the old path
clamped its position without clipping the polygon and interpolating its
attributes. The source candidate checks every vertex produced by near
clipping. It keeps the five-unit near plane, authored model, frame selection
and existing `aw_torch_depth_bob` rollback control unchanged.

A synthetic fixture runs the actual alias projection/clip routines through
96 cases covering all screen edges, cyclic vertex order, both windings and
near-plane rejection. It passes with undefined-behavior/float-cast-overflow
sanitizers in offline Docker; restoring the old three-vertex check makes it
fail. The existing stride-depth fixture also passes. An independent audit
of the owned model finds the omitted-edge condition in some idle poses and
view configurations; this does not establish that it explains every reported
grip fragment. This correction is for a subsequent development build.
Fresh target rendering and standing/idle visual acceptance remain pending.

## LIGHT-UV-DISTANCE-29: texture scale changes dynamic-light reach (SOURCE REPAIR CANDIDATE)

- **Type/version:** confirmed renderer bug, reproduced 5 October 2026 at
  18:50 EEST against the current v0.0.29-dev2 source path. The introducing
  revision and first affected release are not established. This is a next
  development source repair, not a change to sealed dev2 artifacts.
- **Symptom/reproduction:** run the actual surface accumulator on a synthetic
  floor with radius 192, light height 25 and the same sample 16 world units
  from its projection. Contributions were 38,656 at unit UV scale, zero at
  scale 16, and 42,240 at scale 0.125. Light reach incorrectly depended on
  material UV density. The owner's dim-underfoot and weak-guard views remain
  separate native reproduction targets; this fixture does not identify their
  exact causes.
- **Cause/proposal:** radius and surface-plane distance were world units, but
  lateral distance was unnormalized texture space. Convert the in-plane UV
  basis, including skew, before Quake's existing cheap falloff calculation;
  preserve radius/count/admission and the singular-mapping fallback.
- **Tried/results:** the real C regression fails on the unchanged renderer.
  The candidate passes 85 equivalent-point UV comparisons and near-foot,
  range and singular controls. Six focused Linux Docker methods passed with
  sanitizers, including existing guard/player lights, negative/collision-only
  brush roots, transformed brushes and final indexed pixels at all mip levels.
  This is automated source evidence; target appearance/performance remain pending.
- **Related diagnosis:** `dbg guardtorch` now distinguishes active/selected
  point lights from visible flame proxies and reports range, contents and trace
  rejections without changing admission. This supports the still-open
  TORCH-LIGHT-29 owner-view investigation. Guard diagnostics have bounded
  rejection/eviction controls.
- **Status:** source repair candidate. **Fixed: N. First verified fixed
  version: none.** See [torch evidence and limits](TORCH.md#5-october-texture-density-dependent-surface-light-next-development-candidate).


The same candidate also passes finite tiny-scale, near-singular and extreme-UV
offset controls under float-cast-overflow sanitization. Out-of-range or
non-finite distances are rejected before integer conversion. Target 68040
compilation of both changed C files passed in Linux Docker. Compilation reported
four maybe-uninitialized warnings in the existing 16-bit surface-block routine
and two misleading-indentation warnings in existing guard statements; this
check does not certify those paths or establish native visual acceptance.

## AUDIO-CLOCK-29: long DMA gaps lose elapsed playback time (SOURCE REPAIR CANDIDATE)

- **Type/version/observation:** confirmed accounting and recovery bug in the
  v0.0.29-dev2 source, reproduced on 5 October 2026 during the renewed WIN-05
  report. The owner hears more crackling in WinUAE than FS-UAE. The introducing
  revision and first affected release are unknown, and this test does not
  establish the cause of the complete audible report.
- **Where/how:** the real `snd_dma.c`/`snd_mix.c` fixture advances a synthetic
  playback cursor while the game does not poll it. A 16,584-frame gap loses a
  whole 16,384-frame ring from the inferred clock, records zero late frames
  instead of 15,482, and does not promptly repaint the current playback cursor.
  Two-wrap and five-second cases also reproduce the defect. A 120 ms control
  correctly reports a shorter deadline miss.
- **Cause/correction:** counting only observed backwards modulo positions
  cannot recover complete unobserved wraps. The next source uses the driver's
  existing EClock-derived absolute sample-pair estimate, exact fractional Paula
  period rate and double start time. A ring-aligned signed-counter epoch keeps
  long sessions bounded. Epoch/device-time resets cancel stale channel
  deadlines, clear old PCM and re-prime through the existing mixer.
- **Tried/results:** four focused Linux Docker methods pass, including actual
  PCM written at the current cursor after long gaps, PAL/NTSC driver clocks,
  long unpolled intervals, reset/epoch/shutdown, loading and speech preservation.
  The old scheduler fails three long-gap and two reset controls. New fixtures
  use sanitizers. Both changed translation units compile for Amiga 68040:
  three existing pointer-signedness warnings in driver buffer interfaces and
  none from the scheduler. No host compiler/probe or owner emulator change ran.
- **Limits/status:** ordinary mix-ahead, DMA/source queues, music state and
  rendering gates are unchanged. This repairs a demonstrated recovery and
  diagnostic defect; it is not a verified cure for all crackling. Delivered
  WinUAE has explicit sound settings while FS-UAE mostly uses defaults, so
  active backend/override equivalence is unverified. Sealed dev2 is unchanged.
  **Fixed: N. Next development source candidate; native listening pending.
  First verified fixed version: none.** See [audio evidence](AUDIO.md#5-october-long-stall-playback-clock-recovery-next-development-source).

## SKY-MIDNIGHT-29: default nightly clearing (DEV3 SOURCE CANDIDATE)

- **Observation/cause:** the owner still reported dense midnight clouds in
  v0.0.29-dev2. The default `aw_cloud_control 1` retains the old coverage and
  leaves its V2 night selector inactive. Its legacy role map also rejects
  opaque palette index 254, preventing the night overlay through that map.
- **Change:** archived `aw_nightsky_mode 1` now defaults on independently of
  the base cloud controller. Coverage fades toward clear during 23:00–00:00,
  stays clear through 03:00, and returns to the selected base by 04:00.
  Both cloud layers use the existing ordered coverage compositor and validated
  night roles. The 04:00–23:00 path stays unchanged. This is an intentional
  AmiWind visibility policy, not original regional-weather simulation.
- **Rollback:** `dbg nightskymode legacy` / `0` removes the new override;
  `clear` / `1` restores it. `dbg cloudcontrol legacy` / `1` also disables
  midnight clearing for the retained coverage policy. Clouds, stars, night
  layer and master-sky switches remain independent, with world depth intact.
- **Evidence:** 15 real-renderer fixture modes pass in Linux Docker with
  undefined-behavior and float-cast sanitizers. The new mode checks every
  protected minute across three styles, both base controllers and both cloud
  types: 13,692 whole-tile comparisons plus directional pixel comparisons.
  Every old weather day clears, transitions are monotonic, and command/cache
  rollback, opaque 254, master switches and invalid clock/value fallbacks pass.
  An independent prior renderer build has identical protected-view output.
  Console routing and candidate configuration checks pass; both changed C
  files compile for Amiga 68040.
- **Status:** source candidate only. Native visual and frame-cost acceptance
  are pending, and earlier frozen binaries remain unchanged. **Fixed: N.
  First verified fixed version: none.** See
  [midnight-mode policy and limits](DAY_NIGHT_AND_SKY.md#dev3-midnight-clearing-mode--source-candidate-5-october-2026).

- **Owner observation, v0.0.29-dev3:** distant horizon outlines are loading
  noticeably better than before. Preserve this as a qualitative regression
  baseline only; occasional fill gaps remain. It does not close remaining
  horizon gaps, turning/popping,
  region coverage, or performance questions.

## LAND-HORIZON-GAPS-29: sky visible through distant resident ground (OPEN)

- **Reported:** 5 October 2026, v0.0.29-dev2, Bitter Coast. This new LAND report
  is tracked separately from the previously attributed Ashlands static rock.
- **Reproduction:** exterior camera near global XYZ `-10712 -65443 380`, heading
  269, time18:55; `-11051 -65442 377`, heading272, time19:05; and
  `-11323 -65423 378`, heading272, time19:11. Pitch is approximately zero.
  The second screenshot's Y is **-65442**, not -64942. HUD integers do not
  preserve the complete native eye/bob state, so these are approximate replays.
- **Observed:** distant ground has gaps through which bright sunset sky shows.
  Expected: solid authored terrain coverage up to its real visible skyline,
  preserving genuine valleys, water, foreground scenery and the existing sky.
- **Established source cause in these samples:** the current forward-distance
  BSP-node gate omits resident upward LAND. A terrain-only independent raster
  loses1,645/1,444/1,251 pixels in the three views when that gate is enabled.
  The no-far reference restores them; PVS adds no further missing LAND pixels
  in these sampled cameras. This does not attribute every bright gap in a full
  native scene or the earlier missing opaque rock peaks.
- **Source candidate for v0.0.29-dev3:** `aw_terrain_horizon 1` adds a bounded
  flat-fog pass over exact resident LAND polygons beyond the detailed draw
  range. It uses the normal projection/depth buffer and excludes water,
  downward/vertical brush closures, trees, buildings and placed models.
  `aw_terrain_horizon 0` retains the previous behaviour and remains the default.
- **Checks:** actual C raster output restores all the missing LAND pixels above,
  with zero false coverage and zero nearer-depth overrides in those samples.
  Synthetic ray/plane, camera, seam, depth and invalid-input checks pass in
  Docker, and the no-background control fails the geometry oracle as expected.
  Selected existing sky/culling tests and 68040 object compilation pass.
- **Remaining:** matched native OFF/ON/OFF screenshots, actual target cost,
  crossings/coastline/high-view checks, unsupported large-world cases, and
  separate nonresident terrain/static-rock representation. No HDF or asset
  bundle was changed by this source candidate. **Fixed: N. First verified fixed
  playtest version: none.** See [distant terrain](DISTANT_TERRAIN.md).


## HAND-IDLE-BLINK-29: fists disappear once per breathing cycle (NATIVE VERIFIED)

- **Report/reproduction:** v0.0.29-dev2 fists disappear together while standing
  still. Equipping a torch stops the blink; removing it restores the blink.
  This supersedes the earlier crossing-only attribution. The observed interval
  is about 2.67 seconds, with each disappearance lasting about 0.17 seconds.
- **Cause:** the QuakeC declaration bound `floor` to builtin #36, which the
  engine implements as round-to-nearest (`PF_rint`). Floor is #37. During the
  last half-frame of the eight-frame idle cycle, rounding selects frame 8,
  the lowered start of the draw sequence. Native hand-state tracing confirms
  ready state 2 and unchanged equipment while frame 8 is selected. The torch
  uses its own animation frame and therefore masks this incorrect fist frame.
- **Correction:** bind QuakeC `floor` to #37. The existing fixture had masked
  the error by installing a floor stub at #36; it now derives builtin indices
  from the actual engine table and supplies faithful round/floor behavior.
  Quarter-frame samples check draw, idle, punch and lower sequences, followed
  by 40 seconds of idle. A retained negative control recompiles the old #36
  declaration and must fail the same fixture. These checks pass in Docker.
- **Native evidence:** the original independent FS-UAE recording contains four
  paired hand dropouts in 12 seconds. Changing only `progs.dat` on a fresh
  independent disk copy removes them: both hands remain visible in all 1,500
  captured frames across two 25-second stationary recordings, including after
  torch equip/unequip. Two native traces total 2,400 samples over 31.638 and
  30.989 seconds; every sample remains ready fists in frames 0–7, with every
  idle frame represented. The guest exited cleanly after verification.
- **Status/limits:** **Fixed: Y in corrected QC, independently verified in
  FS-UAE. First delivered fixed version: none.** Inclusion in the next full
  development package and owner WinUAE acceptance remain pending. Sealed dev2
  remains unchanged. This finding does not resolve the separate idle grip
  fragments, punch self-occlusion or hand-detail/race-selection reports.


## VIEW-AUTOCENTER-29: forward motion recenters free-look (OPEN)

- **Report:** the owner reports that yaw/viewport tilt can reset while walking across outdoor cells or subcells, described as a pull toward the default view.
- **Original-engine baseline trial:** the recorded control sequence issued `aw_aim 90 -10`, restaged to local position 0,350, issued the same angle command again, then walked forward. A subsequent screenshot showed HUD pitch P:0 at local 0,468/469, still before the next sub-cell crossing threshold. There is no screenshot or angle readback immediately before walking, so this establishes a pre-boundary post-walk discrepancy after the commanded -10 view, not a measured continuous angle trajectory.
- **Source finding:** the legacy Quake pitch routine starts automatic centering after forward movement exceeds `v_centermove` (default 0.15 seconds). `IN_Move` also returned immediately when no mouse delta was pending, before stopping drift for held `+mlook`. This matches a plausible pitch-recentering path but is not yet proven as the cause; it does not explain any yaw reset.
- **Design/candidate:** automatic centering is legacy Quake behavior and is not an appropriate default for Morrowind-style free-look. The source candidate adds archived `aw_auto_center` defaulting to 0, preserves opt-in legacy walk/lookspring centering, and keeps an explicit `centerview` command. Held `+mlook` stops drift even without new mouse events; a same-frame explicit center command is allowed to proceed.
- **Verification/status:** the new Docker fixture passes for the config default and archived registration, opt-in threshold, mid-drift opt-out, explicit centerview after a same-frame quiet-mouse stop (including while +mlook remains held), cancellation by real mouse pitch input, and ordinary quiet-mouse +mlook. Four existing mouse, map, gallery and cell-transition fixtures also pass. Changed 68040 `view` and `in_amiga` objects compile; the `view.c` indentation warning is present in both current and HEAD baseline, while `in_amiga.c` is warning-free in both. This paragraph records the initial source gate; the subsequent native pitch follow-up below supersedes its former pending status. The yaw cause remains unresolved. **Fixed: N. First fixed version: none.**

The dev4 native follow-up now verifies the default-off automatic pitch-centering
candidate on a bounded ordinary-walking route and an actual sn037/sn054 crossing.
The legacy opt-in still recenters, and explicit `centerview` still works. A later
diagnostic replay retained client pitch with drift disabled after an explicit
center and fresh aim. The requested -11.25 degrees settles to -9.84375 through
the existing byte-angle protocol; that is distinct from a reset to zero.
An earlier discrepant HUD capture remains unexplained; no extra behavioral
patch was made for it. Actual mouse routines also passed 24 source cases of
600 walking/drift frames each. This establishes bounded pitch-fix acceptance,
not closure of every reported yaw/transition reset or an already-delivered dev4.

## PERF-READAHEAD-29: cell crossing pauses and premature prefetch cancellation

- **6 October follow-on evidence:** one unmeasured sn054-to-sn048 trace filled
  131,072 bytes for the matching destination, then recorded high-hunk move
  failure/free before two copy misses. No prefix bytes were consumed; ordinary
  loading completed. This attributes one eviction, not its frequency or cost.
  A caller-specific bottom-gap relocation prototype passes real allocator
  fixtures and 68040 object/ABI checks. A separate, legacy-behavior gap probe
  has linked successfully; the observed crossing's actual gap/fit still needs
  native capture. Both are outside the frozen playtest. No speedup is claimed.
  See the dated follow-on section in the linked investigation report.

- **Category/status:** Performance / Needs work. **Fixed: N.** First fixed
  version: none. Investigation and measurement are complete for the bounded
  route below; no transition-speed fix or accepted speedup is claimed.
- **Report:** visible loading pauses interrupt outdoor traversal. Preserve
  view direction, equipment, active voices and music during optimization.
- **Measured baseline, 5 October 2026:** eight automatic sn048/sn054 boundary
  crossings on the same engine/assets, four per loading method, reached the
  ready/presentation-callback estimate in 1.070–1.149 seconds. This callback
  runs after screen update returns and may follow an early return without the
  destination world being drawn. Thus these numbers are not proven first-world-frame
  latency. The route used fixed-height noclip to isolate loading, not ordinary
  walking/collision acceptance.
  Instrumented model reads consumed about78.9–79.7% of server loading time;
  measured decode was about4.8–5.2%. The read timer is guest elapsed time inside
  the model loader, not physical-device throughput. Nested phases overlap and
  must not be added as independent totals.
- **Read-ahead finding:** with128KiB/1.5-second lookahead, method2 filled its
  prefix on all four crossings, but only one later load reused any bytes
  (130,948); three prefixes were unconsumed. Both southbound misses match the
  replayed early target switch; the remaining northbound miss is unexplained.
  Its approximately30ms lower medians do
  not establish a read-ahead benefit. Exact source/directory replay shows the
  southbound endpoint prediction advancing to sn043 before hysteresis allows
  the actual sn054-to-sn048 handoff, replacing the useful sn048 prefix early.
  This is a concrete cancellation mechanism consistent with the counters,
  not native per-frame tracing of the predictor.
- **Source candidate:** method 2 now targets the first crossed region; method 1,
  its default, and the stream reader are unchanged. Four focused C fixtures, a
  68040/FPU object compile, and the full 916-test integration suite pass (912 passed, 4 skipped, no failures/errors). These
  establish source/compile correctness, not patched native performance.
- **Fresh matched native comparison:** four counted method-2 crossings per
  engine, two per direction and two preceding warm-ups, compare the unchanged
  control with only the first-crossed-region candidate. With 128 KiB and
  1.5-second lookahead, prefix use improved from 0/4 to 3/4. Callback medians
  changed from 1,100.757 to 1,119.780 ms southbound and from 1,154.541 to
  1,093.892 ms northbound. This small mixed result does not establish an overall
  speedup. One fully filled 131,072-byte prefix was still unused. The original
  method-1/method-2 baseline above is a separate sample set.
- **Next attribution:** allocator fixtures demonstrate that hunk pressure can
  move a resident prefix or evict it before copy. They do not identify the
  cause of the native miss by themselves. The historical trace proposal aimed to distinguish
  target changes, explicit cancellation, relocation, eviction and actual copying
  without changing cache LRU through extra observational lookups.
- **Timestamp limitation:** the profile callback runs after screen update returns;
  that routine may return early without drawing the destination world. Heap audit
  also precedes this timestamp. Treat 1.070–1.149s as a ready/presentation
  estimate, not proven first-world-frame time. See [the investigation report](performance/CELL-TRANSITION-INVESTIGATION-v0.0.29-dev4.md).
- **Profiler gap:** current profiles do not retain predicted-target changes,
  cancellation/eviction reasons, file-open/seek timing, or transition-scoped
  audio continuity. The current controls are aw_cell_change_method (1/2),
  aw_cell_prefetch_kib (128/256/512), and aw_cell_prefetch_seconds (0.5–4,
  recorded at 1.5). The load TSV records model, method, read bytes/calls/time,
  decode/world/actor/total times, prefix consumed/read time, low/high hunk,
  capacity/filled bytes, worst prefetch slice and look-ahead. The visible TSV
  records model, method, elapsed callback time, requested capacity and look-ahead.
  These files are appended by AW_StreamLoadEnd and AW_StreamPresented;
  AW_StreamPresented runs after SCR_UpdateScreen returns and is not proof of a
  destination draw. Proposed bounded, opt-in instrumentation is described in
  the report; the later bounded cache-event ring does not implement that entire profiler.
- **Resolution path:** extend the matched native route on patched source versus
  unchanged baseline, with direction and boundary cases, and compare prefix reuse,
  callback timing, frame cost, and memory. Keep method 1/default unchanged. Do not
  close this issue merely because the source patch compiles.
- **Acceptance remaining:** verified useful prefix reuse and measured latency
  improvement, ordinary-walking routes, unchanged cell selection/collision,
  exact view and equipment state, and audible voice/music continuity. The
  eight baseline crossings retained sampled hands/torch state but did not
  establish waveform continuity or a comprehensive regression pass.

## SKY-NIGHT-COVER-29: owner appearance acceptance, 5 October 2026

The owner reports that the night sky now looks great. Record the current
night-sky appearance as owner-accepted and preserve it as the visual regression
baseline. This is acceptance of the observed appearance, not a new synthetic
test result. The report does not identify the exact active configuration,
weather, region or executable hash. Broader clear/partial/overcast behavior,
all-region transitions and frame cost retain their existing open gates.
Keep legacy sky/cloud variants selectable when making further changes.


## GUARD-TORCH-CYCLE-29: intermittent night visibility

On 5 October 2026, the owner first observed a nearby guard without a visible
torch during a night-cycle check, then saw a torch on the same guard after
reapproaching later that night. This is an intermittent/delayed-visibility
report, not confirmation that the cycle is lost or that the torch was absent
continuously. The triggering transition, cycle state, source placement, and
visibility/light cause are unverified. Keep this separate from the report that
torch flames look weak and provide little immediate illumination. No fix or
acceptance is claimed; inspect the torch schedule and visibility/render path
under a controlled same-guard return before changing cycle logic.
## HARVEST-WORLD-29: persistent mushroom state and map admission

**Category/status:** Missing feature / In progress. Dedicated catalogue-bound
state is integrated in dev4 source, with 4,096 placement slots independent of
quest globals and sparse saved facts. It covers the source census of 2,083
supported base-master placements without claiming they are all converted.
Six original placements have candidate geometry and harvest catalogues across
nine real maps (54 resident copies). All nine retain prior map geometry and
collision and pass the current target heap estimate; native interaction is pending.

The small-mushroom converter now preserves shared material seams. The old
reduction lost 20/32/20 shared positions across the three sample meshes; the
candidate keeps original geometry and UVs. A focused old-control regression
fails while 28 candidate checks pass. Other flora modes remain unchanged.

The packaging fingerprint reader initially rejected the new AWH3 envelope.
It now accepts and binds the shared global catalogue, rejects incompatible
mixed map sets, and preserves the old no-harvest fingerprint. Nineteen focused
Docker checks include the real converter-to-fingerprint path. This was caught
before writing the native diagnostic images. The combined integration006 engine
passed 921 tests with four skipped; the later Python seam/fingerprint changes
have separate focused receipts and are not part of that frozen source snapshot.

Global map admission remains open: the current 24 plants/map bound is below
the 75-origin regional lower bound. Native picking, original quantity/name,
pickup sound, empty absence, cross-map return, save/load and target memory
acceptance remain required. No global shipped or delivered-dev4 claim is made.


## SAVE-EQUIPMENT-29: quickload returns with hands and torch put away

**Category/status:** Save/load state / Open observation, 6 October 2026.
In the exact v0.0.29-dev4 FS-UAE package check, the viewmodel query reported
hands state 2 and torch 1 before quicksave. After F9 quickload it reported
state 0 and torch 0. Mushroom inventory and picked state survived the same
load. Ordinary cell travel uses a separate transient hand snapshot; this report
is specifically about restoring equipment at a saved moment.

**Cause established:** the dev4 AWS3 writer records character/story/map state
but has no equipment-intent field. The actual save therefore contains no
historical hands/torch state for quickload to restore, and the new player starts
with zeroed equipment fields. Ordinary travel's transient snapshot does not
supply the state omitted from a save.

**Proposed correction and evidence:** an AWS4 candidate adds dedicated
validated equipment-intent flags, captures them through the existing transient
helper, and restores them before player spawn. It preserves AWS1/AWS2/AWS3
reading, defaults those older formats to unequipped, and rejects malformed or
unsupported flag combinations. The original dev4 negative control reproduces
the save/restore assertion failure; the candidate passes three save/character/
harvest checks and a global compatibility suite covering legacy decoding,
maximum size and malformed inputs.

**Current gate:** the candidate has not passed native quickload or full
integration. Verify hidden hands, fists, torch, weapon and weapon-plus-torch
across save/load, then confirm compatibility and native behavior. No accepted
integrated fix or release is claimed.
## HARVEST-WORLD-29: bounded dev4 native pickup result, 6 October 2026

One original Luminous Russula showed its name and E: Pick, then displayed
"Picked up 1 Luminous Russula." and disappeared. The prompt also disappeared
when aiming away. Repeated E did not grant another item. Actual packaged
character and save codecs decoded manual save generations 5 and 6 with one
Russula ingredient and one picked plant in each, retaining the same six facts
and content identity. A real-selector trip from sn007 to sn032 and back,
followed by F9 restore, retained the picked plant's absence and quantity.

This is one native interaction in the six-placement pilot. None of its six
plants resolved naturally empty in this run, so native empty-plant acceptance
remains open. Worldwide placement, dense-map admission, walked-boundary tests
and broader target memory coverage remain open. The intro_docks memory warning
was not exercised by the head-selection shortcut used in this run.

## AUDIO-ENTER-29: sub-second soundtrack cut on Enter

**Category/status:** Audio regression report / Open, 6 October 2026. The
reported affected package is v0.0.29-dev4; the earliest introducing build is
unknown and independent native reproduction is pending. Enter reportedly cuts
the soundtrack for less than a second when opening race/head selection and at
the intro prompt "Enter to follow the guard." Reported negative cases are
exiting character selection, Census attribute and starsign menus, and final
confirmation. No cause or fix is established. Check explicit stop/restart calls
separately from audio-service starvation during Enter-triggered work. Preserve
the intentional world pause while audio continues; do not add a fade or global
latency change to hide the symptom.

## TORCH-HAND-NORD-29: detached-looking grip fragment in dev4 (OPEN)

The Nord screenshot/close-ups show a detached-looking fragment at the left torch
grip. Dev4 still ships the reduced legacy model, not the topology candidate.
[Exact package findings, pose and acceptance](BUGS-v0.0.29-RC1.md#torch-hand-nord-29-detached-looking-grip-fragment-in-dev4-open).
**Fixed: N; final-release blocker.**

## HUNK-RESERVE-SN012-29: dev4 warning below 2 MiB (OPEN)

The `sn012.bsp` first-presented diagnostic has1,940,480 B clearance, below the
2MiB target. Current supplied reproduction vicinity is-11510,-73406,123.
[Full measured fields, limitations and memory work](BUGS-v0.0.29-RC1.md#hunk-reserve-sn012-29-dev4-warning-below-2-mib-open).

## Debug flame feedback and renderer-metadata warning: dev4 follow-up

Style2 is confirmed in playtesting. Setter confirmation is added to the next
source candidate. The reported flame disappearance occurs with sampled
`hands state 2 goal 1 frame 5 torch 1`; the shaft is visible beneath the console.
Full-viewport flame acceptance remains open. The independent native render-range
reader recognizes `aw_render_ranges`, while generic field parsing warns.
[Details and required checks](BUGS-v0.0.29-RC1.md#debug-flame-feedback-and-renderer-metadata-warning-dev4-follow-up).


## 6 October 2026: bounded native lighting and exact-storage progress

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
