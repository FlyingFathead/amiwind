# Playtest status by development version

Keep owner reports separate from local acceptance tests. A fix at one location
is not evidence that every collision/rendering issue is solved. New reports
append to the relevant version; do not rewrite earlier observations as passes.

<!-- contents start -->
## Contents

- [v0.0.24-rc1](#v0024-rc1)
- [v0.0.23-dev1 / parallel-build checkpoint](#v0023-dev1--parallel-build-checkpoint)
- [v0.0.12-dev2 / checkpoint-013](#v0012-dev2--checkpoint-013)
- [v0.0.13-dev1 / checkpoint-014](#v0013-dev1--checkpoint-014)
- [Reporting a regression](#reporting-a-regression)
- [New terrain/formation report, 27 September 20:55 Helsinki](#new-terrainformation-report-27-september-2055-helsinki)
- [v0.0.14-dev1 / checkpoint-015](#v0014-dev1--checkpoint-015)
- [v0.0.15-dev1 / checkpoint-016](#v0015-dev1--checkpoint-016)
- [v0.0.15-dev1 follow-up reports, 27 September 22:17–22:40 Helsinki](#v0015-dev1-follow-up-reports-27-september-22172240-helsinki)
- [v0.0.15-dev2 / checkpoint-017](#v0015-dev2--checkpoint-017)
- [Owner checkpoint-017 playtest, 27 September 23:28 Helsinki](#owner-checkpoint-017-playtest-27-september-2328-helsinki)
- [Latest owner playtest and default decision, 27 September 23:29–23:31 Helsinki](#latest-owner-playtest-and-default-decision-27-september-23292331-helsinki)
- [Final recovery handover update, 27 September 23:32–23:35 Helsinki](#final-recovery-handover-update-27-september-23322335-helsinki)
- [28 September 15:50 owner follow-up](#28-september-1550-owner-follow-up)
- [v0.0.21-dev1 regression / v0.0.21-dev2 correction](#v0021-dev1-regression--v0021-dev2-correction)
- [v0.0.21-dev2 owner follow-up / dev3 maintenance](#v0021-dev2-owner-follow-up--dev3-maintenance)

<!-- contents end -->

## v0.0.24-rc1

**AmiWind v0.0.24-rc1 — candidate for Welcome to Balmora.**

Balmora now includes 43 destination interiors (42 city interiors plus Tharys
Ancestral Tomb), 93 NPC placements (90 living and three authored corpses), and
80 living NPC voice sets. Original links cover 70 exterior entrances and two
additional same-room Fighters Guild links. All 43 maps passed native loading;
all 70 entrance/return routes and both internal links passed targeted native
checks. Ordinary walking checks cover the reported stairs/arches except the
unresolved positive-Y report. The exact stairs/rock wedge is also still open.

Full selected interior geometry is retained, including distant-origin towers
and previously omitted dressing. The checklist records stair collision and
slope classification, ground-material repairs, clearer gold e/H glyphs, shared
NPC targeting, the guard's final dock post and filename packaging corrections.
These are local checks, not owner acceptance of every route or the full game.

The accepted Strider, frozen-frame Loading... box, Shift+V, 90-degree FOV,
base player hull and race/sex eye heights remain. Balmora has 64 overlapping
regions; Seyda Neen has 25 regular regions plus the intro pier and ring
courtyard. Loading replaces a BSP synchronously. Background streaming,
whole-map polygon-density analysis, full NPC services, schedules, combat and
quest simulation remain future work. Greetings use a bounded authored fixture.

Stable v0.0.23 and the published dev5 prerelease remain unchanged. Final
v0.0.24 needs the owner's green light. See [RC scope](RELEASE-v0.0.24-rc1.md),
[complete checklist](INVESTIGATION-v0.0.24-rc1.md),
[conversion lessons](BALMORA_CONVERSION_LESSONS.md) and
[Amiga naming constraints](RELEASE_WORKFLOW.md#amiga-limitations).

## v0.0.23-dev1 / parallel-build checkpoint

Both TTF-present and bitmap-only builds compile and boot to the menu/prison
name prompt in FS-UAE 3.1.66 with the reference profile. Font receipts verify
automatic selection and filled bitmap paper ink. Movie skip works. The debug
town transition completes, but the following scripted Census command was not
confirmed and is not an acceptance pass. No full opening-route, hardware or
Windows test is claimed. Earlier intermittent freezes remain unresolved.
See [the release record](RELEASE-v0.0.23-dev1.md) for conversion comparisons,
build timings and remaining audio/interior work.

## v0.0.12-dev2 / checkpoint-013

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Invisible obstruction in the middle of Seyda Neen town square | **User-confirmed fixed** | Owner confirmation, 27 September 2026, 19:22 Helsinki. Local bounded-hull comparison also removed a reproduced remote solid spike; see CHECKPOINT_013_VALIDATION.md. |
| Standing startup, slopes and tested stair route | Local tests passed; owner said walking worked greatly | Preserve those routes in later acceptance. Other locations are not certified. |
| Door panels and town details | User previously reported working | Retain as regression coverage; exact earlier repair version was not supplied in that report. |
| Pier deck / abrupt walkway end | **Open** | Owner screenshots show missing surfaces and an abrupt end. Separate conversion bounds from clipping and source geometry. |
| Suspended geometry / incomplete Seyda Neen portion | **Open** | Owner screenshots, 27 September. Need exact camera coordinates and reference/terrain audit. |
| Blinking blue square | Identified as generated RAM-cache indicator | `showram` was enabled. Default-off change is staged for the next checkpoint, not retroactively delivered in dev2. |
| Shack walls disappearing at a specific viewpoint | **Open** | Owner screenshot, 27 September 2026, 19:34 Helsinki. Needs exact XYZ/yaw; do not equate every visibility fault with the pier fix. |
| Repeated NPC voice | Known prototype limitation | One preselected Hello sample per appearance. Full condition-driven selection not implemented. |

## v0.0.13-dev1 / checkpoint-014

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Missing pier deck faces | Locally reproduced and repaired | Unsigned 16-bit plane indices; same-camera native comparison restores planks. Owner acceptance pending. |
| Dock edge/surface exhaustion | Buffer budget adjusted | Restored geometry exposed the old limit. Final native counters are recorded in CHECKPOINT_014_VALIDATION.md. |
| Nord hands and punch | Visual prototype | F toggles draw/sheath; Mouse1 punches. No combat damage. |
| Escape menu | Implemented | Return and confirmed Exit; future options greyed out. |
| Blue RAM indicator | Default off | Underlying cache behavior is still measured. |
| Noclip flight / recall | Local focused acceptance | Full camera pitch, E/Q vertical movement, Shift speed and checked recall point 0; see checkpoint record. |
| Live coordinates/debug master | Implemented | Reserved bottom strip included in video updates; individual settings preserved. |
| Extended sea | Temporary placeholder | Z=0 flat surface, +/-2048 bounds, independently toggled with amiwind_debug_sealevel. Not actual surrounding map coverage. |
| Position-specific shack-wall disappearance | **Owner reports no longer reproducing** | 27 September, 20:37 Helsinki, latest checkpoint-014 playtest. Preserve the route; the exact failing camera and individual causal fix remain unconfirmed. |
| Abrupt land/object boundary | **Open** | Terrain/selected references remain bounded; expanding the sea does not fill missing land/structures. |
| Orphan ship hatch / missing hull | **Identified, not repaired** | Scenery filter omits ACTI hull; origin cutoff also excludes it. See SEYDA_NEEN_SCOPE.md. |
| Connected starting-area exteriors | Next major milestone | Port/islets/bridges/opposing shore/mainland approach; current bounded slice is incomplete. |
| Census and Excise interior | After exterior acceptance | Original linked doors and repeatable entry/exit are still to implement. |
| Town containers | Planned | Placement audit, visible conversion, then interaction and persistent contents; no native container logic yet. |
| Silt strider stop and creature | Planned | Opposing shore/approach is in scope; creature conversion and travel service are separate tasks. |

The private voice index preserves original conditions and ordered records.
Its actor lists are static candidates, not approved random-playback pools.
Native NPC speech still uses one Hello per appearance; varied native dialogue
is not implemented. Owner feedback is recorded per item above; this is not blanket acceptance.

## Reporting a regression

Include runtime version, area, XYZ from `amiwind_debug_coords on`, view direction,
what happened and the preceding action. Attach the preset or exact CPU/FPU/RAM/
ROM settings if changed. For collision add `aw_pos` and `aw_blockers`; for native
performance retain frame/music profiles. Keep the original image untouched and
play from a writable copy. Never put screenshots containing converted game data
or generated lookup tables into public source archives.

## New terrain/formation report, 27 September 20:55 Helsinki

Checkpoint-014 owner screenshots show a terrain/rock formation rendered
incompletely left of the road, with a pointed fragment and sky where the rest
of the formation is expected. The owner explicitly clarified that it should
not be described as an intended overhang. **Open, cause unknown**:
compare the source LAND heights, placed rocks and converted triangles at the
same camera before classifying it. Candidate checks: cell edge/corner indexing,
triangle connectivity/winding, large placed-rock bounds, omitted adjacent
geometry and depth/culling. The visible appearance alone cannot identify a
boulder or prove a terrain error. XYZ was unavailable to the reporter; the next
checkpoint provides `dbg coords on`, `dbg pos` and underscore-free recall.
Preserve this as a distinct issue from the fixed pier index defect and the
owner-reported improvement at the shacks. Private screenshot retained; no
commercial game image is included in public source.

## v0.0.14-dev1 / checkpoint-015

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Arrival hull/gangplank/hatch/cabin | Locally rendered | Named complete assembly; simplified exterior; opening state not executed. |
| Ship deck/gangplank collision | Bounded local check passed | Short deck walk and gangplank standing; not the entire opening route. |
| Console solid background/font/aliases | Locally verified | Typed commands, blue/black, retro/readable, close/reopen, dbg coordinates and long-prefix recall. Owner acceptance pending. |
| Actor/hand cache failure in 8 MiB trial | Final trial passed with 9 MiB heap | Same 16 MiB Fast hardware profile; failed run preserved. |
| Quit and amiWind relaunch | Locally verified twice | Focused same-session relaunch, hands and clean exit; no ERROR.TXT. |
| Incomplete terrain/rock formation | Open | Two owner screenshots from checkpoint-014; same-camera source comparison needed. |
| Low-light ship interior/day-night | Planned | No interior or daycycle commands active yet; see DAY_NIGHT_AND_SKY.md. |

## v0.0.15-dev1 / checkpoint-016

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Prison interior and both E hatch links | Local native pass | Both builds load/walk; final routes exercise both directions. No full opening quest or Census office. |
| Compact console, fullscreen, scrollback, overlay alias | Local host/native pass | Small default; normal and retained retro available. Finnish physical key mapping still needs owner confirmation. |
| Player eye height | Corrected prototype calibration | 33.0588 above feet; collision unchanged. Full original-camera parity not claimed. |
| DEG/pitch in coordinates | Implemented | Include both with XYZ for future visibility reports. |
| Hands blink/dark appearance | Partially addressed, still open for visual acceptance | Post-fog 3D drawing and optional sprite build; some sprite animation poses are empty/offscreen. |
| Deck/bow gaps and detached rail details | **Open** | Owner XYZ (804,-311,61), (615,-548,74), (777,-373,61), (790,-413,62). |
| Disappearing house | **Open** | Owner XYZ (-41,715,69). Ordinary scenery origin cutoff is an audit lead, not a confirmed cause. |
| Malformed terrain/rock formation | **Open** | Owner XYZ (235,596,29); source and converted topology comparison required. |
| Joined-plank pier and distant building backdrops | Planned A/B | Existing converter retained; no new flattening experiment claimed. |

Owner acceptance of checkpoint-016 is pending. Earlier user-confirmed fixes stay
recorded against their original versions.

## v0.0.15-dev1 follow-up reports, 27 September 22:17–22:40 Helsinki

Owner rejects lower hold: flattened hull intersects furnishings and hides the
stair route. Exterior formation persists at XYZ211/447/47 DEG4/P0; Silt Strider
port is a hypothesis. Owner also reports slower performance, occasional music
clicks and red/brown immersion. Preserve these as open until individually verified.

## v0.0.15-dev2 / checkpoint-017

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Curved interior hull / stair visibility | Local visual repair | Same-source reduction reproduces fault; structural preservation restores native views. Owner acceptance and continuous stair route pending. |
| Scene-picker popup | Host/native pass | dbg/debug/amiwind debug scene change, both choices and cancellation; missing files covered by host tests. |
| E links and music continuity | Native regression pass | Four successful scene transitions; no music read errors; audio late updates still occur. |
| Vicinity NPC/door/container lookup | Host audit complete | 15 exterior / 28 directly linked interior NPC references; no new native actors or interaction logic. |
| Exterior formation and Silt Strider omission | Open | Owner viewpoint reproduced; strider ACTI omission known, malformed formation identity not established. |
| Water color, damage/audio, slowdown | Open | Recorded in follow-up register; current inherited water tint is warm brown. |

Default 3D image only in this hotfix. Previous sprite experiment and exterior
method_001 remain preserved. See CHECKPOINT_017_VALIDATION.md.

Additional checkpoint-017 controls: live fog/draw-distance aliases, Options →
Graphics slider with 10/1-unit normal/Shift nudges, default700, and default-off
`dbg fps`. Earlier native slider testing exposed a readout-format issue; final
675→665→664→700 and FPS/overlay acceptance passed and is recorded separately in CHECKPOINT_017_VALIDATION.md. All latest
slow-view/ship/deck screenshots and hypotheses remain in SEYDA_NEEN_NEXT_STEPS.md.

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

## 28 September 15:50 owner follow-up

The Silt Strider-port defect persists in v0.0.19 at XYZ260/417/30, DEG11, P-19;
the strider and driver are still absent. Track as AW-20260928-03 in [BUGS.md](BUGS.md).
The v0.0.20 maintenance work does not close this scene-conversion issue.

## v0.0.21-dev1 regression / v0.0.21-dev2 correction

| Item | Status | Evidence / remaining scope |
| --- | --- | --- |
| Invisible opening walls obstruct plank and redirect player into sea | Owner-reported dev1 regression; dev2 locally verified correction | Compound rotation order corrected; original placements and state condition retained. |
| Deck/plank passage to dock race screen | Local FS-UAE 3.1.66 pass in dev2 | Debug setup at hatch arrival; ordinary walking thereafter, noclip off. Both lateral plank pushes blocked. Owner retest pending. |
| Full natural intro-to-release, every escape route and courtyard edge | Still open acceptance scope | A focused plank pass does not certify the whole opening. See journal J015 and CHARACTER_CREATION.md. |
| Compiler/host checks | 93 warnings, none new; 210 host tests pass | The new converter regression fails against the old code. Unrelated intermittent freezes remain open. |


## v0.0.21-dev2 owner follow-up / dev3 maintenance

Owner reports: dock guard misses interception; pier escape; missing Census floor
and wall; blurred hanging art; unreadable papers; downstairs doors unavailable;
punch fails after leaving the office; barrel falsely says Empty. Source-confirmed
causes/candidates and fixed Y/N/version fields are maintained in [BUGS.md](BUGS.md).

The selected default interaction layout is
[npc_interaction_layout_template_001](INTERACTION_LAYOUTS.md). The latest owner
console capture separately shows unbound MOUSE3/right click; attack is MOUSE1/left.
Repeated `No valid compatible save generation` messages in that capture need
exact selected-slot context before being treated as corruption: F9 requests the
quicksave slot and does not automatically select the latest autosave. Existing
saves are retained on failure. Keep this evidence in the private playtest bundle.

Host suite:215 passing tests. Native warnings:87, down from93, no new diagnostics.
The release evidence records focused FS-UAE checks; neither intermittent freeze
has a demonstrated fix and the complete natural intro route remains unaccepted.

Focused native checks cover automatic dock race interception, WASD choices,
clerk/class/birthsign/review, readable papers with paging, and hall-guard paper
acceptance followed by draw/left-click punch input. The final binary additionally
passes demo-mode barrel pickup, a second activation showing Empty, and left-click
punch input. These checks use debug positioning; they are not a continuous
natural-route playthrough. The final demo F5/F9 attempt was correctly rejected
before registration/release and is not evidence of a save/load pass. Persistent
ring depletion and released-state controls have host regression coverage.

The planned default-on door simplification is documented in journal J021 and
the graphics/culling roadmap. No conversion flag or speedup ships in dev3 for
that proposal. Only concealed wall patches may be simplified; visible wall
texture/shape and actual openings must remain intact.
