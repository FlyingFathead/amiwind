# CHIM

CHIM is how AmiWind's world is stored and streamed from v0.0.33 on: the
CHIM builder turns your own Morrowind data into a world where every mesh,
collision hull and texture is stored once and placed by reference, and the
CHIM Engine streams that world around the player on an Amiga. This page says
what CHIM is, where it stands and where to read more. The ideas that are
designed, measured or held back are collected in [CHIM ideas](IDEAS.md), and
what CHIM has already achieved, with the measured gains, is in the
[CHIM feature tracker](FEATURES.md). How far the open world has been
converted, cell by cell, is on the generated
[CHIM cell tracker](CELL_TRACKER.md).

<!-- contents start -->
## Contents

- [What CHIM is](#what-chim-is)
- [Versions](#versions)
- [Design rules](#design-rules)
- [Milestones](#milestones)
- [Credits and licences](#credits-and-licences)
- [CHIM documents](#chim-documents)

<!-- contents end -->

*AmiWind is an unofficial, experimental project. Not affiliated with or
endorsed by Bethesda Softworks or ZeniMax.*

## What CHIM is

**The CHIM Engine** is the AmiQuake engine AmiWind has always used, with a
world streamer added; it is not a second engine. The renderer, lighting,
collision, sound and QuakeC are Quake's. What changes is the outdoor world:

- **Exteriors are chunks, stored once.** The land is cut into frames of 3 x 3
  Morrowind cells, frames into chunks of 256 units, chunks into sectors of
  3 x 3 chunks. Each sector is one small file that a classic Amiga FFS disk
  reads whole, front to back. Every shared model and texture lives in the
  sector that first needs it; every placement is one record that names its
  model. Nothing is copied into every map that can see it, as the legacy
  region maps did (each exterior object about ten times,
  [WORLD-REGION-DUPLICATION-31](../bugs/WORLD-REGION-DUPLICATION-31.md)).
- **A ring around the player.** The chunks within the view distance (plus a
  margin) are resident; models and textures live in a memory zone with an
  LRU list and leave when no resident chunk needs them. Chunks join and leave
  a little at a time, within a per-frame budget, so streaming does not stop
  the game.
- **Terrain is world geometry.** Each chunk's ground is a small BSP subtree
  grafted under the frame's world, so Quake's visibility, collision and water
  work on it as on any map.
- **Interiors stay Quake maps.** Houses, caves and the prison ship are
  ordinary Quake maps behind doors, built as before; Quake's `vis` works well
  indoors.
- **One frame map per area.** A small Quake map (`maps/<town>-chim.bsp`) holds
  what is not chunk data: actors, flora sprites, the start point and the
  frame's position. Loading it switches the engine to CHIM for that area.

The data files are specified in the [world format](WORLD_FORMAT.md); the
engine side is in [CHIM engine](ENGINE.md).

### The name

CHIM was the working name of the streamer and became its public name. The
humorous backronym: **CHIM = [C]hunks and [H]eaps [I]n [M]emory**, which is
exactly what the engine juggles. It is also a nod to CHIM in The Elder Scrolls
lore, the state of knowing that the world is a dream and keeping hold of
yourself anyway: a fitting name for an engine that only ever holds a small
part of the world in memory.

In the project's own wording the two builders and engine paths are
**legacy** (the region-map pipeline up to v0.0.32) and **CHIM**. They are
names, not numbers: there is no "builder v2" or "engine v2".

## Versions

CHIM has its own version number, separate from AmiWind's:

| | |
| --- | --- |
| First release | CHIM 0.1.0 with AmiWind v0.0.33 |
| Where it is kept | the `CHIM_VERSION` file at the repository root, the one source for the builder receipts, the engine header and the boot check |
| How it is shown | short form on the boot check, "AmiWind vX / CHIM vY"; long form "Running on CHIM Engine vY" in the README and release notes |
| Numbering | semantic versions: a new world format major version is a new CHIM major version (the engine refuses a world of another major with a clear message); minor = features; patch = fixes |
| Builder and engine | always the same CHIM version |
| Receipts | every CHIM build records `builder: chim`, `chim_version` and `world_format` |
| CHIM 1.0 | the release in which the whole island runs on CHIM |

The world format has a version of its own (0.5 in source, 0.6 for large
frames); the engine reads the range it knows and refuses the rest.

## Design rules

These rules come from measurements and owner decisions; every CHIM change is
checked against them.

- **Stored once, placed by reference.** One copy of every mesh, hull, texture
  and terrain face. An asset is converted and fixed once, and every placement
  of it on the island gets the fix: the silt strider of all nine caravan
  towns is one model.
- **One builder.** Everything a CHIM build contains comes from the
  repository's builder and your own game files, with no private step. Release
  candidates and finals are built from scratch. The legacy builder stays in
  the code, selectable (`--builder legacy`); no working method is deleted.
- **Vis must work.** Placements are linked to the leaves their boxes touch,
  terrain is world geometry, and every change is checked with the renderer
  counters (entities sent, faces drawn and clipped, BSP nodes per face) on
  fixed cameras: they may not get worse
  ([renderer counters](../performance/RENDERER-COUNTERS.md),
  [town visibility](../performance/TOWN-VISIBILITY.md)).
- **Think in Quake first.** Before inventing anything, find how Quake or
  AmiQuake already does it (brush models, efrags, the PVS, lightstyles, the
  Hunk and the zone) and map Morrowind's data onto that.
- **Think in scale.** A bug in one place usually has a cause that repeats.
  Each finding names its mechanism, the whole island is swept for the same
  mechanism, the fix goes into the shared converter once, and the sweep stays
  as a builder gate (see [island-wide audits](IDEAS.md#island-wide-audits-mechanism-classes)).
- **Don't block the traffic.** Incremental streaming spreads loading across
  frames with a per-frame budget, and the whole-world rebuild is off the main
  path; reads are still synchronous, so a chunk read can cause a short stall.
- **No artificial clamps.** The view distance follows the ring and the memory
  budget; a limit that remains is measured and stated by the engine, never a
  silent cap.
- **Classic FFS on disk.** File names of at most 30 characters, few files per
  directory, files well under 2 GiB, packs written whole in walking order. A
  disk-layout gate checks every build. The target is the whole game on one
  legacy-safe hard file.
- **Counts first.** Emulator frame rates are relative until a real
  accelerated Amiga has been measured; faces, entities, bytes read and memory
  peaks are the main currency.

## Milestones

Each milestone is a private test build made from scratch with the repository
builder, walked in FS-UAE, gated and compared with the legacy maps at the
same poses before it counts. Status on 9 October 2026:

| Milestone | Area | Status |
| --- | --- | --- |
| M1 | Balmora exterior | Built and walked: five benchmark cameras, the street loop, gate exits and doors in and out of interiors pass in FS-UAE. Played in the first private test builds. Open: chunk loading when the memory zone is full ([CHIM-CHUNK-LOAD-FAIL-33](../bugs/CHIM-CHUNK-LOAD-FAIL-33.md), repair on a branch), the distant view ([CHIM-FAR-TERRAIN-33](../bugs/CHIM-FAR-TERRAIN-33.md)). |
| M2 | Seyda Neen, the intro docks and the courtyard | Built; passes the validator, the stair gate, the strict heap gate (no exceptions) and the frame-map checks against the shipped maps. The temporary Seyda Neen heap bypass of the legacy builder ends here. Open: the Hunk safety margin at the default zone ([CHIM-SEYDA-HUNK-GAP-33](../bugs/CHIM-SEYDA-HUNK-GAP-33.md)). |
| M3 | Vivec | Stage A (the Arena canton, with v0.0.32 parity gates) in progress; stage B (all of Vivec in one frame, format 0.6) designed. |
| M4 | The open world between the towns | Designed: a fixed grid of frames, frames crossed without a map load. |
| M5 | The whole island | After M4; this is CHIM 1.0. The project is aiming for 1 May 2027, Morrowind's 25th anniversary: an aim, not a promise. |

v0.0.33 ships when the areas v0.0.32 ships run on CHIM and the distant view
is at least as good as v0.0.32's horizon (the HORSTATOR APPROVED method,
`aw_skyline_fill 0`). Until an exterior is on CHIM, a CHIM build either
leaves it out ("Area unavailable") or, in test builds, keeps its legacy maps
marked as not yet CHIM; a CHIM build never ships legacy exterior maps for an
area that is on CHIM.

## Credits and licences

The CHIM Engine is built on the GPLv2 engine of id Software's Quake (John
Carmack and the id team) and on AmiQuake (Peter McGavin, NovaCoder, Stephen
Leary). The CHIM builder is GPLv3. Details and the reviewed upstream revision:
[licensing and credits](../LICENSING_AND_CREDITS.md).

## CHIM documents

| Document | What it covers |
| --- | --- |
| [CHIM feature tracker](FEATURES.md) | What CHIM has done so far: every feature with its status, measured gain and visibility story |
| [CHIM ideas](IDEAS.md) | Every idea and held-back item with its status |
| [World format](WORLD_FORMAT.md) | The files the CHIM builder writes, the M3 and M4 designs, the heap gate, the version rules |
| [CHIM engine](ENGINE.md) | How the engine loads, keeps, draws and collides with a CHIM world; memory and tests |
| [CHIMport](CHIMPORT.md) | The whole island converted cell by cell from the sea inwards, every audit per cell |
| [Disk space](DISK_SPACE.md) | Amiga disk limits, what CHIM saves, and the size budget of the whole game |
| [CHIM statistics](STATS.md) | `chim-stats.json`: polycounts, disk, memory and streaming figures of every build |
| [CHIM texture effects](TEXTURE_EFFECTS.md) | Optional `.chimfx` texture effects |
| [CHIM lighting](LIGHTING.md) | How CHIM lights a cell like the original: the options measured, the hybrid lighting type |
| [CHIM lights roadmap](LIGHTING_ROADMAP.md) | The lighting milestones, their checks and the pending decisions |
| [CHIM NPC pathfinding](CHIM_NPC_PATHFINDING.md) | The walkable graph in the world format, budgets and gates |
| [CHIM cell tracker](CELL_TRACKER.md) | The generated live status of every open-world cell on CHIM |
| [CHIM Progress Tracker guide](PROGRESS_TRACKER.md) | How the tracker works: statuses, audits, lighting, releases, the Toolkit legend, commands |
| [Cell result format](CELL_RESULT_FORMAT.md) | `aw-cell-result-1`, the file a conversion run hands to the tracker |
| [CHIM build guide](build_guide/README.md) | Builder types, MiniWind, quick test builds, speed, emulator presets |
| [Builder profile](../performance/BUILDER_PROFILE.md) | Where a full build spends its time, the cost of a failure, and the builder fixes and time savings since v0.0.33 (chart) |
| [World streamer](../WORLD_STREAMER.md) | The original design and its requirements (memory placement, visibility) |
| [Asset census](../ASSET_CENSUS.md) | The measurement behind "stored once" |
| [Modular NPCs](../MODULAR_NPCS.md) | NPCs assembled from shared body parts |
| [NPC pathfinding](../NPC_PATHFINDING.md) | How Morrowind, OpenMW and Quake move characters, and the plan for AmiWind |
| [Distant shells](../DISTANT_SHELLS.md) | Closed low-poly "mold" shells for distant buildings |
| [CHIM bug tracker](../bugs/CHIM_TRACKER.md) | The CHIM bugs at a glance; every bug also has its row in the [bug register](../BUGS.md) |
