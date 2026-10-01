# Implementation journal: mappings, failures and decisions

Started 27 September 2026, after v0.0.13-dev1 / checkpoint-014. Record a finding
when it changes a design or exposes an assumption. Append later corrections
instead of erasing old results. Keep rejected trials and their evidence.

Entry format: **symptom -> confirmed cause (or hypothesis) -> change -> first
fixed version -> evidence -> regression check -> remaining limitation**.
Distinguish host tests, native tests and owner confirmation. Never assign a fix
version to an unresolved hypothesis. Raw extracts, screenshots and source lookup
tables remain private; public notes describe the mapping. Untried proposals live
in [IMPLEMENTATION_IDEAS.md](IMPLEMENTATION_IDEAS.md).

Area chapter: [Seyda Neen, arrival ship and opening tradeoffs](journals/SEYDA_NEEN.md).

## Index

- [J024 — initial NPC support and incomplete overlap collision](#j024--initial-npc-support-and-incomplete-overlap-collision)
- [J025 — RC2 gallery and bounded geometry exceptions](#j025--rc2-gallery-and-bounded-geometry-exceptions-1-october-2026)
- [J026 — completing the missing gallery appearances](#j026--completing-the-missing-gallery-appearances)
- [J027 — pale faces mapped back to sky grey](#j027--pale-faces-mapped-back-to-sky-grey)

- [Verified mapping at checkpoint-014](#verified-mapping-at-checkpoint-014)
- [J001 — later pier faces disappeared](#j001--later-pier-faces-disappeared)
- [J002 — restored geometry exposed capacity and cache limits](#j002--restored-geometry-exposed-capacity-and-cache-limits)
- [J003 — a hatch appeared without its ship](#j003--a-hatch-appeared-without-its-ship)
- [J004 — movement stuck far from visible architecture](#j004--movement-stuck-far-from-visible-architecture)
- [J005 — tight movement was partly a scale mismatch](#j005--tight-movement-was-partly-a-scale-mismatch)
- [J006 — playlist advanced but the same file played](#j006--playlist-advanced-but-the-same-file-played)
- [J007 — door panels disappeared behind walls](#j007--door-panels-disappeared-behind-walls)
- [J008 — coordinates were drawn but the display stayed stale](#j008--coordinates-were-drawn-but-the-display-stayed-stale)
- [Updating this journal](#updating-this-journal)
- [J009 — arrival assembly, collision and cache pressure (checkpoint-015)](#j009--arrival-assembly-collision-and-cache-pressure-checkpoint-015)
- [J010 — console contrast, typing and font (checkpoint-015)](#j010--console-contrast-typing-and-font-checkpoint-015)
- [J011 — incomplete terrain/rock formation (open)](#j011--incomplete-terrainrock-formation-open)
- [J012 — hollow ship rooms and collision stack (checkpoint-016)](#j012--hollow-ship-rooms-and-collision-stack-checkpoint-016)
- [J013 — lightmap UVs, links and test-state mistakes (checkpoint-016)](#j013--lightmap-uvs-links-and-test-state-mistakes-checkpoint-016)
- [J014 — eye height, hands and repeatable reports (checkpoint-016)](#j014--eye-height-hands-and-repeatable-reports-checkpoint-016)
- [v0.0.15-dev2: curved interior shell and placed deletion](#v0015-dev2-curved-interior-shell-and-placed-deletion)
- [28 September 2026: UI checkpoint preparation](#28-september-2026-ui-checkpoint-preparation)
- [2026-09-28: actor poses, escort and palette work (0.0.18-dev2 candidate)](#2026-09-28-actor-poses-escort-and-palette-work-0018-dev2-candidate)
- [v0.0.18-dev2 native checkpoint result](#v0018-dev2-native-checkpoint-result)
- [v0.0.18-dev3: alias cache and front-end palette](#v0018-dev3-alias-cache-and-front-end-palette)
- [v0.0.18-dev4: ship corrections, movie support and branding](#v0018-dev4-ship-corrections-movie-support-and-branding)
- [v0.0.18-dev5 — UI redraw, entrances and compile workers](#v0018-dev5--ui-redraw-entrances-and-compile-workers)
- [v0.0.19 — routine OST notice respects debug visibility](#v0019--routine-ost-notice-respects-debug-visibility)
- [J015 — opening invisible barriers crossed the plank (v0.0.21-dev1)](#j015--opening-invisible-barriers-crossed-the-plank-v0021-dev1)
- [J016 — dock approach used mismatched actor anchors](#j016--dock-approach-used-mismatched-actor-anchors)
- [J017 — scripted room was omitted as an activator](#j017--scripted-room-was-omitted-as-an-activator)
- [J018 — paper contrast and lost wall-art detail](#j018--paper-contrast-and-lost-wall-art-detail)
- [J019 — independent fighting gates, target hints and container contents](#j019--independent-fighting-gates-target-hints-and-container-contents)
- [J020 — repeatable room standing-hull audit](#j020--repeatable-room-standing-hull-audit)
- [J021 — door-shaped cuts remove redundant runtime geometry](#j021--door-shaped-cuts-remove-redundant-runtime-geometry)


## Verified mapping at checkpoint-014

| Input / identity | Current representation | Limit / next work |
| --- | --- | --- |
| Exterior CELL and LAND | Source-cell coordinates, quarter-scale local terrain and resident compiled scene | Bounded coverage; source cells are not future RAM chunk sizes. |
| STAT/DOOR base records and placements | Shared mesh variants, transforms, textures and approximate collision | Doors render but do not load interiors. Origin-only selection misses boundary objects. |
| Supported foliage | Baked sprites | Not proof that every plant/material is supported. |
| NPC/body/outfit/skeleton records | Host-assembled appearances baked into sampled MDL poses; three placed actors share two idle appearances | No runtime skeletal system, walking or arbitrary equipment changes. |
| First-person body/animation records | Nord hand poses for idle/draw/lower/punch | Follow source references, including shared meshes; no damage or stamina yet. |
| Ordered dialogue INFO records | Private lookup preserving conditions, links, scripts and sound paths | Candidates are not eligible responses; native speech uses one Hello per appearance. |
| Music and selected voices | Host-resampled PCM; streamed music and selected voice auditions | No guarantee of glitch-free playback at stock speed. |
| ACTI ship hull | Identified, omitted by current scenery type/cutoff selection | Ship assembly repair is open. |
| CONT records and placements | Planned audit/conversion | No native container/inventory state; see CONTAINERS.md. |
| Interior CELL and DOOR destinations | Planned separate scene and safe handoff | After exterior acceptance; state must survive geometry unloading. |

See [pipeline](PIPELINE.md), [world mapping](WORLD_MAPPING_PLAN.md),
[NPC research](OPENMW_REF_NPCS_AND_DIALOGUE.md) and
[dialogue lookups](DIALOGUE_LOOKUPS.md). Model drawing does not itself supply
Morrowind's actor assembly or game rules.

## J001 — later pier faces disappeared

- **Symptom:** dock planks were absent despite being in converted geometry.
  View-dependent changes resembled a visibility/depth fault.
- **Confirmed cause:** unsigned BSP face-plane indices above 32767 were
  sign-extended. The original scene contained 34,643 planes.
- **Fix/version:** unsigned decode plus plane-lump bounds validation,
  v0.0.13-dev1 / checkpoint-014. No wider field or bank switching needed.
- **Evidence/regression:** actual-loader boundary fixture and same-camera native
  pier comparison in [checkpoint-014](CHECKPOINT_014_VALIDATION.md). Retain 32767,
  32768 and maximum/bad-index cases. Locally verified; owner pending. The separate
  shack-wall report remains open.

## J002 — restored geometry exposed capacity and cache limits

- **Symptom:** correct dock views exhausted edge/surface pools.
- **Confirmed cause:** 8192 surfaces / 16384 edges could not hold the restored
  geometry. A trial at 16384/32768 consumed an extra 1 MiB within the fixed heap
  and repeatedly evicted actor/hand model caches.
- **Fix/version:** 10240/20480, adding 256 KiB, in v0.0.13-dev1. Acceptance peaks
  were 8587/17167 with zero overflow and one load per actor/hand model.
- **Regression/limit:** measure overflow and cache reloads together at matched
  cameras/coverage/fog. Larger buffers alone are not an optimization; new views
  need measurement. See [performance history](OPTIMIZATION_HISTORY.md).

## J003 — a hatch appeared without its ship

- **Symptom:** orphan hatch and missing hull at the port.
- **Confirmed causes:** the hull is ACTI, while the scenery filter accepts STAT
  and DOOR; its origin also exceeds the cutoff. The hatch is a supported DOOR
  inside the bounds. Both omissions must be addressed.
- **Planned remedy:** explicit visible-ACTI support, transformed bounds selection
  and assembly dependencies for hull, hatch, cabin, gangplank and opening actors.
- **Status:** identified after checkpoint-014; **not fixed**.
- **Evidence/regression:** owned-master audit summarized in
  [area scope](SEYDA_NEEN_SCOPE.md). Test arrival and post-registration states
  separately. Missing geometry does not prove departure logic was implemented.

## J004 — movement stuck far from visible architecture

- **Symptom:** an apparently empty town-square spot blocked the player.
- **Confirmed cause:** expanding only facet planes of acute/thin convex pieces
  could create distant solid extensions.
- **Fix/version:** six axial bounds on expanded architectural hulls in
  v0.0.12-dev2 / checkpoint-013. Keeping point hulls unchanged avoided the extra
  memory of an early candidate. Owner confirmed the central square repaired.
- **Regression/limit:** retain the exact route and hull fixtures in
  [checkpoint-013](CHECKPOINT_013_VALIDATION.md). Bad host samples are not a count
  of proven gameplay traps; other approximate collision still needs testing.

## J005 — tight movement was partly a scale mismatch

- **Symptom:** narrow approaches/stairs felt restrictive; idle slopes drifted.
- **Confirmed causes:** inherited player bounds were about 2.2 times too wide at
  quarter scale; ground-support and step handling also needed repairs.
- **Fix/version:** scaled humanoid dimensions and rebuilt world hulls, plus
  support/step repairs, v0.0.12-dev1 / checkpoint-012. Walking bob retained.
- **Regression/limit:** untouched startup walking before recovery, narrow
  approaches, stairs both ways and idle slopes. See [movement](PLAYER_MOVEMENT.md)
  and [checkpoint-012](CHECKPOINT_012_VALIDATION.md). Entity size alone is
  insufficient; later architecture correction is tracked separately in J004.

## J006 — playlist advanced but the same file played

- **Symptom:** repeated title track despite changing playlist IDs.
- **Confirmed cause:** native numeric filename formatting opened track00 for
  different small IDs; this was not solely a shuffle fault.
- **Fix/version:** construct digits directly and log actual filenames/progress,
  v0.0.11-dev2 / checkpoint-009. Distinct complete songs were verified.
- **Regression/limit:** actual opens, natural completion and history controls,
  not just playlist counters. See [checkpoint-009](CHECKPOINT_009_VALIDATION.md).
  Deadline misses remain a separate issue; zero read errors is not clean audio.

## J007 — door panels disappeared behind walls

- **Symptom:** frames remained while panels disappeared at certain views.
- **Confirmed cause:** overly broad depth band in the reproduced near-door case.
- **Fix/version:** narrow 1% to 0.001%, v0.0.11-dev3 / checkpoint-010. No draw-last
  override that would display doors through nearer walls.
- **Regression/limit:** matched cameras with panel/frame/foreground geometry;
  [checkpoint-010](CHECKPOINT_010_VALIDATION.md). Do not reuse this diagnosis for
  the open shack-wall report without reproducing it.

## J008 — coordinates were drawn but the display stayed stale

- **Symptom:** reserved coordinate strip did not reliably refresh.
- **Confirmed cause:** drawing changed the chunky buffer outside the normal
  viewport, but the Amiga update path copied only the viewport.
- **Fix/version:** include the strip in updates while visible, v0.0.13-dev1.
- **Regression:** move with coordinates enabled, toggle overlays, and check both
  buffer content and update rectangles. Offscreen drawing is not display proof.

## Updating this journal

Include runtime/pipeline version, source/build hashes, camera/route, hardware
profile and evidence location when relevant. Keep public fixtures synthetic.
Link [playtest status](PLAYTEST_STATUS.md) for owner acceptance and
[optimization history](OPTIMIZATION_HISTORY.md) for measured comparisons.
Do not replace a prior failure with a later pass: explain what changed.

## J009 — arrival assembly, collision and cache pressure (checkpoint-015)

- **J003 follow-up:** select the complete named hull/gangplank/hatch/cabin assembly,
  admit its specific ACTI and use assembly bounds. Synthetic tests reject missing,
  deleted and ambiguous members. Unrelated object coverage is still bounded.
- **Failed intermediate:** the old alias stage tried to squeeze the hull into a
  600-face MDL budget even though the final BSP pass would replace it. Grouped
  static geometry now goes straight to the BSP pass; retain failure evidence.
- **Measured conversion:** 5908 visible ship triangles produced 9976 BSP surfaces.
  Material/component-aware host reduction plus 32-pixel material textures gives
  1954 triangles / 3931 surfaces. UV projection is approximate; fine-detail texture
  baking remains future work. This is not a native FPS claim.
- **Collision mapping:** the unnamed hidden RootCollisionNode holds 581 authored
  collision triangles. Converting it separately produces 60 approximate convex
  pieces rather than 217 from visible detail. Fixture checks hidden-node exclusion
  from visuals, collision inclusion and accumulated transforms.
- **Native failure:** the 8 MiB trial reached 7,927,984 hunk bytes; a 253,632-byte
  cache allocation failed during the acceptance route. Retain the failed run.
  Set the reservation to 9 MiB inside the unchanged 16 MiB Fast configuration,
  with matching contiguous-memory preflight/reporting. No silent hardware upgrade.
- **Evidence/limits:** [checkpoint-015](CHECKPOINT_015_VALIDATION.md) records final
  native deck movement, cache openings, surfaces, audio and memory. Scene residency
  still needs bounded chunks; a larger heap is not an offloading strategy.

## J010 — console contrast, typing and font (checkpoint-015)

- **Owner report:** the console backdrop seemed to appear/disappear and text was
  hard to read. Its old color could blend into sky; the exact reported flicker
  cause is not isolated. Do not call that a proved cache or transparency bug.
- **Change:** fill all visible console rows with a solid palette color every draw,
  default black. No alpha pass or extra framebuffer. Validate named/RGB settings.
- **Typing:** add bounded `debug`, `dbg`, `amiwind debug` dispatch over existing
  handlers, reject command-separator injection, retain underscore forms. Help is
  a small resident command table. No per-frame disk dictionary needed.
- **Font:** original 5x7 readable glyphs in existing 8x8 cells; preserve the previous
  atlas on disk as retro. Validate file size/read before replacing the active
  16 KiB atlas. Font changes are explicit disk reads; normal text/background draws
  do not read disk. Synthetic tests and native open/close/switch checks are retained.

## J011 — incomplete terrain/rock formation (open)

- **Owner report:** two checkpoint-014 views show an incompletely drawn formation
  beside the road. The second view clarifies the first; this is not classified
  as an intended overhang or a creature.
- **Cause:** unknown. Needs same-camera original LAND/placed-rock comparison and
  converted topology/coverage/visibility audit. Do not apply the pier fix by analogy.
- **Next evidence:** `dbg coords on`, `dbg pos`, camera direction and source mapping.
  No fix version assigned. See [playtest status](PLAYTEST_STATUS.md).

## J012 — hollow ship rooms and collision stack (checkpoint-016)

A convex enclosure of the authored collision shell filled the room. Converting
actual wall/floor surfaces to thin prisms preserved empty space, but 1,205 shell
pieces exposed deep same-side recursion in hull traversal and a native boot
failure. Iterative same-side descent boots the same geometry; segment-splitting
recursion remains. A 24,000-node/256 KiB host-stack regression covers the chain.

## J013 — lightmap UVs, links and test-state mistakes (checkpoint-016)

Constant UVs have no invertible surface mapping: use a face-centre light sample.
Linked door coordinates can start the standing head inside a hatch: bounded
downward/local floor search is necessary. Scene-use math must supply real right
and up vectors because the inherited AngleVectors routine does not allow null
outputs; a fixture exposed the null-pointer fault before final testing.

Earlier automation typed commands into gameplay because map loads close the
console. Another trial pressed E while still in noclip, so it flew rather than
using the hatch. Neither counts as an activation pass. Corrected final routes
exercise both walking-mode links and retain the failed evidence.

## J014 — eye height, hands and repeatable reports (checkpoint-016)

Collision dimensions did not justify the prototype eye height. Sampling the
first-person camera and Nord scale raises the nominal eye about 10.5% without
changing the successful footprint. Local view-height precision avoids the old
network-byte truncation. The actual animated original view still needs comparison.

Hand drawing moved after fog; brighter 3D lighting and a separate sprite build
are experiments, not proof that every flicker is fixed. Preserve the source 3D
model, coverage report and independent hands timer. Record geometry and collision
choices as conversion policy; see CONVERSION_RECIPES.md.

## v0.0.15-dev2: curved interior shell and placed deletion

- Symptom: hull panels intersect hammocks, stretch textures and obscure stairs.
  Cause: the same aggressive LOD ratio used on decorative detail also reduced
  structural curved surfaces, and nearest-triangle UV projection amplified the
  distortion. Same source transforms rendered correctly without that reduction.
  Repair: carry source shape names through the exporter and preserve selected
  structural material groups with their exact UVs. Reject unknown requested
  shape prefixes. Native fixed views improve; collision/complete stair-route
  acceptance and exact original lighting remain separate checks.
- Host audit fixture: a DELE inside a placed CELL reference must not delete the
  entire cell. Restrict cell-level deletion detection to the header before FRMR;
  then process each placed deletion separately. The new vicinity tests caught
  this mistake; real base-master audit counts remain unchanged after repair.
- Scene menu: command matching for `scene change` precedes generic `scene`.
  Cancel restores the previous input destination; selection clears held buttons
  and queues the existing bounded scene loader. No second world remains resident.

Live Options trial: the Amiga numeric label showed zero despite correct slider
state. Host tests did not catch the target formatting difference. Use explicit
long values/formats, as in existing coordinate HUD output, and verify visible
values natively (675 → 665 → 664 → 700). This affects diagnostics, not the fog
value itself. Preserve the failed screenshots and final native acceptance.

## 28 September 2026: UI checkpoint preparation

### Baseline and recovery

The owner's `amiwind-2026-09-28_045110.zip` contains v0.0.17 and is the source
baseline. All 162 original host tests passed before edits. Do not restart from
v0.0.15-dev2 source just because those playable/recovery archives are attached.
The older playable still provides a geometry/data comparison, not current code.

Attempted recovery downloads and SDK extraction hit storage pressure. The
previous development workspace still contained the complete validated SDK,
map tools, compiler, emulator and owned input set. Reused those tools read-only;
new source, build output and checkpoint candidates remain separate. Several
recovery downloads reported HTTP 502; that is not proof that their archives are
corrupt. Temporary duplicate recovery data were removed or relocated after the
originals were located. No historical release was overwritten.

### Font and UI decisions

The independent preserved font-study reader was promoted into a public converter
without artwork. A first font-format inspection used a 284-byte glyph offset;
that was wrong: 284 is the name field size, preceded by the 12-byte header, so
glyphs begin at byte 296. The retained study and format reference agree. Native
assets use validated packed 2-bit coverage and per-glyph proportional metrics.

The first dialogue animation targeted a position above the bars, which would
cover rendered world pixels. Owner clarified that the panel belongs entirely
inside the unused lower strip. Corrected the target: starts off-screen at the
screen bottom, ends at the 3D viewport's lower boundary, temporarily replaces
bars. Long subtitles page inside that strip. The console remains top-opening
and retains its independent glyph/atlas selection.

A version bump without matching emulator preset filenames broke nine launcher
unit tests. Added new versioned presets while retaining historical ones; the
launcher checks passed again. The new native font boundary test initially used
`float` for the engine's `double host_frametime`; corrected the fixture type.
These were development failures, not shipped regressions. Native visual
acceptance and final checkpoint results are recorded separately after testing.

Native run 1 loaded the fallback instead of Magic Cards: the SDK's Amiga
formatted-output path treated `%d` as a word, so a 32-bit size argument produced
`magic0.awf`. Changed the filename format to `%ld` with a long cast; native run 2
loaded and displayed all three actual font sizes. The cream area outside the
320x200 display was hardware border color, not the engine's tile fill. Added
AGA/ECS border blanking via VideoControl, preserving palette index zero in game
textures. Moved an options footer back inside its border after the larger font
exposed an overlap. These fixes require another native visual check.

Native run 3 showed that VideoControl alone did not activate border blanking.
The AmigaOS graphics documentation requires rebuilding the screen viewport with
MakeScreen and RethinkDisplay after changing the ColorMap. Run 4 confirmed black
hardware margins. Font variants, lower-strip subtitle pages, original console,
menu/options and prison transition all passed the native visual checks. 163 host
tests pass. The existing world palette makes the original bar artwork muted;
a later conversion should reserve suitable UI colors before world quantization.
The main-menu background request arrived after these checks and is queued with
the next UI/intro work. It is not claimed by this checkpoint.

## 2026-09-28: actor poses, escort and palette work (0.0.18-dev2 candidate)

- Female ship guard failed the original male-only outfit gate. Added female skin,
  equipment CNAM with BNAM fallback, and female race proportions.
- Female animation file has no ordinary idle: use the shared base idle and the
  female walk override. Do not substitute idle4 or a male appearance.
- Walk groups contain root translation; baking those unchanged makes an actor
  slide away from its collision body. Remove XY root displacement while keeping
  vertical motion, and use authored loop start/stop rather than transition keys.
- Script Say paths end in WAV but the owned distribution supplies MP3. Resolve
  the same exact stem with MP3 fallback and record requested/resolved hashes.
- Four talk levels and blink use original relative morph targets. The mouth
  envelope follows native audio playback samples, not accumulated render time.
- First native run played Jiub, accepted a name, and then exposed a guard route
  block at the upper stair turn (-7,360,27). Do not teleport past it or call the
  escort complete. Testing collision-aware local steering next.
- The old scene palette uses indices 225..253 as duplicate sky colours. Audit
  BSP textures, alias skins, fonts, WAD graphics, hand spans and lighting tables
  before allocating those otherwise-unused slots to original status-bar hues.
  Preserve world pixels, lighting tables and console glyphs byte-for-byte.
- Ship scripts attach Boat Hull to two containers, not generic sound activators.
  Convert those two localized water loops, and retain their scripted volume.
  The recorded creak effects do not by themselves prove a prison-cell emitter.
- Camera comparison against the recompiled original snapshot found unchanged
  eye/NPC geometry; see PLAYER_MOVEMENT.md. The new reserved band moves the view
  centre upward. The first diagnostic queued noclip after aw_view via the command
  buffer, so placement was rejected; both captures remained at the same original
  spawn. Their comparison is valid at that spawn, not the requested debug pose.

- Sharing player movement initially stopped earlier: scripted actors still had
  MOVETYPE_NONE, so SV_WalkMove skipped its step path. Enable MOVETYPE_WALK only
  during the bounded movement trial and restore it afterwards. Use the moving
  entity's water-jump flags, not the global player, in shared stepping. Added a
  regression assertion for this mode and for complete rollback at a drop.

- The corrected movement mode let the guard descend to Jiub and play the first
  escort line in native run 6. Run 5's automated typing was not received; slower
  individual key presses made the test reliable. Do not treat a missed synthetic
  key sequence as proof of an intro-state failure.
- Sample blink at the maximum authored key, not the time-range midpoint: the
  midpoint did not fully close the lids. Reconverted all ten appearances.
- Include intro conversion in the guided build; a private hand-built scene alone
  does not make a source checkpoint reproducible by the owner.
- A debug reload of the same ship map must also clear old intro pointers/prompts.
  Reset the adapter on every non-New-Game scene spawn, including same-map reloads.

- Native run 7 reached the requested downstairs stop but stalled six units from
  the auxiliary final grid node, which lies beyond the stop against the player's
  hull. Accept arrival at the actual destination on the final graph leg instead
  of demanding an overshoot. Added a regression with a wall beyond the goal.
  This preserves collision and does not warp or shrink either actor.

- Run 8's return escort was obstructed by the diagnostic player camera placed
  directly in the lower aisle at (5,235,-8). Noclip does not remove that body's
  collision against NPCs. Keep scripted test cameras to one side and distinguish
  a test obstruction from a staircase defect. This is not a manual route test.
- Join a clear first path-grid leg directly, using a standing-hull sweep at the
  current floor height. Otherwise an escort may double back into its follower
  just to visit the nearest start node. Normal movement still checks floor and
  collision on every step. A regression covers a blocked backward start.

## v0.0.18-dev2 native checkpoint result

Final run 9 (engine revision 12, freshly converted actor revision 5) entered New
Game through the menu, accepted the name, played Jiub's responses, brought the
guard downstairs, enabled movement, climbed the stairs and completed both upper
travel targets. Guard state reached 70 with failed=0; the final instruction and
reminder voices played. Diagnostic player positions stayed beside the route to
exercise escort following/waiting without blocking it. This verifies NPC travel;
it does not certify a manual player walk through the complete hull/hatch.

The final native image also shows distinct bar colors and the optional frame.
172 host tests pass; full native cross-build and every HDF payload readback pass.
The legacy 9MiB heap and 16MiB Fast preset remain. Repeated alias-cache loads
add visible overhead: 2,374 frames over 225,908ms in this mixed diagnostic run,
with 3 late audio updates and no claim of glitch-free playback. Preserve this
receipt for a paired cache investigation; do not report it as a hardware benchmark.

## v0.0.18-dev3: alias cache and front-end palette

- Dev2 repeatedly opened Jiub/escort models every rendered frame. The exact
  alias visibility test first fetched the payload from the cache; hidden models
  could therefore evict visible models before being rejected. Preserve a sphere
  enclosing the entire packed quantization domain and reject wholly off-screen
  models before Mod_Extradata. Keep exact per-frame culling for survivors.
- The first native trial recorded Jiub=3, escort=2, upper=1 model opens across
  menu-to-intro play, eliminating the observed per-frame reload pattern. Do not
  quote a speedup percentage from different camera routes or timing.
- Mapping the original menu image through the world/status-bar palette made it
  too red. Give the front end a separate palette, retaining every UI atlas and
  text color index. Palette selection must itself trigger an update: changes in
  gamma/water/damage are not guaranteed on menu entry or exit. Tests also verify
  that the menu ignores stale gameplay tint and restores it when returning.
- Main Menu is a separate disconnected state. Escape there must not accidentally
  resume a nonexistent game; New Game leaves that state before starting the map.

Final dev3 native run confirms the original golden menu colors, disabled Load,
Options and New Game back into the ship with restored world colors. It accepted
the name and continued Jiub speech while the guard approached. Model opens remained Jiub=3, escort=2,
upper=1. 173 tests pass against the final source, which cross-compiles and passes
independent HDF payload readback.

## v0.0.18-dev4: ship corrections, movie support and branding

- Boot used the historical town-demo command even after the front end existed.
  Startup now runs the short project-logo fade, then the main menu. Menu music
  has its own canonical title identity and loops there; New Game starts the
  selected explore track 04 only after the prophecy movie. The original base
  CharGen scripts contain no music-change commands. This is not proof about
  hard-coded original-engine cue selection; ship/deck/Census parity stays open.
- The upper hatch origin is not a usable point target. Use source model bounds,
  reference transform and DODT/DNAM destinations. Audited 41 placements; activate
  only the two links with converted maps. Sounds/scripts are catalogued, not
  general door scripting. Keep one scene resident.
- A failed hatch trial was a test error: the camera was placed inside the hull,
  so disabling noclip was rejected and E continued to fly up. Another lost its
  pitch to view drift. Verify MOVETYPE_WALK and the actual camera angle. Native
  run 4 aimed from approximately (20,52,43), yaw270/pitch-26, displayed the hatch
  prompt and loaded the exterior. The return door also passed at about
  (695,-486,74), yaw217/pitch37. Both logs report checked arrivals. This proves
  activation and teleport placement, not a full manual walk of the escort route.
- The first target hint was accidentally placed only in the draw-dialog branch;
  move it into the ordinary HUD branch before speech, below the world viewport.
- Ship NPC bodies previously did not stop the player, although the player could
  stop the escort. Set body solidity for the three ship roles and explicitly
  wait when the route sweep hits the player. Reset failure timers while waiting,
  preserve the goal and resume when clear. Native run 1 reached guard state70,
  failed0 with diagnostic follower positions; deliberate blockage waited and
  resumed. Ordinary walking confirmed Jiub blocks passage.
- The flashing upper-right square was Draw_BeginDisc, not the old RAM warning.
  Pair begin/end only when aw_showdisk is enabled; default zero.
- Native run 1 still reopened escort and upper-guard models 992 times each. Raw
  MDL input in the high hunk and decoded staging in the low hunk consumed cache
  headroom. Read bounded alias inputs through transient heap storage and release
  decoded staging before allocating the final cache entry. Run 2 records escort1,
  upper2, Jiub1. Host loader tests poison freed staging and inspect decoded data.
  Do not quote an FPS multiplier: camera paths differ and world geometry remains
  costly. No actor rescaling, viewport change, barrel reduction or extra resident
  game heap was used.
- The first game-data ZIP had no video payload. The owner supplied Video files
  separately. Decode Bink on the host; AWV1 streams indexed frames and PCM with
  about 21KiB of picture/audio/palette buffers. A synthetic native fixture passed
  both EOF and Esc into Jiub. Original mw_intro.bik is 640x480, 57.5 seconds, with
  stereo 44100Hz source audio; the first target conversion is 160x100/10fps and
  mono11025Hz, 575 frames/9,834,738 bytes. Preserve aspect ratio with pillarboxing.
- Startup-logo completion/skip goes to the menu; prophecy completion/skip goes
  to Jiub. Sharing the stream reader must not conflate those continuations.
  Missing optional video warns during conversion/build and skips at runtime.
- Preserve the supplied 2048x682 transparent logo unchanged in resources/media;
  README scales its display. Derived startup frames and the upper menu composite
  are built separately. Public packaging allows only this explicitly named PNG,
  not arbitrary game art.

Final native image (engine revision9) plays the supplied logo's fade, presents
the branded menu with disabled Load, plays the original 57.5-second prophecy,
and reaches Jiub after both EOF and Esc. Movie PCM round-trip comparison is
byte-identical to an independent source conversion. 177 host tests pass; the
final 68040/FPU build matches its source-hash receipt and every HDF payload file
passes independent SHA-256 readback. The same 9MiB game heap and 16MiB Fast RAM
emulator preset remain; no physical-hardware playback or subjective audio claim.

The final post-movie ship run also reached guard state70, unlocked1, failed0,
using diagnostic follower positions through the original route. Preserve the
manual-route caveat; camera placement was used to control this test.

Movie counters in the final native run: startup logo 26/26 pictures, 2,573ms;
original prophecy 575/575 pictures, 57,822ms; zero skipped pictures in both.
Esc trial stopped at 5,791ms and reached Jiub. These are accelerated-emulator
observations, not a physical-drive throughput guarantee.

## v0.0.18-dev5 — UI redraw, entrances and compile workers

- Quake's `SCR_SetUpToDrawConsole` forces the console up before world sign-on.
  Preserve `con_forcedup` for renderer safety, but suppress visible console
  height by default and draw loading artwork. Archived `aw_transition_console`
  restores the old behavior at 1; 0 is default. Explicit F10 still works.
- Menu geometry alone did not fix the front-end confirmation: partial screen
  updates left the old lower menu visible. Every M_Draw now requests a full
  refresh. Labels, highlight rectangles and mouse hit regions share row bounds.
- Upscaling a 160×100 movie cannot recover burned-in lettering. Use 320×200,
  optional private native-font cards and a larger startup wordmark. Palette
  studies at 40×25 washed out narrow gold strokes and selected a blue movie
  color. Reserve the three exact text shades plus black before quantization.
- Auto jobs respect available CPUs/affinity/quota. Passing `-threads` to the
  pinned QBSP failed (unsupported option); only VIS/LIGHT accept that switch.
  Keep QBSP serial and use make -j for native compilation.
- Earlier door conversion intentionally hid unbuilt destinations. AWD2 keeps
  their bounds and names with unavailable target `-`; E reports the requested
  message instead of queuing a map. Preserve AWD1/legacy readers. Round then
  normalize yaw, since formatting 359.999999 as 360 would fail native validation.
- Read source interior cells directly and keep separate reference identities
  for multiple entrances into the same cell. A shared cell name is not enough
  to infer reciprocal doors. Current catalogue: 41 links, 22 exposed entrances,
  2 working transitions, 14 private source interior layouts.

Final dev5 checks:179 host tests and the68040/FPU build passed. FS-UAE played
all575 prophecy pictures in57.731s with no skipped pictures, then reached Jiub;
Esc also reached Jiub. Native hatch E loaded the deck with checked arrival.
The deck guard emitted one first line and five reminder events in the captured
run. Arrille's front door displayed its name and the exact missing-interior
message without changing scenes. Native reader accepted all22 entrance records.
Saved config confirmed the transition console, debug overlay and disk marker at0.
The maps are byte-identical to dev4; no camera/height change was made.

## v0.0.19 — routine OST notice respects debug visibility

The track opener still emitted an unconditional Con_Printf notice. Dev5's
gameplay draw gate was useful but did not stop that notification being queued.
Gate the routine notice with AW_DebugOverlaysEnabled at the shared track-open
path, covering startup, EOF, Next, Previous and group changes. Preserve the
event-log call and explicit status command. The player test checks silent
off-state transitions, enabled notices, runtime toggling and status availability.

Promoted this accumulated checkpoint to the owner's requested public v0.0.19
release, without a development suffix. The final version passed 179 host tests,
68040 compilation, complete HDF payload readback, and FS-UAE debug on/off/status
checks. Only the enabled Next event emitted a routine OST console notice; three
Next and two group events were still recorded privately.

## J015 — opening invisible barriers crossed the plank (v0.0.21-dev1)

- **Symptom:** owner report, 28 September 2026: walking from the ship toward
  the dock guard was obstructed and pushed the player into the sea.
- **Confirmed conversion defect:** the 22 original collision-only references
  had correct centres and extents, but compound rotations used `Rz @ Ry @ Rx`.
  Most side-wall thickness normals consequently faced world X. The placed
  object convention requires `Rx @ Ry @ Rz` for our column vectors and negative
  source angles. Compare the direct scene-node rotation in OpenMW 0.49
  `Misc::Convert::makeOsgQuat`, taking OSG's quaternion product convention into
  account. EditorMarker collision bounds were independently re-read from NIF;
  those bounds were already correct.
- **Candidate change:** v0.0.21-dev2 corrects the collision-only converter and
  rebuilds its private AWB1 data. It retains all 22 references, source positions,
  dimensions and conditional lifetime; it does not remove the enclosure.
- **Failed coverage:** the earlier native collision fixtures exercised identity
  and yaw rotations, and release conditions, but did not exercise the converter's
  combined pitch/roll/yaw or walk the actual plank. Passing those tests was not
  adequate route acceptance. The dev1 report remains a failed playtest.
- **Host evidence:** the actual runtime SAT sweep with the standing player hull
  and privately converted references hits two unintended walls along the old
  plank route. The corrected data passes the same four route segments without
  startsolid or allsolid. A synthetic ESM combined-rotation regression now checks
  a diagonal wall's expected thickness normal. Native state tests also keep the
  enclosure active across dock, race, office, courtyard and captain stages.
- **Validation status:** locally verified correction in v0.0.21-dev2; owner
  confirmation pending. In FS-UAE 3.1.66, debug setup placed the player at the
  hatch arrival, then ordinary walking crossed the deck/plank. Sustained lateral
  inputs hit both plank boundaries without falling into the sea. Continuing to
  the dock guard triggered speech and the appearance selector. This focused
  route is not a natural uninterrupted New Game-to-release acceptance run.
- **Reusable game rule:** see [persistent opening access conditions](CHARACTER_CREATION.md#persistent-rule-opening-access-is-conditional-world-state).
  Globals, journal indices, NPC locals, item checks and enabled references have
  independent lifetimes. Keep route passage, sideways containment and eventual
  release in the same acceptance plan. Jumping restrictions are separate again.
- **Build:** 93 native compiler warnings, no new diagnostic messages versus
  dev1; existing warnings and both intermittent freeze reports remain open.

## J016 — dock approach used mismatched actor anchors

- **Symptom:** owner says the dock guard does not catch the player as in the
  original. Character selection itself otherwise works in the owner's playtest.
- **Cause:** NPC native origin is at the feet; player native origin is at body
  centre. Comparing raw origins shrank the source108-unit approach sphere.
  OpenMW's GetDistance compares full 3-D reference positions; it is not a 2-D
  radius or hull-edge distance. Native quarter scale gives a27-unit threshold.
- **Candidate, v0.0.21-dev3:** compare both feet positions and use exact distance.
  Keep speech completion, menu completion, 1.5-second delay and follow-up speech
  as separate gates. Race acceptance does not remove the enclosure.
- **Evidence:** production opening-state test fails against dev2 and passes the
  candidate with undefined-behavior checks. It covers the exact boundary,
  vertical separation, automatic speech, movement-lock state, menu gating and
  later reminder. Focused native testing uses debug positioning followed by
  ordinary walking; it does not certify the entire natural opening route.

## J017 — scripted room was omitted as an activator

- **Symptom:** owner falls beneath the Census Office floor and sees a missing
  wall behind a cupboard. The precise later view is XYZ127/206/0, not the
  supplied OCR's127/266/0. A separate wall view is XYZ46/192/65.
- **Cause:** architectural reference172861, `chargen stuff room`, is ACTI using
  `i/In_C_plain_room_side.nif`. The interior selector rejected all unsupported
  activators, so an entire visible room segment and its floor collision vanished.
- **Original behavior:** CharGenStuffRoom issues one-time item/tutorial messages
  and tests GetStandingPC. Its script returning after CharGenState=-1 does not
  disable the geometry. Architecture and tutorial activity are separate facts.
- **Candidate, v0.0.21-dev3:** explicitly admit this audited ID/model pair, retain
  its source placement/reference and existing hollow RootCollisionNode pipeline.
  Unknown activators and editor markers remain outside this bounded adapter.
- **Evidence:** missing-floor fall reproduced in FS-UAE3.1.66 at127/206/0.
  Converted candidate collision has reference172861 under five room samples,
  including127/206. Synthetic selector regression covers the intended room,
  deleted reference, unknown activator and wrong model. Native result is recorded
  with the release evidence; owner acceptance remains separate.
- **Reusable lesson:** classify placed content by its visual/collision role and
  scripted lifetime. A script-bearing record type does not imply disposable
  geometry. Audit omitted structural references before accepting a new interior.

## J018 — paper contrast and lost wall-art detail

- **Paper cause:** noisy parchment and curled edges sit under small text; the
  proportional renderer used menu-gold antialiasing even for explicit black ink.
- **Candidate:** a white reading surface and black/gray glyph coverage, restoring
  menu ink afterward. Original font assets and converted artwork are retained.
  A real-renderer regression checks all three coverage values and restoration.
- **Wall-art cause:** the owned source class hangings use256x512 DDS textures.
  A32-pixel intermediate reduced them to16x32, then the BSP enlarged them to64x64.
  Verified source paths and hashes; the correct artwork had lost its detail.
- **Candidate:** retain up to128 pixels in the Census intermediate, producing
 64x128 class art before the existing64x64 final bake. Native texture dimensions
  stay bounded; this is not a global quality increase or a new asset pack.


## J019 — independent fighting gates, target hints and container contents

**Failed approach:** the global opening barrier condition also masked all attack
buttons until final release. Meanwhile draw/sheath was allowed earlier. Original
`CharGenDoorGuardTalker` enables fighting on paper acceptance. Preserve this as
an independent persisted fact; UI locks temporarily mask input, and future
status effects must remain separate. Host tests exercise ship/dock, hall,
courtyard, UI lock and final release. Native punch acceptance is recorded in the
release evidence rather than inferred from the test of permission alone.

**Failed approach:** returning "Empty" for every barrel interaction outside one
UI stage confuses progression with world state. Persist a placed-container
removal independently of inventory ownership; item transfer and depletion are
atomic. A synthetic save round trip retains both facts. Future loot/container
implementation must preserve this distinction and source-defined respawn rules.

**UI:** use a pure shared opening-target query for E and the small two-line prompt;
line of sight, range, hidden state and available action agree. Existing generic
QC greeting selection retains its cooldown and scripted-actor exclusion. Native
NPC dialogue remains a bounded greeting framework, not full dialogue trees.

## J020 — repeatable room standing-hull audit

`tools/audit_walkability.py` scans the actual compiled standing hulls, including
placed brush transforms. It classifies blocked/supported/steep/unsupported
samples and optionally follows connected surfaces within the 4.5-unit step limit.
It reports reachable unsupported neighbors and scan boundaries for inspection.
Finite samples are diagnostics, not proof against sub-grid holes or visual gaps.

On the Census room region X80..144/Y180..248, origin height75, drop20, spacing4,
old dev2 has128 blocked,84 supported and94 unsupported samples. Restoring room
reference172861 yields128 blocked and178 supported, no unsupported samples.
Probes127,206,75 and112,224,75 now hit that reference at origin Z64.825.
The connected fixed scan reaches175 of178 supported samples; isolated furniture
surfaces are not automatically treated as traversable routes. Do not patch every
flag with a box: investigate omitted source geometry, transforms and collision.


The later owner out-of-bounds view XYZ201,-210,0 is outside the restored room.
Both old and fixed BSP standing hulls at X201/Y-210 trace down to the outer
world enclosure at origin Z0.625; that is a catch floor, not a valid room floor.
This illustrates why a long downward hit alone cannot certify walkability.
Use a bounded drop for room audits and retain AW-20260928-20 until the escape
route is reproduced. Do not turn the enclosure hit into a recovery checkpoint.


## J021 — door-shaped cuts remove redundant runtime geometry

**Observation (owner, 28 September):** both Census exterior exits show wall
geometry protruding through the door. Reference camera: Seyda Neen XYZ396,-171,39,
yaw170,pitch-3, v0.0.21-dev2. The proposed benefit is less unnecessary geometric
work as well as a correct door surface; the actual FPS cost is unmeasured.

**Required experiment:** a host conversion tool creates a door-shaped cut-out
through the intruding/covered wall geometry, using the placed door's orientation,
aperture and bounded depth. Preserve the frame, surrounding wall, visible opening
and collision. Audit both door instances and record changed references/faces.
Expose `door_priority=true` as the planned default once implemented and validated,
with false retaining the original A/B baseline.
Removing redundant faces before runtime is the goal; a draw-on-top bias retaining
all geometry does not satisfy that goal. Compare original source geometry first:
a conversion-created obstruction should be fixed at its cause rather than masked.

**Status:** design/optimization observation, not a completed tool or fix.
Tracked by AW-20260928-21 and the high-priority graphics/culling roadmap section.
Do not add this to the lessons-confirmed-fixed list until the geometry and
same-camera rendering/performance checks support the result.


J021 owner refinement: leave a conservative margin concealed under the frame.
For a transition doorway whose opening is never revealed, a wall-coloured flat
backing rectangle can replace unnecessary covered depth. Preserve actual openings
for hinged doors. Planned assisted simplification defaults on, with a disable
switch; record it as design until the converter, config and acceptance exist.

Further owner clarification: "blank" only the concealed patch to the wall's base
colour/texture, beneath the door/frame margin. Do not blank or simplify exposed
wall detail. The reason is to omit geometry which cannot contribute to the view
from the runtime asset, reducing resident data and geometric work. Validate
concealment across door states and viewpoints before removal.


## J022 — accepted sub-cell loading presentation (30 September 2026)

The owner tested Balmora's v0.0.24-dev3 sub-cell transitions and explicitly
approved the frozen last frame with a small top-centred **Loading...** box.
Keep this as the default method for exterior sub-cells, including Seyda Neen.
Retain the existing blank-frame mode as an option. This acceptance concerns
the presentation, not asynchronous streaming: replacement remains synchronous,
with only one BSP resident and music serviced during loading.

Seyda Neen must use real sub-cells from the first ship-exit exterior entry.
The Census courtyard containing Fargoth's ring is an explicit separate area.
Reuse Balmora's shared coordinates, complete intersecting placements, overlap,
hysteresis, persistent state and arrival checks. Do not repeat facade loss by
clipping buildings at their origins or applying blanket mesh reduction.

New owner observation: pressing the old distance-1000 shortcut made the opening
pier view faster. Keep this as an open performance report until matched-camera
measurements reproduce it; do not infer that larger distances are always faster.
The intro_docks variant hides distant scenery and world marks but retained the
full BSP payload. True offloading must remove unreferenced geometry from the
loaded file, and performance claims need frame-time evidence.


The arrival-area design name is `intro_seyda_neen_subcell_pier`; its short BSP
filename remains `intro_docks.bsp` for the existing runtime/image workflow. The
owner's annotated circle guides a conservative polygon footprint retaining
whole intersecting objects and the Strider silhouette across the water.
A wider map-density study is explicitly deferred to the next version.


## J023 — Balmora dev3 acceptance and second stair report

Owner acceptance, 30 September 2026: Balmora's region/sub-cell approach works
surprisingly well and is a promising foundation for streaming the wider game
without disruptive scene transitions. Preserve the frozen frame and Loading...
box. This is acceptance of the current synchronous approach, not a claim that
asynchronous whole-world streaming is already implemented.

The owner also accepts Balmora's Silt Strider in v0.0.24-dev3: **leave its
geometry and conversion profile unchanged**. Earlier broken-Strider reports
are superseded by this confirmation.

New stair report: XYZ613,-125,59, yaw22, pitch-5, looks deformed. The camera is
beside placed reference 41159 (`ex_hlaalu_dsteps_03`) and building 22548
(`ex_hlaalu_b_04`). Keep this separate from the earlier blocked stair entrance
at XYZ925,-290,62, belonging to `ex_hlaalu_b_17` reference 32631. Source mesh,
conversion and walking collision need separate evidence before calling it fixed.

## v0.0.24-dev5: measured Balmora and ship follow-up

Separate native surface-order defects from collision volume defects. Add mesh
span depth crossings, authored stair shells with complete box bevels, the
checked road tile and torso-reduction coverage checks. Index the prison shell's
large collision union; matched lower-cabin server time falls from roughly 34 ms
to 1 ms while retaining the floor. See the dev5 investigation for failed trials,
walking endpoints, measurements and limits. Gold glyph coverage, appearance
arrows/Race focus, compact HUD, Hors preset, authored door sounds and rotated
hall-door targeting accompany the focused fixes. Preserve accepted Strider,
FOV/dimensions, Shift+V and frozen-frame loading behavior.

## RC1 — Balmora completion and repeatable conversion checks

Missing tower rooms came from applying an exterior distance cutoff around
local zero to complete interiors. A separate dressing filter dropped another
99 selected references. Remove the inappropriate cutoff for explicit complete
cell selection and audit reference IDs, not only visually representative rooms.
All 3,408 selected geometry references now occur once across 43 maps.

Stair failures had separate geometry/bevel and movement-classification causes.
An authored ramp normal Z=0.6976600289 was below the old 0.7 floor threshold.
The shared 0.69 threshold passes the measured ramp and rejects steeper surfaces;
player dimensions and FOV remain unchanged. Keep ascent/descent and arch
clearance checks distinct. See [recurrence guide](STAIR_RAMP_WALKABILITY.md).

The release packer exposed a third boundary: a 31-byte host-valid door filename
failed legacy Amiga FFS. Shorten producer and consumer together, retain backwards
lookup, preflight every payload component and preserve original source identity
in a generated mapping. [Amiga limitations](RELEASE_WORKFLOW.md#amiga-limitations)
is now a release-workflow requirement. Full findings, implications and validation
limits are collected in [Balmora lessons](BALMORA_CONVERSION_LESSONS.md).

## J024 — initial NPC support and incomplete overlap collision

**Symptom:** several RC1 Balmora residents visibly float; a broad settling pass
also risks moving some occupants below their visible platforms. **Cause:** source
placement Z is not proof of contact with converted geometry, and distant render
overlap can retain a platform whose collision is omitted there. **Change under
validation:** resolve initial placement in the owning sub-cell, copy it to every
overlap instance, classify initial support explicitly, and independently audit
final BSP/MDL contact on the host before packaging. Unknown states and unresolved
contact fail the build. See [the workflow](NPC_GROUND_CONTACT.md).

The first expanded mesh-contact audit also exposed a bookkeeping error: source
IDs were case-folded during lookup but some policy entries retained original
capitalization. Normalize the policy as well as the lookup; do not misreport a
known actor as a new unsupported case. It further flagged contact cases that an
origin-only floor trace accepted. Those require investigation, not relaxed
thresholds merely to obtain a green report. Native restore and overlap checks
remain separate evidence. Final release acceptance is still pending.

## J025 — RC2 gallery and bounded geometry exceptions, 1 October 2026

The disk-backed browser keeps eight rows only while open. Search and paging scan
on demand; ordinary play does not scan the catalogue. Gallery return uses a
captured supported save state, with the queued map load inserted before following
commands. Earlier queued-command checks exposed and corrected that ordering bug.
The return snapshot survives a missing-map attempt. F1 stays local to the gallery.

The original 2,000-vertex path is preserved. Extended models use a separate draw
frame bounded to 2,331 vertices, gated by an opt-in boolean, auto/numeric cap and
byte-specific per-model table. Three of 28 initially failing conversions fit the
777-triangle trial; 25 still fail rather than discarding protected shell geometry.
The source/engine baseline before this trial is retained with a checksum.

The owner requested an interim RC2 while these investigations continue. The
candidate reports its 23 open contact findings and reproducible walking stalls;
it does not assert a passed production placement gate or final visual acceptance.

Final native screenshot review found a browser-only formatting defect: friendly
names were blank while source IDs remained visible. The Amiga formatter's `%c`
path did not accept the int-sized prefix as the host libc did. Constructing that
prefix directly restored the friendly names; the final HDF screenshot verifies
both names and IDs. Host-only rendering stubs had not exposed this difference.

The matched loading comparison is retained in
[PERSISTENCE_AND_STREAMING.md](PERSISTENCE_AND_STREAMING.md). Disk reads and BSP
setup are measured separately from the complete visible transition. Across both
directions, method 2 and larger buffers did not consistently beat method 1.
Retain method 1 as the default and investigate lost return-prefetch reuse before
raising default RAM costs. Do not present partial-loader time as the visible pause.

## J026 — completing the missing gallery appearances

**Symptom:** RC2 leaves 25 appearances unavailable, while three earlier failures
fit its 777-triangle trial. **Confirmed cause:** protected torso/clothing panels
keep more triangles than the nominal allocation. Shrinking the rest of the body
does not reliably bring those shells below 777. A geometry-only scan finds that
all 25 fit within 980–1,012 triangles at the normal 480-triangle allocation with
shell protection retained. The geometry scan and complete conversion have slightly
different final counts; the completed asset receipt is authoritative.

**Change under final-release validation:** allow up to 1,024 triangles / 3,072
face-local vertices through the existing opt-in and exact-model allowance table.
Keep the original 2,000-vertex draw path and default-off extension. Reconvert all
28 exceptions at the normal detail allocation. Compact the gallery atlas before
MDL encoding so the intermediate texture does not breach the renderer's existing
skin-height limit. Numeric caps, including 777, remain restrictive choices;
`auto` admits only the explicitly recorded models within the hard ceiling.

**Evidence so far:** all 3,551 distinct assets now convert; the allowance audit
has 28 exceptions and zero unresolved models. All 28 loaded and rendered in the
native 68040 reference run, followed by gallery return: 861 recorded frames,
zero surface/edge overflow frames. This establishes availability and focused
native rendering, not individual visual acceptance of the entire catalogue.
The 47 host engine checks and six worker-budget tests pass. Final placement and
walking acceptance remain separate gates.

The worker planner also exposed a misleading memory estimate: a warm container
could count several gigabytes of clean disk cache as unavailable RAM and choose
one worker. Count reclaimable clean file cache while excluding tmpfs, dirty
pages and writeback. Retain the host memory ceiling, CPU quota/affinity and
quarter-headroom reserve. On this workspace that changes the estimate from one
worker to five, without treating the resident tmpfs game assets as spare RAM.

## J027 — pale faces mapped back to sky grey

*…and then their faces turned ashen.* What looked like a rough low-polygon
conversion was also a colour-pipeline fault. Fewer triangles and small texture
tiles can soften facial detail, but they do not explain warm pixels turning
blue-grey. The owner had seen the effect for a long time, especially on pale
Nords and Bretons; darker skin concealed it more readily.

**Symptom:** the owner reports longstanding grey blotches on pale faces, most
noticeable on Nords and Bretons. The RC2 screenshot identifies Sjorvar Horse-Mouth.
**Confirmed cause:** status-bar conversion repurposes palette indices 225–253,
previously duplicate sky colours. Later NPC conversions legitimately choose those
new warm entries, but the lighting and fog tables still describe the old sky
bank. At lighting level zero, even index 228 (RGB 209,183,171) maps to index 224
(RGB 102,119,136). The original facial texture itself is intact.

**Correction under final-release validation:** rebuild the 29 affected columns
of both lookup tables from the final palette. Preserve existing world-colour
columns. Full brightness and zero fog preserve each new index; distance fog
still converges on sky. Update existing palette receipts when reopening a build,
and reject stale lookups at image packaging. This is offline work: table sizes,
runtime RAM and per-pixel lookup cost do not increase.

**Evidence:** a synthetic regression catches the warm-to-grey substitution,
verifies unchanged columns and the final fog endpoint, and rejects malformed
tables. All four palette checks pass. Matched native Sjorvar views show the warm
skin restored; this does not certify every face, lighting condition or texture
seam. RC3 is the first release candidate containing this correction.

Dagoth Ur's separate mask and crest also receive an explicit geometry profile:
retain their original 240 and 47 triangles, plus the 30-triangle neck piece.
The resulting 903-triangle model uses the exact-model opt-in allowance, with
its original gold texture. Both source records share that appearance. The
isolated gallery is being checked with steady daylight for clearer inspection;
ordinary scene lighting retains its existing rules.

**Recurrence check:** treat palette, skins, lighting table and fog table as a
matched set. After reserving or changing any palette bank, regenerate dependent
lookup columns and verify their hashes before packaging. Test a pale face and a
darker face at full brightness, ordinary scene lighting and several fog depths.
Keep a source-texture sample and a matched native before/after view so geometry,
UV seams, quantization and stale colour tables can be distinguished. A larger
polygon budget is not a repair for a stale lookup table.
