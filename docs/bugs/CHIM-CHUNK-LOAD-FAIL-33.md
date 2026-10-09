# CHIM-CHUNK-LOAD-FAIL-33: Balmora chunks fail to load on CHIM, never recover, and leave holes without ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM chunk loader and zone (chim_chunks.c, chim_zone.c), Balmora CHIM world |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Whole areas of Balmora are missing and the player falls through the ground. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the CHIM world receipt records no commit: world built 8 October 2026 17:54 +03:00 on the v0.0.33-chim-format branch before 8caf66e (CHIM-RECEIPT-COMMIT-33) |
| Build note | first seen in a development emulator session of the same Balmora world on 8 October 2026 (a3ef932); the owner saw it in CHIM Preview 1 on 9 October 2026 |

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
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Open; cause measured, repaired in source on v0.0.33-chim-chunkload (see Repair), not yet in a build. Present in the private CHIM preview (the v0.0.32
disks with the CHIM engine of v0.0.33-chim-engine 0d8bf4f and a format 0.4 Balmora world) and in the
v0.0.33-dev engine source up to the repair.

CHIM area: streaming. Build: "CHIM Preview 1", engine commit 0d8bf4f, world format 0.4, base source
0f467e4, world builder commit unknown (the preview receipt records no builder commit,
CHIM-RECEIPT-COMMIT-33).

## Symptom

Owner playtest of the private CHIM preview, Balmora on CHIM, 9 October 2026. The console repeats
"CHIM: chunk N not loaded (zone full or bad data); retrying" and the chunks never arrive:

| Global position | Chunks named | What was seen |
| --- | --- | --- |
| -20081 -18113 272 | 89, 59, 60 | bridge area; message only |
| -23807 -15931 570 | 92, 106, 102 | message; buildings missing |
| -25296 -12545 1026 | 272, 274, 278, 277 | a whole area missing, flat fog and sky colour where buildings and ground should be |
| -24721 -11329 -1378 | 252 | the player fell through the ground |
| -22906 -14199 951 | 92, 87, 91, 98 | ground missing between buildings; an actor standing over the void |
| -18541 -13591 362 | 287, 86, 90 | message; a few minutes into play, failures all over Balmora |

## Where

CHIM engine: `chim/chim_chunks.c` (ring scheduler: activation, `Failed`), `chim/chim_zone.c` (the
non-moving zone allocator), `chim/chim_models.c` (model blocks). Builder: `tools/chim/heap.py` (the
heap gate's model of the ring). The world data is not affected (see below).

## How it happened

Measured in FS-UAE on fresh copies of the preview's disks, at the owner's poses in his order (the same
chunk numbers fail at the same poses: 92 and 102 at -23807 -15931), and with the map reloaded before
each pose:

1. Not bad data. Every chunk, model and texture record of the world reads back with its size and CRC
   (the builder's `chim.validate.load_world`), and every failure was an allocation that found no room:
   the decode bound was computed, the zone refused the block.
2. The zone is full of locked data. At -23807 -15931 the zone (6,864 KiB, one bank, never moved) held
   6,111 KiB locked with the map reloaded just before (5,573 KiB after the route); 1,181 KiB were free
   but the largest free piece was 211 KiB, while the house models the ring needs decode to
   258,336 bytes (`ex_hlaalu_b_11`) and 291,728 bytes (`ex_hlaalu_b_24`); the silt strider is
   477,568 bytes. A block that does not fit evicts every unlocked block and still fails, because the
   locked blocks split every gap.
3. Chunks stay locked out to the load radius. A chunk is activated (catalogue, terrain and models
   locked) within the active radius (636 units: view 540 + hysteresis 96) but released only past the
   load radius (892: + prefetch 256). The heap gate counts the active ring at one position: at most
   6,239,776 bytes against 6,242,304 for Balmora (2,528 bytes of headroom, nothing for fragmentation);
   counting everything a moving player can hold locked (the load radius), 661 of 9,216 positions are
   over the budget, peak 7,661,472 bytes; at the owner's poses 5.6-7.5 MB.
4. The ground waits for every building. A chunk is activated, and its terrain joins the frame world,
   only when all models its placements use are resident. One house model without room keeps the ground
   of its chunk out: a hole, and with no collision there the player falls.
5. It never recovers. A failed chunk waits 50 ticks and tries again, but nothing it can do unlocks
   anything; while the player stands still the same request fails forever. The route run also shows the
   cache thrashing at the last pose (964 model loads at one pose).
6. Failures grow with play. With the map reloaded before each pose only the two densest poses fail
   (-23807 -15931 and -22906 -14199: 28 failed loads); along the route the same disks fail at four of
   seven poses (152 failed loads), because locked blocks left by earlier rings split the zone further.

The two far views without a message (-17541 -15916, looking west) are not failures: that ground is
past the view distance and the active radius; nothing draws it in a CHIM frame (there is no resident
far terrain layer).

## Why it was not caught

The heap gate sums one position's active ring and so cannot see fragmentation in a zone that never
moves a block, nor the hysteresis band out to the load radius. Emulator runs before the preview walked
straight lines through the town centre with an earlier zone size; none visited the dense west and
south-west streets, and the preview's memory defaults were not run in the emulator before release.

## Reproduction

Fresh copies of the preview disks; `dbg tp -21800 -12300` into Balmora; `chim_tp` to -20081 -18113,
then -23807 -15931; `chim` shows "N failed" and the console the failing chunks 92 and 102 (model 165,
197,620 bytes on disk, 258 KB decoded).

## Repair

In source on v0.0.33-chim-chunkload (CHIM engine; each method selectable, 0 being the first method,
documented in `docs/chim/ENGINE.md`, "When the zone is full"):

- A loading chunk keeps what it has (`chim_release 1`): while a chunk within the active radius loads its
  terrain or a model, its catalogue, terrain and resident models are locked. The first method could
  evict them to make room for the next model, and a chunk whose models did not fit together loaded them
  in turn for ever (the cache thrash: about a million model loads over the owner's route in the
  simulation, 964 at one pose in FS-UAE).
- Nearer chunks win (`chim_release 1`): a chunk within the active radius that finds no room releases the
  active chunk farthest from the player that is farther than itself and outside the collision margin
  (the hysteresis band past the active radius first) and tries again. A released chunk is not activated
  again for 50 ticks unless the player comes within the collision margin of it; every release lets the
  waiting chunks try again at once; a chunk without ground within the collision margin that failed
  tries again on the next tick instead of after 50.
- The ground never waits for a building (`chim_partial 1`): a chunk whose model has no room is activated
  without it; its ground, collision and other placements are there, and the model follows when there is
  room (a reach copy draws the placement meanwhile when another chunk holds the model).
- Small blocks from the zone's high end (`chim_zone_ends 64`): blocks under 64 KiB (textures, catalogues,
  terrain, small models) come from the top of the zone, larger ones first fit from the bottom, as
  Quake's Hunk keeps a low and a high end; the zone map at the first failure showed 2 KB textures locked
  by cached models scattered through the whole zone (2.5 MB free, largest piece 187 KB).
- The failure line says which part failed and why (`zone full (model 165, 236576 bytes; largest free
  187280, free 2522208, locked 4489968 of 7028736)` or `bad data in ...`), once per chunk and 50 ticks;
  the first one of a map prints the zone's layout; `chim` reports the largest run without a lock, the
  failures by reason, releases and partial activations.

Tried and measured worse, not kept: eviction of the cheapest run of unlocked blocks (thrash: 1.3 million
model loads on the sweep) and least-recently-used eviction restricted to such runs (more failures than
evicting all unlocked blocks, which leaves the most contiguous room).

A larger zone helps further (simulated over the owner's route with all methods on: 30 loads without room
at 6,864 KiB, 14 at 7,680 KiB); the budget stays CHIM-ZONE-BUDGET-33's owner decision.

## Verification

The engine's own zone allocator over walks (simulation, `tools/chim/zone_sim.py`, Balmora world, target
ABI block sizes; holes = steps with a chunk within the collision margin without its ground):

| Methods | Owner's route twice (1,192 steps) | Sweep of the frame (6,111 steps) | Teleports to the poses x3 |
| --- | --- | --- | --- |
| first methods (preview, dev1 engine) | 701 failed, 860 holes, 1,010,584 model loads | 382 failed, 231 holes | 70 failed, 180 holes |
| all methods, zone_ends 0 | 52 failed, 0 holes, 1,105 model loads | 42 failed, 0 holes | 16 failed, 0 holes |
| all methods, zone_ends 64 (default) | 30 failed, 0 holes, 997 model loads | 34 failed, 0 holes | 14 failed, 0 holes |

Seyda Neen (CHIM world seyda-009, format 0.5; its ring also overflows the zone at the load radius:
6,417,728 bytes against 6,242,304 at 29 positions), sweeps of the frame with rows 256 and 128 units apart:
first methods 28 and 107 holes (45 and 178 failed loads); all methods 0 and 0 holes (16 and 44 failed
loads, 11 and 31 partial activations).

FS-UAE, fresh copies of the same disks (v0.0.32 release image plus the format 0.4 Balmora world), the
owner's poses in order, twice, with a short walk at each; the engine's nearest chunk without ground
(collision margin 224 units):

| Engine | Nearest chunk without ground, worst | Failed load attempts | Data read | Notes |
| --- | --- | --- | --- | --- |
| A0 preview (0d8bf4f) | 69 units, inside the collision margin at 5 poses | 180 | 24.8 MB | |
| B2 v0.0.33-dev1 (f95cf75) | 94 units, same poses | 152 | 24.7 MB | 1,124 streamed model loads; stopped answering after 11 of 14 poses |
| C2 repair, chim_zone_ends 0 | 229 units | 137 | 20.1 MB | 12 loads left without room, 44 chunks released inside the ring |
| D2 repair, all defaults | 438 units | 95 | 16.7 MB | 11 loads left without room (7 partial activations), 25 released inside the ring, 0 bad data |

An earlier run of the preview engine over the route three times stopped answering at the seventh pose
(the game froze with the cache thrashing: a chunk within the collision margin loads past the frame's
budget, and its models evicted each other). No run of the repaired engine froze. No run printed a texture
fallback ("drawn untextured") or bad data.

Remaining: the owner's playtest of a build with the repaired engine.

## Prevention

- The builder's zone walk gate (`tools/chim/zone_sim.py`, run by `chim_build.py --validate` after the
  heap gate): the engine's `chim_zone.c` built for the host, driven by the ring rules of `chim_chunks.c`
  with the engine's defaults (read from the engine source through `tools/engine_limits.py`), over a walk
  through every frame; it fails when a step leaves the player without ground or a chunk fails for bad
  data, and reports loads without room, releases, partial activations and loads.
- Host tests: `fullzone` (a starved zone: no hole under the player, partial activation, the model arrives
  when there is room, no thrash; the first methods leave the hole) in `tests/aga_chim_world_test.c`; the
  zone's failure count, largest unlocked run and layout in `tests/aga_chim_zone_test.c`;
  `tests/test_chim_zone_sim.py`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
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

Related bugs in other categories:

- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner

<!-- END GENERATED CATEGORY -->
