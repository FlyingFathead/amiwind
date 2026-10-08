# Data streaming: how AmiWind loads the world today

**Status: describes v0.0.31 (8 October 2026).** Decided next: a world streamer
with no duplicated assets; see [the roadmap](ROADMAP.md).

Quake loads one level at a time and keeps all of it in memory until the next
`changelevel`. AmiWind keeps that engine and streams Morrowind's world through
it in pieces, so that no piece needs more than one map's memory.

## What is resident and what is loaded

| Data | When it is read | Where it lives |
| --- | --- | --- |
| Open-world terrain | Once; one terrain BSP with explicit local origins per region (`aw_world.c`), so original coordinates survive crossings while render and network coordinates stay small | Second disk (`world-01`) |
| Town and area maps (Seyda Neen 64 sub-cell maps, Balmora 64) | Whole map at a region crossing, chosen by position with hysteresis | Main disk, `maps/` |
| Interiors | Whole map behind a door (`changelevel`) | Main disk, `maps/` |
| Night lamps (`world/lamps.awl`) | The 3 x 3 cells around the player, on a cell change | Engine table, 256 lamps |
| Region and place names (`world/regions.awr`) | One lookup per visited cell | Read from fixed disk rows; no second map in memory |
| Fog per location, night windows | Once per map | Small tables |
| NPC and creature models, sounds | When first needed | Quake's cache (least recently used first out) |

Nothing reads the disk every frame. Each map's brush geometry, collision and
lightmaps go on Quake's hunk, which is cleared at every map change; models and
sounds in the cache survive a change while there is room.

## Memory per map

Every map must fit an 11 MiB heap budget (11,534,336 bytes) together with the
engine's fixed allocations; the builder estimates each map before it is
accepted ([MEMORY_ALLOCATION.md](MEMORY_ALLOCATION.md)).

## What a crossing costs

A region crossing loads the destination map in full. In v0.0.29 a crossing
took about 1.1 seconds on the emulated A1200, about 79 % of it in file reading
([cell-transition investigation](performance/CELL-TRANSITION-INVESTIGATION-v0.0.29-dev4.md)).
A larger read buffer in v0.0.31 cut Seyda Neen crossings from 0.70-0.91 s to
0.39-0.48 s ([SEYDA-READ-SLOW-31](bugs/SEYDA-READ-SLOW-31.md)). A read-ahead
experiment (a 128 KiB prefix read before the crossing) gave mixed results and
is not the default. Everything that must survive a crossing (position, held
keys, health, torch, time of day, ...) is listed in the
[cell-change checklist](CELL_CHANGING.md).

## Why it is heavy

Each region map has to contain everything visible from its core, out to the
draw distance, so neighbouring regions overlap almost entirely:

- Seyda Neen's 64 maps store each face 24.1 times, Balmora's 7.3 times
  ([sub-cell redundancy](SUBCELL_REDUNDANCY.md), 7 October 2026).
- Across the whole island, each exterior object would be stored about 9.8
  times ([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md)).
- The v0.0.31 disks hold 4.79 GB of game files for two towns, their interiors
  and the terrain; every map of the island would need about 20 GB.

The repeated geometry also makes each map bigger in memory and slower to
load, which is where most heap failures and crossing time come from.

Drawing has the same root. Renderer counters (8 October 2026) show that most of
a Balmora frame goes into placing building faces through a deep world BSP, and
Seyda Neen views rebuild their surface cache every frame
([What a town frame is spent on](performance/LESSONS_LEARNED.md)).

## Where this is going

Two candidates are being measured against today's layout, for disk use, heap
and bytes loaded per crossing (Balmora measured, the island extrapolated):

- **Shared object models:** each unique object compiled once as its own small
  brush model, like Quake's health and ammo boxes, with region maps holding
  terrain and references; shared models stay loaded across crossings.
- **Cells streamed around the player:** a resident layer (terrain and distant
  shells for the whole island) plus full-detail cells stored once, loaded as
  the player approaches and released through Quake's cache.

Interiors stay ordinary Quake maps. The open question is load time on a real
Amiga disk, which needs measuring in the emulator before any change.
