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
