# Cell crossings: how the engine moves from one CHIM frame to the next

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [The two methods](#the-two-methods)
- [What a crossing costs today](#what-a-crossing-costs-today)
- [What the level change throws away](#what-the-level-change-throws-away)
- [Quick wins that keep type 0](#quick-wins-that-keep-type-0)
- [Type 1: one continuous world](#type-1-one-continuous-world)
- [Weak points](#weak-points)
- [How it is built](#how-it-is-built)

<!-- contents end -->

The outdoors of Vvardenfell are built as CHIM frames: each region frame holds one cell, each town frame a town.
This page describes how the engine crosses from one frame to the next today, what that costs, and the method that
replaces it. Today's method stays selectable; Quake's networking code stays in the engine.

## The two methods

| Method | What a crossing does | Status |
| --- | --- | --- |
| Type 0, "AmiQuake" | A full level change: the game-logic half of the engine shuts down and starts the next frame as a new map, the display half reconnects and reloads its lists | Today's method; stays as an option |
| Type 1, "CHIM" | One continuous world: the frames around the player are a sliding window, nothing restarts | Designed; prototype next |

Real doors, travel and interiors stay level changes in both methods. The Vivec Arena duel idea (multiplayer over a
network or a null-modem cable) concerns the indoor Arena, an ordinary level, and is not affected.

## What a crossing costs today

Measured on the v0.0.44 data in an Amiga emulator (relative numbers; real hardware differs), median times from the
crossing until the player stands in the next frame, at 128 MiB of Fast RAM:

| Crossing | Light area | Balmora |
| --- | --- | --- |
| Edge | about 320 ms | about 680 ms |
| Corner | about 360 ms | about 880 ms |

About 220 to 260 ms of every crossing is the level change itself, the same with 16 or 128 MiB, so more memory
cannot shorten that part. Loading the ring of chunks around the player costs about 70 ms with 128 MiB and 260 to
280 ms with 16 MiB. v0.0.45 reads the neighbouring frames ahead into spare Fast RAM, which roughly halves a crossing
on a 128 MiB machine ([CHIM-CROSSING-SYNC-LOAD-43](../bugs/CHIM-CROSSING-SYNC-LOAD-43.md)); the level change stays.

Corner crossings go straight into the diagonal frame; they do not pass through the two neighbours.

## What the level change throws away

A crossing runs the `map` command (`engine/aga/src/aw_scene.c` `load_scene`): the client disconnects, the server
shuts down and starts again (`host_cmd.c` `Host_Map_f`, `sv_main.c` `SV_SpawnServer`), and the client reconnects
over the engine's internal connection (`net_loop.c`). On the way it rebuilds much that is the same in neighbouring
frames:

- the game scripts (`progs.dat`), read and checked again;
- the surface cache, flushed whole;
- the entity links, the world's area nodes and the light styles;
- the client's model and sound lists;
- the chunks of the old frame that are still within reach, and the old frame's distant terrain;
- with 16 MiB, the decoded world index.

The reconnection is also a handshake over several rendered frames (server info, pre-spawn, spawn, begin), and the
engine caps its rate at 72 frames a second, so part of the cost is waiting, not work.

Replacing `map` with Quake's `changelevel` would not help: it still starts the server again. The start-up work
itself has to leave the crossing path.

## Quick wins that keep type 0

Measured one at a time against today's method before any is kept:

- process the reconnection replies already waiting during loading, a bounded number, instead of one per host
  frame (same handlers and order, no extra physics steps), if the timeline shows real waiting;
- keep the game scripts loaded when they are unchanged;
- keep the decoded world index with 16 MiB too, if the memory gate allows it;
- skip reading the frame's entity text twice when the sky and lighting settings are the same;
- skip stopping all sounds twice and drawing the loading screen for a crossing;
- keep the chunks of the neighbouring frame that are still in reach.

## Type 1: one continuous world

- **Nothing restarts.** The game logic, the display, the player and the game clock keep running; a frame is only
  which part of the island is loaded.
- **One composite world from several frames.** CHIM already grafts its streamed chunks into one world model that
  rendering, collision and visibility use (`engine/aga/src/chim/chim_graft.c`). It is extended so the active chunks
  can come from up to four frames (two at an edge, four at a corner). Each physical chunk has one owner, so terrain
  margins that two frames share are never loaded twice. Visibility data is per frame today; across a border the
  engine either gets rows that cover both frames from the builder or falls back to distance culling, measured by the
  faces drawn.
- **Coordinates.** Since v0.0.36 the engine uses wide coordinates by default: ±32,768 units, 1/256 unit
  resolution (`engine/aga/src/aw_coord.h`), instead of Quake's ±4,096. A cell is 2,048 units wide, so about 15
  cells fit on each side of the origin. Moving the origin (a rebase) is a separate event from crossing a border: it
  is triggered by how far the loaded surroundings reach, with a margin, and many borders are crossed at one origin.
  A rebase moves the loaded geometry (plane distances, vertices, bounds, texture offsets, as CHIM's terrain shift
  already does) and every loaded entity, sound and effect as one coherent step; preparing it can be spread over
  several frames, switching it cannot.
- **Entities come and go by distance.** A frame's people and objects are spawned a little before its border is
  reached and removed a little after it is left, with a margin so walking along the border does not repeat it.
  Their state is captured when they leave, so they come back where they were.
- **Memory that does not depend on a level reset.** Today a level change also frees entity data in bulk: entity
  strings, for example, are allocated on the level's memory and only freed when that memory is reset
  (`pr_edict.c` `ED_NewString`, `host.c`). Entities that come and go need shared or separately reclaimable memory.
  The test: walking the same small area again and again keeps memory within a bounded range.
- **Model and sound lists.** Quake's lists hold 256 models and 256 sounds, with byte-sized indices. CHIM scenery
  already needs no list entries; actors, animations, sounds and scripted entities do. Freeing an asset's loaded data
  and reusing its list entry are different things: an entity can still refer to an entry (a client falls back to
  its baseline model), so entries get stable identities and are reused only when nothing refers to them, or the
  index space grows.
- **Saves keep a stable place.** A save records the source cell, the position inside it and the changed object
  state, per actor; the loaded window is rebuilt on restore, whatever was loaded when the game was saved.
- **Work spread over many frames.** Joining and leaving frames runs in small pieces while the player walks, so no
  single frame pays for a crossing.

## Weak points

1. The level change's cost is not yet split part by part; if most of it is the handshake, the quick wins above may
   come first.
2. Town frames are not aligned to cells; crossings between a town and the open world may stay type 0 at first.
3. Visibility across a border (see above).
4. The composite world's index limits must hold a full ring at a corner of four frames.
5. Every engine-side store of a world position has to follow a rebase; a missed one shows only when a rebase
   happens, so the prototype forces one at every crossing.
6. Streamed statics are read from the frame map's entity text today; a window reads that text without starting a
   level, or the builder stores them in the frame file.
7. The memory gate models one frame per level today; it has to model a window.
8. Objects that reach across a frame edge must not be drawn twice.
9. Doors, harvesting and the conversion between world and frame coordinates still identify the current area
   by the running level's name. Type 1 tracks the player's logical cell separately from the running session and
   from the coordinate origin, and those systems read the logical cell.
10. Data can be late. Bytes in memory, decoded data and installed, safe collision are three different states;
    needed collision is kept while the incoming side is prepared, and a missing piece means a short, counted stall,
    never walking through absent ground.
11. Some loading work cannot be interrupted today (one model, one terrain chunk); the worst rendered frame over the
    whole approach is measured, not only the crossing, so a pause is not just moved before the border.
12. Today's setting `aw_cell_change_method` already has meanings (1 the current method, 2 the read-ahead
    experiment); type 1 gets its own setting or an explicit migration, so a saved value never switches methods.

## How it is built

Each step is measured against type 0 on the same route, with the same image, memory size and cache state, at 16
and 128 MiB, with a repeated type 0 run as drift control:

1. The level change split part by part; the quick wins tried one at a time.
2. A sandbox of four light frames around one corner: crossings at a fixed origin, the four frames in one composite
   world, server, client, player and clock kept running, with a model and sound set that fits today's lists.
   After a seamless crossing the terrain, the doors and harvesting all keep working, checked in each frame.
3. Repeated loading and unloading in that sandbox with a person, an object across a seam and changed object state:
   memory and list use stay bounded.
4. A rebase forced in the same sandbox: collision, camera, effects, saving and loading.
5. Edges and the corner measured for the longest single frame and the memory peak, beside the median crossing.
6. Then the whole island, with type 0 kept as an option.

What the sandbox has to show:

| Case | What it shows |
| --- | --- |
| Edge and corner crossings | The session and the player stay alive, game time runs on, no level restart |
| A door and a plant across a seam | The area services follow the player; nearby objects keep their own area |
| Late incoming data and an immediate turn back | Needed collision stays; loading priorities recover |
| A forced rebase | Position, collision, camera motion and attached effects stay consistent |
| Repeated visits with eviction, saving and loading | Changed objects keep their state; memory and list use level off after warm-up |
| The same standing views and route in both methods | Smooth crossings do not cost a lasting rise in game logic or drawing work |

A crossing is timed to the first frame of the new world actually shown, and the timeline records the host frame of
each step, so waiting between frames is told apart from work.

See also: [the roadmap](../ROADMAP.md#cell-crossings-one-continuous-world-19-october-2026),
[the v0.0.45 plan](../PLAN-v0.0.45.md), [CHIM engine](ENGINE.md),
[CHIM-CROSSING-SLUGGISH-43](../bugs/CHIM-CROSSING-SLUGGISH-43.md).
