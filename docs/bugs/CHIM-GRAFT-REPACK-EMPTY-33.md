# CHIM-GRAFT-REPACK-EMPTY-33: A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33 |
| Where | CHIM frame world (engine chim_graft.c Repack), Seyda Neen town square on CHIM |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | high: The ground and every building vanish and the player falls through the world in the starting town. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33 final3 |
| From commit | source 4b26ffc, engine 4b26ffc, CHIM world 4b26ffc |
| CHIM engine version | CHIM 0.1.0, engine 4b26ffc, world format 0.5 |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Safety net: the terrain floor (second layer)](#safety-net-the-terrain-floor-second-layer)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Fixed in source on v0.0.33-fix-terrain-fall, not yet in a build. Found by the owner in the v0.0.33
final3 image (source 4b26ffc), Seyda Neen on CHIM.

## Symptom

Owner playtest of v0.0.33 final3, Seyda Neen town square on CHIM, 9 October 2026. Walking from
Fargoth between the two buildings towards the silt strider, or north-east past the guard towards the
bridge to the mainland (with or without `dbg aw hors 0`), the ground and every building vanish: only
the sky and the NPC sprites are left, and the player falls under the world without end. The console
repeats lines such as:

    CHIM: frame world repacked (planes full): 0 chunks, 768 KiB block
    CHIM: frame world repacked (marks full): 0 chunks, 768 KiB block
    CHIM: frame world repacked (nodes full): 0 chunks, 768 KiB block

| Global position | Local position | What was seen |
| --- | --- | --- |
| -11545 -70162 302 | -70 379 75 | the spot before it breaks (world intact) |
| -10407 -71343 282 | 214 84 70 | world gone, player still on ground height |
| -9521 -70863 1148 | 435 204 287 | world gone, NPCs floating in the sky |
| -9354 -64533 -47208 | 477 1786 -11802 | the player far below the world |

## Where

The engine's CHIM frame world (engine/aga/src/chim/chim_graft.c, Repack): the active chunks'
terrain grafted into the map's world model, in one block of the CHIM zone (768 KiB in final3:
the reserve laid out at map start, twice chim_pool_kib).

## How it happened

The incremental frame world copies each chunk that joins the ring into free ranges of its arrays
(nodes, leaves, marks, surfaces, edges, planes, clipnodes ...). When one array has no free range
for a joining chunk, Update calls Repack ("<array> full"). Repack sizes a block for the whole
desired ring. In the Seyda Neen town square the ring needs more than the 768 KiB block, and the zone
had no free run for a block twice the need. Repack then let the old block go first (let_go),
asked for a block of the exact need (also no room), took a block of the old size back and, marked
empty, laid out only the grid: 0 chunks. The ground (render and collision) left with them; the next
tick tried again with the same result. "No room for the frame world" is said once per run of
failures, so the console showed only the repack lines.

No data hole: a downward trace over the whole final3 Seyda Neen frame (28,224 points at 32 units,
standing and point hull, chunk terrain and placements) finds floor everywhere, at every owner pose.

## Why it was not caught

The engine tests covered a zone too small for the models (CHIM-CHUNK-LOAD-FAIL-33) and a block too
small at map start (slots), not a ring that outgrows its block while the zone has no free run for a
larger one. The zone walk gate replays the Balmora walk, not the Seyda Neen town square.

## Reproduction

In the final3 image: Seyda Neen, walk from Fargoth between the two buildings towards the silt
strider, or past the guard north-east towards the bridge. Engine test: tests/aga_chim_world_test.c
"trim" with CHIM_FIRST_METHOD (chim_graft_trim 0): a ring that grows from the frame's corner to its
centre in a fragmented zone ends with ticks of 0 chunks.

## Repair

Repack never lets the old block go before a new one is secured: when no larger block can be had
and the whole ring does not fit the old one, it keeps the old block and lays out the nearest
chunks that fit it (the largest squared-distance cap, by bisection on the layout); the rest wait.
Chunks beyond the cap do not trigger further repacks; once every desired chunk is within reach or
the zone has room for the whole ring's block again, the ring is laid out whole. The repair is in
Repack itself, so it holds for every array that can trigger it (marks, nodes, planes, surfaces,
edges, clipnodes, the graft table and the grid reserve). It says once "frame world holds the nearest
N of M chunks". The first method stays selectable: `chim_graft_trim 0`.

## Verification

tests/test_chim_engine_native.py, test_a_ring_outgrowing_its_block_in_a_full_zone_keeps_the_nearest_ground:
a 16 KiB pool and a zone fragmented into 24 KiB runs while the ring grows from the frame's corner to
its centre: 23 trimmed repacks, never fewer than 28 chunks, no tick with 0 chunks, no step with a
hole under the player, the standing box lands on the ground under the player, and with room again
the whole ring is grafted. The first method still ends with ticks of 0 chunks. All 38 CHIM engine
native tests pass.

## Prevention

The engine test above, and a second layer below the frame world: the terrain floor (next section).

## Safety net: the terrain floor (second layer)

Owner rule: with noclip off, the terrain height is the lowest height. Whatever the frame world holds,
no walking body may fall below the terrain at its X/Y.

- Data: the frame's far terrain layer (`maps/<frame map>.far`, CHIM-FAR-TERRAIN-33), read once at
  map start into the low Hunk and resident for the whole map. It is never streamed, so it is still
  there when the frame world has 0 chunks. Its samples are the chunk terrain's own (one every 128
  local units, exact LAND heights, the water level where the ground lies below it), so no new data
  is written. Under water, where the layer keeps the water surface and not the bed, the lowest
  terrain point of the chunk (the frame's chunk table, also resident) stands in for it.
- Quake mechanism: the server's movement, not the renderer or the BSP. `AW_TerrainFloor`
  (`aw_walk.c`) runs after the player's walk move (`SV_Physics_Client`, `MOVETYPE_WALK`, through
  `AW_WalkPlayer`) and after a free fall of a `MOVETYPE_STEP` body (`SV_Physics_Step`): one lookup
  per body per frame, four samples, plain arithmetic on the 68040 FPU (no unimplemented
  instructions; the engine build's FPU check passes). Noclip and flight never reach it.
- Rule: a body whose feet are below the lowest height (the quad's lowest sample less 64 units on
  land, the chunk's lowest terrain point less 64 under water), with nothing of the world below it,
  is lifted onto the ground surface (the chunk terrain's tile triangles through the samples) with
  one console line: `Terrain floor: the player N units below the ground at X Y, lifted onto it`.
  The player is then held on that surface while the world has no ground under it (it can walk,
  turn and jump; no fall-and-lift loop, no further lines); the world's own ground or water ends the
  hold. The world's own ground always wins, however low, so normal walking does not change.
- Switch: `chim_terrain_floor` (default 1); 0 is the previous behaviour, kept for A/B. Applied
  object stamps (`chim_far_objects` 1, experimental) turn it off, as the heights then hold object
  tops. Legacy maps have no far layer and are unchanged.
- Tests: tests/test_chim_far.py (the floor against the tile triangles at about a thousand points,
  land and water, chunk and frame lowest; nothing outside the layer, when off, on a legacy map,
  with stamps or after the map; hook and console line contract) and tests/aga_walk_test.c (a world
  emptied under a standing player: one line, lifted, held, walks uphill, jumps; the world coming
  back ends the hold; the world's ground 100 units below the layer's is never lifted from; noclip
  and flight pass below; an actor's trial step never uses it; a free-falling body is lifted; with
  the floor off the fall has no end; walking, a cliff and a jump are unchanged with it on).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec

<!-- END GENERATED CATEGORY -->
