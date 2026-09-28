# Roadmap and implementation options

Core world/cell/chunk design: [WORLD_MAPPING_PLAN.md](WORLD_MAPPING_PLAN.md).

## Build-tool TODOs, 28 September 2026

- Add measured parallelism to independent host conversion stages and per-asset
  work. Native compilation already uses `make -j4`, and some map tools use
  internal threads; the overall conversion pipeline still runs stages in order.
  First identify actual dependencies, then try independent music/terrain work
  and bounded model or audio conversion workers. Preserve stage dependencies
  and avoid concurrent writes to shared output directories.
- Provide a configurable worker limit, account for memory and disk bandwidth,
  and avoid multiplying worker counts with tools that already start threads.
  Keep a serial mode for diagnosis. Compare elapsed time, peak memory and output
  content with the same inputs before choosing a default.
- Preserve live CLI feedback, step separators, progress and per-stage logs when
  jobs overlap. Prefix concurrent output clearly; do not hide it by default.
  Propagate failures, stop dependent jobs and retain completed results/logs.

This parallel execution work is a future task, not a change to the owner's
currently running v0.0.17 test-006 build.

> *Fog only saves rendering work when we also cull what it hides.*

Keep fog shading and visibility rejection coupled. The current renderer already
rejects distant BSP nodes and models against the fog's forward-depth limit;
fog is not being proposed as a new culling mechanism. Geometry within that limit
still needs conversion-time simplification, shared models and measured render
budgets. Preserve partially visible bounds to avoid cutting holes in the view.

AmiWind retains PAL A500, 68000/OCS, 512 KiB Chip + 512 KiB slow RAM,
Kickstart 1.3 as the low-end experiment. A richer 040/FPU/AGA target with
16 MiB Fast RAM and KS3.1 is the current emulator reference. The preferred
optimization target is an A1200 with its original 68020, added Fast RAM and HDD;
that target is not yet playable or proven. Disk images may grow as large as a measured, documented storage
profile supports. Keep public source and private assets as separate deliverables
at every checkpoint. The owner handles Git/GitHub publication.

## Next major milestone: the connected starting area

Owner priority, 27 September 2026: **Seyda Neen exteriors first, then interiors,
then a working local gameplay slice before expansion to other towns.** Complete
the port, lighthouse/islets, bridges, opposing shore, residential connections
and mainland/Silt Strider approach. The strider itself is a desired later visual
landmark; its travel service is a separate task. See the coverage and acceptance
routes in [SEYDA_NEEN_SCOPE.md](SEYDA_NEEN_SCOPE.md).

Inventory town containers alongside scenery now. First preserve their placement,
appearance and collision; then add activation, player/container item transfer and
per-reference state that survives area changes. Resolve ownership, locks, traps,
scripts and leveled contents explicitly instead of silently treating all storage
as free loot. See [CONTAINERS.md](CONTAINERS.md). This system is planned, not
implemented by the current mesh renderer.

Census and Excise is the first town interior **after exterior acceptance**;
the prison-ship interior establishes the opening before that handoff. Load each on
entry and release area-specific exterior resources, retaining compact world and
music state. Measure peak transition memory and repeat entry/exit before adding
more interiors. Host lookup preparation can proceed alongside exterior repairs.

Use the dim opening ship as the first low-light rendering acceptance scene:
test silhouettes, doors, actors, local light falloff, palette banding and readable
UI while measuring lighting/frame cost. Current bright exterior tests are not
evidence that low-light presentation works. See the
[Seyda Neen journal](journals/SEYDA_NEEN.md).

Add a day/night cycle later: persistent game time, exterior sky/fog/ambient
transitions, supported local lights and separate interior lighting. Start with
host-baked lighting/lookup candidates and measure memory traffic and update cost.
Time progression, waiting/saving and time-dependent NPC/quest conditions need
explicit behavior; changing screen brightness alone does not implement them.
Include dawn/day/evening/dusk/night debug presets, exact-hour and freeze controls.
Test locally converted night-sky textures as a low-cost backdrop, then moons/clouds
within measured budgets. Include a small precomputed gradient sun disc, following
audited original timing and correctly occluded by scenery. Add cheap warm
dawn/dusk horizon gradients centered on that same solar direction. This is an impression of lighting, not global illumination.
See [day/night and sky plan](DAY_NIGHT_AND_SKY.md); these commands are not implemented yet.

Record verified asset mappings, implementation ideas, rejected approaches and
symptom/cause/fix/version/regression checks in the
[implementation journal](IMPLEMENTATION_JOURNAL.md). Keep performance history
and local/user acceptance evidence linked rather than replacing their records.

Later combat presentation research: identify the owner's Nexus mod reference
that reportedly visualizes failed attack rolls as dodges/blocks. Preserve the
dice-roll rules and distinguish cosmetic responses from actual gameplay blocks.
Study its behavior, then implement independently without copying the mod's code
or assets. It remains unnamed/unverified; see [implementation ideas](IMPLEMENTATION_IDEAS.md).

## Checkpoint-014 delivered work and next acceptance routes

- Delivered Nord male first-person hands, draw/sheath with F and a visual punch
  on primary attack; preserve walking bob. Hit tests, stamina, damage and enemy
  reactions remain a separate combat milestone.
- Escape opens a pause menu with Return and confirmed Exit; New, Save, Load and
  Options are visible but disabled until implemented. Keep shell `amiwind`
  relaunch and the versioned loading message.
- `amiwind_show_debug` is the master for development overlays, with
  `amiwind_debug_all` as an alias. Accept case-insensitive on/off, true/false,
  and 1/0. Preserve individual selections while hidden. Coordinates have a
  reserved bottom-right strip outside the 3D view; `amiwind_debug_coords`
  toggles it. Keep `showram` off by default; `amiwind_debug_showram` is an alias.
  Crosshair, dialogue, menus and loading feedback are not debug overlays.
- Pier repair: unsigned BSP face-plane indices restore the missing dock faces;
  measured edge/surface overflow is removed by preallocating larger buffers.
  Tune the allocation against high-water marks and model-cache residency;
  an oversized buffer can evict models and create repeated disk reads.
  Reduce visible triangle/edge
  cost through material/UV-aware simplification and distance variants next;
  retain silhouette and doorway/platform collision. Avoid dropping random faces
  to satisfy a hard budget. Fixed-camera profiles must compare equivalent output,
  including restored geometry; smaller textures do not reduce edge counts.
- Continue investigating the owner's pier screenshots: suspended
  geometry, and roads/walkways ending abruptly. Separate source-conversion loss,
  renderer clipping and the fixed scene boundary. This is the Seyda Neen slice,
  not a complete town/world export. Audit selected/skipped references and record
  camera XYZ/yaw for native regression captures before expanding coverage.
- Temporary sea backdrop: expand the simple water/enclosure beyond the bounded
  terrain slice so the cutoff is less abrupt at the normal fog presets. This
  is a demo placeholder while the basic rendering, movement and interiors are
  established. It is not the real surrounding coastline, archipelago, infinite
  ocean or world streaming. Replace it with converted neighboring cells and
  proper streaming/coverage as the map grows; keep this limitation in code notes
  and checkpoint documentation. The land/object export remains bounded.
- Opening/arrival scene is the overall first playable milestone, rather than
  full-world expansion. The pier repair is included in checkpoint-014. Preserve
  the separate position-dependent shack-wall report until reproduced/fixed.
- After the connected exterior acceptance gate, begin the opening in the prison
  ship interior, then the Census and Excise office as the first town interior. Read
  the original DOOR destinations and interior CELL; E loads the separate space,
  returning through its linked exit with a safe position/orientation. Repeated
  trips must preserve music state, release old geometry and report load time.
- Host export now provides ordered INFO lookup tables for Hello/Idle and other voice categories,
  indexed by actor/race/sex/class/faction. Keep condition operands, response IDs,
  original sound paths, order and scripts. Static candidates are not yet eligible
  playback. Multiple appropriate greetings follow a supported condition evaluator;
  unsupported conditions must not turn into unconditional/random folder playback.
- Keep NPC wandering/pathgrids, Fargoth's ring dialogue, combat tests, Balmora
  recall travel, interiors, saves and equipment on the retained queue below.

## Priority debugging controls — checkpoint-014

Delivered and locally verified in checkpoint-014: noclip look-directed flight. W/S move along camera forward/back, including
pitch; A/D strafe; Shift boosts speed. Keep explicit E up / Q down, with immediate
stop on release and no gravity/slope drift. This is a navigation debug mode, not
combat invulnerability. Preserve safe collision re-entry and aw_recover.
Test looking up/down through terrain, steep pitch, diagonal speed limits,
console/menu transitions and restart so no held inputs remain latched. Add `amiwind_debug_reset_location 0` as the numbered recall entry point for
the validated town spawn. Reject unsupported IDs without moving the player;
future points need stable IDs, area identity and safe standing placement.
Keep E/Q vertical movement and aw_recover; the owner
reported that returning above terrain was not discoverable enough.

## Quick usability fixes

On normal exit, show `To restart AmiWind, type: amiwind` at the AmigaDOS prompt.
This launches the executable again; it does not depend on keeping the game in
RAM. Keep the message after shutdown and before returning to DOS.

## Dialogue presentation and font work

The Finnish keyboard's section-key position (left of 1) currently opens the
console smoothly. Reuse the *timing/presentation approach* for a dialogue panel
that slides upward from the bottom, then retracts downward. Keep it separate
from debug console routing/history. Activation faces the NPC, blocks gameplay
inputs appropriately, and restores input without stuck keys when dismissed.

Use a classic Morrowind-inspired black dialogue panel with a restrained warm
border, readable text and clearly distinct topic/choice links. Preserve that
visual character at Amiga resolution; do not reuse the debug console artwork.
Original interface art, if converted locally, remains outside public source.

Keep the current compact font for diagnostics. Dialogue needs a more readable
font at the actual 320 x 200 output size: test letter spacing, contrast, accented
characters, line wrapping, long topic/response text and scrollback. Investigate
locally converting the owner's Morrowind font files through the host pipeline;
converted glyph atlases/metrics remain private derived game data. Alternatively
use a suitable freely distributable font with its license. Do not claim either
approach accepted before native readability and memory measurements. Greyed menu
options must remain distinguishable with the selected palette.

## Checkpoint-013 collision bounds and NPC behavior

Owner confirmation (27 September 2026): the central town-square obstruction is
fixed in v0.0.12-dev2. Track per-iteration confirmations and open reports in
[PLAYTEST_STATUS.md](PLAYTEST_STATUS.md); keep this location as regression coverage.

Bound each architectural convex piece before player-hull expansion. Facet-only
expansion can create remote solid spikes around acute or thin pieces. Keep the
existing slope/stair fixes and walking bob. Use `aw_blockers`/`aw_pos` for exact
remaining town-square reports. This is still approximate collision, not a claim
that every doorway and ledge is solved.

NPCs now have independent idle-pose, facing and proximity-Hello timing, a shared
voice cooldown, and a distance reset. E remains a generic voice audition, not
an interactive dialogue window. Authored AIDT ratings and ordered AI packages
are retained privately by the converter; AI_W range, duration, time, idle weights
and repeat are decoded. No wander package is executed yet.

Next NPC work, before more townsfolk:

Add player/NPC and NPC/NPC collision after validating scaled actor bounds. The
current three actors are deliberately nonblocking. Test doorway and stair
approaches, overlaps at spawn, sliding past an idle actor and later wandering
without pushing the player or recreating stuck-spawn regressions. Keep noclip
and safe recall available during acceptance.

Create a complete private Seyda Neen actor registry: inventory exterior cells
covering the agreed town area plus named interiors. Record NPC base ID and each
placed reference ID, cell, position/rotation/scale, race/sex/body, normal initial
outfit/equipment, voice candidates and authored AI packages. Distinguish shared
base records from separate placements and preserve disabled/deleted/scripted
states; do not blindly spawn every record. Include missing/unsupported assets
and a deterministic fallback policy in the conversion report.

First inclusion target is each actor's recognizable initial appearance, even
before full AI or dialogue. Budget shared model/skin/voice allocations, active
actors and nearby resident actors separately. Cache shared appearances once;
load/sleep/unload by area and distance with stable reference IDs and saved state.
Audit actual actor counts and memory before choosing limits; the existing three
actors are an initial subset, not a complete Seyda Neen population.


1. Bake walk poses from the original skeleton, preserving shared topology and
   matching foot speed to movement. Do not slide an idle model around.
2. Read original pathgrids and choose collision-checked routes inside each
   authored wander radius. Respect stationary/zero-range packages, return after
   interruptions, and handle blocked steps without pushing the player.
3. Suspend locomotion while greeting/activating, turn smoothly, then resume.
   Nearby actors get bounded updates; distant actors should sleep or tick slowly.
4. Add separately filtered Idle speech with a time-based chance. Do not recycle
   Hello samples as idle chatter or fire a random MP3 by voice folder alone.
5. Add full Greeting/INFO selection and dialogue state, then ring quest, combat,
   inventory/equipment changes. Keep Nord first-person hands/punching queued.

Both public/private packages include `docs/FS-UAE-PLAYTESTING.md` and versioned
FS-UAE/WinUAE presets under `resources/emulators/`. Keep pristine images as
checkpoints; run writable copies.

## Checkpoint-012 actor and movement slice

Implemented: host-assembled dressed Fargoth and two Imperial guards, shared
8-pose idle models, nonblocking actors and an E-key generic voice audition.
Full dialogue filtering, quest state and combat remain open; checkpoint-013
adds bounded proximity polling. The player box now matches the scaled base humanoid collision dimensions;
native startup, idle and one stair route passed after ground-support and stair
repairs. Other reported tight spots still need route-specific checking. Keep the preferred Quake bob. See [movement](PLAYER_MOVEMENT.md)
and [checkpoint validation](CHECKPOINT_012_VALIDATION.md).

## Checkpoint-011 startup repair and NPC handoff

Dev4 addresses a reproduced blocked initial spawn. The next acceptance route
must walk immediately after boot, before noclip/recovery, then test recovery
separately. Preserve the owner's now-working door rendering and town details.
Approximate collision still needs ledge/approach tests; a safe start does not
certify the whole town.

Owner playtest after dev4: walking now works from the initial spawn, but movement
near the town centre feels sticky and constrained. This remains a distinct open
regression. Capture a repeatable route and split ground/slope response from
architecture-hull overlap before changing collision. First NPCs must not add
blocking volumes until placement is validated. Combat comes after basic actors.

NPC research has identified the initial actors, base body/outfit records,
leveled guard equipment and original skeleton/text-key animation ranges. Their
ring/voice records have been inspected; Fargoth's ring conversation is text,
not an assumed voice clip. Assembly/baking and native actors remain next work.
See [the research handoff](OPENMW_REF_NPCS_AND_DIALOGUE.md).

## Checkpoint-010 repair scope

The owner's filesystem requester, stuck/falling movement and disappearing door
panels take priority over adding another town. Dev3 corrects legacy image root
metadata, rotated collision and floor-trace merging, adds console/noclip/recovery,
and tests near-door depth ordering separately from distance/PVS culling.
A known camera route and floor sweeps are required alongside existing audio
and restart checks. Do not claim the approximate collision proxies are exact.

Next collision work: test low ledges and door approaches at multiple yaws,
refine conservative hulls only where measured traps remain, and compare standing
height to visible terrain during repeated movement. Next rendering work: keep
door panels with frames, preserve attachment ordering without drawing through
walls, and investigate remaining terrain/roof seams before increasing coverage.

## Player body and first-person hands

- Preserve the Quake walking bob (owner preference, 27 September 2026):
  `cl_bob 0.02`, `cl_bobcycle 0.6`, `cl_bobup 0.5`. Camera motion is separate
  from collision dimensions, grounded movement and stair handling.
- First visible player-body milestone: Nord bare hands in first person,
  assembled from the owner's body-part data with the appropriate first-person
  skeleton/animation. Bake a bounded punching animation on the host.
- Verify handedness, skin/UV seams, wrist cropping, camera-relative position,
  near clipping and animation timing. Test while standing and walking with bob.
- Then wire attack input, hit timing, reach/line-of-sight, damage and reactions
  into a small combat test. A visible punch alone is not working combat.
- Full third-person player model, configurable race/sex and clothing/equipment
  variants follow the shared NPC appearance pipeline. No converted hands,
  character meshes, textures or animations in public source packages.

## First NPC milestone after this repair

Start with Fargoth and two town guards using compact animated alias models.
The host assembles race/sex body parts, heads, hair, equipped clothing, armour
and weapons from the owner's data, then bakes a bounded set of idle/walk frames.
AmiQuake supplies model drawing, not Morrowind actor assembly or gameplay rules.
Start with their recognizable normal outfits and an original greeting from the
owner's files. Validate feet/ground contact, model bounds, palette, memory and
frame cost with one, then three visible actors before filling the town.

For later equipment removal/changes, swap cached complete appearance variants
initially; clothing often changes geometry, not only textures. A body/underwear
base and modular equipment are longer-term options. Do not promise arbitrary
wardrobes, full actor animation, combat AI or dialogue trees in the first NPC
checkpoint. Keep conversion reproducible and all derived character/voice data
outside the public package. Add attack/damage tests only after basic actor
rendering, movement and collision are stable.

## Checkpoint-009 progress

v0.0.11-dev2 replaces convex facade scenery with shared mesh surfaces, corrects
the native music filename fault, restores history controls and verifies shell
relaunch. Linux `build.sh`, public notices and versioned `resources/emulators/`
presets are present. See [validation](CHECKPOINT_009_VALIDATION.md).

The queue below is retained in full: terrain joins and remaining visual gaps,
audio deadlines, Balmora/recall travel, NPCs, dialogue, combat and interiors
still need acceptance. Fixing a renderer or loading a Quake model does not
implement those game systems.

## Current repair and expansion queue (27 September 2026)

1. Repair the v0.0.10 architecture bake: preserve door recesses, deck/support
   separation, full instance transforms, and terrain/structure joins. Diagnose
   the separately reported view-dependent foreground disappearance.
2. Restore OST behaviour and controls: title excluded from in-world playlists,
   shuffled exploration/battle bags, Shift+F5 Previous, Shift+F6 Next, bounded
   buffering and separate transition/underrun evidence. See
   [OPENMW_REF_MUSIC_AND_AUDIO.md](OPENMW_REF_MUSIC_AND_AUDIO.md).
3. Convert a bounded Balmora area using the same pipeline. Add a recall-style
   travel control using owner-supplied sound data, with repeated Seyda Neen /
   Balmora trips, safe spawn points, preserved music state, load timings and
   memory recovery checks. This tests area replacement, not continuous streaming.
4. Introduce recognizable Fargoth and guards: assembled appearance, idle poses,
   collision and one greeting. Then add a small movement/attack/damage exercise
   with explicit limits and profiling. Quake's model renderer does not supply
   Morrowind character assembly, AI or rules automatically.
5. Extract and map dialogue records/conditions, actor identity and quest state
   before claiming functional dialogue trees. Keep NPC/gameplay work separate
   from the image-correctness and audio repair acceptance gates.
6. Add interior cells through the area replacement path: door activation,
   destination cell/position, safe entry orientation, return-door linking and
   persistent state. Provide selectable original-style and modern control
   profiles; modern E activates/uses doors and Space jumps. Verify the original
   mapping against primary documentation before labelling it a faithful preset.
7. Verify clean quit and `amiwind` relaunch from the Amiga shell, including
   repeated sessions. Later add an Escape overlay for resume, restart and quit;
   save/load becomes available only after persistent gameplay state exists.
8. Provide a Linux `build.sh` entry point with a Python build coordinator,
   dependency checks, installed Data Files selection, external private workspace,
   staged conversion/build progress and actionable failure messages. Document
   install prerequisites and reproducible toolchain identities. Never bundle
   game data or ROMs in the public checkout or fetch them for the user.
9. Keep copyright/licence notices specific: original authors retain their
   copyrights; each reused component remains under its own licence; Bethesda
   assets and ROMs are not GPL. Fan-tribute wording is not a licence exemption.

Save a versioned public-source and private playable checkpoint at each usable
stage. Preserve the prior build and comparable performance evidence.

## Completed checkpoint history

- Pipeline 0.1.x: owner-supplied game folder, base terrain/placement audit,
  converted packets, portable C reader and checked source packaging.
- Demo v0.0.1: OpenMW-captured opening, stereo PCM clip, centred speech and boot.
- Demo v0.0.2 / checkpoint-001: native wireframe, WASD/Shift and mouse movement.
- Demo v0.0.3 / checkpoint-002: filled terrain, baked surface colours, dense fog,
  blitter spans, projection tables and frame counters. Owner tested locally.

- Demo v0.0.4 / checkpoint-003: complete installed OST, fixed-size stereo queue,
  original voice, track selection and sustained streaming baseline.
- Demo v0.0.5 / checkpoint-004: native profiler, measured async refill options,
  smaller OFS partitions inside one RDB HDF, damaged-file recovery tests.
- Demo v0.0.6 / checkpoint-005: AmiWind name/version banner, exploration/battle
  playlists without consecutive duplicate songs, original static scenery export
  and host turntables. Native scenery rendering remains pending.

- Demo v0.0.8 / checkpoint-006: native AGA textured town, bounded BSP buildings,
  tree sprites, palette fog, WASD/mouse, whole-song stereo playback and profiling.
  Emulator 040/FPU reference only; stock 020 target and NPCs remain open.

- Demo v0.0.9 / checkpoint-007: startup dependency hotfix and linked-binary gate;
  separate 3.1/3.1.4 smoke records; unchanged world/audio payloads.

- Demo v0.0.10 / checkpoint-008: 68000 hardware/RAM preflight, checked Fast-memory
  hunk allocation and current WinUAE profiles. Audio deadlines at reduced CPU
  speed remain a measured optimization target.

## Current work: automatic scenery conversion and measured rendering

- Shared BSP architectural meshes replace convex facade proxies in dev2. Refine
  terrain joins, source texture seams and multipart collision before expanding.
- Profile world surfaces, models/sprites, C2P, mixer work, memory and I/O separately.
- Bring up a 68020/no-FPU build without loading the Workbench desktop; distinguish
  OS library dependencies from desktop memory use.
- Keep JIT/maximum-speed emulation separate from stock-machine claims.
- Add one stationary NPC with interaction and an owned greeting before crowds,
  inventories, animation variants or quests.
- Move from a resident scene to measured chunk residency/prefetch only after the
  renderer and collision workload are bounded. Prebaking is host work; HDD storage
  does not execute animation, collision or gameplay logic for the Amiga.

## Previous scenery milestone

The full soundtrack, playlist fix and first static-model translation are complete.
See TRANSLATION_LAYER.md for the two runtime routes and SCENERY_FORMAT.md for
measured source-asset budgets. Keep
profiling as scene complexity grows, record frame pacing alongside averages,
and preserve each tested build. See PROFILING.md and ENGINE_STUDY.md for measured
results and the Doom/DoomAttack/AmiQuake source study.

## Storage and runtime options

| Option | What it buys | Decision gate |
| --- | --- | --- |
| AmigaDOS files on a modest OFS HDF | Simple 1.3 boot, inspectable files | Current baseline; measure filesystem/read CPU cost |
| Indexed asset file | Fewer names, batched sequential requests | Compare to individual files before adopting |
| Reserved raw asset partition | Potentially less filesystem overhead | Implement bounds/device discovery; prove improvement and clean exit |
| Large UAE image with 64-bit access | Room for extensive baked variants | Verify exact API/driver; label emulator-specific dependence |
| A1200 / Fast RAM / accelerator | Larger cache and more CPU capacity | Separate build/profile; preserve A500 baseline |
| Pre-rendered views or billboards | Recognizable scenery with less geometry work | Assess camera freedom, occlusion, scaling and storage demand |

See [storage profiles and limits](STORAGE.md). Below 4 GiB is not a universal
old-controller compatibility guarantee. 8/16/32 GiB images are candidate
configurations, not implemented support or assumed speed improvements.

## Next visual checkpoint

Refine terrain and structure joins, remaining roof gaps and pier traversal in
the current mesh scene. Trees/buildings are CELL placements separate from LAND
height samples; they are already visible in AGA. Then reuse a parameterized
scene pipeline for Balmora and measure area replacement. Keep correctness and
worst-frame timing gates before expanding the resident scene.

## Audio effects and world cache

Add movement effects beside music/dialogue, explicit channel ownership and
sample-position-preserving handoff. Cache likely effects/voice and nearby world
chunks. Test simultaneous audio reads, turns, cell boundaries and hilltop views.
No hardware unit performs MP3 decoding or general 3D transformation for free.

## Host character baker

Use OpenMW on the PC for actor assembly, equipment and animation where practical.
Bake a bounded set of body/appearance/pose/view combinations. Reusing OpenMW
source requires its applicable licence and notices; current native code is
independent and the repository bundles neither OpenMW nor Hunter code.

## Later interaction and compatibility

Collision, doors, NPC interaction, dialogue conditions, inventory, combat, quests
and scripts are separate milestones. A complete game port is not established by
terrain rendering or asset conversion. Every public release requires the user's
original game files; converted game assets and ROMs remain outside that release.

For the first Fargoth/guard milestone, see [NPC and greeting behaviour](OPENMW_REF_NPCS_AND_DIALOGUE.md), including the requested UESP voice reference and OpenMW selection/trigger paths.

## Waterline and topographic diagnostics

The temporary sea-height reference is visible by default; the console command
`amiwind_debug_sealevel on/off` hides/shows its surface without changing physics.
Its current Z=0 plane helps compare the pier and terrain heights. For a later
host topomap, draw source LAND contours and the selected waterline, mark the
converted-cell boundary, and leave unconverted areas clearly identified rather
than inventing elevations. Verify cell water metadata before generalizing the
datum to interiors or other regions. Replace the expanded sea placeholder as
proper surrounding map coverage becomes available.

## First complete vicinity

Use [SEYDA_NEEN_SCOPE.md](SEYDA_NEEN_SCOPE.md) and the owner's UESP map as the
coverage target: town/tradehouse, shacks, lighthouse peninsula, docks, Census
buildings, prison-ship arrival and Silt Strider approach. Audit neighboring source
cells before choosing smaller runtime streaming chunks. Fix origin-only object
selection and explicitly handle supported visible activators. Keep the prison
ship/hatch/gangplank and character-generation state coherent. Checkpoint-015
restores the static assembly; opening-state removal still needs implementation. Opening and office entry/exit remain
ahead of distant-region expansion.

## Open incomplete terrain/rock formation report

Reproduce the checkpoint-014 screenshot's incompletely drawn terrain/rock formation
beside the road. The owner clarified this is missing/malformed formation geometry.
Compare original LAND/placed rocks with conversion at the same XYZ/yaw. Diagnose
source topology, selected coverage and render visibility separately. Use the
new `dbg coords on` / `dbg pos` aliases to collect coordinates. This remains
open; see [playtest status](PLAYTEST_STATUS.md).

## Checkpoint-016 playtest steering (27 September 2026)

- Console: compact font by default; retain normal readable and retro fonts.
  Shift + physical key left of 1 (Finnish §), or Shift+F10, toggles full/half
  height. PageUp/Down and Shift+Up/Down scroll. `debug overlay off` aliases the
  existing debug-only master switch; accept on/off, true/false and 1/0.
- Coordinates: add heading and pitch so a reported disappearing surface has
  both position and camera orientation. Do not call a location-specific bug
  fixed without reproducing that view.
- Keep first-person 3D hands and their conversion path. Add a compile-time
  `--hands 3d|sprites` selection; bake sprites from the same owned poses.
  Compare idle/draw/punch/sheathe visibility, frame cost, RAM and loading cost.
  Owner reports flicker and weak/transparent-looking hands in checkpoint-015.
- Exterior ship gaps: deck `(804,-311,61)`, bow `(615,-548,74)`, detached edge
  views `(777,-373,61)` and `(790,-413,62)`. Preserve the current silhouette as
  reference; check source surfaces, winding, LOD and renderer before changing
  shape. Simpler straight bow sections are an experiment, not an assumed fix.
- Pier A/B: retain the current separate-plank conversion; add an optional
  joined, textured deck while preserving outline, supports and collision.
  Capture from `(630,-388,56)` and walking-height side views; measure surfaces,
  edges, frame stages and RAM. No universal flattening of source meshes.
- Distant-building A/B: keep current geometry as baseline. Try baked backdrops
  only beyond the interaction range. Check parallax, silhouettes and entrances.
  Open house-disappearance report at `(-41,715,69)` needs heading/pitch.
- Height audit: current collision dimensions come from base_anim's bounding
  box; eye height was a prototype 90%-of-height choice. Compare the first-person
  Camera bone and Nord scale separately. Preserve the successful width.

## Checkpoint-016 outcome and next priorities

Implemented: first dim prison interior, bidirectional hatch loads, compact/full
console and scrollback, overlay alias, DEG/pitch, calibrated Nord eye height,
compile-time hand sprite experiment with the 3D path preserved. Full verification
and exclusions: CHECKPOINT_016_VALIDATION.md.

Next: reproduce exterior ship deck/bow gaps and the terrain/rock formation using
XYZ/DEG/pitch; audit ordinary scenery bounds for the disappearing house near the
current coverage edge. These are OPEN, not closed by adding an interior. Then
complete the opening walk/actors and Census office with the same scene pipeline.

Keep the joined-plank textured-pier and distant-building-backdrop alternatives
as explicit A/B recipes. Require connected walkable outlines, interactive doors,
collision/occlusion parity, counts and fixed-camera performance evidence. Neither
experiment is implemented in this checkpoint. Lift scene choices into a validated
recipe schema after the two-scene pipeline stabilizes; preserve all source and
conversion reports so later areas inherit lessons rather than manual patches.

## Recovered owner list, 27 September 2026, 22:17 Helsinki

The complete active register is [SEYDA_NEEN_NEXT_STEPS.md](SEYDA_NEEN_NEXT_STEPS.md):
interior structural regression first; town-edge/Silt Strider audit; exterior and
interior actor rosters; authored activities and conditioned speech pools; container
placement/state/refresh; separate interiors and door lookup tables; opening and
hatch state; sky fallback, sun, night torches; audio deadlines; exterior method_001.
Do not drop these items when handling the immediate geometry regression.

### Water feedback and scene-picker follow-up

- [ ] Separate blueish underwater presentation from red damage feedback and
  mapped hurt audio; test harmless immersion, damage and surfacing.
- [ ] Track the owner's v0.0.15-dev1 slowdown against identical fixed-camera
  runs; new exterior report: XYZ 211 447 47, DEG 4, P 0.
- [x] Scene-picker command `dbg scene change` (also `debug` and `amiwind debug`);
  host/native acceptance passed in checkpoint-017. See SEYDA_NEEN_NEXT_STEPS.md.

### Opening-state residency

- [ ] Host audit of original opening scripts: stages, actor prerequisites,
  controls, dialogue waits, door/menu transitions and disabled references.
- [ ] Persist compact opening state across the already separate interior/exterior
  scenes; remove the disabled ship assembly on post-registration town loads.
- [ ] Compare baked dim lighting with bounded AmiQuake-style dynamic lights for
  torches; retain the static path and measure cache rebuild/audio costs.

### Adjustable visibility and appearance A/B

- [x] Live fog/draw-distance aliases and first Options → Graphics slider,
  default/Medium 700 local units; 10/1-unit normal/Shift steps. Native check passed.
- [x] At the slow camera (-44,259,75), yaw328/pitch-14, compare 700/400
  coupled fog/culling on the same machine: one short native sample gives
  11.46 vs17.21 FPS. More views and physical-machine validation remain.
- [ ] Preserve whole-exterior method_001; test separate texture/geometry candidates
  and reject missing-scene geometry as a false optimization.
- [ ] Bake a low-poly Silt Strider landmark candidate from the owned ACTI model.

- [x] Default-off `dbg fps` counter, roughly one-second average, respects debug master.

## Next milestone after checkpoint-017 and recovery backup

- [ ] Audit the original ship-waking sequence, script gates and voice-completion
  pacing; distinguish scripted waits from time taken by the player.
- [ ] Add an opt-in first intro sequence and dark bordered subtitle/message boxes.
- [ ] Evaluate original Fonts/*.fnt + *.tex conversion as a selectable UI font.
  Keep readable/retro atlases and all existing font selection paths.
- [ ] Preserve existing feature variants and immutable checkpoints; follow the
  non-destructive experiment rule in DEVELOPMENT.md.

Recovery snapshot work takes priority until all required owner data, source,
toolchain and handover files are durably saved. Intro implementation has not begun.

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

## Persistent world and disk loading direction (v0.0.16 planning)

See [the proposed implementation approach](PERSISTENCE_AND_STREAMING.md) for
state ownership, stable IDs, cell loading, memory budgets and save recovery.

Keep converted cell data immutable and identify placed objects with stable source
reference IDs. Save deltas for doors, containers, removed items, NPC state and
quest variables separately. Global quest/time state must survive cell unloading.
On cell load, apply saved deltas to its base data. Begin with explicit cell/door
transitions and bounded resident memory; investigate adjacent-cell preloading
after measuring RAM, disk latency and audio deadlines. A larger HDF increases
storage capacity without making all content resident. This is a design direction,
not implemented save support or seamless streaming.
