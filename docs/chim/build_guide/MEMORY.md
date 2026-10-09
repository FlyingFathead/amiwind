# Memory on the Amiga: the game heap, the CHIM zone and what the builder checks

This page explains, in plain terms, where AmiWind's memory goes on an Amiga, what the CHIM
engine adds, which rules keep a map from running out, and how to read the numbers the game and the
builder print. All figures were measured in FS-UAE with the A1200 profile (2 MiB Chip RAM, 16 MiB
Fast RAM) on 9 October 2026, with the v0.0.32 release image and the CHIM engine of v0.0.33 (CHIM
0.1.0); counts of bytes are exact, they do not depend on emulator speed.

<!-- contents start -->
## Contents

- [The picture](#the-picture)
- [The 2 MiB Hunk-gap rule](#the-2-mib-hunk-gap-rule)
- [What a CHIM map adds: the zone](#what-a-chim-map-adds-the-zone)
- [The whole-map rule](#the-whole-map-rule)
- [Per map](#per-map)
- [How far the world is loaded](#how-far-the-world-is-loaded)
- [Fragmentation](#fragmentation)
- [What the builder checks](#what-the-builder-checks)
- [Choosing another heap size: `--heap-mb N`](#choosing-another-heap-size---heap-mb-n)
- [Reading the numbers](#reading-the-numbers)

<!-- contents end -->

## The picture

An A1200 with 16 MiB of Fast RAM holds, from the bottom up:

- **Chip RAM (2 MiB)**: the screen, the audio buffers and the mouse pointer. The game keeps it for
  the hardware; nothing of the world goes there. The boot check asks for 512 KiB free (256 KiB in
  one block).
- **The game heap (11 MiB of Fast RAM by default)**: Quake's Hunk, one block taken at start-up.
  Every map, model, texture, sound and the CHIM zone live in it. The boot check asks for the heap
  plus 3 MiB of free Fast RAM (14 MiB) and the heap plus 16 bytes in one block.
- **The rest of Fast RAM**: the program itself, the screen and z buffers, the surface cache,
  short-lived copies (alias model staging up to 512 KiB, the world map screen's 250 KB map, movie
  buffers), and the guard torch's 1 MiB probe. With the 11 MiB heap about 1.4 MB stays free in one
  block after the heaviest map.

Inside the heap, Quake allocates from both ends (the Hunk's low and high marks) and keeps a cache of
actors and sounds in the middle, which it can evict. What is not allocated at the load peak is the
**Hunk gap**.

## The 2 MiB Hunk-gap rule

The engine wants at least 2 MiB of the heap free when a map has finished loading, and the heap audit
prints `WARNING: hunk-gap safety below 2 MiB` when it is not. The gap is what Quake's cache works in:
actors' models and animations, sounds and the alias loader's staging come and go there while you
play. A map that loads with less than 2 MiB free can still run, but the next actor or sound may evict
others constantly, and one larger allocation than usual ends the game with an error.

## What a CHIM map adds: the zone

A CHIM map (`maps/<town>-chim.bsp`) is a small frame map; the world itself is streamed in chunks.
When it starts, it takes one block from the heap, the **CHIM zone** (`chim_zone_kib`, default 6,864
KiB), and gives it back at the next map change. Maps without a frame (the ship, interiors, the
gallery) take no zone. The zone holds:

- the frame's chunk directory and the loading buffer (`chim_buffer_kib`, 32 KiB);
- the chunks near the player: their catalogues, terrain, and every model and texture they place,
  each stored once and shared;
- the **frame-world pool**: one block of twice `chim_pool_kib` (384, so 768 KiB) reserved when the
  map starts, in which the nearby chunks are joined into the map Quake draws and collides with.

The zone works like a second, smaller cache: blocks the current ring needs are locked; everything
else stays as a cache and is evicted when room is needed. It never moves a block.

## The whole-map rule

The zone is taken before the frame map's entities (actors, sprites) and the client's per-map
allocations load, so it has to leave room for them. The rule, which the engine keeps and the
builder checks:

    before the zone + zone + 64 + after the zone + chim_reserve_kib (2 MiB) <= the heap

- *before the zone*: the engine at start-up (782,416 bytes) and the frame map's own BSP;
- *after the zone*: the frame map's actors and sprites, then 1,589,344 bytes the client takes on
  every map (the renderer's surface and edge lists, 786,448 bytes each, and the scores);
- 64 bytes are the zone's own header.

The frame map states what it loads after the zone in its worldspawn key `"_chim_hunk_rest"` (bytes),
written by the builder. The engine makes the zone at most what the rule allows. After the map has
loaded it measures what really came after the zone; if the gap ended under 2 MiB it says so, with the
zone that would have kept it, and the next load of the same map in that session leaves room for the
most it has measured there (on frame maps that state the figure; `chim_rest_measured 2` does it on
every frame map). `tools/engine_limits.py` (`whole_map_zone`) states the same rule for the builder.

## Per map

The heap audit after loading, 11 MiB heap (the CHIM towns with the default zone of 6,864 KiB):

| Map | Load peak | Peak gap | Largest zone the rule allows | Fast RAM left in one block |
| --- | ---: | ---: | --- | ---: |
| Balmora on CHIM | 9,431,840 | 2,102,496 | 6,864 KiB | 1,400,176 |
| Seyda Neen on CHIM | 10,434,912 | **1,099,424** | 5,888 KiB | 1,397,800 |
| Balmora legacy region `bm019` | 8,006,912 | 3,527,424 | no zone | 1,430,560 |
| Vivec Arena legacy region `va010` | 5,294,784 | 6,239,552 | no zone | 1,390,824 |
| Prison ship | 6,336,496 | 5,197,840 | no zone | 1,430,560 |
| Census and Excise Office | 4,824,400 | 6,709,936 | no zone | 1,430,560 |
| Caius Cosades' house | 3,448,864 | 8,085,472 | no zone | 1,430,560 |
| NPC gallery | 2,473,232 | 9,061,104 | no zone | 1,390,824 |

Seyda Neen's CHIM frame map carries all of the town's 229 flora sprites and its actors at once (about
0.96 MB of sprite models); that is why it ends under the 2 MiB gap at the default zone. The builder is
moving those sprites into the chunks, so they load with the ring instead.

Free Fast RAM goes down by about 115 KB with the first map and 40 KB more with the first Arena visit
(one-time allocations), then stays put on later visits.

## How far the world is loaded

Around the player the chunks form a ring with three radii, in map units (one unit is four Morrowind
units):

- **active** = view distance + hysteresis (Balmora and Seyda Neen: 540 + 96 = 636): these chunks are
  joined into the map, drawn and solid, and their models are locked in the zone;
- **load** = active + prefetch (636 + 256 = 892): these chunks are loaded ahead into free room only
  (prefetch never evicts), and an active chunk is let go only beyond this radius, so walking back and
  forth over a border does not reload anything;
- **collision margin** (224): the chunks under and next to the player always load first, past every
  per-frame budget, so the ground is never missing.

The view distance follows the fog distance (`dbg fog distance`) up to what the world's visibility
data covers. A larger view distance makes the ring larger and needs more zone.

## Fragmentation

Because the zone never moves a block, a ring can fit by the sum of its sizes and still find no single
piece large enough for one house model. Three rules keep the room in one piece:

- blocks smaller than `chim_zone_ends` (64 KiB) are taken from the zone's high end, larger ones from
  the low end, so small locked blocks (textures, catalogues, terrain) do not split the room large
  models need;
- with `chim_release 1`, a chunk that finds no room lets go of the active chunk farthest from the
  player (outside the collision margin) and tries again;
- with `chim_partial 1`, a chunk whose model has no room is activated without it, so its ground and
  the rest of it are there; the model follows when there is room.

`chim` prints the largest run without a lock: the largest model that could still be loaded now.

## What the builder checks

- **The CHIM heap gate** (`tools/chim/heap.py`): over a grid of player positions in every frame, the
  largest active ring and load ring against the zone's room for chunks (the zone less the frame-world
  pool), and the largest single block.
- **The whole-map rule**: each frame map's `"_chim_hunk_rest"`, and the zone the rule allows on that
  map with the build's heap size.
- **The zone walk** (`tools/chim/zone_sim.py`): the engine's own zone code run on the host over a walk
  through every frame; it fails when a step leaves the player without ground.
- **The legacy map heap gate** (`tools/check_world_map_heap.py`): every legacy map's estimated load
  against the heap the engine was built with.

All of them read the engine's numbers from the engine source (`tools/engine_limits.py`), never a
copy, and the heap size from the engine build receipt.

## Choosing another heap size: `--heap-mb N`

The heap is 11 MiB unless you ask otherwise:

    ./build.sh --heap-mb 12          # or "heap_mb": 12 in a --build-config file

The builder uses exactly what you ask, like `--jobs N`: it is never refused. 11 MiB is the size
measured to run the whole game on 16 MiB of Fast RAM; above it the build prints one warning and
records it in `engine-build.json` (`heap_mb`, `heap_mb_selected_by`, `heap_warning`), the boot check
prints a `Game heap: ... [!] WARN` row and the engine says so at start. The map heap gates use the
size you chose. To try a size for one start without rebuilding, start the game with `-heapmb N`
(same warning).

What 12 MiB does on the 16 MiB profile (same route as the table above, plus save and load):

| Heap | Seyda Neen CHIM peak gap | Fast RAM free (least) | Largest free Fast block (least) |
| ---: | ---: | ---: | ---: |
| 11 MiB | 1,099,424 | 1,429,312 | 1,390,824 |
| 12 MiB | 2,148,000 | 380,864 | 342,240 |

Every map loads and saves load back at 12 MiB, and Seyda Neen keeps its 2 MiB gap, but only 342 KB of
Fast RAM is left in one block: the guard torch's 1 MiB probe can never pass (guards keep their torches
unlit) and other allocations outside the heap have little room. On a machine with more Fast RAM the
same heap leaves more room outside it (not measured yet).

## Reading the numbers

The heap audit line, printed on the console after every load phase (and written to
`heap-audit.log`, with the free Fast and Chip RAM, in the game's folder):

    Heap maps/seyda-chim.bsp snapshot: low 10422144 high 12768 peak 10434912 / 11534336,
        gap 1099424 peak gap 1099424; cache 852704 peak 2614768, zone largest 30552

- `low` / `high`: the heap in use from each end; `peak`: the most since the map started; `/ 11534336`:
  the heap size;
- `gap`: free now; `peak gap`: free at the load peak, the figure the 2 MiB rule is about;
- `cache`: actors and sounds held in the cache now and at most;
- `zone largest`: the largest free block of Quake's small memory zone (not the CHIM zone).

`chim` on a CHIM map prints, among others:

    zone: 1 banks, 6243 KiB used, 620 KiB free, largest free 565 KiB, 314 blocks, 254 locked
    Hunk: zone 6864 KiB; the map loads 2519 KiB after it (stated 0 KiB, measured on its last load 2519 KiB);
        chim_reserve_kib 2048 kept beside both
    zone: 5672 KiB locked (needed now: ring, frame world, buffers), most since the map started 5711 KiB
    zone: largest run without a lock 565 KiB; 2 failed requests, the last 1297472 bytes
    ring: active radius 636, load radius 892 (prefetch 256), look-ahead 256, collision margin 224

- the first line is the zone as a cache: used, free, the largest free block, blocks and locked blocks;
- `Hunk:` is the whole-map rule for this map: the zone, what the map loads after it, the figure the
  frame map states and the one measured on its last load;
- `locked` is what the map cannot do without right now (the ring, the frame world, the buffers); the
  builder's heap model is checked against its peak;
- `largest run without a lock` is the largest model that can still be loaded; `failed requests` also
  counts the frame-world pool's tries for a larger block before it repacks in place, which are
  expected;
- `ring:` gives the radii above for this map and view distance.

`hunk_print` lists the heap's blocks by name with their sizes (`hunk_print all`: every block).
