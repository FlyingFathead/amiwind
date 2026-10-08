# Roadmap and implementation options

## Next: v0.0.33 - Towards CHIM: Replacing the Engine Block

v0.0.32 (Last Stop on the Old Line: Window-Shopping in Vivec) is out: the last
release on the AmiQuake-based legacy engine and the legacy builder, with the
Vivec Arena as an outside-only preview ([release notes](RELEASE-v0.0.32.md)).
v0.0.33 is the first release on the CHIM engine, the world streamer (plan
below and [world streamer](WORLD_STREAMER.md)).

## v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec (released)

v0.0.31 (Lamps, Lanterns and Loading) was out. v0.0.32 started with Vivec, built
by the generic town importer with no hand-building, and with fixes found by
measuring the whole island on 8 October 2026
([world progress](trackers/WORLD_PROGRESS.md), [bug register](BUGS.md)):

1. **Vivec first.** The Arena and the cantons through the normal doors, after
   the limits that block them: texture mappings read unsigned (32,767 to
   65,535, [VIVEC-TEXINFO-31](bugs/VIVEC-TEXINFO-31.md)), leaf face lists read
   unsigned ([MODEL-MARKSURF-SIGNED-31](bugs/MODEL-MARKSURF-SIGNED-31.md)),
   surface extents ([MESH-EXTENT-GRID-31](bugs/MESH-EXTENT-GRID-31.md)), the
   lightmap overrun ([LIGHTMAP-TAIL-31](bugs/LIGHTMAP-TAIL-31.md)), the night
   lamp cache ([LAMPS-CACHE-31](bugs/LAMPS-CACHE-31.md)) and interior
   coordinates ([INTERIOR-COORDS-31](bugs/INTERIOR-COORDS-31.md)).
2. **Real 68040 compatibility and speed.** The engine reaches FPU instructions
   the 68040 does not implement, every frame, and the boot disk loads no FPU
   support library; the emulator hides both
   ([ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
   [ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md)). Fixes reuse
   Quake's own answers: no rotation for unrotated brush models, table
   sine and cosine, work done once per frame.
3. **Distant shells.** Buildings far away drawn as closed low-poly shells
   instead of full meshes, so the town stays visible without its full cost
   (prototype on Balmora first).
4. **Your own estimate.** A builder command that estimates every map of the
   island from your own Morrowind files, shown as a layer on the Toolkit's
   World Map.

Before the v0.0.32 release (fix-before-release list):

- Visiting Vivec: `dbg tp vivec` takes you to the Vivec Arena preview (outside only;
  its doors do not open yet), and the release notes say so
  ([DEBUG-TP-TOWN-NAMES-32](bugs/DEBUG-TP-TOWN-NAMES-32.md), fixed in source).
- A from-scratch build with the repository builder reproduces the release payload,
  file by file, with the recorded Seyda Neen exception
  ([BUILD-WORLD-LAYOUT-DRIFT-32](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md) byte check
  included).
- No private-test waiver: the Arena residents pass the actor check or are left out
  ([VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md)).

### Decided: a world streamer with no duplicated assets - the whole game on one hard file

Keep the AmiQuake engine (renderer, lighting, collision, QuakeC) and change how
the open world is stored: every asset stored once and placed by reference, as
Morrowind itself does (its base game holds all meshes and textures in about
310 MB and the whole world in an 80 MB file), streamed around the player.

**Why.** Today every exterior region is a self-contained Quake map holding
everything visible from it, so each exterior object is stored about ten times
([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md); Seyda Neen
24 times per face, Balmora 7 times, [sub-cell redundancy](SUBCELL_REDUNDANCY.md)).
Two towns and the terrain already take 4.8 GB; with today's pipeline the whole
game would need about 24 GB (15 legacy partitions), and the oversized regions
cause most heap failures. Quake's `vis` gives little outdoors
([town visibility](performance/TOWN-VISIBILITY.md)), so the new layout gives up
nothing it was providing.

**Measured result (8 October 2026, estimate built from the game's own data:
every unique mesh, collision hull and texture counted, light per placement
checked against real bakes; [asset census](ASSET_CENSUS.md),
[streamer design](WORLD_STREAMER.md)):**

| | Today's pipeline | World streamer |
| --- | ---: | ---: |
| Whole game, all files | about 24 GB | **about 1.75 GB** (a leaner layout 1.61 GB) |
| Legacy-safe drive images (under 4 GiB) | 8 | **1** (estimated; see the note below the table) |
| Every texture of the game | about 1.4 GB (a copy in every map) | **19 MB** (each stored once) |
| Island terrain | about 1.8 GB compiled | **17 MB** as a heightfield |
| Exterior model variants | 33,076 | **1,405** meshes (scale and tilt applied at run time) |
| Worst memory around the player | regions over the heap budget | **4.9 MB** with 256-unit chunks |
| Largest load while walking Balmora | 4.6 MB per region crossing | **0.8-1.4 MB** per chunk |

The non-map part of these totals (sound, music, video, the NPC gallery) is still
v0.0.31's, which covers two towns: the whole game's actors and voices will add to
it, so expect the hard file to be well over half full, but still one hard file.

The target is the whole game on one legacy-safe drive image (under 4 GiB, with
partitions under 2 GiB); two images is the absolute limit. Every file follows
classic FFS: files well under 2 GiB (asset packs of about 1 GiB at most, split
by area), names of at most 30 characters, few files per directory, packs
written last and whole in map order. The builder will check this layout.

**How it works:**

- **Asset packs** (Quake PAK files, split by area and stored in map order): each
  mesh, collision hull and texture once, one shared texture pool.
- **Chunks** (grain still to be measured; 256 units looked best on memory, larger
  chunks need fewer disk reads): each holds terrain (compiled per chunk first; a
  quantized heightfield built at load is a later optimisation, because collision
  then needs a new path) and a list of placements: which mesh, where, which
  way, how large, and a lighting record.
- **Scale and tilt at run time** for drawing; collision hulls stored once and
  expanded per placement at load.
- **Three lighting tiers:** terrain keeps its lightmaps; buildings, furniture
  and rocks get lightmaps per placement on shared geometry; flora and clutter
  get one light level each (outdoor objects already have no lightmaps today).
- **Memory:** a ring of chunks around the player inside draw distance, loaded
  ahead of you and released through Quake's cache (made able to move brush
  models); a loader process reads the disk while the game keeps drawing;
  coordinates re-centred as you travel so they stay within Quake's range.
- **Distance tiers** for the frame rate: full detail nearby, closed low-poly
  shells further out, the horizon beyond.
- **Interiors** stay legacy Quake maps behind doors in the first CHIM releases.
  Moving their pieces to shared placements later removes the 220-model limit, but
  then they also need the per-sector visibility lists outdoors needs, because
  placements are not culled by Quake's `vis`.

**Plan:**

1. **v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec** (released, the last
   release on the legacy engine and builder, built from scratch): Vivec with today's format; the measurements behind the
   streamer (census done; renderer counters and a cycle-approximate emulator
   profile in progress); real 68040 safety (no library sine and cosine per
   frame, Quake-style number parsing, your own FPU support library if you have
   one); a map loader without temporary copies; one shared face builder with a
   validator; builder types: today's region pipeline kept as the "legacy"
   builder, CHIM as the new one (named, not numbered; CHIM has its own version).
2. **v0.0.33 - Towards CHIM: Replacing the Engine Block** (next, the first CHIM engine release): the streamer (CHIM builder and engine 0.1.0) on Balmora, Seyda Neen and the cells
   between them, measured against v0.0.31 on the same routes: worst frame time,
   bytes per crossing, memory peak, saves mid-stream.
3. **Next:** the south-west corridor (Seyda Neen, Pelagiad, Balmora, Vivec,
   Ebonheart exteriors), then the rest of the island release by release. CHIM 1.0
   is the release in which the whole island runs; expect months, not weeks.

Repository layout from v0.0.33 (decided 8 October 2026). CHIM is the same AmiQuake
engine growing a streamer, not a second engine, so the engine stays one tree:

- `engine/aga/src/` remains the one engine; CHIM's own code (model library, chunk
  loader, world shift) lives in `engine/aga/src/chim/` with small hooks in the
  Quake files. "Legacy" is the old code path, used whenever no CHIM data is
  present, and the v0.0.32 tag.
- `tools/chim/` holds the CHIM builder. The parts both builders use (model and
  texture conversion, BSP writing) move step by step into one shared package, so
  the legacy builder and CHIM call the same code rather than copies.
- `docs/chim/` holds the CHIM format, design, measurements and release notes.
- Licences stay clear per folder: the engine is GPLv2 (from Quake), the builder
  GPLv3.
- Existing files move only after v0.0.32 ships, in one restructure commit with
  `git mv` (history follows) and the path tests and release file list updated
  in the same commit. Until then CHIM work only adds new folders.

The open question is speed on a real 68040: every figure so far comes from the
emulator ([BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md)), so a small
benchmark for real accelerated A1200s is being prepared. How data streams
today: [DATA_STREAMING.md](DATA_STREAMING.md).

### Near future: fires and lava across the world

- **Fires everywhere.** The new hearth fire (flames shaped by each Morrowind
  emitter, a hot colour ramp and rising embers) reaches every fireplace,
  brazier, campfire and firepit as maps are rebuilt; each keeps its baked
  light, and Morrowind's flicker and pulse light flags become Quake light
  styles so the firelight flickers (cost measured on the 68040 first).
- **Lava fields** (Red Mountain and the Ghostgate approaches): Morrowind's lava
  surfaces converted to Quake liquid surfaces, which the engine already draws
  with an animated warp and full brightness, with lava contents (orange view
  tint and damage when entered) and a few embers rising from the surface.

Before building more of the world at scale: the [trackers](trackers/README.md)
(world progress, entities, points of interest), so nothing is left behind.

After that: lighting follow-ups, a battle-arena test room, then inventory,
character statistics, a map that reveals as you travel, and the heap option
below.

## Planned: heap size matched to the host machine, 7 October 2026

The game heap is a fixed 11 MiB. On the reference configuration a fully loaded
Seyda Neen sub-cell leaves only about 2.6 MB of it for cached models, so each
crossing evicts and re-reads actor models
([Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md)). Accelerated Amigas such
as an A1200 with a PiStorm32 Lite or a full 68060 board have far more Fast RAM
([hardware FAQ](FAQ.md#can-todays-heavily-upgraded-amigas-realistically-run-amiwind)).

Plan, measured before it is built:

1. Emulator test: more Fast RAM and a larger heap on the same Seyda Neen route.
   Continue only if evictions and crossing times improve clearly.
2. Startup check: when much more Fast RAM is available, ask whether AmiWind may
   use a larger game heap (Y/n). The choice is saved and can be changed in
   Options; the engine falls back to 11 MiB if the larger allocation fails.

The baseline does not change: AmiWind must stay playable on the reference
configuration with the 11 MiB heap. Memory budgets, release gates and
acceptance stay measured there, and nothing may depend on the larger heap.

## Other ideas and wildcards

Ideas worth keeping, not scheduled. They wait until the work they depend on
exists.

### Weather: ash storms and blight winds

Morrowind's regions have their own weather, and two kinds define the land
around Red Mountain: ash storms and the red blight winds. Both belong in
AmiWind at some point, built from what the engine already has: the
[day and night sky](DAY_NIGHT_AND_SKY.md) layers with faster, darker clouds,
the distance fog pulled in close, a full-screen colour tint like the one Quake
uses under water and in lava (ash grey, blight red), and a capped stream of
wind-driven grit from Quake's particle system, plus the storm sound. Each
region keeps its Morrowind weather chances; the cost is measured on the 68040
before it ships.

### Long-term possibility: a reusable Amiga game engine

Underneath the Morrowind content, AmiWind is becoming a general open-world
toolkit for AGA Amigas, all GPL: streaming sub-cell worlds with bounded memory
and build-time memory budgets; a converter pipeline from large 3D scenes to
Quake BSP maps; glow, NPC floor lighting, emitter-shaped flames,
Quake-particle embers and warped liquids; menus, rebindable controls, a book
and journal reader, music streaming, saves, dialogue and first-person hands;
and headless emulator testing, a debugger harness and heap auditing.

Someone making their own Amiga RPG, dungeon crawler or adventure game could
start from this instead of from zero. The aim: document the engine and tools as
reusable on their own, separate from the Morrowind conversion, with a small
example project that uses no game data.

### Long-term possibility: Lua scripting

Game logic today runs in QuakeC (the engine's built-in script VM) plus C.
A small Lua interpreter could later carry quest, dialogue and event scripts
(Morrowind's own scripts translated at conversion time) and make AmiWind
moddable without recompiling. To be decided by measurement on the reference
Amiga: the interpreter's code and heap cost against the 11 MiB budget, script
speed on a 68040, and whether it replaces or complements QuakeC.

### From Quake Arena to Vivec Arena: two-Amiga 1v1 duels

Once the battle arena and its test fights work, two Amigas could fight each
other: a 1v1 player-versus-player arena under a new **Extras** entry in the
main menu.

- **Link options.** A null-modem serial cable between the two machines, or
  TCP/IP over a network: an A1200 can take a PCMCIA network card with a
  standard Amiga TCP/IP stack. A TCP/IP stack can also run over the same
  serial cable (SLIP/PPP), so one network layer could serve both; a raw
  serial path (through `serial.device`, or directly through the Amiga's UART)
  remains an option for the lowest latency.
- **Bandwidth is small.** A duel needs two players' positions, view angles and
  action events (attack, block, hit, dodge), sent 10-20 times a second: a few
  hundred bytes per second, well within a 19,200-baud serial link. Quake's own
  network protocol, which the engine source still carries, was designed for
  28.8k modems.
- **Fair results.** Combat follows the arena rules (Morrowind's hit chance,
  shown as dodges and parries). One machine decides each roll and sends the
  result, so both screens agree.
- **The venue.** Morrowind already has the right place: the Arena Pit in
  Vivec's Arena canton. Converted on its own, it makes a small, closed duel
  map: from Quake's arenas to Vivec's.
- **Scope.** Two players, the arena map, no world state. Both machines run the
  same AmiWind version and their own copy of the converted game data; only
  game state crosses the link.

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

## RC1 regression priorities: 2026-10-06T15:03:42+00:00

Keep Temple partial geometry/collision, Seyda traversal lighting and maximum-punch
coverage open until their exact native reproductions pass. The inspection-room
timing failure and dim-floor issue are tracked separately in
[DEBUG-GALLERY-TIMING-29](bugs/DEBUG-GALLERY-TIMING-29.md); restore those tools
before using them to accept torch or combat repairs. Building-only1.2 brightness
now has bounded Census/cave native evidence. Broadening cave brightness, town
subdivision tuning, alternating punches, torch fuel and disk-backed console
history remain distinct follow-ups. See the [current bug checkpoint](BUGS.md).

## Building brightness and inspection tools: next candidate

Implementations for building-only `dbg interiorluma` (default1.2), empty-floor
`dbg combattest` and dark-room `dbg torchtest` have passed focused source checks.
Complete combined/native acceptance before claiming availability in a playtest.
Caves remain unchanged. Use these controls for subsequent lighting and hand
acceptance; keep Temple-only geometry repair and the punch-hole defect open.

## Next candidate: Seyda lighting boundary correction

The empty-versus-unused lightdata cause is isolated and the narrow renderer
correction passes six focused checks. Complete integrated checks and native
walking acceptance before marking it fixed. Review Seyda subdivision cost later;
Balmora/open-country performance observations do not establish cell count as cause.
See [lighting evidence](DAY_NIGHT_AND_SKY.md).

Interior pipeline gate: use [the partial Temple failure and intact upper-route control](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) to add stage-specific structural accounting, shifted-origin invariance and visible/collision coverage regressions. This follows the current lighting repair priority.

## Balmora Temple geometry/collision report: 6 October 2026

**[BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md): open, major,
final-release blocker.** RC1 WinUAE playtesting found multiple missing walls,
floors and structural connections; the player can accidentally pass through.
Primary reported local position: **1063,1048,3700**, heading E076, pitch65;
additional captures span game05:22 to06:11. Cause and introducing version are
unknown. No repair candidate or shipped fixed version exists yet. Preserve
visual and collision regressions together and verify the repair in FS-UAE/Docker.

## RC1 comparative traversal feedback: Balmora and Seyda Neen

Owner playtest, 6 October 2026; recorded 2026-10-06T13:48:58+00:00: Balmora feels smoother than
Seyda Neen, with very short loads even when running through its streets. More
open fields also felt acceptable on the owner's tested route. Preserve these
as subjective route-specific results, not measured timing or whole-world approval.

The owner suspects Seyda Neen's sub-cell count/partitioning. Compare equivalent
routes for crossing frequency, resident/transition RAM, geometry, entities,
load duration, audio continuity and frame time before attributing the difference.
Roadmap follow-up: review town partitioning **after LIGHT-EXTERIOR-JUMP-29**.
Fewer cells must not sacrifice Amiga reserve or hide the brightness discontinuity.

## Console history working-set investigation: 6 October 2026

The owner requests disk-backed debug output scrollback, loading old pages only
while the game is console-paused. Current source uses a fixed **16 KiB output
ring**; command recall is a separate **8 KiB** array. Console resizing also uses
a transient **16 KiB stack copy**. Output history does not grow without bound.

Evaluate a small resident recent-page cache plus bounded disk history and index,
with explicit pause-state checks before historical reads. Batch writes outside
frame-critical work, preserve readable failure behavior, and bound file growth.
Report net RAM after indexes/cache and measured I/O/audio/frame cost; the gross
saving is at most the current output ring, not the separate command history.
Existing `-condebug` writes per message and is not a suitable streaming design.
Fix CONSOLE-WHEEL-29 independently rather than adding disk I/O to its input path.
Status: investigation requested, no disk-backed implementation yet.

## Seyda Neen partition review after lighting repair

6 October 2026 owner RC1 playtest: load-ins/outs feel acceptable while walking
through the more open fields. The owner asks whether Seyda Neen has too many
sub-cells. Preserve this route-specific positive feedback without calling all
streaming solved. **Fix LIGHT-EXTERIOR-JUMP-29 first.**

Later compare the same town route with its current split and a measured
coarser/merged candidate. Record crossings per distance, peak live/transition
RAM, loading pause, time to first world frame, steady frame cost and audio
continuity. Fewer cells reduce handoff frequency but can increase resident
geometry/texture/entity load; keep the Amiga reserve and collision/coverage gates.
Do not merge cells merely to hide a lighting-state defect.

## FPV combat action creation pipeline: RC1 baseline

Requested 6 October 2026; recorded 2026-10-06T13:34:07+00:00. Keep the RC1 race/sex fist models
as immutable inputs for an adjustable first-person action pipeline. This is
new conversion/preview work, not an implemented editor or a shipped correction.

The pipeline should retain original animation/mesh identity, expose bounded
camera-relative offsets and per-action/per-frame adjustments, and export a
fresh candidate plus a repeatable profile. Preview idle, draw, lower and the
entire punch sequence at the actual viewport/FOV/near plane, with exact frame
selection and contact sheets. Compare the unchanged baseline side by side.

The initial target is the exposed camera-near forearm at maximum extension.
Moving the arm toward the player's viewpoint is a requested framing candidate;
measure which axis/direction improves coverage before adopting it. Distinguish
UV loss, open geometry, face culling and near-plane clipping. Repositioning alone
must not be called a topology repair or accepted if another pose opens a hole.
Retain surface connectivity and validate any explicit cap/stitch separately.

Add right/left unarmed sequencing using verified source animations or an
explicit derived-animation profile. Preserve held equipment and race/sex
appearance. Reuse decoded source data and profiles to avoid repeated full
conversion; load only the selected runtime model. Record triangle/vertex count,
model/cache bytes and render cost alongside the coverage result. Preview tools
and profiles can be public; original/converted game assets remain locally owned.
The existing sprite baker's neutral projection is a framing aid, not acceptance
of the actual game renderer's clipping or lighting.

## Unarmed right/left sequence request: 6 October 2026

Recorded 2026-10-06T13:23:09+00:00. Successive accepted bare-knuckle attacks should alternate
**right, left, right, left**. The current converter samples only
`handtohand: chop start` through `handtohand: chop large follow stop` as one
ten-frame punch clip; alternating hands is not implemented in RC1.

Inspect the owned first-person animation catalogue for authored left/right
motions before choosing their conversion. Do not describe strict alternation
as verified original-Morrowind behaviour merely because it is requested here.
Add a second attack only when its appearance, timing and fallback contract are
explicit; count one accepted attack per input and avoid switching sides midway
through a punch or a cell handoff. This is an animation requirement, not a claim
of implemented combat damage or combo rules.

The owner further localizes HAND-PUNCH-COVERAGE-29 to **maximum arm extension**.
Inspect that pose and adjacent/interpolated frames on both arms. Fix visible
forearm coverage before accepting the new sequence. Preserve race/sex appearance,
held-item behavior and a bounded selected-model working set; measure any extra
frame/cache cost rather than retaining all race animations in RAM.

## RC1 fist appearance and punch coverage: 6 October 2026

Preserve the owner-accepted fist improvement. Repair and target-test the
marked camera-near forearm coverage during punching before final release;
[HAND-PUNCH-COVERAGE-29](FIRST_PERSON_HANDS.md#hand-punch-coverage-29-exposed-forearm-during-punching-in-rc1)
tracks topology, animation and clipping checks separately from torch grip.

## Additional RC1 reproduction gates: 6 October 2026

- Reproduce and fix the Census Office door snag, retaining collision and safe
  passage in both directions after opening and after save/reload.
- Investigate abrupt outdoor brightening near shacks with no carried torch;
  separate map/light-state handoff from clock/weather changes.

Both are open playtester reports with unconfirmed causes. See [the follow-up](BUGS-v0.0.29-RC1.md#rc1-door-snag-and-outdoor-brightness-reports-6-october-2026).

## Post-delivery RC1 priorities: 6 October 2026

RC1 is now a delivered private playtest. Final **More Mushrooms** remains the
current release goal; the combat milestone follows it.

- Preserve owner-accepted appearance-entry music and Go back / Choose borders.
- Deliver and playtest bounded Options/Interface/Audio navigation and the 75%
  Effects default, retaining saved settings. Source checks pass; these edits
  are not in the published RC1.
- Resolve the remaining guard-follow Enter jump and investigate OST crackling
  during ship-to-deck loading as separate audio cases.
- Investigate Census Office NPC lighting independently of environment surfaces
  and the carried-torch case; require controlled target evidence.
- Continue the existing hand/grip, memory reserve, world/interior mushroom
  coverage and outdoor traversal gates; these new observations do not close them.

The [current issue matrix](BUGS-v0.0.29-RC1.md#rc1-owner-playtest-follow-up-6-october-2026)
records owners, next checks and bounded acceptance. Earlier dated plans remain
historical context.

## Historical: v0.0.29-rc1 work, following published dev4

The published development checkpoint is
[v0.0.29-dev4](https://github.com/FlyingFathead/amiwind/releases/tag/v0.0.29-dev4).
Next comes the rc1 playtest, then final More Mushrooms once worldwide picking
and the final-release gates pass. The [current release plan](PLAN-v0.0.29.md)
tracks scope and next evidence steps; [BUGS.md](BUGS.md) is the issue-status index.
Current blockers include NPC torch illumination, connected torch-bearing hands,
the Enter-music regression and world-map admission. Flame visibility and the
low-memory warning also require their own checks. Outdoor crossing smoothness
remains open performance work. The combat arena follows this release.
Source candidates, packages and target-verified fixes are distinct states.
Earlier plans below preserve historical scope and evidence.

### Asset coverage accounting

The dated [asset coverage report](ASSET_COVERAGE.md) separates available source
files, converted output, packaged output, runtime acceptance and geographic
coverage. Update it when omissions are discovered or resolved and reconcile it
with each development handoff. Unknown source-to-output coverage remains unknown;
file counts are not whole-game completion percentages.

### Media source gaps and separate soundtrack events

The 5 October media import found nine unresolved original audio references
(seven INFO voice paths and two SOUN paths). Track each source identity,
archive/loose resolution, override/deletion state and actual event eligibility
before choosing any fix. Missing original input is distinct from failed
conversion or an unwired runtime event; never substitute unrelated dialogue.

Three imported videos (`mw_credits.bik`, `mw_logo.bik`, `mw_menu.bik`) have no
embedded audio stream. Duration-matched silent PCM is a conversion fallback,
not a decision to mute the presentation. OpenMW 0.48 source explicitly starts
separate title music before its configured logo, and only pauses other audio
for movies that have an audio stream. Its menu background uses a different
filename, so the exact `mw_menu.bik` event mapping remains open.

- [ ] Resolve or explicitly classify each of the nine missing references with
  source and playback evidence.
- [ ] Verify logo, credits and menu music selection/ownership, including loop,
  skip, completion and return paths; preserve continuous music through ordinary
  full-screen modal views.
- [ ] Complete matching image readback and target playback checks before
  claiming imported media is playable through every intended event.

The exact reference list, pinned source evidence and investigation checklist are
in [missing media references](MEDIA_MISSING_REFERENCES.md). This is follow-up
work; it is not included merely because a previous playtest archive exists.

## Historical baseline — published v0.0.27, 3 October 2026

[AmiWind v0.0.27 — Rocks, Mushrooms, and Then Some is published](RELEASE-v0.0.27.md).
Its exact-commit hosted CI, public source release and downloaded-asset checks
passed. Rock/giant-mushroom coverage, bounded town conversion, held-input
preservation, map-marker repair and dual-emulator configuration generation are
included. Private stable HDF assembly/readback and the full 2,717-map static gate
passed; target heap, FPS, crossing and map-panel acceptance remain open.

The immediate follow-up is to playtest and profile that released scope, then
complete the map, condition-aware voices and video catalogue. Earlier versioned
plans below preserve their original scope and evidence; they do not change the
published baseline or certify an unperformed target check.

## Assemble first, then optimize the measured world

The released rock/giant-mushroom coverage and bounded town maps provide the
baseline for target cell-handoff checks and profiling. This is not a claim that the present output size or conversion cost is
already optimized. Keep the existing FPS subdivisions while assembling content.

- Require target-ABI memory estimates after mapping changes and before image
  assembly, plus runtime load/crossing profiling during playtests. Much of the
  current world is still terrain with rocks and giant mushrooms, yet already
  has heap/headroom failures; later content must not be added without renewed
  accounting. Additional HDFs do not increase the engine heap. See
  [memory allocation and the mandatory headroom policy](MEMORY_ALLOCATION.md).
- Measure source input, converted payload, duplicated overlap data, allocated
  HDF capacity/headroom, conversion time, peak/resident memory, loading stalls
  and actual game FPS separately. Record comparable scenes and build profiles.
- Investigate shared converted models/textures and identical boundary geometry
  deduplication across neighbouring cells. Preserve source-reference identity,
  position/rotation/scale, material/UV data and collision. Shared storage must
  still allow bounded residency and reliable map loading.
- Consider mirroring/reuse only where geometry and texture/collision semantics
  permit it; do not mirror the authored landscape as a substitute for original
  placements. These are investigation options, not implemented size savings.
- Reduce overlap duplication without removing the visible/collision margin
  needed for draw distance, hysteresis and diagonal views. Keep Seyda Neen and
  Balmora transition correctness as regression gates; see the growing
  [cell-change continuity checklist](CELL_CHANGING.md).
- Refine seam-preserving LOD, texture storage and conversion-cache reuse after
  measuring their contribution. Closed mushroom joins and original UVs remain
  requirements; the earlier independently reduced caps are not acceptable.
- Publish before/after size, memory, build-time, loading and FPS measurements.
  Optimization must improve a measured cost while preserving placements,
  appearance, gameplay state and collision. No savings target is promised yet.


## Implemented: generate both emulator configurations during image assembly

The normal full-game, dry-run and Docker build paths now emit versioned FS-UAE
`.fs-uae` and WinUAE `.uae` configurations from the verified `build.json` HDF
list. Asset-free images also receive both formats. The v0.0.27-rc4 templates were missing; matching rc4 asset-free presets were
added from the unchanged rc3 presets, and the writer selects the version-matched
template while preserving the user's ROM selection policy.

- [x] DONE: implemented in v0.0.27-rc3 — mount all required HDFs together, with
  the boot HDF first, and retain compatibility with the previous single-HDF
  layout.
- [x] DONE: implemented in v0.0.27-rc3 — support an optional owner-supplied
  `--kickstart-file`; otherwise leave ROM selection empty. Never distribute or
  download ROMs.
- [x] DONE: implemented in v0.0.27-rc3 — validate the HDF list, unsafe/missing
  paths and stale mount handling in configuration hooks; print both config paths
  and all HDF paths in build summaries/footers, with Docker paths rebased for the
  host.

- [x] DONE: implemented in v0.0.27-rc4 — add matching asset-free FS-UAE and
  WinUAE presets based on unchanged rc3 templates; select the version-matched
  preset during build.

Windows validation: configuration tests pass 11/11. The Windows `run_fs_uae`
suite reports 12 passed, 1 error in the symlink case unavailable on this Windows
setup, and 1 failure in the POSIX-stub launcher test that cannot execute here.
Those local failures remain historical evidence. Published v0.0.27 subsequently
passed the hosted Linux and Windows launcher-parity jobs; that does not establish
a full native Windows suite or actual emulator gameplay.

- [ ] Run actual FS-UAE multi-drive gameplay from the generated configuration
  and validate every disk, boot order and paths. Configuration generation tests
  do not prove emulator playability.

The missing-template regression and repair are recorded in the
[bug journal](BUG_JOURNAL.md). The complete Linux Docker suite and asset-free
compile passed for v0.0.27; actual multi-drive gameplay remains pending.

## v0.0.26 released - validated Windows and Docker builds

The final Docker helper/export run passed full conversion, strict actor-ground
validation, verified HDF assembly and WinUAE game entry. All 3,551 NPC models and
2,526 terrain regions passed; the HDF is 3,489,693,696 bytes with SHA-256
`da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`. The cached
run had conversion elapsed of 1,566.061 seconds (26 minutes 6 seconds), excluding export, provisioning and emulator testing, and reported 78 warnings. The local wrapper suite
passed 433 tests with 3 skips. Hosted source, Linux/Windows parity and Docker CI passed; v0.0.26 is published. See [release notes](RELEASE-v0.0.26.md).

The earlier cold Docker run used rc1 identity and took 35 minutes 3 seconds; its
separate evidence remains in [Docker validation](VALIDATION-DOCKER-2026-10-02.md).
Keep Linux builds supported through the same portable converter; host-specific
setup and launchers must not create a separate conversion implementation.

- [x] Provision native Windows tools and compile the engine.
- [x] Boot the asset-free test image in WinUAE 6.0.3 with an owned A1200 KS3.1 ROM.
- [x] Correct archive path separators and generated Amiga script line endings;
  preserve Linux's existing slash-separated identifiers and LF output.
- [x] Finish full conversion and payload validation on Windows; corrected image
  assembly and WinUAE prison-scene entry passed. See the
  [recovered-build validation record](VALIDATION-WINDOWS-2026-10-02.md).
- [x] Record timings, versions, warnings, output hashes and recovery limits.
- [x] Prepare the v0.0.26-rc1 Windows source checkpoint.
- [x] Complete the final v0.0.26 full conversion, strict actor-ground validation,
  HDF assembly and WinUAE game-entry acceptance locally.
- [x] Implement the [Docker builder](DOCKER_BUILD_ROADMAP.md), read-only private
  game inputs and persistent Linux conversion/cache volumes.
- [x] Complete cold offline Docker conversion and verified HDF assembly with all
  NPC models, terrain regions and strict actor-ground validation.
- [x] Play the opening movie and enter Jiub's prison scene from the Docker HDF
  in WinUAE 6.0.3; verify Enter/Escape controls.
- [x] Complete final v0.0.26 helper/export validation and WinUAE game-entry check.
- [x] Complete hosted Docker CI and owner-run publication.
- [x] Review exported image layers; measured full-build peak storage remains open.
- [x] Deliver the source-only handoff for Linux validation and owner-run publishing.

Native Windows remains experimental, with worker and cancellation reliability
limits documented in the [Windows roadmap](WINDOWS_BUILD_ROADMAP.md). The final
Docker helper/export and WinUAE validation for v0.0.26 passed locally; hosted CI
and owner-run Linux publication completed successfully.


## Release progress and planned follow-up

### v0.0.27 — published: Rocks, Mushrooms, and Then Some

The release includes 37,960 exterior rocks and 816 giant mushrooms across 2,526
world regions, using original base-game placements. Small collectible mushrooms
are excluded. Joined mushroom sections retain source geometry and UVs; the closed
caps were accepted in the rc2 WinUAE playtest. See [What are rocks?](WHAT_ARE_ROCKS.md).

Terrain handoffs, held-input preservation, bounded town maps and heap estimates
are implemented, with separate runtime checks still open. The final private
image passed its static gates and filesystem readbacks. The original rc3 load
incident still requires exact-route target acceptance; publication and static
estimates do not close it. See the [release evidence and limits](RELEASE-v0.0.27.md).

### v0.0.28 — Trees and Grass, Day and Night

The stable v0.0.28 identity is in preparation, not published. Default V3 sky,
two cloud layers, moving sun and clock-aligned world tone are implemented.
The corrected camera-tour/night/guard build passes 822-test host gates and
matching 742,884-byte Amiga compiles, including tiny-star, arrival and slower-cloud
changes and 64 KiB music-only source read-ahead. Shared mixer timing and
guard voices are unchanged. Owner listening still reports intermittent
audio artifacts, mostly at load-ins and in heavy scenes. Audio remains open;
publication proceeds with the known issue and further audio investigation
is deferred until after publication.
The corrected image passes 10,766-file readback and three partition
checks. Independent replay remains pending, including Balmora at night and
both moon silhouettes. See the [current release record](RELEASE-v0.0.28.md).

- [x] Default-on automatic cycle using the persistent clock and explicit T waits.
- [x] Default V3 and selectable V1/V2; independent default-on sun/cloud toggles.
- [x] Source-reproducible owned-cloud conversion and seven-colour asset remap.
- [x] Adjustable cloud speed, default `0.00333333333`; camera-tour gallery and `here` mode.
- [x] Four-stage `dbg nightgallery [here/off]` using actual saved-date moon paths;
  native appearance and cancellation acceptance remain pending.
- [x] Bounded original stars/nebula and Masser/Secunda atlas; default-on
  `dbg starsky` / `dbg nightsky`, with complete moon-disc star occlusion.
- [x] Bounded coherent 64-map canonical repeat and actor-support host gates.
- [x] Original-asset guard runtime and `guards_torch_cycle`, with
  `dbg guardtorch on/off/auto`; host checks passed.
- [x] Fresh matching Amiga builds, full host suites and image readback after
  the latest tiny-star, arrival and cloud-speed changes.
- [ ] Native one-pixel stars behind moons/clouds/foliage; additional night views
  and Balmora at night, with actual final-build stills and GIF frames.
- [ ] Verify Imperial and Hlaalu torch grip, timing, occlusion and cache/light cost on target.
- [ ] Native startup, controls, travel/profile, terrain/NPC routes and lifecycle acceptance.
- [ ] Fresh native V3/night views, gallery stills/GIF and visual/performance review.
- [ ] Broader-world canonical-culling validation; no global certification yet.
- [ ] Regional weather and precise lunar simulation; see the [pinned weather and blight source study](WEATHER_AND_BLIGHT_STUDY.md).
- [ ] Original-road survey, route/bridge and broader cell-join acceptance.

## Follow-up: static asset gallery and remaining scenery

The current foliage conversion preserves detailed Balmora's mesh policy and
uses shared sprites for admitted foliage elsewhere. This does not establish
complete conversion or native appearance for every source reference. Keep
deferred references and boundary copies explicit in build receipts.

- [ ] `dbg assetgallery`: browse original IDs and inspect static assets beside
  a character for scale, with visible unsupported/missing conversion status.
- [ ] Extend original CELL/FRMR scenery beyond the admitted rock, mushroom and
  foliage categories while preserving transforms, collision and boundary overlap.
- [ ] Verify scaled and tilted foliage, distant silhouettes and cell joins in
  native views. Finite captures cannot certify the full world's appearance.

See [the asset/scenery plan](ASSET_CATALOGUE_AND_GALLERY.md). The NPC gallery is
already included in normal builds; required game NPCs remain included even when
its optional inspection facility is disabled.

## Top engineering priority: world-terrain build time

The reported full-world conversion takes an impractical part of an evening on
the workstation. Prioritize making `vfXXXX` compilation and repeated builds
practical alongside the current native Windows validation, before speculative compiler acceleration.
The [build/compiler toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) defines the work:

1. Preserve the current run and measure individual phases, including both BSP
   compilations per region. Record success or failure rather than assuming it.
2. Reuse unchanged terrain across new build names using validated persistent
   caching, correct overlap dependencies and selective invalidation.
3. Reduce duplicate BSP/collision work; investigate a terrain-specific standing
   hull builder and separately cached collision output.
4. Optimize the measured CPU/I/O costs, then evaluate GPU work if justified.

Keep collision, shoreline, memory/format budgets and image gates intact. Hand
over one logical source checkpoint at a time; a profiling-only change must not
alter generated content. First-build speed and incremental-build reuse need
separate measurements. These improvements are planned, not implemented.

## Asset catalogue and placement completeness

The carried torch now uses the original mesh, authored hand pose and bounded
flame sprites at its emitter; guard equipment extends that conversion separately.
Native torch retesting and the reported brief fist blink recurring every 1–2
seconds remain open. That interval is not the duration of the disappearance. The
[torch investigation](TORCH.md#original-model-replacement-and-reported-hand-flicker)
keeps these separate from the rc8 dynamic-light crash correction.

The [asset catalogue and gallery plan](ASSET_CATALOGUE_AND_GALLERY.md) starts
with original object IDs, model/dependency lookup and per-reference coverage.
The proposed `dbg assetgallery` will show a selected asset beside a character
at game scale, including missing/unsupported conversion status. It is not
implemented. Inventory the game's assets before trying to convert everything.

A focused retained-scene audit confirms eleven of sixteen large Bitter Coast
tree placements in the two named Seyda Neen cells are skipped by the existing
non-unit-scale filter. Track this as a real conversion bug. Full-world terrain
coverage and a populated asset catalogue do not establish scenery completeness.

## Windows build host, 1 October 2026

Linux remains the established build foundation. Native Windows 11/MSYS2 is
experimental: complete current-recipe conversion, corrected image assembly and
a WinUAE prison-scene smoke test passed on 2 October 2026. Intermittent
Windows worker failures remain open. The
[Windows build roadmap](WINDOWS_BUILD_ROADMAP.md) records the current evidence,
recovery limits and acceptance milestones. WSL2 is a separate Linux-host route
and now has a [full Docker conversion record](VALIDATION-DOCKER-2026-10-02.md).

## Docker builder and v0.0.26 validation

The builder, private input/export helper and local final-version validation are
complete. The cached v0.0.26 helper/export run passed all conversions, the strict
actor-ground gate, verified HDF assembly and WinUAE game entry. Hosted Docker CI
and publication completed for v0.0.26; the later v0.0.27 hosted gates also passed. See the [release notes](RELEASE-v0.0.26.md) and
[Docker builder details](DOCKER_BUILD_ROADMAP.md). Full-build peak storage remains
unmeasured; the 40 GiB figure is an initial planning allowance.
The implemented optional Linux build environment wraps the established pipeline
with the same full-content defaults and validation gates. Windows testing uses
a Linux container through WSL 2; that result does not establish native Windows
reliability. Native Linux and experimental native Windows entry points remain
maintained alongside Docker.

- [ ] Package the toolchain and build dependencies with a recorded, tested version
  set and image digest. Check redistribution terms before publishing an image.
- [x] Accept the user's existing Morrowind installation through a read-only
  input mount; persist outputs and validated caches in separate writable mounts.
  Exclude game data, ROMs, local builds and private notes from the Docker build
  context and all published image layers.
- [ ] Measure the current native build directory as a starting estimate, then
  measure a complete container build. Report tool/image storage, input data,
  shared caches, one run's intermediates, partition/final-image/readback copies
  and peak temporary space separately, with a safety margin. Exclude historical
  failed runs from the single-build requirement; include Docker image/build-cache
  and VM-disk overhead in the container estimate.
- [ ] Benchmark cold and cached builds, worker/CPU/RAM limits and mount I/O on
  Linux and Windows. Verify persistent-cache invalidation, ownership and clean
  cancellation, and produce the same content/validation receipts as normal builds.
- [ ] Document installation, resource allocation, disk preflight, offline use
  after provisioning, and a simple command that takes input and output paths.

Host mounts keep large private assets and generated builds outside the builder
image; they still consume host disk space. A tool-only image's download size is
not the total space needed to build AmiWind. See Docker's
[bind-mount documentation](https://docs.docker.com/engine/storage/bind-mounts/) and
[Windows WSL 2 backend](https://docs.docker.com/desktop/features/wsl/).

## Build and compiler toolkit

The separate [toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) proposes phase profiling
for `vfXXXX` conversion, measured CPU/storage improvements, optional GPU asset
work and deferred GPU-assisted QCC research. These are future investigations,
not implemented backends or measured speedups.

## v0.0.25-rc1 regression work

See [the consolidated dev1 feedback](FEEDBACK-v0.0.25-dev1.md). Priorities are
Seyda Neen's grounded island handoff, trustworthy global coordinates/map marker,
water/terrain verification, console M/N protection, normal compass and Ctrl flight.

- [ ] Add original-game unexplored-area masking/fog of war to the world map,
  driven by visited exterior locations and persisted with saves. Deferred;
  explicitly outside the v0.0.25-rc1 implementation.
- [ ] Review retained terrain compiler diagnostics: scale collision-only entity
  seeds consistently and reduce near-coplanar portal clipping. Preserve native
  collision and visibility checks when changing that pipeline.

Historical rc1 planning context: release [v0.0.24 - Welcome to Balmora (and Vvardenfell!)](RELEASE-v0.0.24.md).
Candidate at that time: [v0.0.25-rc1](RELEASE-v0.0.25-rc1.md), correcting the first
playable terrain pass. Next work includes retained placement findings, broader
route playtesting and scenery beyond the detailed towns. Solstheim/Bloodmoon and
Tribunal are outside this island pass.
The [29 September plan](PLAN-2026-09-29.md) retains historical priorities.

## Balmora interiors and loading

- [ ] Implement [character presence and progression](CHARACTER_STATES.md),
  preserving original actor activation and movement conditions independently
  of ground-contact acceptance. The [source progression review](NPC_GROUND_CONTACT.md#source-progression-review-1-october-2026)
  confirms that the Balmora Dreamer is disabled at startup, Fargoth has an
  externally scripted quest route, and the dock guard, Vodunius and freed slaves
  have state-dependent movement or disappearance. Verify source-derived new-game
  state, quest transitions, scene re-entry and save/restore. A passing geometric
  audit does not close this behavior gap.

- [x] Convert 43 original Balmora destination interiors, 93 NPC placements and
  80 living voice sets. Native checks cover all 70 exterior round trips and both
  same-room Fighters Guild links. Full services/quests/schedules remain future work.
- [x] Offer frozen-frame sub-cell loading with a small top Loading box; keep
  the existing black-screen method selectable. Implemented in dev3.
- [ ] Profile read/decode stalls and memory ownership before bounded prefetch
  or offloading. Preserve audio servicing and persistent state when releasing
  scene resources. Frozen-frame presentation does not remove synchronous pauses.

## Seyda Neen subdivision

Owner feedback: Balmora's dev3 subdivision works surprisingly well; its exterior
often feels faster than Seyda Neen. Use that successful approach from the first
ship-exit scene. Performance observations remain separate from measured claims.

- [x] Add 25 regular overlapping Seyda Neen regions, a dedicated compact pier
  (`intro_seyda_neen_subcell_pier`, file `intro_docks.bsp`) and ring courtyard.
  Retain complete intersecting objects, stable reference IDs and shared coordinates.
- [x] Keep the accepted frozen frame with a small top Loading... box; retain
  the black-screen choice. Physically remove unreferenced BSP data from files.
- [ ] Complete owner playtest of natural ship/plank/guard/office/courtyard flow,
  bidirectional seams, containment, save/restore and peripheral views.
- [ ] Profile matched views and transition stalls on the owner's weaker machine;
  investigate the view-dependent distance-1000 speed-up. Keep the prison ship's
  interior cost separate. Background loading/prefetch remains future work.

## World-coordinate HUD

- [x] Establish a reversible transform from each runtime scene's local XYZ to
  original Morrowind world coordinates and exterior cell/grid coordinates.
  Check quarter-scale conversion, each area's origin and axis conventions,
  negative-cell boundaries, sub-cell copies and interior identity. Interiors
  must not invent an exterior location when the source has none.
- [x] rc1: compact console-font GLOBAL XYZ and LOCAL XYZ at bottom right,
  retaining yaw/pitch. The existing `debug coords` switch controls both rows.
- [x] Use the same source transform for HUD, map marker and exterior-cell index;
  print exact scene identity through `aw_pos` for reproducible reports.
- [ ] Consider separately configurable coordinate rows if requested; the current
  paired display follows the owner's revised HUD request.

## World map, inventory and journal TODO (owner request, 1 October 2026)

The post-RC3 world/map/journal pass has started at the owner's request.
[Current implementation and limits](WORLD_MAP_AND_JOURNAL.md).

- [x] **M: basic full-screen Vvardenfell map.** Show Morrowind and the player's current
  position. Reuse the verified local-to-world transform described above; define
  how interior locations appear without inventing exterior coordinates. Provide
  a clear return to play, keyboard navigation and mouse pan/zoom where practical.
- [ ] **I: inventory.** Show the player character beside their items, with
  readable names, quantities, icons and equipment slots. Support mouse selection
  and equipping/unequipping, with a visible cursor and keyboard alternatives,
  following the original game's interaction style.
- [ ] Connect equipped items to the character preview and persistent player
  state. Verify slot compatibility, quantities and save/load before allowing
  equipment changes; opening either screen must capture input from the world.
- [ ] Measure the map, preview model, item icons and UI memory on the reference
  Amiga profile. Load their resources on demand and release them on close.
- [x] **J: basic dated progression journal and quest links.** Present an open book with a central
  fold and two facing pages, page turning, dated entries and clickable topic/quest
  links. Provide keyboard navigation and a visible pointer, with a route back
  from linked topics to the current spread. Preserve progression and entry order across save/load. Follow the original journal's book
  presentation; use scrollbars for indexes or long topic lists where appropriate.
  Implemented: two-page earned entries, quest filter links and AWS2 history.
  Pending: learned dialogue-topic links, saved reading position, larger quest
  capacity and full original-script progression. Source journal data is DIAL/INFO,
  not XML; the supplied master has no QSTN quest titles.


## Optional field-of-view control

- [ ] Consider an Options FOV slider, subject to measured performance acceptance.
  Keep the owner's preferred **90-degree horizontal Quake FOV as the default**.
  A narrower setting, including 75 degrees, would be an optional preference.
- [ ] Use the existing runtime projection setting; changing FOV does not require
  reconverting assets, rebaking collision or rebuilding maps. It does not change
  the player's dimensions relative to the world and is not a height correction.
- [ ] Benchmark fixed boat, Seyda Neen and Balmora views on the reference profile
  before adopting the slider. Compare frame times, surface/edge work and overflow
  at the proposed limits; wider views can expose more geometry. Proceed only
  without a measurable default-setting regression and with an acceptable cost
  across the supported range. Defer the feature if that condition cannot be met.

## Next implementation milestone agreed 28 September 2026

Maintenance v0.0.20 is retained. v0.0.21-dev1 implements the bounded opening,
character/save and UI prototype; the checkboxes below track full acceptance,
not merely source presence. See [checkpoint limits](RELEASE-v0.0.21-dev1.md).

- [ ] Dock guard route, original CharGenDock dialogue and race-menu speech gates.
- [ ] Race/sex/face/hair selector with rotating head preview and bounded resource use.
- [ ] Authored invisible chargen barriers and their completion-dependent removal.
  Preserve deck/plank/pier/courtyard containment and forward passage together;
  see the persistent state rule in CHARACTER_CREATION.md and journal J015.
- [ ] Census Office interior rooms, door links, Socucius Ergalla, hall guard and
  Sellus Gravius; class, birthsign, review, papers, ring and release logic.
- [ ] Versioned character/attribute state and compact, recoverable save/load;
  manageable named manual saves and player-adjustable autosave history of the
  last X snapshots (not character levels). Deliver save/load together with completed
  Census attributes as the next playable milestone. Compare semantics
  with original ESS/OpenMW, test corruption/interruption and repeated-save growth.
- [ ] Add the unimplemented Silt Strider and driver; keep that content work
  separate from diagnosing the malformed landing geometry at XYZ260/417/30.
- [ ] Keep both intermittent FS-UAE freezes open during the new work.
- [ ] Review compiler warnings on every build and reduce the remaining 93; follow
  the mandatory gate in DEVELOPMENT.md. Preserve full diagnostic evidence.

Source audit, order and acceptance: [CHARACTER_CREATION.md](CHARACTER_CREATION.md).
Save design and pending comparison gates: [SAVEGAME_PLAN.md](SAVEGAME_PLAN.md).

Core world/cell/chunk design: [WORLD_MAPPING_PLAN.md](WORLD_MAPPING_PLAN.md).

## Next world-mapping milestone: entire-world terrain inspection

**First world-expansion milestone after v0.0.24 (owner priority, 1 October):**
build the Vvardenfell main-island topographic map from terrain and its original
textures. Start with the source game's exterior cells and the existing loading
method, then fit Seyda Neen and Balmora into that common world space. This
terrain-first milestone does not imply that every settlement, interior or
gameplay system is complete.

- [x] Catalogue the source exterior-cell grid, bounds, terrain heights, texture
  assignments and water; document the actual cell layout before choosing
  runtime boundaries. Produce a coverage view with both converted towns marked.
- [x] Produce a matching **source polygon-density map ("polymapping")**: count source
  triangles per cell and smaller spatial tiles, including placed
  copies of buildings and other meshes. Show concentrated geometry as a heatmap
  alongside terrain and existing region boundaries. Use it to flag candidates
  for sub-cells, then confirm with visible geometry, collision cost, texture
  residency, peak heap use and transition measurements. Raw polygon count alone
  is a screening tool, not a sufficient runtime budget. Whole-island converted
  BSP costs remain pending; the first survey calibrates against the existing
  89 town regions. See [measurements and private outputs](WORLD_SURVEY.md).
- [ ] Convert and traverse terrain cell by cell, checking texture continuity,
  shared edges, player coordinates and return crossings. Reuse the current
  selectable loading methods and measure memory and stalls on the Amiga profile.
- [ ] Begin with source-cell-sized regions where they fit. Subdivide only after
  geometry, visibility, collision or memory measurements show the need. Reuse
  Balmora's overlap/ownership lessons and canonical actor placements.
- [ ] Investigate logical boundaries in dense settlements, including Vivec:
  bridges between city sections are candidate crossing points, subject to the
  actual source-cell layout, sightlines and measured region budgets.
- [ ] Integrate the existing Seyda Neen and Balmora regions without duplicate
  terrain, shifted origins or broken door/return links. Compare ground height,
  materials, water and collision along every join.
- [ ] Turn the Seyda Neen/Balmora dwelling workflow into reusable conversion
  stages: source-reference inventory, complete building/interior geometry,
  entrance and return links, resident/outfit mapping, canonical initial support,
  and independent packaged-data checks. Carry the documented distant-origin,
  opening, stair and overlap lessons forward. Emit per-cell exception reports
  for review instead of silently dropping troublesome dwellings or placements.

- [ ] Export a topomesh of the **entire map's terrain**, with original exterior
  terrain coverage, global coordinates, source-cell IDs and a missing-data report.
  Preserve the full-detail baseline before creating LODs.
- [ ] Extract and inspect original water levels, coverage and shorelines; do not
  derive the whole world from the current placeholder sea plane.
- [ ] Add a separate terrain-only observer scene/viewer: free camera, coordinate/
  cell readout, water toggle, optional wireframe/boundaries, fog/view distance and
  LOD controls. Exclude NPC/quest/intro activity so geometry can be studied calmly.
- [ ] Compare whole-world overview and detailed terrain patches for LOD error,
  seams, triangle counts, RAM, load time and frame time. Complete source coverage
  must not require complete full-detail native residency. Use findings to choose
  streaming, optional polygonal BSP regions and elevated-view handling.

See [terrain inspection plan](WORLD_MAPPING_PLAN.md#next-milestone-entire-world-terrain-topomesh).


## Recovered follow-up: FREQUENT FLYER BONUS / whole-world scaling harness

Recovered from the surviving conversation after the frozen v0.0.21-dev4
package; documentation/planning only.

- [ ] Add a terrain-only native observer command, proposed as `dbg fly 1`, with
  unrestricted noclip flight over the full Morrowind terrain coordinate space.
- [ ] Start with terrain topology plus ground colour/texture identity where
  practical and a sea-level plane; keep NPCs, quests and normal gameplay out of
  the first benchmark so geometry/residency costs are measurable in isolation.
- [ ] Keep fog active and couple it to actual work rejection/residency policy,
  not only presentation. Measure low and high-altitude flight paths at fixed
  viewpoints and speeds.
- [ ] Expose/select prebuilt terrain LODs and record triangle/edge work, visible
  surfaces, RAM, cache behaviour, loading/offloading stalls and audio deadlines.
  The experiment's central question is: **the mechanics work locally; can they
  scale to the whole world?**
- [ ] Investigate **something akin to Nanite, but on these old pieces of gear**:
  host-precomputed geometry hierarchies/clusters and cheap runtime selection of
  immutable representations. Possible criteria include projected size, distance,
  altitude and fog. No runtime mesh simplification is assumed. Adopt only if the
  total measured cost beats simpler AmiQuake/BSP/LOD handling.
- [ ] Preserve the open-world illusion as an acceptance criterion. Interiors may
  load separately as in Morrowind, but exterior traversal should not degrade into
  gratuitous loading screens merely to satisfy the partitioning strategy.

See [world-scale flight and precomputed geometry experiments](WORLD_MAPPING_PLAN.md#recovered-follow-up-world-scale-flight-and-precomputed-geometry-experiments).

## Fundamental mechanics before attribute effects

- [ ] **Tables, tables, we need more tables:** catalogue character attributes,
  modifiers, skills, quests, globals/script locals, containers/items, NPCs,
  dialogue, world references and persistence. Record sources, types, defaults,
  dependencies, read/write events and save/unload behavior, with unknowns marked.
  Use the shared catalogue to guide conversion/runtime/save schemas and bounded
  memory; see [development notes](DEVELOPMENT.md#tables-tables-we-need-more-tables).

Owner priority, 28 September 2026: establish persistent conditional game state,
reference enable/disable behavior, interaction and dialogue gates, NPC actions,
scene transitions and save/load before expanding what each attribute does in
combat, movement, skills and spell calculations. Keep the character fields and
starting-value work already present. Research later effects using UESP, original
data and OpenMW; record uncertainty and exceptions in the implementation journal.
See [research references](REFERENCES.md#game-mechanics-research).

## UI readability and text scaling

- [x] Add Options controls for existing 16, 14 and 12 px fonts plus the readable
  fallback; preserve every font and size. Start the next playtest at 14 px.
- [x] Move/size the main-menu panel with its font metrics so it clears the
  background title at every supported size. Verify keyboard and mouse hit boxes.
- [ ] Later separate menu, dialogue, journal and book size preferences, with
  measured reflow/pagination and preserved content at each size. Text-heavy scenes
  need readable wrapping and accessible controls rather than clipped paragraphs.
- [ ] Owned TTF inputs may be rasterized on the host into bounded AWF1 atlases.
  Preserve original bitmap-font conversion as well. Book pages and birthsign
  artwork belong in the reading/character UI, with private source assets.

- [ ] Explore the lower screen area for needed status icons and interaction/menu
  controls as those mechanics arrive. Measure against 320x200 output, selected
  font size, dialogue, resource bars and debug coordinates. Establish readable
  priority/reflow before committing to an icon count or permanent layout.

## Opening exterior residency and playtest blockers

- [ ] Close the new Census missing-room and pier-escape reports before treating
  the full opening as accepted; use BUGS.md fixed Y/N/version index.
- [ ] Build a separate opening exterior with configurable radius X around the
  boat/dock/Census route. Include intersecting bounds and complete assemblies,
  all required doors/NPCs/navigation/barriers and enough backdrop for visibility.
  Keep original world coordinates and stable reference IDs. Unload prison before
  this scene, unload it on office entry, load the full town after release; include
  courtyard round trips while still restricted. Preserve globals, script locals,
  actor state and save content identity across both exterior variants.
- [ ] Compare full/reduced scenes at identical cameras for frame time, polygon
  work, resident geometry/textures, peak transition memory and audio continuity.
  Existing radius selection is preprocessing only; the native BSP is resident.
  Avoid loading both exteriors at once. Choose X from coverage and measurements.
- [ ] Audit Census texture resolution and UV/material bindings; use bounded
  per-material quality where close wall art needs it, not universal reduction.
- [ ] Add generic interior hinged doors with source sound, pivot, motion and
  swept collision; retain locked and opening-script-specific gates.
- [ ] Add ambient NPC idle vocalizations/whistling later, with bounded polling,
  distance, cooldowns and priority below active dialogue/intro speech.

## Optional polygonal POI regions

Owner principle: **"the fog is our friend"** for both bounded rendering/loading
work and Morrowind's mystique. Preserve atmosphere when measuring view-distance
tradeoffs; merely fogging still-processed/resident geometry is not the goal.

Horstator's evening proposal, 28 September 2026: [full note](HORSTATORS_JOURNAL_2026-09-28.md#evening--polygonal-poi-regions-if-streaming-is-insufficient).
First use fog-limited visibility to support measured cell/chunk streaming and
offloading, allowing brief pauses at selected crossings. Only if no sane version
of that approach meets the target budgets are explicit region swaps a required
fallback experiment. Fog culling alone does not evict resources from RAM.

- [ ] Add an optional polygonal region recipe around POIs, starting with Seyda
  Neen; allow regions to span original cell boundaries. Keep the original cell
  approach and source mapping intact. Use compiled BSP regions with associated
  resource packs; the earlier "WAD region" shorthand does not prescribe the
  container. No region converter or loader is implemented yet.
- [ ] Plan crossings and inexpensive horizon/tree/canopy backdrops; show a short
  Loading indication during a level swap and restore the matching safe position
  and facing only after collision is ready. Outdoor cell crossings get only a
  minimal upper-center "Loading..." box, not a large overlay window. Preserve
  original-style loading screens for interior/exterior transitions that use them.
  Test both crossing directions.
- [ ] Keep stable reference ownership and persistent state across overlapping
  coverage. Preserve original cell-dependent rules independently of rendering
  regions; no duplicate loot, actors or script execution at seams.
- [ ] Compare memory, peak load scratch/overlap, load duration, frame time and
  audio continuity against the cell/chunk approach. Verify repeated travel,
  save/load, missing-pack recovery and a handoff that does not require two full
  regions in RAM. Adopt only on measured results; retain both recipes.

- [ ] Treat elevated viewpoints and continuous topomap coverage as a major
  acceptance risk for POI regions. Trial a broader/coarser terrain mode above
  configurable height X over local ground; define the actual up-axis, preserve
  world coordinates/state, and test adjacent-region views, descent, collision,
  memory and separate enter/exit thresholds. A height switch alone is not proof
  that hidden boundaries or missing terrain are solved.

## Graphics and performance: crate geometry options

Requested 28 September 2026; add containers using the normal method first.

- [ ] **Type 001 / normal:** preserve the source crate's shape and recognizable
  details through the normal conversion. This is the initial default when crates
  are added, pending measurement.
- [ ] **Type 002 / low polygon:** offer a simple rectangular box with the source
  texture patterns mapped onto its faces, reducing geometry. Retain both methods
  as selectable conversion options; do not silently replace the normal version.
- [ ] Compare matching scenes and camera positions for visual quality, polygon
  counts, memory use, frame time, collision and interaction. Decide whether type
  002 is needed from those results.
- [ ] Later evaluate a streaming/distance hybrid that uses detailed crates nearby
  and simple boxes farther away, with bounded residency and controlled switching.
  Keep container reference identity, inventory, ownership and saved state stable
  across geometry changes; do not duplicate or reset contents during a switch.

## Build parallelism, 29 September 2026

v0.0.23-dev1 implements default dependency scheduling and bounded process workers
for scenery decoding, alias/sprite previews, BSP model geometry/lightmaps, intro actors, character heads and soundtrack
conversion. It preserves single-writer scene assembly, live prefixed output,
per-stage logs, failure propagation and explicit serial mode. Native make and
VIS/LIGHT use the shared budget; Census no longer hard-codes two threads.
See [PARALLEL_BUILD.md](PARALLEL_BUILD.md) for boundaries and measured validation.

Remaining opportunities: individual actor/hand conversion internals, terrain
conversion, final assembly and safe incremental caches.
Measure them before adding workers or changing the conversion recipe.

Next gameplay checkpoints requested by the owner: restore audible intro sea
ambience, verify continuous gameplay music, and cover every Seyda Neen interior
with original door destinations and repeatable entry/exit. Do not mark these
complete from a successful host build.

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

The current candidate implements persistent time, waiting, exact and named debug
time setting, automatic-cycle pause/resume and coordinated exterior sky/fog colors.
It includes a moving occluded sun, the reduced original stars/nebula and both
moons. Guard torches use original equipment and bounded automatic exterior
timing, with passing host fixtures. Interior lighting remains separate. Combined native
acceptance and memory/frame-cost measurements are pending. Regional weather,
general NPC schedules and time-sensitive quest conditions require their own
semantics; the existing wait dialog is a clock jump. See the
[implemented controls and remaining sky work](DAY_NIGHT_AND_SKY.md) and
[guard torch policy](TORCH.md).

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

- Investigate a catalogue of transparent, pre-rendered hand sprites, including
  an OpenMW-based capture path, all race/sex variants and animation/equipment
  states. Compare appearance, lighting, RAM and streaming with the mesh path;
  this is a potential pipeline, not an RC1 requirement or chosen replacement.
  See [the investigation](FIRST_PERSON_HANDS.md#investigation-first-person-hands-rendered-as-sprites).

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
- [ ] Measure the rc7 F/V placeholder torch against the same dark cave camera;
  one bounded dynamic light is implemented, but target cache/audio/FPS cost and
  visual acceptance remain open. See [torch scope](TORCH.md).

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


## Interaction and inventory follow-up, 28 September 2026

Default layout: [npc_interaction_layout_template_001](INTERACTION_LAYOUTS.md).

- [x] Small 12 px target hint, right-aligned immediately below the viewport:
  `Fargoth` in the small Morrowind font, then `(Talk: E)` on the next line in
  the current console font. Shared opening action query; range, visibility and current
  permissions determine the displayed action. No extra panel or debug dependency.
- [x] Menu/character choices accept arrows and WASD; preserve name-entry letters.
- [x] Separate the hall guard's fighting permission from the global opening
  enclosure. Do not enable every player action just because one gate ends.
- [ ] General action permissions combine script restrictions, UI capture and
  active effects. Model Paralyze and Silence separately: Silence affects casting,
  not ordinary punches. Verify effect rules and expiration/restoration against
  original records and OpenMW before implementing combat/magic.
- [ ] Import container inventory entries and leveled-item lists from owned data;
  preserve fixed items, quantities, list flags, level rules and chance-none.
  Verify resolution/respawn behavior against OpenMW before choosing roll timing.
- [ ] Item catalogue and icon conversion from original item records; bounded
  palette/size/cache budgets, icons plus readable names/counts in inventory and
  container UI. Do not replace missing icons with unrelated art.
- [ ] Persist each placed container's resolved contents and player removals;
  reopening or loading must not duplicate loot. Track respawn policy separately.
- [ ] Fargoth ring dialogue: keep/return choice, original conditions, journal and
  disposition/reward changes. The ring pickup exists; the return branch does not.
- [ ] Replace the temporary namespaced courtyard-container fact with generalized
  reference state when that store is introduced; migrate saves explicitly.
- [x] Offline standing-hull scan reports floor support, bounded step connectivity,
  reachable scan edges and potential fall edges. Visual completeness remains a
  separate check; no automatically fabricated floors or invisible walls.


### Runtime out-of-bounds safeguard (requested 28 September)

- [ ] Bounded, low-frequency diagnostics poller for non-finite coordinates,
  sustained embedding in solids and escape from converted playable cell volumes.
  Use source-derived room/region bounds and reachable collision surfaces, not a
  single guessed Z threshold; stairs, lower floors, swimming and scripted
  transitions must remain valid.
- [ ] Retain the last verified supported, non-embedded position per cell. Require
  repeated grounded samples and exclude noclip, teleports/loads in progress,
  menus and unsafe/water states. Reset or revalidate it when cell content changes.
- [ ] Record version/cell/XYZ, previous safe location, nearby source references,
  story state and collision reason before offering recovery. Rate-limit notices.
  Do not silently move the player or convert that result into bug closure.
- [ ] Verify the recovery sweep and floor support before returning the player;
  never create autosaves while the character is out of bounds or unsupported.
  Measure the poller's trace/time budget on the Amiga.


### High priority: graphics/culling, door and wall assemblies

Owner explicitly prioritizes this as a key culling/geometry issue. Keep this
reference case when designing broader architectural occlusion and simplification.

- [ ] Reproduce exterior Census door overlap at XYZ396,-171,39, yaw170,pitch-3
  (AW-20260928-21); identify source door/wall references and offending triangles.
- [ ] Planned host `door_priority` true/false recipe, default **true** once implemented and validated (false preserves the baseline): retain real door holes,
  simplify covered planar wall geometry and remove proven redundant overlaps.
  Keep frames, silhouette, visibility through open doors and correct collision.
  Restrict any base-colour/texture backing to the concealed patch beneath the
  door/frame, with a conservative hidden margin. Preserve visible wall texture,
  UVs and shape. Remove redundant faces from the converted runtime asset; merely
  repainting or hiding them does not remove their memory/rendering cost.
  Never use unconditional door draw-on-top as a substitute for correct geometry.
- [ ] Compare source/candidate mesh counts, renderer surfaces/edges and fixed-view
  frame times. Separate visible correctness from a measured performance gain.

- [ ] Automate an oriented doorway cut from the placed door aperture. The owner
  confirms intrusion at both Census exits viewed from outside. Make a door-shaped cut-out: clear obstructing wall geometry behind/through
  the door opening (bounded depth), preserve the surrounding
  frame/wall, interpolate cut-face UVs and rebuild matching collision. Scope edits
  to verified adjoining wall references; never flatten everything in a door AABB.
  Report changed references/faces and retain source/baseline geometry. Validate
  repeated instances, rotated doors, door motion and both sides of each opening.


The door-cut optimization is intended to remove unnecessary geometry before
runtime, so the Amiga does not transform/rasterize redundant faces. Hiding the
artifact with a rendering priority while retaining that work does not meet the
performance goal. Profile the resulting reduction rather than assuming a gain.


Owner refinement: the assisted doorway simplification should be enabled by
**default** in the future build configuration, with an explicit disable switch.
Keep a conservative cut/overlap margin hidden underneath the door frame so no
seam or missing wall leaks around the edge. Where a transition door never reveals
an opening, replace unnecessary covered depth with a simple wall-coloured planar
rectangle behind it. A real hinged/open-through door must retain its aperture;
a backing rectangle must not seal a visible passage or create blocking collision.
This describes the planned default; no such build switch is active yet.

## Next local-area checkpoints

- v0.0.23-dev2: source-driven cast and all 13 Seyda Neen interiors plus
  Addamasartus; original Silt Strider and Darvame Hleran placements; all NPCs
  block the player; new gameplay captures for the main README.
- Clock and calendar: persistent game time and dates, explicit time advancement
  while waiting, and a wait interface. Debug control:
  `dbg timeofday <0..24|morning|night|midday|day|evening|sunset|sunrise>`.
  Match sunrise/sunset direction to the world axes. Start with an inexpensive
  sun disc and colour gradients at dawn/dusk; evaluate a small original-owned
  Morrowind night-sky texture against the Amiga memory and frame-time budget.
  Keep the existing sky as a fallback (`dbg sky on/off`, also 1/0 or true/false).
  Night-time guard torches belong to this lighting checkpoint.
- Weather experiment: an explicitly selectable blight wind test after the clock
  and sky path is stable. Measure the cost of tinted fog, directional particles
  and original owned wind audio before enabling it during normal exploration.
- Continue the audio audit: intro sea splash audibility, continuous exploration
  music, and the reported occasional music clicks under WinUAE.

Delivery gate: check trailing whitespace in every changed source and in the
exact generated apply/publish script before packaging or posting commands.

### Transport and resident voices

After the interior inspection checkpoint, expose Darvame Hleran's source travel
routes in an interaction screen beside the Silt Strider. Show destination, fare
and current gold; check affordability before travel. An unconverted destination
must say "Location not available." and must never deduct gold. Load only the
selected destination scene and charge only after a successful transition.

Replace the prototype single greeting with the original eligible NPC voice
pools and cycling. Preserve speaker/race/sex/class and quest/location/time
conditions; do not play every extracted line indiscriminately. Avoid immediate
repeats, retain speech cooldowns and interruption rules, and distinguish casual
ambient lines from player-initiated greetings and service dialogue. Guard lines
need their own pools. Record skipped/unsupported conditions in the private
conversion audit rather than silently substituting unrelated dialogue.

## dev3 feedback follow-up — 29 September 2026

The reported Vodunius-house visibility holes and the misrotated port rock are
addressed; see [terrain findings and workflow](WHAT_ARE_ROCKS.md). Voice style 2
now defaults to aim-only identity, overriding voiced speaker headers.
NPC conversation-facing, deck/pier sideways containment and door squeaks remain
open in [the consolidated dev2 feedback](FEEDBACK-v0.0.23-dev2.md).

## 29 September 2026 / v0.0.23-dev4

Published base: dev3 / `7e36e9051da477147f78cf22236a0a4c0c7201ae`.
See the updated [dated plan](PLAN-2026-09-29.md) and
[dev3 feedback disposition](FEEDBACK-v0.0.23-dev3.md). This checkpoint corrects
content-sized dialogue, input/rotation glyphs, startup audio/timing, opening quote,
tree sprite depth and Darvame's floor placement. The owner accepts the dev3 rock
fix. Door sounds, containment, complete voice behaviour and sky remain pending.


## Next version: world geometry density analysis

**Future-version work, outside the current fixes, by owner request (30 September 2026).**
Analyze source map placements to identify high- and low-polygon concentrations.
Produce spatial density maps and ranked areas, counting placed instances as
well as unique meshes, textures and expected resident data. Compare source and
converted complexity with actual visible/frame-time cost. Use this evidence
to guide sub-cell boundaries, overlap and loading/offloading budgets.
Treat this as a general world-streaming rule: identify the expensive concentrations
and the inexpensive stretches before choosing boundaries. Keep larger, more
continuous resident areas where measured cost permits; use tighter sub-cells and
earlier offloading around demonstrated bottlenecks. Polygon count is an input,
not a substitute for frame-time, visibility, collision and resident-memory data.
Begin with Seyda Neen and Balmora, then expand coverage. This is a planning
item, not part of the current implementation or validation claim.


## FIXES NEEDED IN BALMORA

### Jagged doorway arches

Owner report, v0.0.24-dev3, 30 September 2026: many Balmora doorways have
strongly jagged upper arches. Reference cameras: XYZ1218,-792,120, yaw352,
pitch-7; XYZ1269,-788,133, yaw343, pitch-18; and XYZ-1012,-939,142,
yaw204, pitch-5. Screenshots show irregular
dark strips around the upper door arch.

- [ ] Inspect source arch geometry, wall/door overlap and converted polygons;
  distinguish conversion defects from low-resolution rasterization.
- [ ] Compare a corrected mesh with a baked flat surface, bitmap or sprite
  where appropriate, choosing the least expensive method that preserves the
  intended appearance from nearby and oblique views. Preserve interaction and
  collision; a world-aligned surface must not turn to face the camera.
- [ ] Measure rendering cost and memory before adopting it broadly. Link this
  investigation with J021's concealed door/wall geometry work.

This is a recorded polish/optimization task, not an implemented dev4 change.


### Recurring deformed and blocked stairs — reusable conversion fix

Owner report from v0.0.24-dev3: XYZ962,119,64, yaw18, pitch-8. The screenshot
shows jagged stair treads and the owner cannot traverse them. The camera lies
inside the bounds of `ex_hlaalu_b_15`, placed reference 41379. Together with
XYZ613,-125,59 and the earlier b17 opening, this makes stair conversion a
recurring city issue, with both visual and movement consequences.

- [ ] Audit affected source visual triangles and authored collision separately;
  inspect surface winding, merging, overlap and depth ordering before attributing
  the jagged appearance to one cause. Check shared meshes across all placements.
- [ ] Build a reusable stair-aware collision conversion/validation step. Preserve
  authored walkable ramp/step surfaces and side boundaries; reject convex volumes
  that fill stair openings. Where reconstruction is needed, use bounded convex
  pieces or surface shells, retaining open space and the original landing heights.
- [ ] Sweep the unchanged standing hull along ascent/descent paths and landings,
  checking clearance, floor support, step height and slope; flag failures with
  source mesh, placed reference and coordinates. Do not force a generic ramp
  through an obstruction or change global player dimensions to hide the defect.
- [ ] Compare native before/after views and traversal, and measure clipnode/RAM
  cost before applying any higher-detail collision method across the city.

The current b17 shell correction is a narrow verified fix. It is **not** a claim
that these newly reported b04/dsteps03 and b15 stairs are repaired. This algorithm
and the doorway arch cleanup remain open work beyond the current dev4 correction.


### Proposed module: Balmora stairway optimizer

Additional owner report, v0.0.24-dev3: XYZ-883,126,300, yaw346, pitch-14.
The narrow stairs cannot be climbed. The camera is within `ex_hlaalu_b_13`,
reference 24020. Add this case to the recurring **Stairway to Balmora** issue.

Plan a reusable **Balmora stairway optimizer** in the Morrowind translation
pipeline, initially validated on these city cases but useful for other locations.
Its acceptance matrix must cover ascent, descent, narrow width, headroom,
landings, source/converted visual fidelity and runtime geometry/memory cost.
Collision success and intact appearance are separate required outcomes. Keep
the unchanged player hull as the test fixture; do not hide defects by shrinking
the character or changing FOV. This is TODO/design, not delivered functionality.


### Missing street ground texture

Owner report, v0.0.24-dev3: XYZ455,-699,61, yaw3, pitch17. The supplied
screenshot has the same XYZ and HUD yaw1/pitch16; retain both as nearby views.
It shows a broad flat untextured street patch around the lightpost in front of
two doorways.

- [ ] Inspect the source ground placement/material and converted face/UV/texture
  references to distinguish missing geometry, missing texture and incorrect mapping.
- [ ] Restore a continuous patch of the surrounding usual paving where supported
  by the original layout, matching texture scale/orientation and edge seams.
  Verify floor collision and avoid extra overlapping surfaces.

Suggested owner treatment: continue the usual street texture across the patch.
Status: recorded TODO; cause and correction not yet verified.


Additional stair validation case: v0.0.24-dev3, XYZ1182,-141,119, yaw91,
pitch-12; the owner cannot enter the stairway. Nearby mapped placements are
`ex_hlaalu_dsteps_03` reference41134 and `ex_hlaalu_b_04` reference22539.
This is another instance of the same dsteps03/b04 asset combination seen at
XYZ613,-125,59, strengthening the case for a reusable per-mesh correction
validated across placed rotations. Add to the Balmora stairway optimizer suite;
currently open, not covered by the b17 correction.


### Hlaalu guard missing/transparent chest armor

Owner screenshot, v0.0.24-dev3, Balmora: XYZ862,-502,58, yaw290, pitch13.
The guard's chest plate/torso appears absent or transparent, with the background
visible between the shoulders and waist. Owner suspects material conversion.

- [ ] Trace the NPC's equipped cuirass and BODY/armor slot resolution into the
  assembled actor; verify that torso suppression is paired with replacement armor.
- [ ] Check source submeshes, triangle retention/winding and transforms, plus
  material/texture presence, alpha flags and transparency-index conversion.
- [ ] Compare the original equipped appearance with the converted actor in native
  front/side/back views and animation; test other users of the same armor mesh.

Status: visual defect confirmed from the screenshot; exact conversion cause
remains unverified. Record independently from static building/door/stair issues.

## Debug teleport expansion

`dbg tp` means **debug teleport**. Keep the current named points of interest.
Future work: support original Morrowind world/map coordinates and placenames,
including case-insensitive `seydaneen`, `"seyda neen"` and `seyda_neen` aliases.
Inspect original coordinate/cell conventions before implementing conversion;
distinguish runtime-local XYZ from original world XYZ and validate safe arrival.
The requested `dbg aw hors 0` preset is current dev5 work: Hors, male Nord,
Barbarian, The Steed, after Census in Seyda Neen's square. A Balmora teleport
creates that preset only when no character exists; it preserves existing ones.

Owner acceptance against dev4, 30 September: Shift+V works; Balmora temple
passage is accessible as a Nord. Additional public stair reports remain in the
dev5 investigation: (-323,226,138), yaw260/pitch0 and (-527,187,143), yaw274/pitch-3.

## dev5 follow-up status (30 September 2026)

The earlier Balmora jagged-arch, blocked-stair, missing-paving and guard-chest
reports now have inspected causes and implemented candidates in
`INVESTIGATION-v0.0.24-dev5.md`. Native walking passes the previously stubborn
b04 arches and the new b02 approach (549,-739,58), plus the bridge05/06 stairs.
Keep citywide route acceptance open; a handful of passing routes is not complete
coverage. The birthsign cursor-only regression remains unreproduced; normal
native key dispatch passes and raw-event tracing is available.
## Recurring conversion acceptance: stair ramps

Every new region/interior family must include an authored stair-ramp check.
The Balmora `0.69766` normal versus former `0.7` walkable cutoff is a reusable
failure mode across repeated meshes, not a one-location defect. Inspect slope
classification separately from player dimensions and arch clearance; validate
idle support, ascent, descent and rejection of steeper non-walkable surfaces.
Procedure and RC1 evidence: [Stair ramp walkability](STAIR_RAMP_WALKABILITY.md).

## Dialogue inspection and long menus

- Reuse a vertical scrollbar for long option, destination, topic and text panes;
  support keyboard paging and pointer/wheel interaction with visible selection.
- Extend the isolated [character gallery](CHARACTER_MODEL_GALLERY.md) from bounded
  greeting previews to one-NPC topic/condition/result-script tests. Declare the
  test state and restore the entry snapshot on return to the game.
- Friendly-name search is debug-only, read from disk on demand. No gallery
  catalogue work belongs in ordinary gameplay's frame loop.

## Mutable NPC equipment

[Character equipment and shared assets](CHARACTER_EQUIPMENT_ROADMAP.md) are
required for partial corpse looting and equipment changes. rc10 caches existing
appearance snapshots; it does not make fixed outfits the final runtime design.
Preserve reusable source parts and per-actor state; do not pre-bake every outfit
combination. Normal gallery coverage and owner-approval requirements remain.

## v0.0.27 follow-up: target playtest and profiling

The stable private playtest package is assembled; the public source release is
published. The next acceptance work is target playtesting of that exact package.
Keep Vivec inactive and retain the bounded release scope during those checks.
The normal converter now emits bounded Seyda maps and the repaired three-rectangle
Balmora layout. The complete 2,717-map optimizer, actor/contact and static heap
gates passed; final image assembly and all HDF filesystem readbacks also passed.
Owner target acceptance, cold/warm lifecycle and runtime heap measurements remain
pending; estimates are not runtime results.

- The ordinary converter generates a 64-region Seyda Neen layout alongside its
  docks, court and fallback entries. Its 67-map static estimate passes, and the
  complete 2,717-map optimizer, actor/contact and heap gates now pass. The final
  private image and both HDF readbacks also pass; target playtesting remains
  pending. Do not confuse the historical 25-region layout with this generated
  result or call 64 regions a proven minimum. Preserve the 3 MiB non-map
  allowance, 2 MiB safety reserve, 896-unit coverage apron, collision/state
  guarantees and required content.
- A separate three-rectangle Balmora layout now merges adjacent cheap outer
  regions and divides the former oversized area while preserving the 64-slot
  format, 896-unit coverage apron, hysteresis and 3+2 MiB reserves. Its three
  static peaks are 3,087,760, 5,971,920 and 5,615,520 bytes. The complete
  saved-ABI audit now passes 65/65 entries and covers all 1,488 source references
  with none lost; the worst fallback is 6,155,504 bytes with 135,952 bytes of
  post-reserve margin. This remains static evidence: 5 MiB is a planning target,
  image/readback gates have passed, and target acceptance is pending.

The `bm027` replacement uses a 128-unit lower core with 96-unit hysteresis; an
adjacent region may remain active as the player crosses the small core's center
within that band. Half-open core ownership remains unique, and switching
thresholds are unchanged. Visual coverage keeps its 896-unit apron while physical
collision coverage uses the existing 224-unit apron. Test both directions around
the split/merge, including rapid noclip and held Ctrl+Shift, for terrain/scenery
continuity and collision. These transitions have not passed target playtesting.

- Run the final heap gate after subcell regeneration and actor annotation, against
  the exact maps that will be fingerprinted and packaged. Record map receipts,
  report/input hashes, runtime fields as pending until measured, and the exact
  engine/loader/configuration identity in the build receipt.
- Build the matching engine and HDF/configuration set from those audited maps.
  Then run the exact playtest entry and record transitions, held input, collision,
  player/actor/equipment state, cold/warm loads, first presentation and warmed
  gameplay. A static estimate, host allocator test, source compile or HDF build
  alone does not accept the playable repair.
- The memory workflow is **Heap Watcher → Profiler → Optimizer**: detect pressure,
  explain its source and phase, then change actual payload/representation and
  re-audit. Keep estimates distinct from target runtime observations. The
  5 MiB figure is a planning target; the 6 MiB BSP ceiling and 3+2 MiB reserves
  remain the policy. Optimization/source checks are not packaged acceptance.
- A matched full-VIS experiment may inform later visual/performance work, but is
  optional and does not block the repaired playtest. Compare equal inputs and
  settings; do not attribute missing scenery to VIS or accept extra visibility
  cost without measurement.

Historical memory evidence remains in [memory allocation](MEMORY_ALLOCATION.md),
[heap watcher and `build.json` receipt fields](HEAP_WATCHER.md#build-receipts-used-free-and-growth-margin),
[bounded-world candidate notes](BOUNDED_WORLD_CANDIDATES.md), and the
[world-detail/topology ladder](WORLD_DETAIL_LADDER.md). The 28-map baseline
included town overlays, special town maps and interiors; the separate
21-candidate trial had 6 passes and 15 failures (9 Seyda Neen and 6 Balmora
overlay/exterior subcells). Those counts describe different scopes and must not
be presented as a refreshed 28-map result or as proof that every town overlay
fails. Candidate failures guide profiling; they do not alone establish which
retained resource caused pressure.

## Reusable polygon-heavy town residency

Future dense settlements require actual payload reduction and bounded subdivision,
not merely more region records. Smaller cores alone can retain shared parent
terrain/PVS and may increase crossing frequency. Preserve the 896-unit apron,
current draw/hysteresis behavior, unchanged reserves, complete textured models,
collision and gameplay state unless matched evidence justifies a separately
reviewed change. Keep shared-border terrain/UVs continuous and test crossings in
both directions, including actors, swept collision and levitation.

Use the normal preparation path to select boundaries from measured per-region
payload, content density, visibility data and geometry/collision costs. Require
per-map receipts and full-cycle profiling before packaging; check region-count
limits and transition rate alongside heap. Adaptive subdivision is a planning
helper, not acceptance by itself. Keep total-town background counts/provenance
separate from per-map converted geometry: verify coverage and content directly.
No single central prototype, collision-only reduction or visual-face pruning
proves a complete town layout is safe. See the [bounded-town candidate workflow](BOUNDED_WORLD_CANDIDATES.md).

## Map panel: complete the Debug / In-Game selector after repaired playtest

The source prototype exposes aw_map_mode and aw_map_debug_available with
selection controls and debug-policy checks. The rc5 engine compile and private
candidate image include the marker/contrast correction and passed HDF readback.
Nine focused source checks passed; the repaired Linux native world-UI fixture
subsequently passed in the complete 558-test Docker suite. Owner target acceptance
remains pending. Complete this feature after
the repaired playtest gate. See [world map and journal](WORLD_MAP_AND_JOURNAL.md)
for the interaction contract and progress checkpoint.

- Present obvious Debug and In-Game mode buttons with a visible selected state.
  Respect the configured default and aw_map_debug_available so debug-only
  controls cannot appear or activate in the regular mode.
- Finish the Debug map and In-Game map as distinct, tested views. The In-Game
  view needs its player-heading triangle, crosshair, verified original-game
  location markers, two useful map scales, click-to-zoom, and navigation/pan.
  Preserve the established marker identities and world-coordinate transforms.
  Validate axes, interiors, cell changes, teleport and levitation.
- Read and decode only verified owner-provided map inputs on demand. Keep
  proprietary map art and icons out of public source and release artifacts.
  Bound input reads, decoded buffers, cache/switching peaks; release inactive
  views and test open/switch/close.
- Add original-game unexplored-area fog/masking as a later milestone, driven by
  visited exterior locations and saved exploration state; it is not a repaired
  playtest prerequisite.
- Accept only after normal build integration from a matching source checkpoint,
  correct engine/configuration generation, input/modal behavior, persistence as
  specified, and target checks. The existing terrain overview/crosshair does
  not alone complete the In-Game map.

## Dialogue, music and video import/runtime milestones

Voiced-dialogue conditions and the complete video catalogue remain later
content/runtime work. The 18-track music package is complete; playback validation
remains separate. Keep all original and converted
proprietary audio/video assets private; public changes may contain source logic,
asset-free manifests/schemas and documentation only.

### Variable voiced dialogue

The current runtime is a bounded generic HELLO audition, not full voiced dialogue.
Implement applicable voiced lines with their original event conditions and ordered
selection semantics. Ambient HELLO/IDLE behavior is distinct from conversation
GREET; do not substitute uniform random selection or treat a static topic match as
a runtime trigger. Verify condition evaluation, speaker/context, priority,
repeat/cooldown and return-to-game state against owned records and a documented
reference implementation. Convert/import all applicable voice lines into
playtest-selectable resources, then test representative states and failure paths.
See [voiced dialogue research](VOICED_DIALOGUE.md); it documents evidence and
remaining work, not completion.

### Music

Compare existing converted and packaged music against the complete available
owner-provided source inventory so individual missing tracks are visible even
when totals happen to match. The observed inventory contains 18 MP3 tracks; all 18 and 124 alias rows are
included in the private v0.0.27 playable package. Target playback checks remain
open, including the number-or-filename-stem `dbg ost play` command. Include any
additional expansion tracks found in the owned source inventory. Preserve the
current music playstyle and playback routine; this is a completeness requirement,
not a playback redesign. Record source identifiers/hashes, converted and packaged
counterparts, missing optional files and conversion failures separately. Keep
original and converted audio private. Acceptance requires per-item completeness
and regression checks of the existing playback behavior.
### Optional video catalogue and playback

Compare converted and packaged files against the complete owned video inventory,
then convert/import every available clip through the normal conversion/compile
pipeline, including Tribunal and Bloodmoon files if present. The observed source
inventory has 17 Bink files; individual converted/package completeness is not yet
verified. The catalogue helper has only syntax-level validation. There is no
completed all-video conversion or accepted runtime integration.

The planned stable catalogue IDs and `dbg playvid` interface are not active. Debug
playback wiring is paused after automatic review did not approve the attempted
change; resume only through an approved implementation route. Acceptance requires
safe missing/invalid-resource handling, bounded buffers, palette/audio ownership,
skip and normal completion, and restoration of the same scene/player/actor state
without advancing the opening script or reloading the map. Verify each source,
converted and packaged identity/hash plus omissions and failures. Original and
converted media remain private. Story-event triggers are separate future work;
the partial New Game intro path does not satisfy catalogue completeness.

## Visual quality, visibility and performance follow-up

Keep coverage completeness, VIS, draw-distance culling, fog, LOD and resident
memory as separate investigations.

Visibility is now required work, not optional
([TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md),
[Town visibility](performance/TOWN-VISIBILITY.md)): every build reports the visible share and the
entities still sent. The 8 October 2026 prototypes measured negligible benefit from the
tested occluders and world-model building faces with the current town partitioning; town frame rate is sought from
drawing less at a distance and cheaper per-model work, and interiors still need
the room occluder test. Measure visual and memory effects per map. VIS cannot create missing terrain, textures
or placements.

For the inspected Ashlands central peak, source attribution now identifies an
opaque `terrain_rock_rm_18` static rejected by whole-model distance culling.
LAND-only fill is insufficient; a bounded heightfield remesh fails 44 of 48
sampled views, with a worst top-silhouette error of 13 pixels at 128x60. Keep
other blank/white-horizon reports separate. Next compare source-preserving rock
geometry/proxies at fixed pose, yaw/pitch, time, draw distance and fog, retaining
near depth protection, seams and resource budgets. No complete fix is accepted;
see the [active horizon study](PLAN-v0.0.29.md#distant-terrain-topology-and-occlusion-study).

The observation that a requested 1000-unit
Balmora distance felt faster is not a measured effective distance or diagnosis;
record requested and effective range, frame timings, culling/rejection counts,
clipped/drawn surfaces and cache/I/O activity. Fog palette behavior is distinct
from distance culling, and culling must not be described as unloading assets
without evidence.

Later LOD work must use full 3D distance and bounds, including levitation,
undersides, cliffs and vertical town spaces. Preserve collision and gameplay
state, use bounded resource ownership and measured hysteresis, and test seams and
transitions. LOD is not a substitute for complete source coverage or a promised
memory/FPS saving.

## Later mapping: Vivec remains inactive

Vivec is mapping/planning work only. Do not add it to runtime registration,
build configuration, the repaired playtest or active gameplay code until after
that playtest and a later explicit scope decision. Any future slice must account
for stacked spaces, cantons, bridges, water, interiors, collision, seams, actors,
levitation and bidirectional crossings, with bounded measured payloads and the
same unchanged reserves. Keep source game assets private.
Full-VIS comparison status (3 October 2026): optional experiment stopped to free
CPU for the repair playtest; inputs/logs and the tool's periodically saved state
were preserved privately. Resumption is unverified and no final comparison is
accepted. Retain this as deferred research, not a normal-build prerequisite.

### Mandatory follow-up: building geometry and collision audit

Owner-confirmed MUST-DO, 3 October 2026, scheduled after the current repair
playtest. Profile source versus converted house/building geometry, polygon counts,
loading/resident memory and frame costs. Investigate decorative details, internal
or genuinely unseen surfaces, exact mesh sharing and collision representation
without assuming those elements are redundant. Preserve doors/windows/openings,
walkable spaces, original UV/material intent, silhouettes and collision. Accept
measured savings only after matched visual and gameplay regression checks. Use
matched original-versus-candidate A/B geometry captures and measurements at the
same camera, region and load state so reduced faces or collision cost are not
confused with culling, fog or changed residency.
This is mandatory follow-up, not a prerequisite that delays this playtest.
Building-audit example: Harry recalls particularly high polygon counts on some Seyda Neen buildings, including arches. Measure curved tessellation, decorative surfaces and collision cost; preserve arch openings, silhouette and original UVs. This is an observation to profile, not established redundant geometry.
Building-audit hypothesis, Harry's “it just works!” observation: original meshes
may include substantial geometry hidden or unused in normal views. Determine
which surfaces genuinely lack required consumers before removing anything;
occluded geometry can still matter for levitation/other angles, interiors,
collision or visibility. Source polygon totals are not visible-frame totals.
Do not present unnecessary-face counts or removable savings as established yet.


### Entity pressure and safe reclamation (proposed; not implemented)

- [ ] Report true live entities, allocation high-water mark, reusable and quarantined free slots, and allocation failure origin separately.
- [ ] Profile allocation lifetimes and ownership across loading, gameplay and unloading; distinguish edict availability from Hunk, cache and external memory.
- [ ] Introduce checked admission only for proven optional callers that can accept rejection without gameplay side effects. Keep required-allocation recovery.
- [ ] Evaluate subsystem-owned cleanup at safe lifecycle boundaries. Generic distance eviction of NPCs, scripts or collision remains unsafe; future virtualization requires protected identities, complete state and dependency handling.

Renderer culling does not release gameplay slots. Existing static catalogue capture retains meshes and collision; its memory must still be budgeted. This work must not delay the current playable candidate or relax memory reserves.


### Selective baked building panels (proposed A/B extension)

- [ ] Extend the existing explicitly selected decorative-window panel baker to audited component/surface selections for eastern Seyda house, balcony and roof/overhang assemblies. Preserve structural depth, silhouette, openings, texture orientation and collision. Whole-building billboards are not the default.
- [ ] Bake from owner-supplied inputs at conversion time. Public source may contain the converter, recipes and synthetic tests only; original and derived game assets remain private.
- [ ] Preserve variant A and isolate variant B; compare matched viewpoints, surface boundaries, texture memory, collision, compiled BSP/heap costs and target frame times. Host face reduction does not establish a playable repair.

The existing surface_flatten.py route currently selects exterior decorative windows, not complete shacks. A private exact-coplanar shack specimen reduced 1,113 faces to 1,100, which is insufficient to close the current heap incident.

### Current compiled-density and building overlay diagnostics

- [x] Refresh the private 64-owner polygon mosaic from hash-matched final maps,
  with disjoint-core density and combined loading margins. Count placed compiled
  polygon pieces separately from source triangles, resident memory, sprites and
  collision planes; retain special routes outside the regular-core mosaic.
- [x] Prepare a private overhead overlay combining the density background with
  selected actual building placements and reference identities. This is a
  diagnostic projection, not a target render or a complete town/walkability map.
- [ ] Review the optional overlay tool and isolated wood-detail LOD prototype
  against visual, collision and target-memory gates before integration. Neither
  is an established fix. The bounded collision-containment trial saved zero
  bytes; the current 29-map heap failure remains open before image assembly.

Keep generated geometry/media private; record actual representation savings and
preserve unchanged reserves. See WORLD-FLORA-HEAP-010 in the bug journal.

The dedicated [Study lanterns and torch lighting more](LANTERNS_AND_TORCH_LIGHTING.md)
covers wall-mounted torches, lantern fixtures and carried lights; authored
placements/attachments; indoor static/dynamic lighting; the guard day/night
cycle; and measured local illumination rather than flame sprites alone.

## Future combat milestone: Time to Fight!

Begin after shipping v0.0.29 **More Mushrooms**. This is planned work, not an
implemented mode or an additional requirement for the current release.

1. **Build the Nerevarine combat arena first.** Establish a bounded, resettable
   test arena with reliable collision, spawn positions and safe entry/exit.
   Survey the original Vivec Arena Pit CELL, placements and routes as the source
   candidate. Verify that source identity before conversion; the prototype's
   name does not establish original quest eligibility.
2. **Enter with `dbg arena`, then trigger combat with E.** The command places
   the player in the implemented arena interior with an initially calm opponent.
   Target that NPC and press E to start the encounter; show a suitable interaction
   prompt. Entering the arena alone must not trigger hostility. Establish the
   calm-to-aggro transition, target acquisition, approach/chase and attack range.
   Retain actor identity, health and target state. Reset returns the test opponent
   to its initial calm state; repeated E presses must not restart active combat.
3. **Start with sword and shield versus sword and shield.** Give the player and
   one hostile NPC that equipment pairing. Establish attacks, blocking, hit and
   damage resolution, health, defeat and encounter reset before expanding the
   weapon and opponent set. Compare intended mechanics against original data
   and the OpenMW reference.

**Make failed hit rolls visibly understandable.** Retain the intended
skill/stat-based hit resolution. When a valid melee attempt against an NPC fails
its hit roll, show a short dodge, lean or appropriate weapon/shield deflection
instead of an apparently solid impact that produces no response. Prototype this
with the sword-and-shield arena opponent after the basic combat loop works.

- Resolve an attack once; its animation and sound present that outcome without
  adding another avoidance roll, damage, skill gain or attack opportunity.
- Keep an out-of-reach or off-target swing distinct from a failed hit roll. Only
  an eligible target should react. A cosmetic deflection must not grant actual
  shield-block effects; mechanically resolved blocks retain their own animation,
  sound and gameplay consequences.
- Synchronize the reaction with the swing's contact window and respect existing
  stagger, death and attack states. Evaluate short animation blends without
  teleporting actors, opening mesh seams or letting cosmetic motion change the
  resolved result. Measure the target animation/frame cost before acceptance.

A useful visual reference is [Can't Touch This — Combat Miss Feedback](https://www.nexusmods.com/morrowind/mods/59155)
by MrArrean and Dubiousnpc: its author describes dodge animations for missed
attacks against humanoid NPCs. It is an OpenMW mod, extracted from N'Garde's miss
feedback feature. This is a behavior reference, not an imported dependency or an
AmiWind implementation claim. N'Garde's other combat changes are outside this proposal.

**Include speech and combat audio in the first encounter.** Resolve the
opponent's appropriate original aggro, combat-taunt and attack speech through the imported dialogue
lookup and its actor/condition rules; do not substitute unrelated dialogue.
Trigger the aggro line on the calm-to-hostile transition, with appropriate
anti-repeat behavior for later combat speech. Include original combat taunts
as a distinct speech opportunity during the encounter, using matching actor voice
and verified dialogue conditions. Give taunts a cooldown and avoid immediate
repeats or overlapping speech from the same actor; suppress inappropriate lines
during death and resolve priority against hurt/aggro reactions. Bound concurrent
speech so taunts do not drown out essential combat cues or interrupt music.
Verify taunt availability, playback and event gating in the arena audio checks.
Include weapon swing/whoosh,
hit/impact, shield-block, hurt and death events using verified original sound
records and available converted assets. Check timing against the actual attack,
contact or block outcome rather than playing every sound on every swing.

Missing or unresolved audio must be visible in coverage/build warnings; converted
files alone do not prove event playback. Test that speech and effects work together
without crackling or interrupting the soundtrack. Original and converted game
audio stays in private build assets; public source contains code and lookups only.

**Exercise combat music and player death in the fight tests.** The calm
arena starts with normal music. The E-triggered calm-to-aggro transition requests
combat music once. When the opponent dies or the encounter otherwise ends with
the player alive, end the combat selection and return to normal music. Drive this
from encounter state, not animation frames, momentary visibility or cell loading;
later multi-opponent encounters must wait until no active threat remains.

Keep music decoding/output serviced during track changes, effects and speech;
avoid frame-driven restarts, unintended silence and crackling. The soundtrack's
priority remains independent of world simulation or full-screen modal freezing.
Verify actual audible start/end transitions in the target emulator, including
encounter reset and abort, rather than only checking playlist variables.

Player death requires its appropriate original death sound and camera movement.
Verify the reference behavior and available actor/audio assets, then implement
the death camera motion and its transition out of normal player control. Trigger
the death sequence once; repeated damage must not restart the sound or camera.
Reset/retry must restore the normal camera, controls and encounter state. Treat
player death as its own audio/state transition instead of briefly returning to
exploration music while the death sequence starts. The precise camera motion,
timing and death-state music handling remain reference-verification tasks.

Arena acceptance includes calm entry, E-triggered combat, NPC defeat, abort/reset,
player death, repeated damage during death, and retry with restored view/control.
Report missing death/voice/effect assets through the build coverage warnings.
These requirements belong to Time to Fight! after the final More Mushrooms
release; none is claimed implemented by this roadmap entry.

Use the planned isolated `dbg arena` mode. Preserve and restore the player's
existing state and isolate test hostility, equipment, deaths, reputation and
scripts from main-quest progress. Canonical duel eligibility, including the
Redoran Hortator/Bolvyn Venim quest, requires its own source verification.
Measure actor, animation, sound and lighting costs; verify completion, abort,
reset, save restrictions and return travel before expanding scope.

After that combat baseline, investigate minimal NPC state and traversal outside
loaded cells as described below. Do not pull that later design into the current
mushroom release.

### Deferred: minimal NPC state outside loaded cells

Sequence: finish the v0.0.29 **More Mushrooms** release, establish the initial
combat behavior and tests, then design NPC traversal outside loaded cells and
sub-cells. This task is not a blocker for the mushroom release. The representation
and scheduling algorithm remain undecided; no implementation is claimed.

- [ ] Define a compact authoritative actor record that survives removal of its
  rendered model and full active simulation. Determine the minimum identity,
  logical location, health/equipment, target, follow/chase intent, travel progress,
  quest/script dependencies and timers that must remain; validate against combat.
- [ ] Decide when off-screen travel is advanced, which connections are traversable,
  and how to restore an actor at a valid entry point when its area becomes active.
  Do not keep every world cell or actor model resident, discard gameplay state,
  or replace path traversal with teleportation directly beside the player.
- [ ] Preserve one authoritative actor through unload/re-entry, overlap and
  save/load. Prevent duplicates, repeated attacks, lost followers and aggression
  resets. Respect original loading-door rules separately from streaming sections.
- [ ] Measure record size, aggregate memory, update cost and re-entry peaks with
  several pursuers/companions and long outdoor travel before choosing limits.

Behavior constraints: [NPC cell traversal](NPC_CELL_TRAVERSAL.md). The exact
simulation detail for unloaded terrain remains a design and profiling question.

## Main-quest milestone: Just an Old Man with a Skooma Problem

Planned follow-up: meet Caius Cosades and progress toward Hasphat's Dwemer
puzzle-box request. Verify the original dialogue, quest conditions and any
recorded voice references before implementing them; available audio conversion
alone does not establish dialogue playback or quest completion.

Use Caius's house as a bounded interior test. Convert low-poly skooma bottles
and appropriate original clutter at their source placements, preserving
silhouette, material seams, collision and interaction identity. Compare the
interior with the original-data OpenMW reference, then check target rendering,
memory and traversal. These are planned tasks, not completed quest or interior
coverage, and do not block a smaller verified development playtest.

### Conditional v0.0.29 release checkpoint -- More Mushrooms

The planned release title is **AmiWind v0.0.29 -- More Mushrooms**. Ship only after worldwide original mushroom placement and picking are complete and the relevant release gates pass; this is a future milestone, not a completion claim. See the [v0.0.29 plan](PLAN-v0.0.29.md#conditional-release-milestone-more-mushrooms) for scope and evidence requirements. Dev4's six-placement pilot may supply clearly labeled progress screenshots only; final release screenshots must show the completed worldwide candidate. The later Caius quest milestone is separate from this release title.

## Mandatory roadmap and bug tracking

Maintain this roadmap with [BUGS.md](BUGS.md) and the [current release plan](PLAN-v0.0.29.md). Each active or deferred milestone needs its current scope, next action and acceptance gate; each defect needs an ID, evidence and status. Reconcile both against the exact package before release. Current priority remains final More Mushrooms before the combat-arena milestone.
