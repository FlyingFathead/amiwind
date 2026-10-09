# CHIM NPC pathfinding

Design, 9 October 2026. How hostile NPCs on the CHIM engine get to the player:
smarter than both Quake's monsters and Morrowind's actors, inside the slow-CPU
budget, with the walkable graph stored once in the CHIM world data. The
background (how Morrowind, OpenMW and Quake do it, what AmiWind does today,
island-wide path grid numbers) is in [NPC pathfinding](../NPC_PATHFINDING.md);
the world format this extends is [CHIM world format](WORLD_FORMAT.md).

<!-- contents start -->
## Contents

- [The idea](#the-idea)
- [Vis story](#vis-story)
- [The ladder](#the-ladder)
  - [1. Quake chase with stair climbing](#1-quake-chase-with-stair-climbing)
  - [2. Stuck check and local ping](#2-stuck-check-and-local-ping)
  - [3. A local patch of the walkable graph](#3-a-local-patch-of-the-walkable-graph)
- [Budget on a slow 68040](#budget-on-a-slow-68040)
- [The graph in the CHIM world format](#the-graph-in-the-chim-world-format)
  - [Where it lives](#where-it-lives)
  - [Layout (big-endian, as CHIM structures)](#layout-big-endian-as-chim-structures)
  - [Sizes](#sizes)
  - [Across chunks, frames and doors](#across-chunks-frames-and-doors)
  - [Collision](#collision)
- [Followers across doors and cells](#followers-across-doors-and-cells)
  - [How OpenMW does it (0.51.0 source)](#how-openmw-does-it-0510-source)
  - [What AmiWind needs](#what-amiwind-needs)
  - [Test cases from Bloodmoon](#test-cases-from-bloodmoon)
  - [Indoor fights](#indoor-fights)
- [Validation gates](#validation-gates)
- [Staged plan and the measurement each stage needs](#staged-plan-and-the-measurement-each-stage-needs)

<!-- contents end -->

Status: a plan with costs, not a promise. Nothing here is implemented. Cycle
figures are estimates unless marked measured; emulator figures are relative.

## The idea

| | Quake monsters | Morrowind actors | CHIM hostiles |
| --- | --- | --- | --- |
| Knows the level | no: greedy chase with step checks | yes: one path grid per cell | yes: a walkable graph per sector, stitched across cells |
| Out of sight, around a house | lost behind the first wall | routes on the grid, if the cell has one | routes on the graph (stage 3) |
| Stairs, slopes | step up to `STEPSIZE` | engine step and slope limits | the player's step: 8.5 units up, 0.69 slope (46 degrees) |
| Stuck on a rock or corner | tries other directions | known to grind | stuck check, local probe, then re-route (stage 2) |
| Player on a ledge or rock | keeps bumping | keeps bumping (the classic exploit) | detects "unreachable" and changes behaviour |
| Cells without a grid (90 % of exteriors) | works (no data needed) | nothing to route on | chase and probe work; the builder generates a graph |

In one sentence: chase like Quake while the player is in sight, route on a
stored graph when not, and notice when the player cannot be reached.

## Vis story

Navigation draws nothing and adds no placements, so it does not change what
the renderer sends. Two places touch visibility:

- "Can I see the player?" is a point trace (Quake's `traceline`), but first
  the cheap test Quake's own monsters use (`checkclient`): if the player's
  chunk is not in the NPC chunk's PVS row, there is no line of sight and no
  trace is made.
- Only NPCs in resident chunks near the player run any of this; others sleep
  (the traversal rules decide what a sleeping hostile remembers).

## The ladder

Each step runs only when the cheaper one failed. Owner direction, 9 October
2026: start from plain Quake movement.

### 1. Quake chase with stair climbing

The NPC turns toward the player and steps, in Quake's order of directions when
blocked (`SV_StepDirection`, `SV_NewChaseDir`: the diagonal toward the
player, the two axis directions, the old direction, all eight, turn around).
Each step uses `AW_ActorStep`, the player's own walk: step up 8.5 units (34
Morrowind units, Quake's `STEPSIZE` scaled as in `sv_move.c` and
`sv_phys.c`), floor normal at least 0.69, no step off a ledge higher than a
step. Every flight of stairs the stair gate passes (risers up to 8.5 units)
is therefore climbable by NPCs too, with no extra data.

What already works today: `AW_ActorStep` itself (the opening's escort and
dock guard use it), the standing hull shared by player and NPCs, the stair
rule in the CHIM collision, and the engine's chase functions. What is
missing: a QuakeC builtin that steps with `AW_ActorStep` (the stock
`walkmove`/`movetogoal` use `SV_movestep`, whose corner test refuses ground
the player can walk), the declarations in our progs (`engine/aga/qc`), walk
poses for residents, ground flags and a think rate for moving residents, more
than one moving actor, and hostile behaviour itself.

Measured offline on CHIM frames (format 0.5, the stair gate's tracer): the
player step walks 642 of 662 Balmora path grid links (97 %) and 144 of 156 in
Seyda Neen (92 %); Quake's `SV_movestep` walks 92 % and 86 %.

### 2. Stuck check and local ping

Stuck: less than half the expected progress over about 1.5 s (OpenMW's rule),
or the same blocked direction twice. Then a local "ping" toward the player,
no stored data needed, so it also works where Morrowind has no grid:

- (a) **Fan probe.** 8-16 short hull traces (about 32 units) in a ring, with
  the NPC's own standing hull and the trace the step code uses. Pick the open
  direction that best reduces the distance to the player or opens a line of
  sight: a wider, smarter `SV_NewChaseDir`. Walk it for a short while, then
  return to stage 1.
- (b) **Tiny flood fill** when the fan finds nothing (a dead end): an 8 x 8
  grid of step-sized cells around the NPC, each classified walkable or
  blocked by traces, breadth-first to the walkable border cell nearest the
  player.

Only when stuck, only for NPCs near the player, spread over one or two frames.
Costs are in the budget below; the flood fill is about twelve fans, so it is
rare (at most once per NPC every few seconds) and is replaced by stage 3
wherever a stored graph exists.

### 3. A local patch of the walkable graph

When the player is out of sight, or the NPC is stuck or kited: hand the NPC a
local patch of its walkable graph ("here is a piece of your map, now get to
the player"): the graph points covering NPC and player, a few hundred units
across, with the player's position as the A\* goal.

- Search: A\* with integer coordinates, a small binary heap and a fixed node
  budget per frame; a search that runs out of budget continues next frame.
  Follow the route until the player is in sight again, then back to stage 1.
- Patch size, measured on the path grids: within 1,024 Morrowind units (256
  AmiWind units) of a point there are 14 points at the median, 72 at p99 and
  113 at most (island-wide); within 2,048 units, 31 at the median, 157 at most.
  The largest whole exterior grid has 246 points.
- **Unreachable.** If the player's nearest point is in another connected
  component (stored per point, below), the player is unreachable without any
  search; if A\* exhausts the patch, likewise for this patch. The NPC then
  switches behaviour: ranged attack or spell if it has one, back off, or wait
  at a sensible spot in reach (the patch point nearest the player). This
  closes Morrowind's "stand on a rock" exploit instead of grinding into walls.
  Path grids split into parts are common (276 of 1,194 grids on Vvardenfell),
  so components are stored, not guessed.
- Fallback where no graph exists: the stage 2 ping grid.

## Budget on a slow 68040

Measured: Balmora on CHIM draws about 0.9 frames per second at a 49.7 MHz
68040 (FS-UAE cycle-exact, relative); the frame is rendering, not movement.
Navigation must stay a small share of the machine whatever the frame rate
becomes. Proposal: 5 % of the CPU, about 2.5 million cycles per second at
49.7 MHz, shared by all NPCs near the player; the per-frame allowance is that
share of the frame time, with at least 64 A\* points per frame.

Cost per operation, estimated from offline clipnode-visit counts on the
Balmora and Seyda Neen CHIM frames (about 80 cycles per visit, 500 per trace
set-up, 400 per placed hull entered; to be replaced by an engine counter):

| Operation | Balmora | Seyda Neen |
| --- | ---: | ---: |
| One step (player walk: 2.6-3.1 traces) | about 24,000 cycles (0.5 ms) | about 88,000 cycles (1.8 ms) |
| 16-way fan probe, median trace | about 85,000 (1.7 ms) | about 254,000 (5.1 ms) |
| 16-way fan probe, mean trace | about 720,000 (14.5 ms) | about 2.6 million (52 ms) |
| 8 x 8 flood fill (about 12 fans) | 1-9 million (20-170 ms) | 3-31 million (60-620 ms) |
| A\* over a 256-unit patch, median / worst (about 400 cycles per point) | 5,600 / 45,000 (0.1 / 0.9 ms) | same graph cost |
| A\* over the largest exterior grid (246 points) | about 98,000 (2 ms) | |

The trace means are dominated by a tail of traces that graze many planes (the
p90 trace in Seyda Neen visits 3,040 clipnodes against a median of 171); that
tail is registered as [CHIM-TRACE-TAIL-33](../bugs/CHIM-TRACE-TAIL-33.md).

What 2.5 million cycles per second buys (estimate): in Balmora, about six
hostiles chasing at five steps per second, plus one fan probe and about
twenty patch searches per second; in Seyda Neen, about three chasers and one
probe every two to three seconds. A search over a stored patch costs about
as much as one or two steps; a probe costs as much as tens of searches. On a
68040, bytes on disk are cheap and traces are dear: that is why stage 3
stores the graph instead of probing for it.

## The graph in the CHIM world format

Stored once, streamed with its sector, never duplicated (CHIM principle 1).

### Where it lives

A new sector record kind `NAVG` (id = the sector's index in its frame) after
the sector's chunk records: one graph per sector of 3 x 3 chunks, not per
chunk, so the 16-byte header and directory entry are paid about ten thousand
times island-wide, not ninety thousand. Adding a record kind is a format
change: it goes into the next format version when stage 3 starts.

Interiors stay Quake maps for now; they get the same layout as a file next
to the map (the opening's `.awn` route files are the precursor).

### Layout (big-endian, as CHIM structures)

```text
head (16)        'NAV0', u16 points, u16 links, u16 doors, u16 cross-frame links,
                 u16 reserved, u16 reserved
points (10 each) i16 x, y, z (frame-local units, rounded), u16 component,
                 u8 link count, u8 flags
links (2 each)   the points' links in point order (as Morrowind's PGRC):
                 bits 15-12 sector code (0 this sector, 1-8 the eight neighbour
                 sectors, 9 = an entry of the cross-frame table), bits 11-0 point
                 index in that sector (or table index)
doors (8 each)   u16 point, u16 flags (load door, can be locked), u32 placement id
cross-frame (8)  i8 frame dx, i8 dy, u16 sector, u16 point, u16 reserved
```

Point flags: bit 0 from a Morrowind grid (else generated), bit 1 door, bit 2
on stairs, bit 3 in water, bit 4 linked across a cell border by the builder.
Components are numbered island-wide by the builder (u16), so "unreachable"
is one compare. Link lengths are short: the median grid link is 277
Morrowind units (69 AmiWind units) and 99 % are under 906 (227), less than
one chunk, so a sector's links reach at most its neighbours; the 293 longer
links (island-wide) are split by the builder with inserted points.

### Sizes

| Data | Points | Directed links | Bytes (layout above) |
| --- | ---: | ---: | ---: |
| Vvardenfell exterior path grids | 7,232 | 19,967 | about 112,000 (+ headers, about 0.14 MB) |
| Generated graphs for the 1,270 gridless exterior cells (estimate: 30 points per cell) | about 38,000 | about 105,000 | about 0.6 MB (upper bound: many are sea) |
| Balmora frame (3 x 3 cells, path grids only) | 395 | 1,330 | 6,610 (about 100 bytes per sector) |
| Vvardenfell interior grids (with the interior maps) | 34,513 | 89,906 | about 0.52 MB |

Resident: the graph of the resident sectors is a few kilobytes. Search
scratch: one shared buffer, about 6 bytes per resident point (cost, parent,
state) plus a 256-entry heap (1 KB).

### Across chunks, frames and doors

- Chunk and sector borders: a link names a point in a neighbouring sector
  directly; a path crosses borders without a special case. A neighbour sector
  that is not resident yet ends the patch there (the route goes to the patch
  edge nearest the player, and continues when the sector arrives).
- Cell borders: Morrowind never links grids across cells. The builder links
  border points (596 of Vvardenfell's 754 exterior border points face a
  gridded cell) to the nearest point across the border when the step walk
  between them passes.
- Frame borders: the cross-frame table, used when frames touch (the open
  world; same rule as the format's "reach across frames" decision).
- Doors inside a cell: a door point; the NPC opens the door (its collision
  changes) and walks on. Load doors: the door table names the placement;
  crossing follows the [traversal rules](../NPC_CELL_TRAVERSAL.md) (hostiles
  normally stop at the exit, followers and escorts may pass).

### Collision

All actors trace the standing hull (hull 1), the player's box, against the
chunk terrain and the placements' hulls (`SV_ClipMoveToEntity` with the
record's origin and yaw). A link the gate walked is walkable by an NPC at run
time on the same data; the stair rule applies to NPCs without extra work.

## Followers across doors and cells

Owner question, 9 October 2026: companions following the player through a load
door, for example into a cave or barrow with its own entrance.

### How OpenMW does it (0.51.0 source)

Paths relative to the [OpenMW repository](https://gitlab.com/OpenMW/openmw):

- **Who comes along.** A load door runs a teleport action with "take
  followers" on (`apps/openmw/mwclass/door.cpp`, `apps/openmw/mwworld/actionteleport.cpp`).
  A follower is an actor whose current package is a follow package aimed at the
  player (`AiFollow` sets `mFollowTargetThroughDoors`,
  `apps/openmw/mwmechanics/aifollow.hpp`); combat and wander packages ahead of
  it are skipped over, any other package type in front stops the search
  (`Actors::getActorsFollowing`, `apps/openmw/mwmechanics/actors.cpp`). The
  search is recursive: followers of a follower come too. Escort packages do
  not qualify: the escorting actor leads, and pauses when the player is in a
  different cell (`aiescort.cpp`).
- **Distance, not sight.** A follower is taken only if it is within 800
  Morrowind units (200 AmiWind units) of the player when the door is used;
  there is no line-of-sight test. A follower whose script sets a local
  `stayoutside` to 1 stays behind when the player goes from an exterior into
  an interior (none of the three masters uses that variable; it is a hook for
  scripted companions).
- **Hostiles.** A follower in combat with the player is not moved; its combat
  is stopped instead. Pursuing enemies (combat packages) never come through
  doors in OpenMW.
- **Where they appear.** At the door's destination position, the same point
  as the player (followers are moved first, then the player), with no
  offset of their own.
- **Door-less teleports.** Paid travel (silt strider, boat, guild guide) takes
  followers along and charges per follower (`apps/openmw/mwgui/travelwindow.cpp`;
  OpenMW notes that, unlike the original game, the first follower is not free).
  Mark/Recall, the Intervention spells and script teleports do not take
  followers (`apps/openmw/mwmechanics/spelleffects.cpp`,
  `apps/openmw/mwscript/cellextensions.cpp`, `apps/openmw/mwworld/worldimp.cpp`).
- **Tribunal and Bloodmoon.** The engine path is the same for all three
  masters; the expansions only add more followers. Counted in the owner's
  masters: base actors with a follow package 70 / 16 / 14 (Morrowind /
  Tribunal / Bloodmoon), dialogue results that start one 81 / 12 / 21, scripts
  that call it 9 / 3 / 9; one escort package (Bloodmoon). A Bloodmoon barrow or
  cave entrance is an ordinary load door, so its companions follow by the
  rules above.

The original engine's exact rules (distance, the free first traveller) are
only known through OpenMW's reimplementation and its compatibility notes; the
summary above is OpenMW's behaviour.

### What AmiWind needs

An interior is a separate Quake map (legacy and CHIM alike), so a follower has
to survive the map change the way the player's own state does. Quake already
has the mechanism: before `changelevel`, `SV_SaveSpawnparms`
(`engine/aga/src/sv_main.c`) copies the player's `parm1..parm16` out of the
server, and the new map hands them back to the QuakeC spawn code. AmiWind
already carries per-actor state across scenes and saves (`aw_save.c`:
reference, scene, position, angles, health, greeting counters, up to 256
actors).

Plan:

1. **At the door** (the engine, where the door link is taken): collect the
   followers by OpenMW's rules (follow package aimed at the player, within 200
   AmiWind units, not in combat with the player, `stayoutside` respected), at
   most a small fixed number (proposal: 4).
2. **Carry a compact follower record** across the load, next to the spawn
   parms: the Morrowind reference (identity and save key), the package and its
   target, the companion settings (follow distance, the script's state
   variables that the follow logic reads), health and equipment intent. About
   64 bytes each, and the existing saved-actor record already holds most of it.
3. **On arrival** the new map spawns each follower from its record at the door
   table's arrival point (`prepare_doors.py` writes the links; the arrival
   position and angle are the door's destination), offset behind the player
   along the arrival heading and placed with the standing-hull floor trace the
   NPC ground snap uses (`AW_NPCFloor`); if no offset spot stands, the next one
   in a short fan, as the stage 2 probe does. The actor's own copy in its home
   map is marked away (the save key says which map owns it), so it is never
   doubled.
4. **Target map unavailable** ("Interior unavailable" today, `aw_scene.c`):
   the door does not open, so nobody moves; the followers keep following in
   the current map. A record whose map disappears from a later build falls back
   to the actor's home map and authored position.
5. **Exterior cells and CHIM chunks** need none of this: there the follower is
   an actor in resident chunks and walks with the ladder above; only a load
   door or a paid travel changes the map.
6. **Hostile pursuers** stop at load doors as in Morrowind
   ([traversal rules](../NPC_CELL_TRAVERSAL.md)); OpenMW agrees.

Measurements: the record size and count (a regression test that a follower
survives door, return door, save and load once, with no duplicate), the
arrival spot standing on collision at every load door island-wide (the door
table gate), and the frame time of the arrival spawn.

### Test cases from Bloodmoon

Read from the owner's `Bloodmoon.esm` (quest and record IDs only): of its
dialogue results, 21 start a follow package aimed at the player and 4 move an
actor with a scripted `PositionCell`; none uses an escort package (one script
does, for a guide leading the player outdoors). Three quests make good test
cases for followers across load doors:

| Quest | Follower | Through which doors | Kind |
| --- | --- | --- | --- |
| `BM_Ingmar` | `ingmar` (placed outdoors) | from the exterior into `Solstheim, Valbrandr Barrow` (one load door) | follow the player through doors (`AiFollow Player` from dialogue) |
| `BM_Draugr` | `draugr_aesliip` (placed in `Solstheim, Aesliip's Lair`) | the lair, its caverns and `Solstheim, Caves of Fjalding` are joined by load doors | follow the player through doors; the same quest also moves another actor by script (`PositionCell` to `Solstheim, Lake Fjalding`), a scripted move, not following |
| `BM_FrostGiant1` | `BM_riekling_Krish_UNIQU` (placed in the Caverns of Karstaag) | through the castle's interior levels | follow the player through doors; the actor's script re-issues the follow if it gets lost |

Also worth a run: `BM_Missionary` (`mirisa` follows from a Thirsk interior to a
Fort Frostmoth shrine; the script checks that the player reached that cell,
and a separate script moves her by `PositionCell`) and `BM_WildHunt` (two
followers in the Mortrag Glacier rings, interiors joined by doors).

Each case passes when the follower arrives behind the player on standing
collision after every load door of the route, keeps its package after a save
and load in the cave, and is never doubled when the player goes back out.

### Indoor fights

Interiors are the easy case for routing: 93 % of Vvardenfell's interior cells
have a path grid (1,060 of 1,134; median 23 points), so stage 3 has data in
almost every cave, tomb and house. Hostiles stop at load doors (OpenMW's rule:
a follower in combat is not taken along, and combat packages never follow
through doors), so an indoor fight stays inside one map. Furniture is the
classic trap: a player standing on a table or counter is reachable neither by
the grid nor by the step code, and the unreachable switch (stage 3: no path
on the patch, or the player's spot in another component) turns that into a
behaviour change (ranged attack, back off, wait beside it) instead of an NPC
grinding against the table.

## Validation gates

Think in scale: the gate runs on every CHIM world the builder validates,
island-wide, in parallel cores like the stair gate (`chim.collision.FrameScene`
and its walker), and writes `chim-nav.json`.

1. **Every point stands on CHIM collision**: a standing-hull floor trace
   finds a walkable floor (normal at least 0.69) within 8 units of the point's
   height, not inside solid. Measured on the format 0.5 frames: Balmora 393 of
   395 points stand (22 of them more than 8 units off the grid height), 2 are
   inside solid; Seyda Neen 104 of 106 (3 off, one on a steep face), 2 in solid.
2. **Every link is walkable** both ways with the NPC step (`AW_ActorStep`
   emulation, 8-unit steps). Measured: 20 of 662 Balmora links and 12 of 156
   Seyda Neen links fail today; the builder moves the end point to the nearest
   standing spot or inserts a point, and drops what it cannot repair, with the
   reason in the report.
3. **Connectivity does not silently drop**: components per cell against the
   source grid; a new split fails the build unless recorded.
4. **Border links** exist only where the walk passes; door points are within
   reach of their door on the walkable side.
5. **Limits**: at most 4,096 points per sector, 255 links per point, the
   patch size (p99) and the largest component reported.

Time: the private probe walked all of Balmora's links twice and fan-probed
every point in 50 s on one core (Seyda Neen 34 s). The island's roughly 156
exterior frames would take under an hour on one core, a few minutes on the
build's worker pool (estimate; the profiler measures it).

## Staged plan and the measurement each stage needs

1. **Quake chase on the player step.** Measure: an engine trace counter
   (traces, clipnode visits, cycles per step) on the cycle-exact preset at
   fixed Balmora and Seyda Neen poses; links walked by the engine against the
   offline numbers above; frame time with 0, 3 and 6 chasers.
2. **Stuck check and local ping.** Measure: cycles per fan and per flood fill
   on the cycle-exact preset; pings per second at the 5 % share; how often
   stage 2 ends a stuck case (test courses: wall between NPC and player, a
   U-shaped dead end, a door off to the side).
3. **Graph patches and unreachable detection.** Builder: the `NAVG` record,
   graphs from path grids plus generated ones, the gate. Engine: patch A\*
   with the node budget. Measure: bytes per sector island-wide, A\* points and
   cycles per search, unreachable cases detected on the rock and ledge
   courses, resident bytes.
4. **Generated graphs everywhere.** The builder samples walkable ground on
   CHIM collision where Morrowind has no grid and simplifies it to a sparse
   graph. Measure: points per cell against the 30-point estimate, gate time
   island-wide, chase success in wilderness spawn areas.

Regression checks with every stage: the gate's counts may not get worse
(points standing, links walkable, components), the renderer counters on the
benchmark cameras do not change, and the frame time with chasers stays inside
the share.
