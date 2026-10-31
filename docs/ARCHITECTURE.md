# Architecture

_Last updated with AmiWind v0.0.57 (31 October 2026)._

How AmiWind is put together today: a host-side builder that converts your own Morrowind files, and the CHIM Engine
(the AmiQuake engine with a world streamer added) that runs the result on an Amiga. Each claim below points at the
file or page that backs it. What is not done yet is marked *planned* and linked to the [roadmap](ROADMAP.md).

## The shape of the project

The host reads your own copy of the game data, converts it and writes the game as disk images and files outside the
repository; the repository holds the tools, the engine source and the documentation, and no game data
([licensing and credits](LICENSING_AND_CREDITS.md)). The target is an Amiga with AGA, a 68040 with FPU and 2 MiB Chip
plus 32 MiB Fast RAM, the safe minimum for the whole game since 23 October 2026 (16 MiB, the baseline the engine
must keep starting on, warns and loads more often; [why 32 MB](REAL_HARDWARE.md#why-32-mb-of-fast-ram),
[AGA runtime](AGA_RUNTIME.md)). The engine
is AmiQuake, which is Quake's renderer, lighting, collision, sound and QuakeC; AmiWind reuses Quake's machinery
before building anything new ([engine study](history/superseded/ENGINE_STUDY.md)).

| Part | Where | Page |
| --- | --- | --- |
| Builder (host) | `tools/build.py`, `tools/chim/` | [CHIM build guide](chim/build_guide/README.md), [build profile](BUILD_PROFILE.md) |
| CHIM engine | `engine/aga/src/chim/`, hooks in `engine/aga/src/aw_*.c` | [CHIM engine](chim/ENGINE.md) |
| World data | `chim/world.cwi`, frame and sector files, `.chim` frame maps | [World format](chim/WORLD_FORMAT.md), [.chim map format](chim/CHIM_MAP_FORMAT.md) |
| Interiors | ordinary Quake `.bsp` maps | [Interior sections](INTERIOR_SECTIONS.md) |
| Toolkit (inspection pages) | `amiwind-toolkit/` | [Toolkit](AMIWIND_TOOLKIT.md) |

## CHIM: store once, place by reference

CHIM is how the world is stored and streamed from v0.0.33 on ([CHIM overview](chim/README.md)). The legacy way
stored each exterior object about ten times, once in every region map that could see it
([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md)). In CHIM:

- Every mesh, collision hull and texture is stored once; a placement is one record that names its model.
- The outdoors are cut into frames, frames into chunks of 256 units, chunks into sectors of 3 x 3 chunks; a sector is
  one small file read whole ([CHIM overview](chim/README.md#what-chim-is)).
- A ring of chunks around the player is resident. Chunk terrain is grafted into the frame's world model, so Quake's
  visibility, collision and water work on it unchanged (`engine/aga/src/chim/chim_graft.c`).
- Placements are linked to the world leaves they touch with Quake's static entities and efrags, so the potentially
  visible set culls them; there is no edict and no model index per placement (`chim_chunks.c`).
- Maps are `.chim` files, not `.bsp`. Today a `.chim` is still an empty BSP29-shaped shell that carries entities and
  the link to its frame; giving it its own header and loader is *planned* ([.chim map format](chim/CHIM_MAP_FORMAT.md)).
- CHIM has its own version, kept in the `CHIM_VERSION` file; the world format is versioned separately and the engine
  refuses versions it does not read ([CHIM versions](chim/README.md#versions)).

### The engine modules

All in `engine/aga/src/chim/`; each file's header comment says which Quake mechanism it reuses.

| File | What it does |
| --- | --- |
| `chim_world.c` | start-up probe, per-map activation, memory banks, the `chim` console command |
| `chim_format.c`, `chim_format.h` | decoders for the world formats (byte access, so a host test reads them as the 68k does) |
| `chim_zone.c`, `chim_zone.h` | banked model zone: allocation after Quake's `Z_TagMalloc`, least-recently-used eviction after `Cache_Alloc`; blocks never move, so brush models keep their pointers |
| `chim_chunks.c` | the chunk directory, the ring around the player, placements, collision and the link into the renderer; each placement is drawn and collided once |
| `chim_graft.c` | grafts the active chunks' terrain into the frame's world model |
| `chim_models.c` | shared models and textures, held in the zone and not limited by `MAX_MODELS` |
| `chim_statics.c` | streamed statics (flora sprites and static models) that become entities while their chunk is active |
| `chim_far.c` | the frame's distant land, resident for the whole map |
| `chim_cuts.c` | whole-structure distance cuts, so a walkway is drawn or left out as one piece |
| `chim_prefetch.c` | reads the frames the player is likely to enter next into spare Fast RAM and serves later reads from it |

Details and limits: [CHIM engine](chim/ENGINE.md), [world streamer](WORLD_STREAMER.md) (memory placement, visibility
and culling requirements), [far terrain](chim/FAR_TERRAIN.md).

## Memory

CHIM never grows the Hunk at run time: a CHIM map takes one bank from the Hunk when it starts and gives it back with
the map (`chim_world.c`). Extra Fast RAM past the 16 MiB baseline becomes banks that survive a map change and hold
shared models, textures and the prefetched frames; the 16 MiB baseline must keep working, and without such banks
nothing prefetches (`chim_world.c`, `chim_prefetch.c`, [CHIM engine](chim/ENGINE.md#memory)). The builder predicts
each frame's heap and refuses frames over the limit ([heap watcher](HEAP_WATCHER.md),
[CHIMport](chim/CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget)).

## What is on CHIM

Every exterior cell of Vvardenfell has been on CHIM since v0.0.43: 1,409 cells, of which 1,292 are land, 98 are
sea floor and 19 are open sea; 1,348 are one-cell region frames and 61 sit in the town frames (Balmora, Seyda Neen
and the whole city of Vivec). No classic region maps remain outdoors. The counts and what they mean are in
[what we count](chim/CELL_TRACKER.md#what-we-count) and the [progress tracker](chim/PROGRESS_TRACKER.md); the
current release is described in the [v0.0.53 notes](releases/notes/RELEASE-v0.0.53.md).

Interiors: since v0.0.48, 1,132 of the 1,134 base-game interiors are CHIM rooms, on CHIM's store-once layout. Only
the prison ship and the census office, where the opening sequence runs, stay classic Quake room maps on purpose
until rooms have object state. Solstheim is not converted
([README](../README.md#where-amiwind-stands-31-october-2026)).

## Crossing from one cell to the next

Each region frame holds one cell, so walking over a cell border is a level change between frames: the engine shuts
the map down and starts the next frame, and prefetch (`chim_prefetch.c`) moves the disk reads out of the crossing.
Measured costs are in [cell crossings](chim/CELL_CROSSINGS.md#what-a-crossing-costs-today). The alternative, a
streamed crossing where the frames around the player form one continuous world (type 1), is work in progress: a
prototype that does not yet create the people and creatures of joined frames, is off by default and does not become
the default until it carries entities ([status of type 1](chim/CELL_CROSSINGS.md)). Doors, travel and interiors stay
level changes in both methods.

## The builder pipeline

One builder builds the whole game from your own files, with no private step: `./build.sh` (Linux), `build.cmd` and
`build.ps1` (Windows) call `tools/build.py`, and the CHIM converters live in `tools/chim/`
([Linux build](LINUX_BUILD.md), [builder types](chim/build_guide/BUILDER_TYPES.md)). The default builder is CHIM; the
legacy one stays selectable. Principles, each documented where it lives:

- **Reuse by hash.** Every unit is keyed by the hash of its inputs; unchanged units are reused after a failure or a
  small change ([build cache](BUILD_CACHE.md)).
- **Profiled and parallel.** Stages report time and cores, and a perf guard compares them with the previous build
  ([build profile](BUILD_PROFILE.md#perf-guard), [parallel build](history/superseded/PARALLEL_BUILD.md)).
- **Checks before the expensive step.** A payload preflight and the disk-layout checks (partitions under 2 GiB,
  files well under 2 GiB, images under 4 GiB) run first ([payload preflight](BUILD_PROFILE.md#payload-preflight),
  [image size](IMAGE_SIZE.md)).
- **Per-cell audits.** Each converted cell passes the heap, stair, hull and seam audits described in
  [CHIMport](chim/CHIMPORT.md#audits-per-cell).
- **Test builds.** MiniWind builds one scene in minutes ([MiniWind](MINIWIND.md)).
- **Release gate.** A release runs the full test suite and the release guard before any kit is made
  ([release workflow](RELEASE_WORKFLOW.md#release-gate)).

## Audio, actors and interaction

Music streams from disk during play ([audio](AUDIO.md)). Actors are dressed NPCs built from shared parts
([modular NPCs](MODULAR_NPCS.md), [NPC model cache](NPC_MODEL_CACHE.md)). Combat, dialogue, quests, saves and most of
the game logic are incomplete; the order of work is in the [roadmap](ROADMAP.md) and the current state in
[project state](PROJECT_STATE.md).

## Speed

Speed on the target is not proven. Emulator figures are relative; the one real-hardware figure so far, from a tester
in October 2026, is about 0.2 frames per second on an A4000 with a 68060 at 100 MHz with an earlier build
([real hardware](REAL_HARDWARE.md), [68060 notes](68060.md)). Compact storage is not proof of fast rendering.

## Reference

The converter uses format facts from OpenMW's sources; it neither runs nor links OpenMW, and OpenMW serves as a
reference for formats and behaviour ([licensing and credits](LICENSING_AND_CREDITS.md)). Earlier design notes:
[world mapping plan](history/superseded/WORLD_MAPPING_PLAN.md), [pipeline](history/superseded/PIPELINE.md), [data streaming](DATA_STREAMING.md).
