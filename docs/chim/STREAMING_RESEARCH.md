# Streaming research: how other games keep a world moving

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [Morrowind and OpenMW](#morrowind-and-openmw)
  - [The original game](#the-original-game)
  - [OpenMW: the active grid and when it moves](#openmw-the-active-grid-and-when-it-moves)
  - [OpenMW: preloading the next ring](#openmw-preloading-the-next-ring)
  - [OpenMW: the cache of preloaded and left cells](#openmw-the-cache-of-preloaded-and-left-cells)
  - [OpenMW: distant terrain and object paging](#openmw-distant-terrain-and-object-paging)
- [Godot](#godot)
  - [Visibility ranges with hysteresis](#visibility-ranges-with-hysteresis)
  - [Visibility parents: hierarchical detail](#visibility-parents-hierarchical-detail)
  - [Threaded loading as low-priority work](#threaded-loading-as-low-priority-work)
  - [Large world coordinates](#large-world-coordinates)
  - [Open-world plugins for Godot](#open-world-plugins-for-godot)
- [Other engines and published work](#other-engines-and-published-work)
  - [Dungeon Siege: the continuous world (2002)](#dungeon-siege-the-continuous-world-2002)
  - [Crash Bandicoot: 64 KB pages from a CD (1996)](#crash-bandicoot-64-kb-pages-from-a-cd-1996)
  - [GTA III-era games: sector archives and paired detail](#gta-iii-era-games-sector-archives-and-paired-detail)
  - [Daggerfall Unity: a tile ring and a floating origin](#daggerfall-unity-a-tile-ring-and-a-floating-origin)
- [What does not carry over](#what-does-not-carry-over)
- [What this means for the 2x2 sandbox](#what-this-means-for-the-2x2-sandbox)
- [Sources](#sources)

<!-- contents end -->

This page collects what other engines and published work do to stream a large world without loading screens, read
for the [cell crossings](CELL_CROSSINGS.md) work: the continuous world (type 1) and the
[near and far system](CELL_CROSSINGS.md#near-and-far-as-one-system-upcoming-direction). Every technique has what it
does, where it comes from, and a "fits a 68040?" note: what carries over to AmiQuake's span renderer on a
single-threaded Amiga with 16 MB to 128 MB of Fast RAM and a slow hard disk, and what does not. It ends with what
this means for the 2x2 sandbox, step by step.

**How the sources were used.** Behaviour and design are learned; code is not copied. OpenMW is GPLv3 and AmiWind's
engine is GPLv2, so OpenMW's source was read and its rules are written here in our own words as "rule from OpenMW
file X"; nothing from it goes into AmiWind. Godot and the open-source projects named below are MIT-licensed, which
is compatible, but they were read for ideas too: nothing on this page needs their code. Published talks and
community write-ups are cited only where the source could be opened and checked; anything that could not be
checked was left out. No decompiled or proprietary code was used.

Units: Morrowind and OpenMW measure a cell as 8,192 units; AmiWind's CHIM world uses 2,048 units per cell, so
OpenMW's distances are divided by four where they are compared with ours.

## Morrowind and OpenMW

The original game is the reference for what the world does; OpenMW is the readable reference for how a modern
engine keeps the same world streaming.

### The original game

- **What it does.** Outdoors, the game keeps a three by three block of cells active around the player. Crossing into
  a new cell shifts that block and shows a short "loading area" pause while the new row or column of cells is read.
  The shipped configuration file keeps a buffer of recently visited cells, larger for exteriors than for interiors
  (32 and 10 in the default file), and names cells to load at start-up (the prison ship and Seyda Neen).
- **Source.** Playing the original game; the configuration file shipped with it.
- **Fits a 68040?** The same three by three block is what CHIM's frames already are around a crossing. The useful
  lesson is the buffer of left cells: going back over a border should find the cell still in memory, which is
  exactly the "no second load when the player turns back" goal in
  [what has to get better](CELL_CROSSINGS.md#what-has-to-get-better).

### OpenMW: the active grid and when it moves

- **What it does.** Rule from OpenMW `apps/openmw/mwworld/scene.cpp` and `components/misc/constants.hpp`: the
  active grid is the player's cell plus one cell on every side (three by three for Morrowind). The grid does not
  move the moment the player crosses a cell edge: its centre moves only when the player is more than half a cell
  plus 1,024 units from the current centre (a hysteresis of an eighth of a cell, 256 of our units). Walking along a
  border therefore does not load and unload the same row again and again. When the grid moves, cells that left it
  are unloaded and the new ones are loaded nearest first (sorted by grid distance from the player's cell). That
  step runs on the main thread behind a short loading bar; only the preparation before it runs in the background.
- **Fits a 68040?** Fully: it is bookkeeping, not rendering. The hysteresis rule belongs in type 1's window as the
  rule for when a frame joins or leaves, and the "nearest first" order is the same as our chunk queue's. The point
  that even OpenMW pays a short synchronous step at the grid change is worth keeping in mind: the background work
  removes the disk and decoding time, not every bit of work at the moment of the switch.

### OpenMW: preloading the next ring

- **What it does.** Rule from OpenMW `apps/openmw/mwworld/scene.cpp` (the exterior grid preload) and the `[Cells]`
  section of `files/settings-default.cfg`: every frame the engine predicts where the player will be one second
  later (current velocity times the "prediction time" of 1 s). It looks only at the ring of cells just outside the
  active grid, and preloads a cell of that ring when either the player or the predicted position comes within a
  set distance of it (the distance mixes half a cell, the grid hysteresis and a "preload distance" of 1,000 units).
  In practice the next row starts to load roughly as the player passes the edge of the centre cell, about 1,000
  units (250 of ours) plus one second of movement before the grid itself moves. Distances are measured as the
  larger of the X and Y differences, so only the side (or corner) the player is heading for is preloaded, not the
  whole ring. The same mechanism preloads the destination of every teleport door within the preload distance,
  together with the cells around an exterior destination.
- **What "preloaded" means.** Rule from OpenMW `apps/openmw/mwworld/cellpreloader.cpp`: a background task reads the
  cell's terrain and every model, animation and collision shape its objects use into the shared resource caches,
  optionally already copied as ready instances. It does not add the objects to the scene; that still happens when
  the grid moves, but from memory instead of disk. A task can be aborted when its cell is no longer wanted.
- **Fits a 68040?** The rules carry over directly; the background thread does not (the Amiga has no spare core).
  On AmiWind the same queue runs as a slice of every rendered frame, the "chunk ring prepared before the border, a
  slice per rendered frame" goal. Two details are worth taking as they are: predicting one second ahead from the
  current velocity (cheap: one multiply per axis), and preloading door destinations near the player, which also
  serves the interiors that come after the crossings.

### OpenMW: the cache of preloaded and left cells

- **What it does.** Rule from OpenMW `cellpreloader.cpp` and the settings file: the preload cache holds at most
  20 cells. When it is full, the entry used longest ago is thrown out, but never one used within the last second,
  so a cell that is still wanted cannot be evicted and requested again in a loop. Above a minimum of 12 cells,
  entries that no stage has asked for in the last 5 seconds expire. The resource caches behind it (models, textures,
  collision shapes) also drop entries unused for 5 seconds, and that cleaning runs in the background so deleting
  never stalls the frame. The cache reports counts of cells added, evicted, loaded and expired. A warning is logged
  when a door destination's surroundings do not fit the cache.
- **Fits a 68040?** Yes, and it matches what v0.0.45 started with the read-ahead into spare Fast RAM: a bounded set
  of whole frames kept in memory, emptied by age with a minimum kept. The age rules translate to rendered frames or
  game seconds; the counters are exactly what the sandbox should print. The size limit becomes a memory budget
  instead of a cell count, since a town frame and a sea frame differ by a factor of ten.

### OpenMW: distant terrain and object paging

- **What it does.** Rule from OpenMW `components/terrain/quadtreeworld.cpp`: distant terrain is a quadtree of
  chunks whose size grows with distance (each doubling of distance allows a chunk twice as large). A chunk that
  would straddle the edge of the active grid is always split further, so no distant chunk overlaps the loaded
  cells. The distant set is rebuilt only after the camera has moved a set distance (150 units), which also stops
  detail from loading and unloading while the player hovers at a transition. Rule from OpenMW
  `apps/openmw/mwrender/objectpaging.cpp`: static objects outside the active grid are merged into one batch per
  distant chunk, and an object is left out of a distant chunk when its size divided by its distance falls under a
  threshold (a hundredth by default), so small things vanish at range while large ones stay.
- **Fits a 68040?** The rule that distant chunks never cross the loaded area's edge is the same as our plan to split
  the far shell along the streamed chunks: OpenMW confirms the approach. The size-over-distance cut is a cheap
  builder-side rule for deciding what goes into the shell (only silhouettes large enough to matter at the handover
  distance). The merging itself is a GPU batching trick; on the span renderer, fewer and larger faces help because
  of fewer edges, not because of fewer draw calls. The rebuild-after-moving rule fits as it is: rebuild the shell
  selection only when the player has moved, never every frame.

## Godot

Godot (MIT) has no open-world streamer of its own, but its renderer has the distance machinery that one is built
from, and its loader shows how to keep loading from disturbing the frame.

### Visibility ranges with hysteresis

- **What it does.** Rule from Godot `servers/rendering/renderer_scene_cull.cpp` and the class reference of
  `GeometryInstance3D`: every instance can have a begin and an end distance, measured from the camera to the centre
  of its bounds; it is shown only between them. Each limit has a margin. With fading off, the margin is a
  hysteresis: an instance that is shown is hidden only when it is past the end distance plus the margin, and a
  hidden one is shown again only when it is closer than the end distance minus the margin. With fading on, the
  margin is the width of a transparent fade.
- **Fits a 68040?** The hysteresis version fits exactly and costs one comparison per object; it is what the fog
  rule needs so that objects at the cut distance do not blink in and out. The fade version does not fit: it needs
  blending, which the span renderer does not have. AmiWind's equivalent of a fade is the fog itself, which is why the
  roadmap's rule is that nothing is cut before the fog is fully opaque.

### Visibility parents: hierarchical detail

- **What it does.** Rule from the same Godot file and the `Node3D` class reference: an instance can name a
  visibility parent. The children are drawn only while the parent is hidden because the camera is closer than the
  parent's begin distance (or while the parent is fading its children in). Godot's manual recommends one simplified
  mesh as the parent of a group (its example is a batch of houses) with the detailed meshes as its children. The
  engine evaluates parents before children, so a whole subtree is decided by one test on its parent.
- **Fits a 68040?** This is the near and far handover in another form: a shell piece is the parent, the streamed
  chunk's detail its children. AmiWind needs one addition Godot does not: the shell piece hides only when the
  camera is inside the handover distance **and** the chunk's detail is installed, so a late chunk shows its
  silhouette and never a hole. One test per shell piece per frame is affordable; the tree evaluation order (parents
  first) is plain bookkeeping.

### Threaded loading as low-priority work

- **What it does.** Rule from Godot `core/io/resource_loader.cpp`, `core/object/worker_thread_pool.cpp` and the
  class reference of `ResourceLoader`: a load request returns at once; the game asks each frame whether it is done
  (with a progress fraction) and picks the result up when it is. Loads already in the cache are reused instead of
  read again. Background loads run as low-priority tasks, and only a share of the worker threads (30 % by default)
  may run low-priority work at once, so loading never takes every core away from the frame.
- **Fits a 68040?** The request, poll and pick-up pattern fits as it is; the threads do not. On the Amiga
  "low priority" becomes a time slice: the queue gets a bounded part of each rendered frame and the frame always
  comes first. The idea of a fixed share is the useful part: a stated budget for streaming per frame, measured, not
  "whatever time is left".

### Large world coordinates

- **What it does.** Godot's manual on large world coordinates explains that single-precision positions lose
  precision with distance and gives recommended limits per game type; Godot's answer is an optional build with
  double-precision positions, and it names origin shifting as the alternative for low-end platforms, at the cost of
  more complex game logic.
- **Fits a 68040?** Double precision does not fit (the 68040's FPU work is already a measured cost). AmiWind's wide
  fixed-point coordinates plus a moving origin are the low-end route the manual describes; the Dungeon Siege and
  Daggerfall Unity sections below show two games that took it.

### Open-world plugins for Godot

Both read for ideas; both MIT-licensed.

- **godot_voxel (Marc Gilleron).** Rule from `engine/priority_dependency.cpp`, `util/tasks/threaded_task_runner.cpp`
  and `util/tasks/time_spread_task_runner.cpp`: every queued load gets a priority from its distance to the nearest
  viewer (closer first, coarser detail levels before finer ones); the queue is re-sorted periodically while tasks
  wait, because the player moves; a task whose block is now farther than the view distance plus a margin is
  cancelled before it runs. Results are installed into the scene on the main thread under a time budget per frame
  (8 ms by default), at least one per frame. **Fits a 68040?** All of it, without the threads: one queue,
  re-prioritised by distance and heading, stale requests dropped, and installation capped per frame. This is the
  queue the near and far system describes.
- **Terrain3D (Cory Petkovsek, Roope Palmroos and contributors).** Rule from `src/terrain_3d_collision.cpp`: in its
  default game mode, collision exists only within a radius of the player, built from small square pieces on a grid;
  it is rebuilt only when the player's position, snapped to that grid, changes, keeping pieces still in range and
  removing those that left it. **Fits a 68040?** The pattern fits our "needed collision is kept, the rest follows"
  rule: collision for chunks near the player first, updated only when the player moves a grid step. The terrain
  drawing (GPU clipmaps) does not apply.
- **O3DE** (Apache 2.0 or MIT) was not read in this round.

## Other engines and published work

### Dungeon Siege: the continuous world (2002)

- **What it does.** From Scott Bilas's GDC 2003 talk "The Continuous World of Dungeon Siege" (slides checked):
  the world is a graph of terrain pieces ("nodes") joined at their edges, with no global coordinate system. A
  position is a node and an offset inside it. A world space exists only for one frame: the node under the camera's
  focus is the origin, and when the party crosses into another node the engine switches to that node's space,
  rebuilding the transforms by walking outwards through the neighbours. The talk gives the reason for switching at
  every node: switching as often as possible keeps the boundary cases exercised. Around each party member a box,
  much larger than the view, decides what exists: nodes and objects inside it are loaded and active, those outside
  are thrown away or queued for removal; objects are classified as critical or not and the non-critical ones expire
  when they leave. The loader ran on a second thread; the lessons were that it had to stay under about a fifth of
  that thread's time or players noticed, that load should be steady rather than bursty (work orders were throttled),
  that missing textures showed a blank placeholder until loaded, and that game logic without levels is hard: an
  object may leave the world in the next frame, so the logic had to tolerate it. Teleports used fog and box-size
  changes to hide loading. Test maps for every boundary case, and the direction of travel, mattered for finding bugs.
- **Fits a 68040?** The design fits better than its implementation: a position as a cell and an offset, an origin
  that follows the player, and a box larger than the view that decides what exists, are all bookkeeping. The
  second thread does not exist on the Amiga; its "steady, not bursty, throttled" lesson is the per-frame slice. The
  game-logic lesson is the one AmiWind meets in type 1's entities coming and going by distance.

### Crash Bandicoot: 64 KB pages from a CD (1996)

- **What it does.** From Dave Baggett's account of the game's development (an answer published on Quora and
  reposted with attribution by Michael Tsai, 2015): levels of more than 10 MB ran in 2 MB of RAM because the game
  paged fixed 64 KB pages in and out as the player moved; a packing tool put sounds, art and creature code into
  those pages, and the data was laid out on the disc in the order of the level's path, so that even at about
  300 KB a second each piece arrived before the player did, without dropping the frame rate.
- **Fits a 68040?** Closely: a slow device, little memory, and data laid out in the order it is needed. CHIM's
  sector files already follow this (one small file read whole, front to back). The lesson for crossings is the
  layout: the builder can place the chunks a crossing needs first, nearest the border, at the front of each sector
  file, so the first read already holds what the player reaches first.

### GTA III-era games: sector archives and paired detail

- **What it does.** From the GTA modding community's wiki (pages on the IMG archive, item definitions and LOD
  models, checked): the streamed models and textures live in one archive aligned to 2,048-byte sectors, the size of
  a CD sector, with a directory of offsets and sizes in sectors; the wiki notes that files next to each other in
  the archive can be read in one call, so the directory order matters. Every large map object can have a
  low-detail partner placed at the same spot with a long draw distance (the wiki gives 301 to 3,000 units for the
  partner), shown at range while the detailed model is streamed in near the player; objects fade in and out when
  they are streamed, unless flagged not to.
- **Fits a 68040?** The paired-detail pattern is the same as the shell pieces and their chunks. Sector-aligned
  files with an ordered directory match what the Amiga's file system rewards (whole files, few seeks, related data
  side by side). Fading in does not fit (no blending); the fog takes its place.

### Daggerfall Unity: a tile ring and a floating origin

- **What it does.** Rule from Daggerfall Unity (MIT) `Assets/Scripts/Terrain/StreamingWorld.cs` and
  `Assets/Scripts/Utility/FloatingOrigin.cs`: a ring of terrain tiles (three on each side of the player's tile by
  default) is kept around the player. Tiles beyond the ring are marked inactive and returned to a fixed pool of 256
  tile slots for reuse; the objects of locations farther than one tile beyond the ring are destroyed. Building new
  tiles and placing a town's blocks are spread over frames, one piece per frame. Every time the player enters a new
  tile, the whole loaded world, the player and the loaded enemies are moved back towards the origin by exactly one
  tile, and an event tells every other system to apply the same offset.
- **Fits a 68040?** The ring, the fixed pool and the one-piece-per-frame spreading fit as they are. The floating
  origin is the second proven example (after Dungeon Siege) of moving the origin at every tile crossing rather than
  only when coordinates run out; with a fixed tile size the shift is a whole number of tiles, which in AmiWind's
  fixed-point coordinates is an exact addition with no rounding.

## What does not carry over

- **Background threads.** Every modern engine read here loads on other cores. The Amiga has one CPU and no spare
  core; everything becomes a slice of the rendered frame, with a stated and measured budget.
- **Alpha fades and blending.** Godot's fades, GTA's fade-ins and OpenMW's blended sky need blending. The span
  renderer draws opaque surfaces; the fog is its only soft transition, so cuts sit behind opaque fog.
- **GPU batching and clipmaps.** Merging objects to save draw calls (OpenMW's object paging) and clipmap terrain
  (Terrain3D) solve GPU problems. On the span renderer the cost is edges and spans, so the measure is faces and edges
  drawn, not batches.
- **Double-precision positions.** Not affordable; wide fixed-point coordinates and a moving origin instead.
- **Placeholder textures.** Dungeon Siege drew a blank texture until the real one loaded. AmiWind's rule is a
  silhouette, not a wrong surface, and a short counted stall when collision is missing.

## What this means for the 2x2 sandbox

Mapped onto the steps of [how it is built](CELL_CROSSINGS.md#how-it-is-built):

1. **The level change split part by part.** Nothing here changes the measurement. OpenMW is a reminder that even a
   threaded engine keeps a short synchronous step at the grid change; the split shows how much of AmiWind's
   220 to 260 ms is that kind of unavoidable switching and how much is restart.
2. **Four light frames around one corner.** Take three rules as they are: the window moves only past half a frame
   plus a hysteresis (OpenMW's eighth of a cell, 256 of our units, as the first value to measure); incoming frames
   load nearest first; the next row or corner is requested when the player, or the player's position one second
   ahead, comes within a set distance, and only on the side being approached. One queue, prioritised by distance
   and heading, re-sorted as the player moves, stale requests dropped (godot_voxel), installed under a per-frame
   budget with at least one piece per frame. The builder can put the pieces nearest each border at the front of
   each sector file (Crash Bandicoot's layout).
3. **Repeated loading and unloading.** A cache of left frames with a size budget, a minimum kept, an age limit and
   a rule that never evicts what was wanted in the last second (OpenMW's preload cache), with counters for added,
   evicted, loaded and expired frames printed by the sandbox. Entities that leave are captured and may disappear
   at any frame (Dungeon Siege's lesson): logic that holds a reference must tolerate that.
4. **A forced rebase.** Two games rebase at every tile crossing on purpose (Dungeon Siege, Daggerfall Unity); the
   sandbox's forced rebase at every crossing is therefore a candidate for the normal mode, not only a test. A rebase
   by a whole number of frames is an exact fixed-point addition. Every system that stores a position subscribes to
   one rebase event, as Daggerfall Unity's systems do.
5. **Edges and the corner measured.** Measure the longest frame over the whole approach, not only the crossing
   (Dungeon Siege's "steady, not bursty"), and keep boundary-case test routes: along a border, at a corner, a
   U-turn at the border, in both directions (Dungeon Siege found bugs that depended on the direction of travel).
6. **The near and far handover.** The shell piece of each streamed chunk is its "visibility parent": it hides when
   the camera is inside the handover distance and the chunk's detail is installed, with a hysteresis margin so it
   does not flicker (Godot); shell pieces never straddle the loaded area's edge (OpenMW); what goes into the shell
   is chosen by size over distance at the handover distance (OpenMW's object paging rule); the shell selection is
   rebuilt only after the player has moved (OpenMW). Collision follows the player on a grid, rebuilt only when the
   player moves a grid step (Terrain3D).

## Sources

| Source | Author, year | What it is, licence | Read |
| --- | --- | --- | --- |
| OpenMW 0.51.0 | The OpenMW team, 2026 | Open-source Morrowind engine, GPLv3: read only, nothing copied | [openmw.org](https://openmw.org), source at [gitlab.com/OpenMW/openmw](https://gitlab.com/OpenMW/openmw), tag `openmw-0.51.0` |
| Godot Engine 4.8 (development, October 2026) | Godot contributors, 2026 | Game engine, MIT | [github.com/godotengine/godot](https://github.com/godotengine/godot); manual pages [Visibility ranges](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html) and [Large world coordinates](https://docs.godotengine.org/en/stable/tutorials/physics/large_world_coordinates.html) |
| godot_voxel | Marc Gilleron, 2026 | Voxel terrain module for Godot, MIT | [github.com/Zylann/godot_voxel](https://github.com/Zylann/godot_voxel) |
| Terrain3D | Cory Petkovsek, Roope Palmroos and contributors, 2026 | Terrain plugin for Godot, MIT | [github.com/TokisanGames/Terrain3D](https://github.com/TokisanGames/Terrain3D) |
| Daggerfall Unity | Daggerfall Workshop, 2026 | Open-source Daggerfall engine in Unity, MIT | [github.com/Interkarma/daggerfall-unity](https://github.com/Interkarma/daggerfall-unity) |
| "The Continuous World of Dungeon Siege" | Scott Bilas, Gas Powered Games, GDC 2003 | Conference talk slides | [gamedevs.org](https://www.gamedevs.org/uploads/the-continuous-world-of-dungeon-siege.pdf) |
| How Crash Bandicoot fit into 2 MB of RAM | Dave Baggett, reposted by Michael Tsai, 2015 | Developer's account | [mjtsai.com](https://mjtsai.com/blog/2015/06/18/how-crash-bandicoot-was-fit-into-2mb-of-ram/) |
| IMG archive, IDE and LOD pages | GTA modding community wiki | Community file-format documentation | [IMG archive](https://gtamods.com/wiki/IMG_archive), [IDE](https://gtamods.com/wiki/IDE), [LOD](https://gtamods.com/wiki/LOD) |
| Morrowind (Game of the Year Edition) | Bethesda Softworks, 2002 | The original game, played; its shipped configuration file read | Your own copy |

See also: [cell crossings](CELL_CROSSINGS.md), [CHIM ideas: the distant view](IDEAS.md#the-distant-view-far-terrain-and-mold-shells),
[the roadmap](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026).
