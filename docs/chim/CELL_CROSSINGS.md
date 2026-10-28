# Cell crossings: how the engine moves from one CHIM frame to the next

_Last updated with AmiWind v0.0.47 (21 October 2026)._

<!-- contents start -->
## Contents

- [The two methods](#the-two-methods)
- [What a crossing costs today](#what-a-crossing-costs-today)
  - [The level change, part by part](#the-level-change-part-by-part)
- [What has to get better](#what-has-to-get-better)
- [What the level change throws away](#what-the-level-change-throws-away)
- [Quick wins that keep type 0](#quick-wins-that-keep-type-0)
- [Type 1: one continuous world](#type-1-one-continuous-world)
  - [The type 1 prototype, measured (20 October 2026)](#the-type-1-prototype-measured-20-october-2026)
- [Near and far as one system (upcoming direction)](#near-and-far-as-one-system-upcoming-direction)
- [Weak points](#weak-points)
- [How it is built](#how-it-is-built)
  - [The plan after the correction (the maintainer's decisions, 20 October 2026)](#the-plan-after-the-correction-the-maintainers-decisions-20-october-2026)

<!-- contents end -->

The outdoors of Vvardenfell are built as CHIM frames: each region frame holds one cell, each town frame a town.
This page describes how the engine crosses from one frame to the next today, what that costs, and the method that
replaces it. Today's method stays selectable; Quake's networking code stays in the engine.

**Status of type 1 (20 October 2026).** Type 1 is a prototype and cannot yet do what a real crossing has to do:

- The people and creatures of a frame it joins are not created.
- Doors and harvestable plants work only in the frame the map started in, not in frames joined by streaming.
- Towns refuse it and keep the level change.
- Followers and escorts do not cross with it.

It is not the default and will not be until it carries entities. The level change (type 0) stays the default.
The type 1 figures below are not a like-for-like comparison with type 0: see
[the box above the measurements](#the-type-1-prototype-measured-20-october-2026).

## The two methods

| Method | What a crossing does | Status |
| --- | --- | --- |
| Type 0, "AmiQuake" | A full level change: the game-logic half of the engine shuts down and starts the next frame as a new map, the display half reconnects and reloads its lists | Today's method; stays as an option |
| Type 1, "CHIM" | One continuous world: the frames around the player are a sliding window, nothing restarts | Prototype without entities in joined frames (see the status above); selected with `chim crossing 1`, off by default; its first figures are [not like for like](#the-type-1-prototype-measured-20-october-2026) |

Real doors, travel and interiors stay level changes in both methods. The Vivec Arena duel idea (multiplayer over a
network or a null-modem cable) concerns the indoor Arena, an ordinary level, and is not affected.

## What a crossing costs today

Measured 20 October 2026 on the v0.0.44 and v0.0.45 release images in an Amiga emulator (FS-UAE, JIT, 68040), on
a quiet host, over the scripted [crossing route](../performance/CROSSING_BASELINE.md) (relative numbers; real
hardware differs). Median (and worst) time from the crossing until the player stands in the next frame ("ready"),
36 straight crossings and 24 corner-loop crossings per image and memory size:

| Fast RAM | Crossing | v0.0.44, light area | v0.0.45, light area | v0.0.44, Balmora | v0.0.45, Balmora |
| --- | --- | --- | --- | --- | --- |
| 128 MiB | Edge | 293 ms (337) | 123 ms (152) | 650 ms (913) | 201 ms (224) |
| 128 MiB | Corner | 367 ms (395) | 123 ms (148) | 822 ms (1,021) | 223 ms (469) |
| 16 MiB | Edge | 448 ms (535) | 422 ms (502) | 665 ms (901) | 658 ms (946) |
| 16 MiB | Corner | 537 ms (668) | 515 ms (610) | 879 ms (1,029) | 825 ms (1,006) |

- **With 128 MiB, v0.0.45 cuts a crossing to about a third** (more than the "roughly halves" its release notes
  say): it keeps the world index, the neighbouring frames and their chunks in spare Fast RAM, so a light-area
  arrival reads about 8 KB from disk instead of 3.2 MB. The longest rendered frame of a light crossing drops from
  about 200 to 260 ms to about 65 ms; a Balmora crossing's from about 500 to 750 ms to about 140 ms.
- **With 16 MiB, v0.0.45 is 1 to 7 % faster**; nothing is kept between frames.
- **Corners:** a diagonal corner crossing switches once, straight into the diagonal frame, not through the
  neighbours. On v0.0.44 it costs about a quarter more than an edge, on v0.0.45 the same. Walking around a corner
  (four crossings in 11 seconds) costs per crossing about what an edge does.
- The first entry into Balmora in a session with 128 MiB takes about 470 ms on v0.0.45; later ones about 220 ms.
- Repeated sessions drift by up to about 12 % in the emulator; the counts (bytes, reads) do not.

The 19 October measurement on v0.0.44 put about 220 to 260 ms of every crossing in "the level change itself" at
either memory size. The part-by-part timeline below shows what that was: most of it is reading and starting the
CHIM world of the next frame, which v0.0.45 keeps in RAM with 128 MiB. RAM does help it; with 16 MiB it does not.

### The level change, part by part

Measured with a timing build of the v0.0.45 engine (its own timers added, nothing else changed) on the v0.0.45
image: one crossing of each kind, the median of three, from the moment the player passes the border to the first
frame of the new world shown on screen, before any audit or logging work. Milliseconds; the host frame the step runs
in tells work from waiting.

| Part | Host frame | 128 MiB, light edge | 128 MiB, Balmora corner | 16 MiB, light edge | 16 MiB, Balmora corner |
| --- | --- | --- | --- | --- | --- |
| Waiting for the next host frame after the border | 0 to 1 | 7.0 | 4.8 | 6.8 | 3.8 |
| Old level left: client disconnected, all sounds stopped, server shut down, loading screen | 1 | 0.1 | 0.3 | 0.2 | 0.2 |
| Memory cleared (`Host_ClearMemory`) | 1 | 7.3 | 7.5 | 7.5 | 6.9 |
| Game scripts loaded (`PR_LoadProgs`) | 1 | 2.1 | 3.0 | 1.7 | 1.6 |
| Server set-up and frame map read and parsed | 1 | 2.6 | 10.5 | 2.7 | 9.0 |
| CHIM start of the frame: world index, frame directory, distant terrain, frame world | 1 | 20.6 | 28.0 | 198.7 | 335.1 |
| Entities spawned (QuakeC) | 1 | 0.0 | 96.1 | 3.3 | 230.5 |
| Physics settle, baselines, server info | 1 | 0.1 | 0.3 | 0.1 | 0.3 |
| Heap audit lines (five per level change) | 1 | 16.6 | 20.7 | 16.8 | 17.4 |
| Client: server info, model and sound lists | 1 | 6.5 | 8.2 | 6.6 | 117.7 |
| Client: `R_NewMap` (its two entity re-parses under 0.1 ms) | 1 | 4.3 | 4.5 | 4.7 | 4.5 |
| Reconnection replies: pre-spawn, spawn, begin (work) | 2 to 4 | 0.3 | 0.4 | 0.3 | 0.3 |
| Console command buffer in the second frame (not yet identified) | 2 | 0.0 | 12.4 | 11.4 | 12.4 |
| Waiting for the 72 Hz frame cap before the spawn reply | 3 | 13.7 | 1.1 | 2.4 | 1.3 |
| Chunk ring loaded around the arrival point | 3 | 37.9 | 54.3 | 230.7 | 95.1 |
| Rest of placing the player (arrival, hands, scene) | 3 | 10.2 | 12.3 | 9.9 | 11.2 |
| First frame of the new world: client read, then drawn | 4 | 16.2 | 24.4 | 19.5 | 41.4 |
| Other, mostly console lines (the timing build's own two lines included) | | 10.0 | 15.7 | 16.3 | 17.0 |
| **To the first frame shown** | **4 frames** | **155.5** | **304.5** | **539.6** | **905.7** |

What dominates:

- **With 128 MiB:** the chunk ring (38 to 54 ms), the CHIM start of the frame (21 to 28 ms) and the heap audit lines
  (17 to 21 ms); in a town the entity spawn comes first (96 ms).
- **With 16 MiB:** the CHIM start of the frame (199 to 335 ms: the world index is read and decoded again on every
  crossing) and the chunk ring (95 to 231 ms); in a town also the entity spawn (231 ms) and the client's model list
  (92 ms, the town's models loaded from disk).
- **Waiting is small.** The handshake spans four host frames, but the frames are long anyway: waiting between frames
  is about 17 ms of a 155 ms light crossing at 128 MiB (the 72 Hz cap and the frame boundary after the border) and
  1 to 4 ms in the other cases. The internal connection itself costs under 0.1 ms (15 reads, 9 sends).
- What repeats identical work between neighbouring frames: the chunk ring (most of the incoming ring was already
  loaded around the player on the old side), the CHIM start (the world index, and with 16 MiB its decoding; the
  distant terrain overlaps), the client's model list in a town, clearing memory, the game scripts and the heap
  audit lines. The entity spawn is new work for the incoming frame; it can be done ahead, not avoided.

## What has to get better

- **No level change at a border.** The restart (about 120 ms of a light crossing with 128 MiB on v0.0.45, about
  500 ms with 16 MiB) goes only when nothing restarts: the outdoors as one running world (type 1 below). Quick fixes
  to the restart can shave part of it, but not the whole.
- **Light frames under 100 ms, towns under 200 ms**, at 128 MiB, measured as the worst rendered frame over the
  approach and the crossing, not only the median "ready" time.
- **16 MiB machines close behind:** the chunk ring prepared before the border, a slice per rendered frame, and the
  world index not decoded again, so the 95 to 231 ms of ring loading and the 199 to 335 ms of starting the frame's
  CHIM world leave the crossing.
- **Town entities without a pause:** people and objects of the next frame spawned ahead, a few per rendered frame.
- **The same pace in both directions and at corners**, and no second load when the player turns back at a border.

With 128 MiB, v0.0.45 already meets the light-area goal for the worst rendered frame (about 65 ms) and is close for
towns (about 140 ms, first entry about 390 ms); the median "ready" time is 120 to 220 ms. With 16 MiB nothing is
close yet: the CHIM start and the chunk ring are 75 to 80 % of a light crossing.

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

Measured one at a time against today's method before any is kept. The timeline above (20 October 2026) sizes each:

- process the reconnection replies already waiting during loading, a bounded number, instead of one per host
  frame (same handlers and order, no extra physics steps), if the timeline shows real waiting: **measured waiting
  is about 17 ms of 155 ms at the best (light area, 128 MiB) and 1 to 4 ms otherwise; not worth doing first**;
- keep the decoded world index with 16 MiB too, if the memory gate allows it: **the largest single part with
  16 MiB, 199 to 335 ms of the CHIM start of the frame** (with 128 MiB v0.0.45 already keeps it);
- no heap audit lines during a crossing (keep them for the development builds or one summary line): **17 to 21 ms
  at every memory size**;
- find the console command buffer's 11 to 12 ms in the second frame of the handshake;
- keep the game scripts loaded when they are unchanged: 2 to 3 ms;
- skip reading the frame's entity text twice when the sky and lighting settings are the same: under 0.1 ms
  measured, not worth it;
- skip stopping all sounds twice and drawing the loading screen for a crossing: under 0.3 ms measured;
- keep the chunks of the neighbouring frame that are still in reach: the chunk ring is 38 to 54 ms with 128 MiB
  and 95 to 231 ms with 16 MiB.

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

### The type 1 prototype, measured (20 October 2026)

> **Not a like-for-like comparison (corrected 20 October 2026).** Type 0's crossing creates the new frame's
> entities: its people and creatures, doors, harvestable plants, their spawn functions and the models they load.
> The type 1 prototype creates none of them in the frames it joins. The ready-time figures (146 to 0 ms at 128 MB,
> 712 to 0 ms at 16 MB) and the worst-frame figures below therefore do not show how much faster a complete
> crossing would be; part of the difference may be exactly the work type 1 skips. How much is not measured yet.
> The table is kept as history. Every A/B in the project now lists the work each variant does before any number is
> reported.

The first version of type 1 runs in the engine behind a console setting, `chim crossing 1` (a `chim` subcommand,
not saved, so a stored setting never switches the method; `chim crossing 0`, the default, is type 0 unchanged).
It takes effect at the next map start. A build can start every game with it: the builder option
`--chim-crossing 1` (the default since v0.0.47, decided for the project, 2026-10-21) ends the image's
`id1/default-game.cfg` with `chim crossing 1`, which runs at start-up before any map; `chim crossing 0` in the
console before a map starts gives the old crossing back. `--chim-crossing 0` writes nothing, the image as before
(`tools/chim_crossing.py`, [experimental flags](../EXPERIMENTAL_FLAGS.md)). A map
that starts on a region frame then runs a window instead of one frame:

- **The window** is the 2 x 2 block of cells (each a region frame) meeting at the corner nearest the player, as
  the read-ahead picks its block. It moves to another corner only 256 units past a cell's midline, well outside the
  ring of active chunks, so walking along a border never swaps it back and forth. Frames join with their chunk
  directory and their streamed statics (read from their frame map), and leave once the frame world has let their
  ground go (`engine/aga/src/chim/chim_chunks.c`).
- **Fixed origin**: every frame is placed at its offset from the frame the map started on (cell steps of 2,048
  units). Nothing moves; the coordinate range holds about 15 cells on each side.
- **One composite world**: the window's chunk grid gives each place one owner, the frame whose cell holds the
  chunk's centre, so ground two frames share is grafted once (`chim_graft.c`). The other frames' chunks at that
  place keep only their placements. Each placement is drawn and collided by the frame whose cell holds it, so an
  object two frames both carry near their border appears once. A chunk's visibility row covers its own frame; a
  chunk of another frame outside that row's area is treated as visible (distance and the view decide).
- **The crossing**: when the player passes 64 units into a cell the window holds, `aw_scene.c` records the frame
  entered as the player's logical frame (the running map keeps its name and coordinates) and nothing is loaded.
  Towns, doors, `dbg tp`, loading a save, and any frame the window cannot hold keep the level change.
- **A test setting**, `chim crossing recentre 1`, moves the origin to the frame entered at every streamed crossing
  (server and client positions, sounds, lights, particles, CHIM's chunks, placements, statics, distant terrain and
  structure boxes, the frame world laid out again), so that any stored position the move misses shows at once.

Measured on the crossing route ([Crossing baseline](../performance/CROSSING_BASELINE.md)) on the v0.0.45 release
image, with the same engine (branch commit ce322285) for both methods and only the setting changed. FS-UAE JIT,
68040, quiet host. Legs ai-c1, ai-l1 and ai-e1, which lie in the four cells 2,-7 / 3,-7 / 2,-6 / 3,-6, each flown
three times: 18 crossings per session. A type 0 session at 128 MB was run again at the end as the drift control
(ready 151 against 146 ms, worst frame 83 against 83 ms). Median (worst), milliseconds. Type 1 creates no entities
in joined frames: not comparable.

| Fast RAM | Method | Ready | Worst frame, 3 s after the crossing | Frame median within 2 s | Worst frame of the approach |
| --- | --- | --- | --- | --- | --- |
| 128 MB | type 0 | 146 (183) | 83 (792) | 14 | 54 (153) |
| 128 MB | type 1 | 0 | 42 (48) | 14 | 46 (55) |
| 16 MB | type 0 | 712 (868) | 373 (460) | 14 | 66 (82) |
| 16 MB | type 1 | 0 | 66 (193) | 14 | 80 (159) |

- **No pause at the border, with no entities created.** The player never stops ("ready" 0), but type 1 skips the
  entity work type 0 does (see the box above), so these numbers do not say a complete crossing would halve the
  worst frame at 128 MB or cut it to about a sixth at 16 MB. The worst single frame at 16 MB was 193 ms, on a
  corner loop. Whether a complete crossing meets the 100 ms goal is not measured yet.
- **The cost moved before the border at 16 MB.** The approach's worst frame rises from 66 to 80 ms median (159 at
  most): the neighbouring frames' chunks, now loaded whole instead of the current frame's terrain-only margin,
  stream in ahead. That is the next thing to spread (1.4, 1.6b).
- **Memory at 16 MB**: the zone's locked peak rose from 4,573 to 4,889 KiB (+7 %), with up to 6,783 of the 6,864
  KiB zone used. Retried loads for a full zone happen with both methods (85 type 0, 97 type 1 messages per session).
  Starting a map with three frames to join costs 160 to 230 ms at 16 MB, inside the teleport's load.
- **The same picture**: screenshots at fixed poses on both sides of the ai-e1 border, type 0 against type 1, differ
  in 0.00 % of the 3D view's pixels before the border and in 0.16 % after it (a sky edge).
- **Saving after a streamed crossing** and loading the save puts the player back at the same place, in the same
  frame (cell 3,-6). The load first primes the ring at the map's spawn, then the window follows the player.
- **Frame by frame**: clips of the same steady move across the ai-e1 border (noclip, constant heading and speed, no
  console command during the move) were checked frame by frame for held pictures, and every engine frame of 40 ms
  or more was named by `chim spikes 40`.
  - At eye height over the ground (128 MB): the flight follows the measured ground profile within -6 to +44 map
    units of a standing player's eye height, steered by the move keys only. Type 0 holds the picture for 120 to
    160 ms around the border (the level change reports 133 ms; engine frames up to 146 ms). Type 1 repeats one
    picture once (two video frames, 80 ms) 27 units before the border; its only engine frame over 40 ms took 47 ms,
    and the crossing itself took 90 microseconds.
  - The first flights were meant to fly level just over eye height but flew about 710 map units (some 10 m) higher:
    the climb before the move was stopped through the console, which acts about half a second late. There, type 0
    held the picture once, right after the border, for 160 ms with 128 MB and 600 ms with 16 MB (the server start,
    the CHIM start of the frame and the ring prime). Type 1 held nothing at the border; with 16 MB its frames that
    read the neighbour's chunks near the border took 50 to 53 ms.
  - The eye-height flights with 16 MB ran while other builds loaded the machine (the emulator at about 60 % of its
    speed), so they show the path only; their timing is to be repeated on a quiet machine.
  - Clips of a walk on foot over the same line also stop where the player runs into a tree, with both methods;
    those stops are collisions, not streaming.
- How the measurement harness affects the game: each console command it sends costs the game one frame of about
  55 ms (the console buffer). The timed flights send none during a crossing; the corner loops send one at each turn,
  between crossings, with both methods alike. For about half a second at a type 0 level change, the harness's state
  line pairs the new map's name with the old view position, so the reported position jumps by one cell; the
  harness skips those lines.

Risks and open items, plainly:

- **Memory at 16 MB**: the window locks 7 % more of the zone at its peak, and loads that wait for room in a full
  zone happen with both methods. The memory gate does not model the window yet.
- **The approach at 16 MB**: the work moved before the border (50 to 53 ms frames, the approach's worst frame 80 ms
  median against 66). It has to be spread thinner, not only moved.
- **Towns** never join a window; their crossings stay type 0.
- **People and other entities** of a joined frame are not spawned yet (no entity windowing).
- **The sandbox**: measured on the release image's four cells, not on a MiniWind build; a MiniWind sandbox of region
  frames needs its own MiniWind scope in the builder first.

What the prototype does not do yet (each its own next step):

- Doors and harvestable plants of a frame entered by streaming: the running map's own catalogues stay loaded, so
  only the starting frame's doors and plants work (the logical frame is known; the catalogues do not follow it yet).
- People, sounds and other entities of a joined frame that are not streamed statics are not spawned.
- Whole-structure cut boxes and the distant terrain are the starting frame's.
- The memory gate still models one frame; the window's peak is measured here, not gated.
- Town frames never join a window (they are not cell-aligned); crossings into and out of towns stay type 0.
- The recentre moves the engine's main stores; modules keeping positions of their own (paths, companions,
  combat) are not moved yet.

## Near and far as one system (upcoming direction)

Proposed 19 October 2026, to be proven in the sandbox before anything else: streaming the world and drawing what is
far away are designed together, because they share everything that matters.

- **Near: streamed detail.** Around the player the full chunks are loaded, a slice per rendered frame, by one queue
  sorted by distance and heading (what lies ahead first), as in open-world games on slow hardware.
- **Far: one shell of the island.** Beyond that, a single low-detail shell of the whole island (terrain plus the
  silhouettes of buildings, towers and bridges) in the fog's colour, resident in memory, as planned in the
  [roadmap](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026).
- **One handover distance, tied to the fog.** Nothing is cut before the fog is opaque, so the distance where the
  shell hands over to streamed detail and the distance the streamer must load ahead to are the same setting.
- **The shell is split along the chunks the streamer loads.** A chunk's part of the shell is shown until its
  detail is in, then hidden, so the swap stays clean and nothing is drawn twice.
- **A late chunk shows a silhouette, not a hole.** If streaming falls behind, the view keeps the shell's shape;
  collision is a separate safety (needed ground is never missing, a short counted stall instead).
- **One memory budget.** The shell's size and how much detail stays loaded are decided together.

The shell is a new distant-drawing mode beside today's horizon methods, which stay selectable. It becomes the
default once the sandbox shows it within its budget (about a tenth of a frame on the 68040 and 68060 profiles; the
edge count is the risk) and no worse than today's horizon at the same viewpoints.

## Weak points

1. The level change's cost is split part by part (20 October 2026, above): the handshake is not the cost; the
   CHIM start of the frame and the chunk ring are, so type 1 and keeping the world between frames matter most.
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
    The prototype has its own, `chim crossing`, which is not saved.

## How it is built

### The plan after the correction (the maintainer's decisions, 20 October 2026)

In order:

1. **One world-state change list keyed by reference ID.** It holds what differs from the base data: moved, dead and
   following NPCs, picked plants, opened doors, container contents. A joining frame is its base data plus its
   changes; a leaving frame writes its changes back; saves write the same list.
2. **Entity windowing.** The people, creatures, doors and plants of the frames in the window are created and
   released as the window moves.
3. **Followers and escorts crossing frame borders.** Some quests, the main quest among them, need it. The companion
   test must pass with type 1 as it does with type 0.
4. **NPC traversal** across frame borders.
5. **Every comparison like for like**: both methods doing the same work, on frames with people.

Each step is measured against type 0 on the same route, with the same image, memory size and cache state, at 16
and 128 MiB, with a repeated type 0 run as drift control:

1. The level change split part by part; the quick wins tried one at a time.
2. A sandbox of four light frames around one corner: crossings at a fixed origin, the four frames in one composite
   world, server, client, player and clock kept running, with a model and sound set that fits today's lists.
   After a seamless crossing the terrain, the doors and harvesting all keep working, checked in each frame.
   Status 20 October 2026: the crossings, the composite world and the running session are in (measured
   [above](#the-type-1-prototype-measured-20-october-2026), on the release image's four cells); the doors and
   harvesting of a frame entered by streaming are not yet.
3. Repeated loading and unloading in that sandbox with a person, an object across a seam and changed object state:
   memory and list use stay bounded.
4. A rebase forced in the same sandbox: collision, camera, effects, saving and loading. Status 20 October 2026:
   the test setting `chim crossing recentre 1` exists and holds ground, objects and links in the engine's own tests
   at every crossing of a six-frame test world; not yet measured in the game.
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

What other engines and published work do for the same problem (Morrowind and OpenMW, Godot, Dungeon Siege and
others), with a "fits a 68040?" note for each and what it means for these steps:
[streaming research](STREAMING_RESEARCH.md).

See also: [the roadmap](../ROADMAP.md#cell-crossings-one-continuous-world-19-october-2026),
[the v0.0.45 plan](../history/plans/PLAN-v0.0.45.md), [CHIM engine](ENGINE.md),
[CHIM-CROSSING-SLUGGISH-43](../bugs/CHIM-CROSSING-SLUGGISH-43.md).
