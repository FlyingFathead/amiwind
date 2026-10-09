# Trees and Grass, Day and Night

<!-- contents start -->
## Contents

- [RC1 Seyda Neen brightness discontinuity: cause isolated](#rc1-seyda-neen-brightness-discontinuity-cause-isolated)
- [v0.0.29 sky follow-up](#v0029-sky-follow-up)
- [Native playtest blockers and preview — 4 October 2026](#native-playtest-blockers-and-preview--4-october-2026)
- [Original night sky, Masser and Secunda — current candidate](#original-night-sky-masser-and-secunda--current-candidate)
- [Guard torches and the saved clock — current work](#guard-torches-and-the-saved-clock--current-work)
- [V3 sky and moving sun — current candidate, 4 October 2026](#v3-sky-and-moving-sun--current-candidate-4-october-2026)
- [Historical image009 / V1 status — 4 October 2026](#historical-image009--v1-status--4-october-2026)
- [Shared exterior background sky: implementation candidate](#shared-exterior-background-sky-implementation-candidate)
  - [Coverage and the fog marker](#coverage-and-the-fog-marker)
  - [Required converter and target acceptance](#required-converter-and-target-acceptance)
- [Cycle control and coordinated sky/fog candidate — 4 October 2026, 09:06 EEST](#cycle-control-and-coordinated-skyfog-candidate--4-october-2026-0906-eest)
- [Earlier V1 host and bounded native verification — 4 October 2026](#earlier-v1-host-and-bounded-native-verification--4-october-2026)
- [Historical pre-release gate after the static-link correction — 4 October 2026, 06:26:57 EEST](#historical-pre-release-gate-after-the-static-link-correction--4-october-2026-062657-eest)
  - [Static foliage links: image004 incident and image005 correction candidate](#static-foliage-links-image004-incident-and-image005-correction-candidate)
  - [Bounded native result and remaining visual defects — 4 October 2026](#bounded-native-result-and-remaining-visual-defects--4-october-2026)
- [One world clock, separate presentation](#one-world-clock-separate-presentation)
- [Source appearance: independent color profiles, texture layers and haze](#source-appearance-independent-color-profiles-texture-layers-and-haze)
  - [Use the Amiga palette creatively](#use-the-amiga-palette-creatively)
- [Historical first day/night sky milestone — 4 October 2026](#historical-first-daynight-sky-milestone--4-october-2026)
  - [Waiting and exact-time debug controls](#waiting-and-exact-time-debug-controls)
- [Remaining debug proposal](#remaining-debug-proposal)
- [Cheap visual candidates to measure](#cheap-visual-candidates-to-measure)
- [Acceptance route](#acceptance-route)
- [Recovered sky fallback and guard-torch request](#recovered-sky-fallback-and-guard-torch-request)
- [Earlier shared sky and regional environment review — 4 October 2026](#earlier-shared-sky-and-regional-environment-review--4-october-2026)
  - [Source references](#source-references)
  - [Owner-authorized reference audit: visual target without asset redistribution — 4 October 2026, 02:41 EEST](#owner-authorized-reference-audit-visual-target-without-asset-redistribution--4-october-2026-0241-eest)
- [Protected sunrise and sunset baseline for v0.0.29](#protected-sunrise-and-sunset-baseline-for-v0029)
- [Additive cloud controls: v0.0.29 development candidate](#additive-cloud-controls-v0029-development-candidate)
- [Dev3 midnight clearing mode — source candidate, 5 October 2026](#dev3-midnight-clearing-mode--source-candidate-5-october-2026)

<!-- contents end -->

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

## v0.0.29 sky follow-up

- **Night coverage:** dense cloud cover can hide moons, stars and nebula. A
  source-level cause is now confirmed: the legacy shared cloud-role validator
  rejects palette-role index 254, so the night overlay cannot use that role
  through the legacy mask. The v0.0.29 candidate adds a separate validated
  night-role map and keeps the legacy cloud-role mask, scaling and tint path
  intact. The dev3 source adds default-on midnight clearing independent of cloud
  control V1/V2, with the retained coverage available explicitly. Synthetic rendered-sky fixtures pass the candidate modes and protected
  legacy comparisons. The bounded native indexed-frame result below passes
  for one dry exterior pose; broader visual/performance acceptance remains
  open. Keep clouds, sky switches and moon/star/world occlusion in the
  comparison. See
  [SKY-NIGHT-COVER-29](journals/BUG_JOURNAL-v0.0.29.md#sky-night-cover-29-frequent-dense-night-clouds-hide-celestial-views-open).
- **Optional veil cloud type:** preserve existing cloud/sky types and defaults;
  add a separate sparse, rasterized/ordered-transparent variant. Keep cloud
  speed, clock, sun, interiors and toggles intact, with bounded rendering cost.
  This experiment alone does not establish a night-coverage policy correction.
- **Ash/blight study:** derive region probabilities and boundaries from owned
  CELL/REGN data and scripts; examine OpenMW transitions and NPC face-shielding.
  Red Mountain's requested treatment is strongly red sky and windblown ash,
  including source-supported storms outside Ghostfence. Exact affected
  settlements and NPC triggers remain a study, not an implemented claim.

See the complete [v0.0.29 fix and feature list](PLAN-v0.0.29.md), including lava
fields and their debug-map representation. Existing sky behavior below is kept
for comparison; weather/lava source data and derived artwork are not included
in the public repository.

v0.0.28 was published on 4 October 2026 after scoped native acceptance and hosted CI. The v0.0.29 follow-up below does not alter that release or claim all-map/physical-hardware acceptance.

## Native playtest blockers and preview — 4 October 2026

The pale foreground defect was traced to rebuilt LAND edge loops ordered opposite
to the native renderer convention. Reversing only those loops restored textured
ground in a matched-camera WinUAE check and the initial combined-engine town
replay. Broader independent routes remain pending; these views do not establish
whole-world acceptance. Cloud scrolling inherited Quake's fast rate on the 30-times game
clock. The latest correction scales only cloud phase by 1/300: one third of
the preceding `0.01` setting, without slowing the sun or passage of game time.

`dbg skyspeed [number]` reports or sets the cloud-speed multiplier, archived as
`aw_skyspeed`. Its default is `0.00333333333` (approximately 1/300 of the old
speed). At the normal game-clock scale of 30, this gives about 0.8 texture units
per second of engine real time instead of 240. `0.01` restores the preceding
candidate's rate, `0` stops cloud motion and `1` restores the old fast rate.
Changing the multiplier can reposition cloud patterns because phase is derived
from persisted time; zero selects the fixed phase zero. Finite values
from 0 through 100 are accepted; invalid input leaves the setting unchanged.
Sun position, palette transitions and automatic game time are unaffected.
The existing sky cache can reuse an unchanged integer cloud phase; a lower speed
does not itself establish a measured CPU or frame-rate improvement.

`dbg daycycle gallery` previews eight lighting stages in a camera tour, holding
each for eight seconds: dawn, sunrise, midday, golden hour, red
sunset, dusk, blue hour and night. It uses the selected sky style and current
sun/cloud switches. Escape, repeating the command or `dbg daycycle gallery off`
ends the preview; it also ends after the last stage or a map change. Opening
the console/menu pauses the preview. It never teleports the player or rewrites
the saved date/time, sky settings or cycle switch. Automatic clock advancement
is suspended during the preview, and cloud phase stays tied to the real clock.
On the tested Seyda Neen town BSP the tour uses the recorded scenic viewpoints;
other exteriors keep the current eye and change viewing direction only. Use
`dbg daycycle gallery here` to keep the current view throughout. Camera changes
are renderer-only and restored after each draw; the player and collision state
never move. Image015 captured and independently caption-reviewed all eight day-gallery stages; automatic completion and renderer-state restoration were observed. This is bounded gallery verification, not whole-world acceptance.

`dbg nightgallery` previews four eight-second stages at 23:00 on the saved
date: the current wide view, Masser, Secunda and overhead stars. It keeps the
current eye position in every scene and uses the same moon orbit calculation as
the renderer. A moon below the horizon gets a caption and the current view;
the tour never moves a moon or changes its phase to make it visible. Clouds,
scenery and the existing sky switches still apply. Add `here` to keep the entire
camera unchanged through every stage. Escape, command repetition,
`dbg nightgallery off`, the final stage or a map change ends the preview.
Console/menu pauses it. Saved time/date, player position and settings are preserved; cloud phase remains tied to the saved clock. Image015 captured and independently caption-reviewed all four night-gallery stages; automatic completion and renderer-state restoration were observed.

## Original night sky, Masser and Secunda — current candidate

The local converter now builds one bounded atlas from the owner's original
stars, three nebula textures and eight phase textures for each moon. The atlas
contains a 128 by 128 indexed night field, sixteen 24 by 24 moon tiles and a
2,048-byte star-role mask. The AWN2 file is 27,664 bytes on disk, including its
header and palette/payload checksums. The new mask adds 2 KiB to fixed atlas
storage; all sixteen moon tiles remain byte-identical to the earlier atlas.
It is generated privately; no commercial texture is included in public source.

`dbg starsky on/off` controls stars and nebula. `dbg nightsky on/off` controls
the complete night layer, including Masser and Secunda. Both accept `1/0` and
`true/false`, report their setting without an argument, default on, and persist
as `aw_starsky` and `aw_nightsky`. The existing master `dbg sky` switch still
applies. Disabling stars leaves the moons available when the night layer is on.

Stars are distant points in the shared background sky. The owned conversion
retains 163 source-derived point locations, each limited by projection to one
native screen pixel. The full source image is mapped into the valid upper-sky
domain, including overhead directions. These locations occupy only dark gaps in
the original nebula artwork; visible nebulosity stays in front with its original
alpha. Empty black background is keyed transparent (maximum source RGB component
16). Stars are background points, never foreground billboards.

Some bright points have a cool-blue tint and gentle twinkle driven by the saved
clock. Complete moon discs cover stars and nebula, including their dark phase
areas: an unlit moon is still solid, not a transparent hole. Both cloud layers
and opaque scenery cover the night sky; foliage holes may reveal it only where
the original sprite is transparent. The night layer is suppressed in interiors
and fades out in daylight. The eight original phase images follow a bounded
24-day approximation. Moon paths and relative size are source-informed artistic
approximations, not full OpenMW lunar/weather simulation.

The renderer uses fixed atlas/fade storage with no per-frame heap allocation.
Fifteen focused Linux fixtures for point size and occlusion pass, including one-pixel projection at 320 by 200
and 640 by 400, dark moon-disc occlusion, background transparency, depth isolation
and legacy-atlas upgrade handling. These fixtures do not establish native visual
acceptance. Image015 bounded native views confirmed both moons, stars/nebula and foreground geometry in selected actual-map scenes. Wider world coverage remains outside scope; measured minimum clearance is below the unchanged 2 MiB safety reference.
The initial AWN2 conversion removed enlarged stars but left most point locations
outside the sampled hemisphere and made the nebula too opaque. The current
`upper-diamond-original-alpha-v1` revision corrects both without enlarging the
atlas or changing the moon tiles. Seven focused converter checks pass; final
Image015 bounded native pixel inspection confirmed stars, nebula and both moons in selected actual-map views. Broader world coverage remains outside the tested scope. Older AWN1 or AWN2 projection data is
backed up and upgraded when owned textures are available; without them it is
retained with an explicit legacy warning, not reported as a current conversion.

## Guard torches and the saved clock — current work

Imperial guards in Seyda Neen and Hlaalu guards in Balmora use the same saved
clock through their original Guard class and torch inventory.
`guards_torch_cycle true` is the default archived policy; automatic exterior
use is strictly before 06:00 or after 20:00. `dbg guardtorch on/off/auto` forces
all supported guard types on or off, or restores automatic use. Boolean forms
also accept `1/0` and `true/false`. The gallery only previews sky presentation;
it does not change the actual time used by guard equipment.

The implementation uses original third-person torch pose and equipment assets,
with bounded flame and light counts. It does not add full NPC schedules,
inventory simulation or guessed interior/weather rules. Image015 passed scoped native guard, gallery and pressure checks. Minimum logged peak clearance was 1,812,304 bytes, below the unchanged 2 MiB safety reference; no production-memory pass is claimed. See [torch controls, original
use rules and budgets](TORCH.md#guard-torches-and-the-clock--scoped-native-verification-passed).

## V3 sky and moving sun — current candidate, 4 October 2026

**V3 is the default.** `dbg skytype 1` / `dbg skytype V1` selects the earlier
soft Clear-derived palette; `dbg skytype 2` / `dbg skytype V2` selects stronger
red twilight with a cool blue hour. `dbg skytype 3` / `dbg skytype V3` selects
"extra stronk": stronger warm contrast and dark low secondary cloud silhouettes.
Letter case is ignored for V1/V2/V3. With no
argument the command reports the selection; invalid values leave it unchanged.
The archived setting is `aw_sky_type`, shipped as 3. `dbg sky off` still restores
the original shared sky and baseline fog and suppresses the sun. Selecting a
profile changes presentation only: the saved clock, cycle pause and explicit
time-setting/wait semantics are unchanged.

`dbg sun` and `dbg clouds` accept `1/0`, `true/false` and `on/off`; both default
on and are archived as `aw_sun` and `aw_clouds`. Clouds off removes both cloud
layers while keeping the atmosphere, fog and sun. Sun off hides the disc/halo
while the shared clock continues advancing. Re-enabling either uses the current
clock immediately. `dbg daynightcycle off` instead freezes automatic time and
holds the current presentation; explicit set-time, completed waits and save
restoration still use that same clock.

V2 targets purple/indigo upper sky, crimson/orange cloud contrast and a warmer
sun-facing low sky. A compact vertical palette lookup uses source texture
luminance. Its horizon meets the matching far-fog color; an additional bounded warm
ramp follows the sunrise/sunset side. V2/V3 also apply a subtle time-dependent
ambient color multiplier through the existing geometry fog lookup: neutral day,
amber evening, red twilight, cool blue hour and a readable darker night. V1
preserves its original near-world colors. `aw_fog off` disables this world tone
and distance fog while leaving sky controls active. UI, independently lit
interiors and hand/torch overlays are drawn separately. This is an artistic
indexed approximation, not a pixel-exact original weather/lighting simulation.

The private image009 input was subsequently found to contain a uniform shared
sky tile, so it cannot demonstrate cloud detail. The new private conversion uses
an original owned cloud image's alpha shape at 128 by 128 pixels, with a cutoff
for clear holes and neutral tones for cloud density. It does not retain RGBA
transparency or original RGB. The same 32,768-byte shared sky contains a masked
left cloud layer and a right atmosphere layer using index 224 plus a sparse
secondary original-cloud layer in indices 2, 4 and 5. The left layer excludes
those secondary indices, 224, the UI bank and the seven new sky output entries;
zero is reserved for its transparent holes. A 256-byte lookup preserves primary
and secondary roles after composition. V3 darkens low secondary clouds while
retaining the warm primary layer. Invalid or overlapping source roles fall back
to legacy luminance interpretation. Valid layers use a broader 128-unit texture
projection; older sky assets retain the original 378-unit scale.

The old global palette has no true violet entries. The candidate palette instead
reclaims seven near-redundant colors and requires a separately audited offline remap of
all affected indexed artwork and lookup tables. The UI color bank is retained.
Exact RGB markers gate the corresponding procedural-particle substitutions;
old palettes keep their original indices and V1 interpretation. The runtime
does not reserve colors by recoloring arbitrary UI or world pixels at display
time. The actual cloud resource and format-aware asset/lookup remap are now integrated
in the assembled V3 image, with the UI bank retained. The default preparation
hook runs before heap gates and image packaging; explicit shared-sky input and
local-skybox debug keep their caller-owned behavior. Unsupported palette or
missing owned cloud input produces an explicit fallback warning, not a vivid-sky
success claim. Image015 passed bounded sky-pixel and caption inspection across the day/night gallery stages. This does not certify every map or unrestricted playthrough.

| V2/V3 clock point | Intended palette phase |
| --- | --- |
| 04:00 | Night, beginning the predawn transition |
| 04:30 | Cool blue predawn |
| 06:00 | Red sunrise |
| 07:00 | Gold morning |
| 08:00–16:00 | Clear-derived daytime sky |
| 17:00 | Soft gold evening |
| 18:00–19:00 | Strong red/orange sunset |
| 19:45–20:30 | Violet/blue hour with a small warm low-sky remnant |
| 21:00 | Night |

V2/V3 intermediate times interpolate with 32 cached steps. V1 retains its earlier
timing and palette stops. All profiles can use the shared original-texture night
layer below. Regional weather remains separate work. The red-cloud and directional-haze balance still needs actual-palette
and target appearance review; a synthetic fixture is not that visual proof.

All three profiles now include a small source-authored indexed sun disc and soft
palette halo. Its position follows the verified source visible-position arc:
between 06:00 and 20:00, `t=(hour-6)/14`, then direction proportional to
`(400*(1-2*t), -75, 400-abs(400*(1-2*t)))`. It rises in +X, moves slightly south
(-Y), peaks at 13:00 and sets in -X. This is the visible-position calculation,
not the separate directional-light vector. The disc is hidden outside that
interval and below the world horizon. Higher positions use cream/yellow; low
positions soften toward orange/red. The central core is cream higher up, gold
then orange lower down and red at the very low horizon, inside a softer red halo.
See the source [weather calculation](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwworld/weather.cpp)
and [visible-position conversion](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwrender/renderingmanager.cpp).

The same `AW_Clock` moves clouds, phase and sun. Pausing automatic time holds
them; setting time, completing a wait or restoring a save moves them together.
Sun/gradient drawing occurs only at `AW_SKY_BACKGROUND_DEPTH` pixels after
opaque world, actor, sprite and particle depth writes. Opaque geometry hides
the sun, while transparent sprite holes retain sky. It adds no local sky mesh,
billboard drawn over scenery, image asset or Hunk allocation. Turning ordinary
distance fog off leaves the sky presentation available.

The new tables add **8,448 static bytes**: 4,096 for vertical colors,
2,048 for directional warmth, 2,048 for the halo and 256 for cloud roles, plus small constants, cvar
and cached state. They are separate from map-Hunk allocations, executable disk
size and the earlier V1 tables. The sun vector is normalized once per changed
clock sample; sky pixels use squared angular comparisons without a square root.
Palette searches remain initialization work. Actual cross-compile section
accounting measures +8,480 BSS bytes and +14,212 loaded executable bytes against
the earlier f19 engine; the 8,448-byte table subtotal above excludes small state.
No additional map-Hunk allocation is introduced by this presentation change.
Native frame cost and visual acceptance remain pending.

All 64 focused Linux native engine methods passed at 11:52:10 EEST, including
sanitized color/clock/sun tests, synthetic source-luminance contrast, warm/cool ordering,
stable noon/night and V1 selection, orbit/freeze, fog-disabled sky, depth
occlusion and the existing background/sprite/particle fixtures. Five additional
fixture modes check valid cloud roles, missing palette markers, overlapping
roles, forbidden source indices and valid secondary clouds. V3 selection/default,
independent sun/cloud toggles, cache restoration, ambient day/night/blue tone and
the actual broader texture sampler are covered. The real particle draw loop applies the
seven substitutions only with a matching palette and preserves its simulation
state. These synthetic checks do not establish original-cloud appearance.
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
audio investigation deferred until after publication. See [WIN-05](journals/BUG_JOURNAL-v0.0.29.md#win-05-intermittent-winuae-background-music-snapping---investigation-open).
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

The image009 and `f19...` results below are explicitly historical V1 evidence.

## Historical image009 / V1 status — 4 October 2026

At the earlier checkpoint, image009 passed the bounded native checks for
cycle aliases, the shared clock, profile save/load time, wait-dialog rendering
and clean shutdown. Its 4,024-frame profile reported zero edge or surface overflow.
Those full suites passed 760 tests on Linux and 678 on Windows, with four
and 86 explicit skips respectively, from 764 discovered tests on each host.
Both actual Amiga compiles match all 205 runtime sources and produce identical
executables. At that checkpoint, canonical terrain joins and NPC owner/overlap support
errors blocked release acceptance. The current coherent host batch is described
in [canonical terrain status](CANONICAL_TERRAIN_CULLING.md); its native acceptance
is still separate. Reserve-margin warnings were not the historical blocker.

The default-on cycle preserves fractional clock ticks and coordinates the shared
exterior sky with distance fog using Clear-profile RGB targets. Uniform cached
color remaps replace the earlier coarse ordered pattern. Stars/nebula artwork,
sun/moons, nearby-world lighting and regional weather remain follow-up work;
the source timing remains an approximation.

The earlier sky-only candidate failed the visual target because its fog stayed gray
and the dawn pattern showed moiré. Its image005 was separately rejected for a private
image-writer defect; image006 passed the bounded route and filesystem write/exit/
reboot checks at 07:30 EEST. Those results establish the earlier checkpoint only.
The image009 observations below establish a bounded historical-runtime result.
Representative appearance, frame-cost and memory acceptance across the world,
and real-hardware performance, remain unverified.
The goal is a crude but coherent impression of Morrowind's lighting. No global
illumination is proposed. The dim prison-ship opening is the first local-light
acceptance scene; see [Seyda Neen journal](journals/SEYDA_NEEN.md).

## Shared exterior background sky: implementation candidate

The renderer now selects shared exterior sky through explicit worldspawn metadata:
`_aw_sky_mode "exterior"` and `_aw_sky_asset "gfx/aw_shared_sky.lmp"`.
The shared file is exactly 32,768 indexed bytes (the existing 256×128 two-layer sky
layout), extracted from the authorized current sky artwork. The file contains
raw mip-level-zero palette indices only: no header, palette, or smaller mip levels.
It is not new art.
An exterior with zero sky faces **and zero map sky textures** can initialize this
resource on its first load. Missing, malformed or unsupported shared assets leave
sky disabled and report the missing resource; arbitrary fallback art is not created.

The existing static sky buffers own the pixels independently of map/Hunk allocations.
Once loaded, subsequent map textures cannot replace them. Cell changes preserve
the shared resource and the saved world-clock cloud phase; the legacy renderer
clock is used only if the world clock cannot initialize. Day/night sky colors now
read this same clock. The current candidate adds the sun and the bounded
original-texture night/moon layer described above; regional weather and a
panorama sampler remain separate work. Clock initialization failure retains
the original sky colors.

`_aw_sky_mode "interior"` disables exterior sky even immediately after an exterior.
**Interior cells retain their independently authored lighting and environment.**
Global exterior weather/day/night/sky must never automatically replace interior
lighting, and this feature is not a global framebuffer fade. Unknown/invalid explicit
metadata fails closed. Old maps without metadata retain texture-based compatibility;
new converters must emit the explicit scene contract.

### Coverage and the fog marker

`D_DrawBackground()` consumes the scan converter's uncovered spans immediately.
It uses the existing direction-based indexed sky sampler, without an alpha
framebuffer, a replacement giant box, a deferred span-pointer list or per-cell sky
meshes. Ordinary opaque world coverage occludes those spans.

Only actual sky-filled background spans receive the reserved signed depth marker
`AW_SKY_BACKGROUND_DEPTH` (-32768). With the current clock-driven exterior
presentation enabled, that marker selects direction-based horizon haze instead
of ordinary geometry depth fog. The legacy/off path skips **that exact value**;
zero-depth geometry and other negative depth values still follow ordinary fog.
Opaque sprite/actor/particle depth writes replace the marker normally. Masked
transparent sprite texels retain the sky pixel/depth. First-person torch/hand
overlays run after world fog, so those color-only overlays are not fogged as sky.
World and sprite depth writers clamp exceptional near/invalid inverse depths to
0–32767, preventing signed overflow from creating the reserved sky marker.
Legacy explicit sky polygons keep their existing ordinary depth behavior.

### Required converter and target acceptance

The renderer change does not remove enclosure geometry itself. Generated sky
ceilings, walls, undersides and fragments must be absent from serialized render
data; required collision, contents, BSP/PVS and lighting structure must survive
the separate render-reference remapping. A zero-face texture alone is not a mesh.
Terrain culling against the authoritative global topomap remains independent.

The asset-free native fixtures cover missing/invalid resource rejection, first-load
zero-map-texture exterior selection, persistent pixels/clock across exterior–interior–
exterior transitions, exact background marker bounds, fog treatment of marker/zero/
other-negative depths, opaque/transparent sprite and particle depth replacement,
and near-depth clamping under undefined-behavior checking. On 4 October 2026,
the refreshed offline Docker gate passed all three focused native test methods
(which compile and execute the sky, fog, sprite, particle and depth fixtures),
both render-range parser/view fixtures, and the matching asset-free Amiga
compile. These results are not emulator or hardware appearance proof.
Target gates remain: pitched/FOV views, neighboring-cell continuity, no interior sky
leak, NPC/particle/water/torch occlusion, unchanged collision/PVS, and measured memory/
frame cost with the actual authorized shared artwork. The bounded native result
below supports only its recorded controls, interior separation and map route;
it does not complete these acceptance gates.

## Cycle control and coordinated sky/fog candidate — 4 October 2026, 09:06 EEST

| Control | Default | Effect |
| --- | --- | --- |
| `dbg daynightcycle on` | on | Advance the saved game clock automatically |
| `dbg daynightcycle off` | — | Pause automatic time and cloud progression |
| `dbg sky on` | on | Apply clock-driven exterior sky colors and matching fog |
| `dbg sky off` | — | Restore the original shared sky and baseline fog |
| `dbg set time 0630` | — | Set that same saved clock to 06:30, preserving date |
| `T` / `aw_wait` | 1–24 hours | Advance that same clock by the selected wait |

Both switches accept `1/0`, `true/false` and `on/off`, case-insensitively; no
argument reports the value and invalid values leave it unchanged. Their archived
variables are `aw_daynightcycle` and `aw_daynight`. Shipped `config/game.cfg`
defaults both to 1; saved user `config.cfg` overrides those defaults.
Turning the cycle off preserves the selected timescale and current clock. Exact
time setting, legacy `dbg timeofday` setting and explicit T waits still work while
it is off. Turning it back on resumes ordinary advancement without catching up
paused wall time. Presentation remains independent: `dbg sky off` does not pause
time, and `dbg daynightcycle off` does not disable the selected sky/fog appearance.
`aw_timescale 0` also pauses automatic advancement; 30 remains the default rate.

Automatic ticks now retain their fraction of one millisecond instead of discarding
it every frame. This removes frame-rate-dependent truncation drift. The fraction
is only a sub-millisecond remainder, not another clock or a saved calendar field.
Explicit time setting/waiting and an inactive server clear it. The persisted
`AW_Clock` continues to own time/date across map changes, waiting and save/restore;
normal menu/pause/reader/intro restrictions still govern automatic advancement.

The earlier V1 renderer interpolates sky and fog RGB targets separately, then quantizes into
the existing palette. It keeps the source sky texture luminance, preserves the
original indexed sky exactly during daytime, and uses the audited Clear sunrise,
sunset and night targets for the other phases. Fog uses Clear day `(206,227,255)`,
sunrise/sunset `(255,189,157)` and night `(9,10,11)`. Near geometry keeps its exact
palette index; all fully fogged geometry shares the selected far-fog color.
Sky horizon haze converges on that same color and fades toward the upper sky.
Its world-direction projection follows camera pitch and roll rather than fixing
the horizon to a screen row. Interior lighting, UI and post-fog hand/torch overlays
remain independent. Explicit shared-exterior metadata is required.

The V1 timing approximation remains night until 05:00, sunrise at 06:00,
original day sky from 08:00–16:00, sunset at 18:00 and night from 20:00. Each
transition has 32 cached color steps. It does not reproduce the source's separate
sky/fog/sun/ambient transition offsets or weather blending. At this earlier
09:06 checkpoint night used the existing clouds without stars or moons. The
current candidate adds the separate night layer and sun described above.

The V1 static arrays are a 4,096-byte RGB-to-palette lookup, a 256-byte current
sky remap, a 4,096-byte current fog ramp and 24 bytes of RGB stops. They replace
the earlier 512-byte sky remaps and 16-byte ordered pattern: **7,944 additional
array bytes**, about 8 KiB with small control/cache state. Separate target section-size accounting
is not yet recorded; the completed compile alone does not establish it. This is resident storage, not extra map-Hunk
allocation or an executable-size prediction. Existing sky buffers and the baseline
fog resource remain. Palette searches run once at renderer initialization; bounded
table rebuilding happens only when the color phase changes. Sky texels use one
uniform remap, without position-dependent dithering. The fog pass adds bounded
integer haze stepping with row-level projection setup and no per-frame allocation.
Startup cost, palette banding and frame cost still require native measurement.

All 63 native engine test methods passed in the offline Docker run completed at
09:05:55 EEST. The focused coverage includes cycle defaults/archiving and Boolean
dispatch, frozen automatic ticks with explicit set/wait, fractional accumulation
and resume, saved-clock millisecond round-trip and midnight rollover, shared sky
persistence/interior isolation, uniform transitions, matching far fog, near-color
identity, viewport bounds, pitched/rolled horizon haze and fallback behavior.
The sky/fog fixture uses undefined-behavior and float-cast-overflow sanitizers;
existing efrag capacity/reset sanitizer fixtures also passed. An initial signed/
unsigned viewport-center bug found by the roll fixture was corrected before this
passing run. That early candidate runner separately reported a terrain source-allowlist
mismatch. The subsequent full host gates below corrected that admission issue.
Image009 subsequently passed the bounded native checks below. That result does
not establish full terrain, NPC, appearance or performance acceptance.

## Earlier V1 host and bounded native verification — 4 October 2026

The 10:30 EEST full-suite checkpoint discovered 764 tests on each host: Linux
passed 760 with four explicit skips, and Windows passed 678 with 86 explicit
skips; neither had failures or errors. Linux runs the native fixtures; Windows
covers its launcher and inspector paths. Both actual normalized-source Amiga
compiles match all 205 runtime files and produce the byte-identical 719,636-byte
executable with SHA-256
`f19ea3089bfb73b3bea801334f51a76a722c54316f471d8d1271807347f3d2d2`,
using the same declared compile timestamp. The previous 84-line compiler-warning
set is unchanged and remains tracked debt. The earlier 09:41 checkpoint discovered
757 tests, with 753 Linux passes/four skips and 671 Windows passes/86 skips;
those counts describe that earlier source/test checkpoint.

Image009 retains that engine and changes only the diagnostic sn045 terrain from
the preceding image. All 10,748 original packaged files and all three partitions
passed assembly readback and allocation-ownership checks. Post-native checks
also passed for the preserved originals, recorded test controls and native writes.
The 2,723-map target-ABI estimate retains 16 reserve warnings and no hard
heap-ceiling failure. A modeled safety-reserve shortfall remains a warning needing
adjustment; allocation failure, missing geometry and invalid actor support do not.

The independent WinUAE run passed the exercised cycle aliases, automatic-clock
pause/resume and explicit time controls, profile time restoration, wait-dialog
rendering and clean shutdown. A quicksave at 15:45 restored 15:45 after changing
the clock to 21:15. Wait-dialog rendering is not proof of every completed wait
duration. The profile recorded 4,024 frames, peak demand of 52,176 efrags and zero
edge/surface-overflow frames. This is a bounded 16 MiB Fast RAM/JIT result, not
all-world, frame-rate or physical-hardware acceptance.

The later autosave rejection followed a raw debug `map` command, which resets
player health to 100 while the existing profile maximum remains 55. The strict
save validator correctly rejects that inconsistent state and retains previous
saves; a subsequent scene transition carries the same invalid state forward.
Source and compiled-game-code inspection establish that debug-route explanation,
not an ordinary world-transition autosave defect. A fresh native retest through
normal transitions from a valid loaded profile remains pending.

Full release acceptance is still blocked by the canonical terrain joins and
NPC owner/overlap support inconsistencies described in the
[terrain record](CANONICAL_TERRAIN_CULLING.md). The bounded day/night pass does
not waive those failures or finish the broader Morrowind lighting target.

## Historical pre-release gate after the static-link correction — 4 October 2026, 06:26:57 EEST

This earlier checkpoint includes the bounded static-entity leaf-link correction,
but predates the cycle/sky/fog candidate above. Its results are retained as history.

| Host | Discovered | Passed | Explicit skips | Failures/errors | Amiga cross-compile |
| --- | ---: | ---: | ---: | ---: | --- |
| Linux Docker | 753 | 749 | 4 | 0 | Passed |
| Windows | 753 | 667 | 86 | 0 | Passed |

Linux skips three Windows-only checks and the Node-dependent inspector wrapper;
the offline image has no Node runtime. Windows runs the inspector JavaScript suite
and real Windows launcher checks; native helper executables run in Linux, while
POSIX-only and unavailable filesystem-capability cases are explicitly skipped on
Windows. Both standalone render-range C fixtures also passed with UBSan in Linux.
These are complementary host results, not 753 executed tests on each platform.

Both cross-compiles match all 205 engine source files and produce 718,032-byte
Amiga executables (+496 disk bytes from the preceding sky candidate). Their only
six differing bytes occur in two embedded build-time strings; all remaining
bytes match. Each compile emits the same 84 compiler warning
lines as the preceding shared-sky compile, with no new file/message warning pairs.
This is not a warning-free codebase. Source allowlist and asset-free packaging
checks passed. Image006 passed the bounded filesystem/native checks below;
appearance/performance acceptance and hosted exact-commit CI remain separate steps.

The earlier 4 October gate, before the static-link correction, discovered 749
tests: Linux passed 745 with four skips; Windows passed 663 with 86 skips. Its
717,536-byte executables differed in ten timestamp bytes. Those results remain
valid for that earlier source checkpoint, not the later corrections.

### Static foliage links: image004 incident and image005 correction candidate

The v0.0.28-rc1 image004 native smoke booted the prison, then `map sn045`
repeatedly reported `Too many efrags!`. This is a functional foliage omission:
the exhausted pool skipped leaf links, making affected static entities absent
from some views. It is not a modeled safety-margin warning that can be accepted
merely because the executable builds or the map loads.

An authenticated audit of all 2,664 packaged exterior maps found 762 needing
more than the existing 8,192 links. `sn045` needs 8,612 links for 77 static
entities: 420 links were omitted across two entities, including one wholly
unlinked entity. Maximum demand is 52,176 links in `vf0538`. The largest static
entity count is 266 against the unchanged limit of 512. The spherical sprite
bounds match the actual frame corners, camera-facing renderer and single scale
application; reducing those bounds would risk additional missing scenery.

The correction retains the 8,192-link base pool and adds 1,024-link pages only
during static linking. The hard limit is 65,536 links; exceeding it raises an
explicit load error instead of silently losing entities. Pages belong to the
map's low Hunk, survive client-state resets for reuse, and have their leaf/static
references cleared before the map Hunk is freed. No frame allocates these pages.

The matching Amiga ABI measures a 16,388-byte page payload: a four-byte next
pointer and 1,024 16-byte links. Twelve bytes of alignment and the 16-byte Hunk
header make each allocation **16,416 bytes**. Maps within the base pool allocate
zero extra pages; `sn045` adds one page. The measured maximum needs 43 pages,
**705,888 bytes**; the hard cap allows 56 pages, **919,296 bytes**. These are
additional modeled Hunk allocations, separate from executable disk size, the
existing base pool, total Fast RAM, safety headroom and measured live heap use.
The estimator charges them after model loading and binds the allocation and
reset source hashes to the matching engine receipt.

All 2,664 public-estimator results matched the independent demand audit using a
fresh target ABI probe. The Linux native fixture exercises all 65,536 links,
visibility of the last static entity, explicit hard-cap failure, removed-link
reuse, client reset, and freeing/reloading pages under address and undefined-
behavior sanitizers. All 63 native engine fixture methods passed, followed by
the full host gates above. The later bounded native route supports the capacity
and map-reset correction, but image005 itself was rejected for a separate
filesystem defect. Image006 subsequently passed the bounded route and
write/exit/reboot checks below.
See [EFRAG-01](journals/BUG_JOURNAL-v0.0.29.md#efrag-01-static-foliage-leaf-links-exhausted-in-image004).

### Bounded native result and remaining visual defects — 4 October 2026

The earlier image005 native validation run used the production engine (SHA-256
`9d1e24a2ce04e388cb27aa53c0325dc12395e9f0f20a78da3d919e841616fd50`)
and loaded `sn045` → `vf0538` → prison → `sn045`. Across 11,346 recorded frames,
the profile reached 52,176 efrags, then ended with a 9,216-link allocated capacity
against the 65,536 hard limit. It reported zero edge-overflow and surface-overflow
frames. This supports page growth for the measured densest map and release/reuse
when returning to the smaller map; it does not certify every exterior placement.

The first `sn045` heap peak was 8,827,056 bytes, exactly 16,416 bytes above the
old image's 8,810,640-byte peak. On returning to `sn045`, low-Hunk use was again
8,814,288 bytes, identical to the first visit; its transient peak was 9,084,960
bytes. The `vf0538` measured peak was 5,922,896 bytes. These measurements describe
that route in the configured 11,534,336-byte heap. They are not total-process RAM,
free Fast RAM, an all-map memory guarantee or a hardware performance benchmark.

Clock commands and the sky fallback worked, and the interior view retained its
independent presentation. That sky-only candidate **failed visual acceptance**:
unchanged gray distance fog produced contrasting distant tree/building silhouettes,
and the ordered dawn pattern showed coarse moiré. The 09:06 candidate above
implements coordinated sky/fog targets and removes the ordered pattern. Image009
subsequently passed the bounded current-runtime checks recorded above.
SKY-VISUAL-01 remains open for the broader appearance target; complete Morrowind
lighting is not claimed. The later V3 sun implementation above awaits native acceptance.

Image005 also failed filesystem acceptance. The private host image editor closed
the device without first closing/flushing the volume, leaving eight owned engine/
checker blocks marked free. Native writes reused header blocks, causing an
AmigaDOS checksum error and directory loss. This is a private assembly defect,
separate from the public engine correction and the sky/fog appearance gap.
Image005 remains rejected. Fresh image006, rebuilt from the intact image004
baseline with volume flush, passed all-owned-block and native write/exit/reboot
validation at 07:30 EEST on 4 October 2026. See
[HDF-WRITER-01](journals/BUG_JOURNAL-v0.0.29.md#hdf-writer-01-private-image005-refresh-left-owned-blocks-free).

The image006 test copy loaded `sn045` → `vf0538` → ship/prison → `sn045`, exited
cleanly to AmigaDOS, and was closed. The same test HDF was restarted, loaded
`sn045` and exited cleanly again. Both post-exit and post-reboot checks verified
8,788 original files, with no missing files or unexpected changes, and zero
free-owned blocks, duplicate ownership or invalid nodes. Twelve new native files
were recorded; three deliberate test controls were accounted for separately.
The copies were authenticated to the assembled image006 before those controls.

The new first-route profile recorded 7,495 frames, peak efrags of 52,176, final
capacity of 9,216 and zero edge/surface-overflow frames. Its heap measurements
repeated the earlier route exactly: `sn045` first peak 8,827,056, repeat peak
9,084,960 and settled low Hunk 8,814,288 bytes; `vf0538` peak 5,922,896 bytes.
The engine hash is unchanged. This verifies the recorded route and persistent
filesystem behavior under WinUAE with JIT and 16 MiB Fast RAM. It is not an
all-world, real-hardware or completed sky/fog visual acceptance result.

## One world clock, separate presentation

Maintain one game-time state for progression, waiting, saved state and eventual
NPC/quest conditions. Exterior ambient shading, fog, sky and sun/moon presentation
read that state. Interior lighting stays independently authored. Avoid a global
screen fade that also darkens the console or makes every interior follow noon.
Exact source transition hours, calendar behavior and time-dependent quest checks
must be audited from the user's installation and relevant OpenMW behavior before
we claim compatibility. A temple/time-of-day quest is a useful future regression
case; do not implement its condition by testing the rendered sky color.

## Source appearance: independent color profiles, texture layers and haze

The visual target includes vivid red/orange dawn and dusk, pale peach horizons,
cool blue/violet twilight, and a sun softened by the draw-distance haze. Preserve
near silhouettes and gradual distant color loss; do not simulate this with an
orange overlay over the whole framebuffer. Interiors and UI keep their own colors.
Sun visibility must vary with weather, and terrain/buildings must occlude it.

A read-only audit of the owned game's configuration found independent sunrise,
day, sunset and night RGB values for sky, fog, ambient illumination and sunlight.
For example, the Clear sunset profile combines blue sky `(56, 89, 129)`, peach
fog `(255, 189, 157)` and orange sunlight `(255, 114, 79)`. This is why one warm
sky tint alone cannot reproduce the effect. These are RGB targets to approximate
within the Amiga palette, not a ready-made 256-color hardware palette. Sunrise
and sunset configuration anchors are 06:00 and 18:00 with two-hour durations;
individual color channels have additional transition offsets. Do not conflate
those anchors with every color transition or infer quest logic from the image.

[OpenMW weather processing](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwworld/weather.cpp)
interpolates the fog, ambient, sun and sky channels independently by game time,
then blends weather transitions. Its sun-disc appearance also applies brightness
and alpha rules beyond directly displaying the configured RGB value.
[OpenMW sky rendering](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwrender/sky.cpp)
uses textured cloud layers, textured night-sky meshes, and sun/glare textures;
cloud tint follows the fog color while atmosphere tint follows sky color.
The haze over distant scenery is the separate distance-fog path, not necessarily
an extra billboard obscuring the entire view. The supplied visual references may
include modifications; they establish art direction, not proof of vanilla output.

For AmiWind, evaluate source-derived color targets, low-resolution indexed layers,
ordered dithering and bounded sun/glare coverage over the shared sky background.
Keep sun/glare behind world coverage and couple its strength to weather haze.
Original game artwork and private reference screenshots remain outside the public
source tree. The current candidate implements separate sky/fog RGB interpolation
and a simple exterior ambient multiplier with compact shared timing. Independent
source-channel lighting/weather profiles remain future work. V3 adds bounded
sun/halo coverage and two authored cloud roles; native appearance and cost require
measurement before claiming this reference look has been delivered.

### Use the Amiga palette creatively

Treat the Amiga indexed palette as a rich design space. Build vivid warm sunrise/sunset ramps and cool twilight/night colors from the audited Morrowind profiles, then map them into Amiga colors with deliberate quantization and dithering. Palette redesign and remapping are valid tools when they improve the scene; coordinate palette slots and lookup tables across terrain, sprites, UI, exterior fog and separately authored interiors. Compare representative scenes and measure memory, frame cost and transition quality. Palette animation is a candidate where the renderer/backend supports it and measurements justify it; this does not claim Copper or bitplane integration.

The earlier 512-byte warm/cool sky-only remaps are superseded by the current
Clear-profile sky/fog cache described above. V2/V3 now include the bounded ambient
tone and sun presentation described at the top; weather remains future work.
External game screenshots are mood references only: they
establish neither a hardware/version identity nor permission to reproduce artwork.

## Historical first day/night sky milestone — 4 October 2026

Historical first-milestone validation, before the later static-link correction:
the offline Linux host gate compiled and ran four focused tests for
sky phases/toggle/midnight/interior isolation, wait/calendar/exact-time behavior,
console dispatch, and shared-background depth. The new Amiga cross-compile also
passed with 20 jobs, and all 205 recorded engine source files matched the working
source after compilation. This is compiled-artifact and native-fixture evidence;
it is not yet an emulator screenshot or hardware appearance/performance result.
Against the preceding shared-sky engine, executable disk size increased from
715,896 to 717,536 bytes (+1,640 bytes). This is executable storage accounting,
not a measurement of total runtime RAM or free map heap.


At this first milestone, archived `aw_daynight 1` enabled exterior sky colors
by default. `dbg sky off` restored the shared image and `dbg sky on` restored
clock-driven colors. That implementation changed only sky pixels, leaving fog
unchanged; the later V1 switch also selects matching exterior fog. Those earlier
versions did not pause the clock, alter near-world ambient color or recolor interiors.
Explicit exterior metadata is required; legacy maps retain their original sky.
Missing shared artwork retains the existing missing-resource behavior.

This superseded 128×128 composition used two 256-byte palette remaps: warm and
cool/dark. These 512 bytes, a 16-byte ordered-dither pattern, and small cvar/cache
state replace no image and require no Hunk/heap allocation. Nearest-color searches
run once during renderer initialization, after the palette loads. Daytime uses
the original composition path. Other phases add one indexed lookup per composed
sky texel plus a bounded ordered-dither selection; no full-screen blending or
nearest-color search runs per frame. Tile recomposition remains cached by cloud
offset and now by color phase, so a frozen-time change or toggle updates on the
next frame even if the cloud offset happens to match.

The first authored visual approximation was dark until 05:00, warm at 06:00,
original day from 08:00 to 16:00, warm at 18:00, and dark from 20:00. Sixteen
ordered blend steps connect each pair. The 06:00/18:00 anchors follow audited
source sunrise/sunset, but these shared image remaps do not reproduce the
original independently interpolated sky/fog/sun/ambient weather profiles.
At that first milestone, night dimmed the existing cloud art: original star/nebula layers and
moon/sun discs were not yet integrated. Keep the historical scope visible in playtest
reports rather than claiming the original night sky has shipped.

For current comparisons, open F10 (Shift+F10 for fullscreen), use
`dbg daynightcycle off`, then `dbg set time 0630`, `dbg set time 1200`,
`dbg set time 1800`, or `dbg set time 0000`. `dbg daynightcycle on` resumes the
selected rate. The earlier `aw_timescale 0` / `aw_timescale 30` method still works.
The calendar and cloud phase survive map transitions; the next exterior frame
also observes waiting, exact-time changes and restored saved state.

`config/game.cfg` supplies the default; saved user `config.cfg` overrides it.
`aw_environment_profile` remains a proposal and is not a recognized setting.

Local enclosure control is already a build-time option, not a runtime config
variable: `tools/exterior_sky_build.py` exposes `--local-skybox true|false` with
`false` as the default, and `--shared-sky-source <local-asset>` supplies the
shared indexed resource. These source options are implemented and focused-tested.
The completed 8-worker conversion processed all 2,664 exteriors in 262.281 s
with zero failures, removing 301,751 local sky faces and staging one shared
resource. A 20-worker final readback took 1.891 s and checked output hashes and
map invariants. That conversion receipt did not include HDF or native/target
acceptance; the later image004 smoke found the static-link defect above. The
subsequent bounded native route is recorded separately from image acceptance.
The source inventory records 2,664 exterior inputs, all carrying local sky
faces (301,751 total); 58 interior maps have none, and one unclassified map's
27 sky faces are retained. This inventory is source coverage, not proof that every map
has been converted. The two flags do not implement day/night coloration.

### Waiting and exact-time debug controls

`T` opens the existing 1–24-hour wait dialog. Waiting and normal play advance
the same saved `AW_Clock` (default timescale 30); waiting is an immediate clock
jump, not an hourly NPC rest/schedule simulation. Defaults remain 09:00,
16 August, year 427, consistent with the audited source globals. Explicit waiting
and time setting remain available with `dbg daynightcycle off`; the cycle switch
only controls automatic advancement.

`dbg set time HHMM` accepts exactly four digits, hour 00–23 and minute 00–59.
`0630` means 06:30. Invalid forms including `630`, `2400`, `1260`, decimal hours,
extra arguments or unknown names are rejected without changing the clock.
Accepted input sets exact integer minutes, clears seconds, preserves the date,
and prints the resolved time/date. Named snapshots are:

| Name | Exact time |
| --- | --- |
| dawn | 05:30 |
| sunrise | 06:00 |
| morning | 09:00 |
| midday | 12:00 |
| day | 14:00 |
| evening | 17:00 |
| sunset | 18:00 |
| dusk | 19:00 |
| night | 00:00 |

Sunrise/sunset use the source anchors; dawn uses the audited pre-sunrise sky
transition start. The other labels are convenient distinct comparison snapshots,
not new game rules or claims of exact source lighting extrema.
The existing `aw_timeofday` and `dbg timeofday` forms still accept decimal hours
and report time without an argument. Their original named presets remain
compatible, including **evening=18:00 and sunset=19:00**. New captures should use
`dbg set time` for the table above. Both forms also accept dawn/dusk.

OpenMW is a behavior reference only: its wait progress callback performs a rest
step and advances the world by one hour, while its date/time manager updates the
calendar on advancement. AmiWind currently performs only an immediate clock jump;
NPC rest/schedule semantics remain unimplemented. See [OpenMW wait dialog](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwgui/waitdialog.cpp)
and [OpenMW date/time manager](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwworld/datetimemanager.cpp).

Beyond image009's bounded native result, representative matching-fog appearance
and cost acceptance remain open. The V3 candidate adds the bounded occluded sun
layer described above; validate it using the frozen-time comparisons
above. Keep the existing shared exterior renderer
and the staged shared resource as fallback. A later region record can choose a
small weather profile (for example `clear` or `blight`) and cloud speed, with
sparse ash effects only after profiling. Do not make per-frame full-scene lighting rebuilds the
initial milestone. Separately loaded interiors keep their own authored lighting
and do not inherit exterior weather. Local skybox geometry remains a distinct
legacy/debug comparison; it must be off by default and is not an environment mode.

The renderer can consume the 32,768-byte shared asset and explicit zero-sky-face
scene metadata, and the source build tools can stage them when given the resource.
The shared asset was staged once in the completed conversion batch. A later
private image004 booted and loaded an exterior, but exposed static-link
exhaustion. The later native route supports the correction, but image005 is
rejected for a separate filesystem defect. Image006 passed the bounded native
route and write/exit/reboot checks; the sky/fog visual issue remains open.
Conversion and assembly alone
do not establish target-render or hardware acceptance.
Promote future presentation only after rebuilding the same exterior maps from both the immutable
original and each immediate input, accounting for the shared asset once, and
checking identical-ABI memory and appearance. The safe control's modeled peak is
115,456 bytes (112.75 KiB) above the 6 MiB map allowance. That is a modeled budget
shortfall, not observed physical heap exhaustion. A private playtest may retain a
modest modeled safety-margin overrun as a warning needing adjustment; actual
allocation failures and functional omissions remain errors. Live memory and
release acceptance still require separate evidence. Current
original-to-candidate disk totals and the full area scope are recorded in the
[map findings ledger](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md); do not infer RAM
from BSP bytes.

Source checks: [`aw_wait.c`](../engine/aga/src/aw_wait.c) and
[`aw_clock.c`](../engine/aga/src/aw_clock.c) implement the current time controls;
[`r_sky.c`](../engine/aga/src/r_sky.c) uses it for scrolling and sky/fog tables;
[`aw_fog.c`](../engine/aga/src/aw_fog.c) applies distance fog and horizon haze;
[`keys.c`](../engine/aga/src/keys.c) and [`console.c`](../engine/aga/src/console.c)
implement F10; [`host.c`](../engine/aga/src/host.c) and [`cvar.c`](../engine/aga/src/cvar.c)
write archived cvars to `config.cfg`. The build-time sky options are in
[`exterior_sky_build.py`](../tools/exterior_sky_build.py), [`build.py`](../tools/build.py),
and [`build_aga.py`](../tools/build_aga.py).

## Remaining debug proposal

`dbg set time`, named snapshots, `dbg daynightcycle` and `dbg sky` are implemented
as documented above. `dbg timeofday` without an argument reports date and time.
The proposed `dbg timeofday status` profile report is not implemented; `status`
is rejected as an invalid time value.

Natural progression already handles midnight/calendar rollover. Specify jump
semantics before quest or schedule evaluation is attached; avoid duplicate triggers
or forced quest advancement. Presentation reads the existing single saved clock.

## Cheap visual candidates to measure

1. Measure the candidate exterior ambient/shading lookup on the target. The current
   implementation updates colors at bounded phase changes; assess transition
   quality and CPU/RAM cost. Keep material palette and UI semantics
   coherent. Do not assume a palette change can independently shade pixels that
   share one palette entry across sky, world and interface.
2. Measure the current locally converted star/nebula atlas, moon layers and
   horizon gradients. Their bounded implementation now exists; native visual,
   memory and frame-cost acceptance is still required.
   Use two presentation components: the whole sky background changes its base
   tone with time, while a local warm horizon region follows the low sun.
   Coordinate the base tone with fog and exterior ambient shading so the scene
   reads as dawn/sunset rather than a colored patch on a daytime sky.
   For dawn/dusk, precompute reddish-orange horizon ramps centered on the sun
   direction, fading toward the rest of the sky. Use the audited original solar
   timing/direction and the viewer yaw; do not keep the warm patch fixed on screen
   as the player turns. Quantize phase/azimuth and test seams/banding at the
   target palette. This is a painted lighting impression, not atmospheric scattering.

**Secondary mood reference:** the owner prefers vivid red/orange sunrise and
sunset and cool contrasting night associated with Skyrim. Keep the Morrowind sky
and weather as the primary source reference; use this color direction only as a
visual target. It creates no Skyrim asset dependency, and no Skyrim art or data
is included or required.

OpenMW's upstream sky renderer is a code reference for layer structure: its
camera-relative sky includes day atmosphere, an optional `sky_night_02` with
`sky_night_01` fallback, and distinct star/nebula content layered before clouds.
AmiWind uses no OpenMW renderer or game assets. Morrowind and Skyrim textures,
meshes, contact sheets and extracted pixels remain private and are not included
in this repository. See [OpenMW sky.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwrender/sky.cpp).

3. Profile the implemented moving sun disc and indexed halo, including its
   shaded pixel count and draw cost. Verify source-informed timing, horizon and
   terrain/building occlusion on the target.
4. Measure the low-resolution original moon layers and cloud occlusion with the
   full night working set. Check that even unlit moon regions cover twinkling
   stars. Precise lunar/calendar parity remains a separate audited requirement.
5. Draw sky only in the renderer's sky/background regions. Buildings and terrain
   must occlude it; interior ceilings must not leak sky. Match horizon fog to sky
   color through dawn/dusk and keep the culling boundary behind opaque fog.

These are implementation candidates, not performance guarantees. Compare sky
pixels/frame, CPU time, memory bandwidth, decoded RAM and disk bytes against a
flat-color baseline. Precompute phase/rotation tables on the host where useful.
Only the required sky working set should be resident; avoid one enormous frame
sequence whose disk size hides an unacceptable read/decode budget. No copied
commercial sky textures, renders or converted backdrops belong in public source.
The user supplies Morrowind; the converter generates private output locally.

## Acceptance route

- Capture the same exterior camera at dawn, day, evening, dusk and night with
  frozen time. Check stars/moon silhouettes, horizon seams, palette banding,
  readable doors/actors and UI. Include a camera turn and an occluding building.
- Keep one shared clock and command vocabulary; verify adjacent exterior maps do
  not reset the sky phase, roof/building geometry occludes sky, and an interior
  transition restores its own authored lighting without exterior sky leakage.
  Account for the shared sky resource as a separate incremental memory item.
- Compare dim ship interior with exterior and test transitions without palette
  flashes, black crush, missing surfaces or audio stalls.
- Profile matched routes on identical emulator/hardware settings and record
  lookup sizes, sky/fog/lighting time, peak memory and audio deadlines.
- Test midnight rollover, exact-hour overrides, invalid commands and persistence
  once clock state exists. Later test waiting/schedules/quest time windows against
  owned source behavior. Presentation approximation must not redefine game rules.

## Recovered sky fallback and guard-torch request

`dbg sky on/off` (and true/false, 1/0) controls clock-driven shared sky and matching
exterior fog. Off restores the existing shared background and baseline fog; clock
advancement still follows `dbg daynightcycle` and `aw_timescale`. The V2 candidate
adds sun presentation; the current candidate also adds both moons through the
shared night layer. General NPC schedules remain unimplemented; the bounded
guard-torch policy above is separate. Retain the baseline for A/B tests and
lower-cost fallback.

Guard equipment now has audited original class, inventory, pose and time rules;
its converter/runtime pass the combined host gates. Native acceptance is pending.
Measure light radius, affected surfaces, update rate, actor count and audio
deadlines. The explicit guard/light caps are recorded in [TORCH.md](TORCH.md);
they are not a measured performance guarantee.

## Earlier shared sky and regional environment review — 4 October 2026

The day/night subsection of this earlier assessment is superseded by the current
sky/fog candidate above. Regional weather and native/target acceptance limits
still apply.

The shared sky path is already a usable renderer substrate; regional day/night and
weather authoring are not yet wired. `R_SetSkyBackground()` reads map-wide worldspawn
mode/asset metadata, and `R_SetSkyFrame()` uses the persistent global clock. The
current two-layer indexed image is composed into a shared buffer when its scroll
phase changes, then sky spans sample it from the view direction. `D_DrawBackground()`
uses the sky for uncovered exterior spans with the reserved far-depth marker. Water
continues through its own surface renderer. These paths allow future region-specific
visual presets without inserting a sky enclosure into each cell BSP, but no regional
weather/day-night selector or authoring option is established here.

Diagnostic 023 is recorded with zero sky render faces and the shared-sky resource
plus world metadata. The inspected runtime can consume map-wide sky tags, but this
source review did not locate their authoring step in the checked-in prepare/build
scripts. Do not imply that arbitrary regional weather/time records already flow
through the production compiler. The fixed shared asset remains the current path;
no new art or asset content is included in this documentation.

For the A500, retain the current shared scrolling sky as the practical baseline. A
flat clear color is the cheapest fallback; a low-resolution indexed scrolling image
is a reasonable visual/cost compromise and avoids BSP geometry. A camera-centered
cube or per-cell BSP enclosure adds transformed/rasterized surfaces with no proven
benefit over the existing direction-based sampler. The build-time comparison option already exists: `--local-skybox true` retains enclosure faces, while the default `false` removes them in the staged map transform. This is not a runtime toggle, and the option does not establish a world-wide conversion or target acceptance. Do not promise Copper/bitplane hardware
acceleration for this software framebuffer path. The Commodore-Amiga Hardware
Reference Manual describes playfield scrolling through bitplane pointers, fetch
settings and scroll delay, and notes that scrolling can constrain sprite/fetch
resources. A hardware-specific path would need backend integration and target
measurements first.

A future regional “blight”/weather record should remain small data: palette/tint
preset, cloud-layer speed and fog/visibility preset selected on region changes or
coarse weather/time steps. The global clock can remain the time source. Prefer
precomputed indexed remaps or a few baked palette variants over per-frame full-scene
lighting rebuilds, storm particles or duplicated sky meshes. Treat these as design
candidates until serialized authoring, transitions, interior separation, CPU/memory
cost and target appearance are verified. The current renderer's explicit interior
mode must continue to keep exterior weather/sky from leaking into separately loaded
interior cells.

This assessment is source review, not a native build, emulator screenshot, A500
benchmark or proof of regional metadata integration. Existing synthetic sky tests
cover mode/resource selection and background/depth behavior; the runner is skipped
on Windows and compiles temporary host executables on its supported platform, so no
such test was run for this documentation update.

### Source references

- [`r_sky.c`](../engine/aga/src/r_sky.c), [`aw_sky.h`](../engine/aga/src/aw_sky.h), [`d_sky.c`](../engine/aga/src/d_sky.c), [`d_edge.c`](../engine/aga/src/d_edge.c) and [`r_misc.c`](../engine/aga/src/r_misc.c) — local runtime implementation.
- [Commodore-Amiga Hardware Reference Manual: moving playfields](https://amigadev.elowar.com/read/ADCD_2.1/Hardware_Manual_guide/node0086.html), [horizontal scrolling](https://amigadev.elowar.com/read/ADCD_2.1/Hardware_Manual_guide/node0088.html), and [DMA/display tradeoffs](https://amigadev.elowar.com/read/ADCD_2.1/Hardware_Manual_guide/node012B.html) — hardware reference, used here for constraints rather than a claim about current backend acceleration.
- [id Software Quake `WinQuake/r_sky.c`](https://github.com/id-Software/Quake/blob/master/WinQuake/r_sky.c) — primary-source precedent for two-layer indexed sky composition and view-dependent span sampling.
### Owner-authorized reference audit: visual target without asset redistribution — 4 October 2026, 02:41 EEST

A read-only reference audit confirms that the original night look is layered: the
star/nebula fields are separate from the atmosphere and moving cloud layers, with
additional moon/sun presentation. Weather profiles change sky, fog, ambient and sun
colors across sunrise/day/sunset/night; regional weather probabilities and cloud
motion also differ. Ash/blight weather includes a separate cloud/dust effect, so its
outdoor appearance is more than a red sky texture. The A500 target can approximate
this with shared sky layers, a small set of time/weather palette states, fog tint and
strictly bounded sparse dust effects; it does not need per-cell sky-enclosure BSPs.

This earlier reference audit established a visual target, not implementation or
asset-authoring integration. Since then the current candidate has added cached
sky/fog transitions with tested interior isolation and the bounded image009
native result above. Broader visual/cost acceptance, regional selection and a
particle budget remain future work. Original textures,
meshes, extracted pixels and private paths stay out of this public documentation
and repository. The audited source categories are sky layers, time-of-day color
profiles, regional weather probabilities and weather effects; public source does
not contain their game art.

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

## Additive cloud controls: v0.0.29 development candidate

The base defaults remain `aw_cloud_control 1` (legacy) and `aw_cloud_type 1`
(classic). The dev3 source also enables independent `aw_nightsky_mode 1` as
described below. `dbg cloudcontrol legacy` selects the retained base and turns
midnight clearing off, restoring the prior cloud coverage. The controls keep
the original cloud artwork.

| Console command | Meaning |
| --- | --- |
| `dbg cloudcontrol legacy/new` or `1/2` | Select the base coverage policy. Legacy/1 also disables midnight clearing. No argument reports both policies. |
| `dbg nightskymode legacy/clear` or `0/1` | Retain the base coverage or enable the independent midnight clearing window (default clear). |
| `dbg cloudtype classic/veil` or `1/2` | Independently select the original clouds or a sparse ordered-mask veil. |
| `dbg dayclouds 0..100` | Set daytime coverage in the new controller. Default 100; only 10:00-14:00 has the full adjustment, fading in/out during 09:00-10:00 and 14:00-15:00. |
| `dbg nightclouds auto/clear/partial/overcast` | Set deep-night coverage in the new controller. Changes fade in during 22:00-22:15 and out during 03:45-04:00. |

Day and night selectors report that they are inactive while legacy control is
selected. The ordinary `dbg clouds` master switch still applies. Dawn, dusk,
sunrise and sunset retain their approved classic intensity; reducing daytime
coverage does not apply a global reduction. An explicitly selected veil is a
separate appearance option, so use classic when comparing protected views.

The automatic night choice is currently a deterministic eight-game-day
prototype (four clear, three partial and one overcast), keyed to the evening
date so it remains stable across midnight. It is not original regional weather
simulation. Night visibility still depends on the actual moon positions, atlas,
world occlusion and existing night/stars switches.

Sanitized real-renderer fixtures cover legacy round trips, protected twilight,
day/night boundaries, command validation, cache invalidation and moon/star
occlusion. A bounded native comparison now records lossless engine-generated
indexed frames in one dry exterior view, with the saved clock frozen at 23:00,
sky type 3, classic clouds and optional cloud-control V2. The 320x152 viewport
contains 32,614 depth-classified sky pixels, 16,017 geometry pixels and nine
crosshair pixels. Relative to clear coverage, partial changes 9,232 sky pixels,
overcast changes 13,774, and disabling the night layer changes 10,867. None of
those comparisons changes a geometry or crosshair pixel. Clear restores and
all corresponding depth masks are byte-identical, with the same palette.

This establishes the sampled control response and depth separation for that
fixed dry-exterior view. It does not establish all-region or moving-view
occlusion, water behavior, native frame cost or physical-hardware acceptance.
Balmora and broader visual coverage remain open. That comparison predates the independent dev3 midnight mode. Protected
dawn/dusk and existing v0.0.28 artifacts are unchanged; **Fixed: N** remains
the incident status.

## Dev3 midnight clearing mode — source candidate, 5 October 2026

`aw_nightsky_mode 1` is the archived and shipped default. Every game night,
cloud coverage fades from the selected base policy toward clear between 23:00
and 00:00, stays clear through 03:00, then returns to that policy by 04:00.
The entire 04:00–23:00 interval retains the existing coverage and pixel path.
Sunrise, sunset, sky colors, cloud scrolling, moon orbits and depth occlusion
are unchanged. This is an intentional AmiWind presentation schedule, not a
claim that original Morrowind weather forces every midnight sky clear.

The mode works with either `aw_cloud_control` version. `dbg nightskymode legacy`
or `aw_nightsky_mode 0` removes only this midnight override. For the complete
prior coverage policy, `dbg cloudcontrol legacy` also sets the midnight mode
to zero. Use `dbg nightskymode clear` to restore the new default. The optional
classic/veil choice remains separate. Saved settings override shipped defaults.
Invalid command arguments leave the setting unchanged; invalid direct values
use the default clear mode.

Night-role validation covers opaque index 254 without changing the legacy
daytime validator. Both authored cloud layers clear through the actual tile
composer. A remaining cloud texel still occludes stars and moons; the mode does
not bypass sky/world depth or enable either the stars or night-layer switches.
Interior, master-sky-off and invalid-clock fallbacks retain their prior paths.

Sanitized real-renderer tests exercise the default, all eight old weather days,
both base controllers, all three sky styles and classic/veil cloud types.
The protected interval has 13,692 whole-tile comparisons at every minute,
with matching directional sky-pixel checks. Window boundaries, monotonic
coverage transitions, commands, cache restoration, master switches and invalid
values are covered. Independent old/new renderer builds also match the existing
protected-view output. Both changed C files compile for Amiga 68040 in Linux
Docker. Native visual and frame-cost acceptance for this mode remain pending;
the previously frozen dev3 integration and sealed dev2 artifacts do not contain
this later source change.
