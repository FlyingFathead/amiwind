# Door graph: every load door and every interior

_Last updated with AmiWind v0.0.48-rc1 (23 October 2026)._

<!-- contents start -->
## Contents

- [Running it](#running-it)
- [The graph (`aw-door-graph-1`)](#the-graph-aw-door-graph-1)
  - [Island and access](#island-and-access)
  - [Hard cases](#hard-cases)
  - [CHIM room limits](#chim-room-limits)
  - [Levitate-only (an approximate rule)](#levitate-only-an-approximate-rule)
- [The batch plan (`aw-batch-plan-1`)](#the-batch-plan-aw-batch-plan-1)
- [Rooms by batch in the builder](#rooms-by-batch-in-the-builder)
- [The interior tracker states](#the-interior-tracker-states)
- [Rooms set aside, and how they come back](#rooms-set-aside-and-how-they-come-back)
  - [Water](#water)
  - [Lava](#lava)
  - [Over the size limit (27)](#over-the-size-limit-27)
  - [Levitate-only (5) and teleport-only (1)](#levitate-only-5-and-teleport-only-1)
  - [No entrance area (16)](#no-entrance-area-16)

<!-- contents end -->

Phase 1 of converting every interior to a CHIM room ([INTERIOR_STORE.md](INTERIOR_STORE.md), the roadmap's
step 3 in [ROADMAP.md](../ROADMAP.md)): `tools/door_graph.py` reads your own masters and writes the door graph,
format `aw-door-graph-1`, and from it the batch plan, format `aw-batch-plan-1`. The CHIM Progress Tracker reads both
for its interior states (`tools/cell_progress_rooms.py`). Both files are made from your game data and stay private:
the tool and this page are public, the data is not.

## Running it

```
python3 tools/door_graph.py graph --data-files DIR --out door-graph.json [--mesh-cache census-meshes.json] [--jobs N]
python3 tools/door_graph.py plan --graph door-graph.json --out batch-plan.json [--md batch-plan.md]
        [--config-dir config] [--chim-rooms chim-rooms-receipt.json] [--batch-rooms 40]
python3 tools/cell_progress.py ingest --out TRACKER --door-graph door-graph.json --batch-plan batch-plan.json
        [--chim-rooms chim-rooms-receipt.json]
python3 tools/door_graph.py room-batches --plan batch-plan.json --graph door-graph.json
        --out config/room-batches.json [--previous config/room-batches.json]
```

The last command writes the public part of the plan, the room list the builder converts by
([Rooms by batch in the builder](#rooms-by-batch-in-the-builder)).

- **Masters:** Morrowind.esm is required. Tribunal.esm and Bloodmoon.esm are read when present; a missing one is a
  warning and the graph is made without its cells and doors (expansions are optional, roadmap step 7). The masters
  are merged in load order as the game merges them: a later master's cell header replaces the earlier one, and a
  reference is keyed by the master that owns it and its index (the high byte of `FRMR` names one of the file's
  masters, 0 the file itself), so an expansion that moves or deletes a door is followed.
- **Every core:** each master is cut into record ranges on record boundaries (only the 16-byte record headers are
  read for that), and every range of every master is parsed side by side on the shared worker pool
  (`build_parallel.ordered_map`, largest first). The results are merged in file order, so the graph is the same for
  any number of workers (a test checks one worker against several).
- **Store sets (optional):** with `--mesh-cache`, every mesh the rooms keep is measured with the asset census
  functions (`tools/asset_census.py scan_meshes`, interior profile; every core; cached by the mesh's SHA-256), and
  each room gets the bytes of its store set and the zone and vertex checks below.

## The graph (`aw-door-graph-1`)

Top level:

| key | content |
| --- | --- |
| `format`, `generator` | `aw-door-graph-1`, `tools/door_graph.py` |
| `masters` | per master read: name, SHA-256, bytes, its own master list |
| `missing_masters` | the expansions that were not found |
| `solstheim_cells` | the box of exterior cells (x min, x max, y min, y max) that counts as Solstheim |
| `limits` | the CHIM room limits used, read from the engine sources (see below) |
| `rules` | the numbers of the approximate rules (Levitate rises, Telvanni share and kit pattern) |
| `timings` | parse and mesh seconds, record ranges, workers |
| `summary` | rooms per master and island, doors per kind, access counts, hard cases per reason |
| `doors` | every live load door (below) |
| `meshes`, `textures`, `mesh_textures` | with `--mesh-cache`: bytes and vertexes per mesh, bytes per texture |
| `rooms` | every interior cell (below), sorted by name |

A door: `kind` (`exterior_to_interior`, `interior_to_interior`, `interior_to_exterior`, `exterior_to_exterior`),
`from` (a room name, or `x,y` of an exterior cell), `ref` (its reference number), `object`, `pos` (where it
stands), `to` (the room, or the exterior cell of its target position), `dest` (where the player arrives),
`dangling` (it names a room no master has) and `levitate` (see the rules).

A room:

| key | content |
| --- | --- |
| `name`, `master`, `modified_by` | the cell name, the master that adds it, later masters that change it |
| `island` | `Vvardenfell`, `Solstheim`, `Mournhold` or `none` (below) |
| `entrance_exterior`, `settlement`, `region` | the exterior cell its shortest door chain starts from, that cell's name and region |
| `access` | `door`, `teleport`, `teleport_only` or `unreachable` (below) |
| `door_in`, `depth` | any load door leads in at all; door steps from the outdoors (0 for a room reached by script) |
| `entrances`, `exits` | the load doors in (`from`, `ref`, `levitate`) and out (`to`, `ref`) |
| `water`, `behaves_exterior` | the water flag and height when the room has water; the cell's "behaves like an exterior" flag |
| `counts`, `placements`, `kept_placements` | references per record type; placements with a mesh; those the interior converter keeps (`mwad.interior.omission_reason`) |
| `actors`, `lights`, `lava`, `telvanni`, `load_doors` | counts, molten placements, the Telvanni test |
| `models`, `unique_meshes` | the meshes the converter keeps; all distinct meshes |
| `store_set` | with `--mesh-cache`: bytes (models and their textures), textures, vertexes, the largest model's vertexes |
| `over_limit` | the CHIM room limits it passes (below) |
| `hard` | the hard-case reasons, in the order of the list below |

### Island and access

Reach is a breadth-first walk over the load doors from every exterior door. A room it finds has access `door`, its
island is the island of the exterior cell the walk started from: Solstheim inside the box of the exterior cells
Bloodmoon.esm adds (one cell of margin), Vvardenfell elsewhere. A room no door chain reaches but that a script or a
dialogue result names in quotes (as `PositionCell` does) is a teleport room: `teleport_only` when no load door leads
into it at all, `teleport` when one does (from another teleport room). A second walk from those rooms gives the rooms
behind them access `teleport`. The island of a teleport room comes from the master that adds the room it was reached
from: Tribunal.esm is Mournhold, Bloodmoon.esm is Solstheim, the base game is `none`. Everything else is
`unreachable`, island `none`.

### Hard cases

A room's `hard` reasons (the batch plan sets it aside, or, for the first two, puts it in the parity batch):

- `unreachable`: no door chain and no script reaches it.
- `teleport_only`: no load door leads into it; a script or dialogue moves the player there.
- `behaves_exterior`: the cell's "behaves like an exterior" flag (sky and weather inside a cell, as Mournhold's
  districts).
- `over_limit`: it passes one of the CHIM room limits (names in `over_limit`).

A room's `notes` (v0.0.48, the maintainer's decisions of 23 October 2026: these rooms are converted like any room):

- `levitate_only`: door chains reach it, but only through a door that needs Levitate (rule below); it is in its
  town's batch and not reachable on foot until the spell exists.
- `water`: the cell's water flag with a water height (the CHIM room carries its water plane).
- `lava`: a placement whose script hurts a standing actor (`tools/lava.py molten_objects`, the same test as the
  exterior lava census). A lava name or texture alone does not count: the lava-rock cave kits use both. The CHIM room
  carries its pools.
- `lava_under_water`: water and lava, a pool's bed reaching the water level (the pools read from the game data as the
  room converter makes them, the numbers in the room's row); the CHIM room carves the pool into the water.
- `zone_over_16mb`: its loaded need is larger than the 16 MB baseline's zone alone (`fits_16mb` false), so it loads
  only with the cache bank of a machine with more Fast RAM (below).

### CHIM room limits

Read from the engine sources each run (`room_limits`), never copied:

| name | limit | from |
| --- | --- | --- |
| `placements` | kept placements over the placed records a room record holds (`h.count > N` in `chim/chim_room.c`), or over the efrag links the room may use (`AW_EFRAG_LIMIT - CHIM_EFRAG_RESERVE`, less the quarter reserve `ChimRoom_Link` keeps; each placement takes at least one) | `chim/chim_room.c`, `client.h`, `chim/chim_local.h` |
| `room_map_entities` | actors, lights and load doors over `MAX_EDICTS` (they are the room map's entities) | `quakedef.h` |
| `zone_bytes` | the room's need (its store set loaded, and its placements) over what the 32 MB minimum machine gives a room: the whole zone (`chim_zone_kib`; a room map has no frame-world pool) less the loading buffer, plus the automatic cache banks, which models and textures prefer | `chim/chim_world.c`, `chim/chim_zone.h`, `aw_heapsize.h`, `sys_amiga.c` |
| `model_block` | one model over the largest single block of that machine (the zone or one cache bank) | the same |
| `model_vertexes` | one model over `MAX_MAP_VERTS` | `bspfile.h` |

Without `--mesh-cache` only the first two are checked. The store set is the asset census estimate at unit scale.
With `--sdk` (the Amiga SDK) it is counted as the engine holds it loaded: each model's faces, planes, texture
mappings, edges and collision as the engine's structures (sizes from the target compiler), each texture as a loaded
texture, each placement as its record and run-time entity (`need_bytes`). Without it, the BSP29 bytes on disk, which
are 17 % under the loaded need. Each room also says whether it fits the 16 MB baseline's zone alone (`fits_16mb`).

The machine is computed with the engine's start-up rules (`engine_limits.fast_ram_memory`: the heap, then the cache
banks of the Fast RAM left) and the Fast RAM the system keeps, measured: 32 MB of Fast RAM gives the 13 MiB heap, 14 MiB
free and one 8 MiB bank (FS-UAE, 23 October 2026); 16 MB gives the 11 MiB heap and no bank. A room then holds
14.7 MiB, one model at most 8 MiB; on 16 MB, 6.7 MiB.

**Measured against built rooms** (23 October 2026, [CHIM-ROOM-ESTIMATE-48](../bugs/CHIM-ROOM-ESTIMATE-48.md)): the
43 rooms of the Balmora CHIM rooms sandbox, each room's need as the image's room heap check reads it from the store
(`chim/heap.py room_map_heap`). The disk bytes were 17 % under it (58.4 MB against 70.3 MB of models and textures);
the loaded estimate is 9 % over it in all (76.9 MB against 70.5 MB of need), the measured need 0.82 to 1.03 times the
estimate per room (Balmora, Temple: 4.10 MB measured in its 7.03 MB zone).

### Levitate-only (an approximate rule)

Telvanni towers have vertical shafts where other houses have stairs. The rule, with its numbers in `rules`:

1. A room is Telvanni when at least 25 % of its interior architecture placements (statics whose mesh name starts
   with `in_`) are from the Telvanni kit (`in_t_`).
2. Outdoors, a door into a Telvanni room needs Levitate when it stands more than 512 units above the lowest outdoor
   door into the same tower complex (rooms joined by interior doors), or more than 3,072 units above the terrain
   under it (Telvanni settlements walk on raised walkways, so the terrain alone cannot tell).
3. Inside a Telvanni room, a door needs Levitate when it stands more than 256 units above every point where the
   player arrives in that room through a door not needing Levitate, the door's own target left out (coming back
   down from a room does not get you up to it). This repeats until no door is added.
4. A room is Levitate-only when door chains reach it but a walk over the doors not needing Levitate does not.

It misses towers whose upper floors are also reached by a walkable outdoor door at a similar height, and it does
not look at stairs or walkways themselves. A room it gets wrong is moved by hand in the plan, not by changing the
graph.

## The batch plan (`aw-batch-plan-1`)

The Vvardenfell rooms and every room of the base game (Morrowind.esm), wherever its door chain starts or when none does
(the maintainer's milestone of 23 October 2026: every base-game interior, the test cells included): the rooms with no
hard case are ready, the others are set aside with their reasons. The ready rooms are grouped and ordered as a
player meets them:

1. towns (the named exterior cell a room's door chain starts from, with at least 4 rooms behind its doors; a lone
   named ruin or tomb goes with its region), towns with rooms in the game today first, then by how many rooms they
   have;
2. the other rooms in the game today (the repo's scene lists, `cell_progress.our_maps`);
3. the rest by region.

Inside a group, rooms go by door depth, then name. A group of more than `--batch-rooms` rooms (40 by default) is
split into even parts; smaller groups of the same kind share a batch, in order, up to that size. Each batch has its
groups, its rooms, how many are in the game, its placements, the models and textures new to the store and the store
growth in bytes (with a measured graph; `null` without), and the store size after it.

**Parity: no room is left out.** After the ready batches comes one final batch of kind `parity` (never split): every
room of the plan that no door reaches (hard reason `unreachable` or `teleport_only`). These rooms are converted like
any other, so they exist in the image and a script or a console command can reach them later. Each keeps its reason as
a state in the batch's `parity` list (room, state, label, reasons), never an exclusion:

| state | label | rule |
| --- | --- | --- |
| `test_cell` | test cell | one of the masters' developer test cells (`door_graph.TEST_CELLS`, listed below) |
| `teleport_only` | teleport only | a script sends the player there; no door leads in |
| `no_entrance` | no entrance, no script | no door leads in and no script or dialogue names it |

The other hard cases (lava at or under the water, size, behaves like an exterior) stay in `aside` with their reasons.
Each batch and the summary count the notes of their rooms (`notes`, `ready_notes`).

**The expansions wait for their land.** `later` has one batch per expansion, named `later: <island>`: every room
outside the Vvardenfell plan, by the island its door chain starts on, else by its master (a room on Solstheim's
exterior that the base game adds goes with Solstheim). Each lists its rooms, how many are ready and set aside, its own
parity rooms with their states, and the reason it waits:

- `later: Mournhold` (Tribunal.esm): Mournhold is reached only by script (Tribunal's teleport), so its rooms wait for
  the scripts step (roadmap step 6).
- `later: Solstheim` (Bloodmoon.esm): Solstheim's exterior is not on CHIM yet; its rooms come in with the island
  (roadmap step 7).

The summary checks the parity: `every_room` (the Vvardenfell plan plus every later batch) equals `graph_rooms`.

## Rooms by batch in the builder

Phase 2 (v0.0.48): the builder converts rooms by batch. EXPERIMENTAL; every batch by default (the maintainer's
decision of 23 October 2026).

**The room list in the repository** (`config/room-batches.json`, format `aw-room-batches-1`). This is the public part of
the batch plan, written by `door_graph.py room-batches`, and the builder's default content input. For each batch it
holds the number, kind and groups. For each room it holds:

- its name, the cell's ID in the game data;
- its order in the batch;
- the exterior cell its door chain starts from (`entrance`, `x,y`);
- the exterior cells with a load door straight into it (`doors_from`);
- its door depth;
- in the parity batch, its state;
- its map name and its id.

The list holds no positions and no other game data. Since 23 October 2026 it holds every room of the base game,
water, lava and Levitate-only rooms and the test cells included: 1,134 rooms in 40 batches. The expansions' later
batches are not in it. The list names a room by `room`, never `cell`: the scene lists' `cell` key means "in the
game today" to the tracker (`cell_progress.our_maps`).

**Map names and save IDs.** A room that a town list or the fixed scene lists already hold keeps that map name and save
ID. Every other room is named `ri` plus the first 10 hex digits of the SHA-256 of its name in lower case
(`room_batches.room_map`), so the name never depends on the list. The engine finds these rooms in its table
(`AW_ROOM_BATCH_*` in `aw_town_table.h`, written by `tools/town_table.py`). Their save IDs start at
`AW_ROOM_BATCH_BASE` (`aw_maps.h`) and come from each room's `id`. An id is given once and never moves: `--previous`
keeps the old list's ids, a new room takes `next_id`, and an id is never reused.

**The option** `--room-batches none|all|N|N-M[,...]`. `all` means every batch of the list, the parity batch included.
Not given, it is `all` (the maintainer's decision of 23 October 2026; `config/option-changes.json`); `none` builds no
batch room. A MiniWind takes batch numbers only, for example `--miniwind-balmora --room-batches 1`; not given, a
MiniWind builds none. Batch rooms are CHIM rooms only: with `--interior-format bsp` the default builds none, and an
explicit selection is refused.

**The stage `chim-room-batches`** (`tools/chim_room_batches.py`) runs after the census and before `chim-interiors`.
One unit per room runs on the shared worker pool, largest first by placed references, through the unit cache
(`interior-room-chim`, [BUILD_CACHE.md](../BUILD_CACHE.md#units)). A room converted once is not converted again while
its inputs are unchanged. The stage opens the unit cache once, restores the cached rooms on its threads, stores each
room the moment it finishes (a stage stopped early keeps them), follows its live share of the build's cores, and in
its tail gives the free cores to the big rooms' scenery geometry (ROOM-BATCH-CORES-49). A unit keeps from today's room
conversion only what a CHIM room needs:

- the scenery export;
- the kept placements (`placements.json`), using the room converter's selection with plants as sprites;
- the plant sprites;
- a shell room map: an empty world with the room's bounds that holds the room's entities (worldspawn, start, sprites);
- a room with water or lava: the water brush and the lava pool brushes in `room.map` (never compiled), their textures
  in the shell's texture lump, the pools' ember and loop entities, and the loop sounds in the unit's own `id1/sound`,
  as the room converter makes them; the CHIM interiors stage makes the room's liquids from them
  ([INTERIOR_STORE.md](INTERIOR_STORE.md#water-and-lava-in-chim-rooms)).

No visual world is compiled: no qbsp, vis or light.

The stage then places every room's residents (`prepare_area.populate`), each resident's bake a unit of the unit cache
(`resident-bake`: its appearance and greeting, the game data, the palette, the level settings, ffmpeg and the code),
so a rerun restores them instead of baking them again. Before any unit runs, the stage checks that every resident NPC
has its grounding class: the policy's, or its reference's in `config/actor_grounding_rooms.json`
([room residents by rule](../NPC_GROUND_CONTACT.md#room-residents-by-rule)). The class says what a resident needs;
the fitting itself happens later, in the image step, once the room's CHIM collision exists
([where a CHIM room's residents are fitted](../NPC_GROUND_CONTACT.md#where-a-chim-rooms-residents-are-fitted-v0048)). It also writes each room's door bank
(`doors-<map>.txt`): every load door with its box from the door's mesh, every target `-`.

A room that another room stage of the same plan converts is left to that stage and listed under `held`, so no room
is converted twice. Those stages are `interior` (Seyda Neen), `balmora-interiors`, `chim-rooms-TOWN` and `town-TOWN`.
The builder works out the held stages after the MiniWind and exclusion filters. A stage the plan dropped holds
nothing.

A room the stage cannot convert is listed with its reason under `refused`, never dropped. Examples: a sectioned room,
water outside the room's bounds, or no placement.

**Doors, both ways** (the image step, `room_batches.link_banks`, after the frame maps are written). In every door bank
of the image, a row whose target is `-` gets its target and arrival in these cases:

- **Into a batch room.** The door leads into a batch room of this build, from the outdoors (a town or CHIM region frame
  bank) or from another room. Its arrival is in the room's own units.
- **Out of a batch room.** The door is a batch room's own door. If it leads into any room the image holds, it is
  linked to that room. If it leads out, the exit goes to the first town frame whose core holds the exit point (the
  engine's handoff rule, `town_interiors.exit_town`), else to the CHIM region frame of the exit's exterior cell, in
  that frame's units.

Arrival positions come from the game data's door records (`mwad.interior.original_doors`), the same records the door
graph and today's town rooms use.

Every other row stays as it is. A door into a listed room that this build does not convert, or an exit to a place it
does not hold, stays inert ("Interior unavailable"). It is listed in the image's `room-batch-links.json`, together with
the link counts per kind.

**Measured** (23 October 2026). The stage commands were run on the MiniWind Balmora run of 22 October with no image
built, capped at 8 cores, while another measurement used the host:

- **Batch 1** (21 Balmora rooms): all 21 are left to `balmora-interiors`, so the stage converts none (0.1 s).
- **Batch 3** (26 rooms of Vivec, St. Olms; their town list names them, Vivec is not in this build): all 26 converted,
  2,265 placements and 51 residents. Rooms 12.5 s on 8 workers, residents 26.5 s, 46.5 s in all, 5.4 cores on
  average.
- **Batch 3 again** on the same inputs: 0 rooms converted, all 26 from the unit cache in 4.6 s, byte-identical
  files. The residents are baked again (26 s, [ROOM-RESIDENTS-NOT-CACHED-48](../bugs/ROOM-RESIDENTS-NOT-CACHED-48.md)).
- **The CHIM interiors stage** with the 43 Balmora rooms and these 26 rooms: 69 rooms, a store of 22.5 MB in one pack
  (642 models, 268 textures). Balmora's rooms alone made 15.2 MB, so the batch adds 7.4 MB (the plan estimated
  5.6 MiB). Its 26 room records take 132 KB. The stage took 15.4 s on 7.6 cores; run again, 3.4 s with every mesh unit
  reused.
- **Door links** (the image's pass, run on the stage output): 38 room-to-room links among the 26 rooms. 90 doors lead
  into rooms this build does not convert, and 18 exits lead to Vivec (cell 4,-12), which this build does not hold. All
  of those stay inert and are listed.
- **Batch 5** (Ald-ruhn, part 1): refused in 4.3 s, before any room ran, because 62 residents in 22 rooms have no
  grounding class ([ROOM-BATCH-NPC-GROUNDING-48](../bugs/ROOM-BATCH-NPC-GROUNDING-48.md)).

**Measured on every batch** (23 October 2026, later the same day, branch v0.0.48-room-grounding; the same MiniWind
Balmora inputs, read only, no image, 6 cores while other work used the host):

- **All 40 batches** (the list of 1,131 rooms then): 1,059 rooms converted, 58 Balmora and Seyda Neen rooms left to
  their stages, 14 refused (water under or over everything the room places; fixed,
  [ROOM-BATCH-WATER-OUTSIDE-48](../bugs/ROOM-BATCH-WATER-OUTSIDE-48.md), the 11 batches with a refusal then ran again
  with no refusal). No batch is refused for grounding any more (Ald-ruhn's first batch converts its 28 rooms). In
  all 46 minutes of stage time on 4.5 of 6 cores on average: 44 to 114 s a batch, a third to a half of it the
  residents.
- **Batch 3 twice** on the final code: 54.6 s, then 20.0 s with every room and all 49 residents from the unit cache
  and byte-identical files ([ROOM-RESIDENTS-NOT-CACHED-48](../bugs/ROOM-RESIDENTS-NOT-CACHED-48.md)).
- **The CHIM interiors stage** over Balmora's 43 rooms and 1,049 batch rooms (1,092 rooms; batch 3's 27 left out of
  this run by a script slip): a store of 334.0 MB in 5 packs (5,390 models, 886 textures). Balmora's 43 rooms with
  batches 3 to 8 (196 rooms) made 87.1 MB. The first run took 8 min on 6 cores; with the unit cache filled, 74 s.
  One room was not made, Akulakhan's Chamber (a model's collision over the clipnode budget,
  [CHIM-ROOM-CLIPNODE-BUDGET-48](../bugs/CHIM-ROOM-CLIPNODE-BUDGET-48.md); fixed later the same day: its cave shell is
  stored as 78 tiles, batch 19 makes all 35 rooms and the room's doors are live); before the fix that one room failed the
  whole stage ([CHIM-ROOM-FAIL-STAGE-48](../bugs/CHIM-ROOM-FAIL-STAGE-48.md)). One more was kept as a room map
  because its folder came from the first run (Gnaar Mok, Caryarel's Shack: water over the room; the final code makes
  it).

The store lives on the disk; a room loads its own set only (the 32 MB room limit above).

**To check in the game:** entering and leaving a batch room through every door kind. Not yet built into an image:
see the bug register.

## The interior tracker states

`tools/cell_progress_rooms.py`, additive to the exterior tracker (the exterior buckets and the World map legend do
not change). Every room of the graph gets a row, keyed by its cell name (the cell's ID in the game data), and one
state, the first that matches. The states fall into the three groups of the World map legend:

| group | state | meaning |
| --- | --- | --- |
| in the game | `on_chim_rooms` | on a CHIM room: a build's `chim-interiors.json` installed it, or a CHIM rooms receipt names a room that is in the game |
| in the game | `room_map` | in the game as today's room map |
| not in the game yet | `converted` | a CHIM room record was made for it, not in the game yet |
| not in the game yet | `not_started` | everything else |
| set aside, with a reason | `test_cell` | no door reaches it; a developers' test cell |
| set aside, with a reason | `teleport_only` | no door reaches it; a script sends the player there |
| set aside, with a reason | `no_entrance` | no door reaches it and no script names it |
| set aside, with a reason | `hard_case` | set aside by the graph for another reason (lava at or under the water, size, behaves like an exterior) |

Each row also has `notes` (water, lava, Levitate-only, over the 16 MiB zone): those rooms are not set aside. A graph
made before v0.0.48 that still lists water, lava or Levitate-only as hard reasons is read the same way.

`--chim-rooms` takes a CHIM rooms receipt (`chim-rooms-receipt.json`, format `aw-chim-rooms-1`: records made) or a
build's `chim-interiors.json` (the rooms its image installed, named by our map name); it can be given more than once.

`cell-progress.json` gets `interior_rooms`: the states, their labels and the three `groups`; `headline` (per island:
the count of each state, the total, the count per group and the set-aside reasons; the rooms with no entrance area
are the island `none`); `totals` (every island); `later` (the expansions' later batches and why they wait); and a
row per room: `id` (the cell name), master, island, state, label, group, reasons (the graph's hard reasons, kept in
every state), batch (a number for a Vvardenfell batch, the parity batch included; `later: <island>` for an
expansion; `null` for a room set aside), access, entrance (the exterior cell `x,y` its door chain starts from),
settlement, region, `on_chim_rooms` and our map name. Every interior record of the tracker that the graph knows also
gets a `room` key. Tracker data without `interior_rooms` (older files) still loads: the World map hides the interior
tracker and the Interiors layer falls back to its older colouring.

## Rooms set aside, and how they come back

Measured on 23 October 2026 from the door graph (first on 22 October). The aim is full parity with the original game:
a room set aside is a room that waits, with a named state in the interior tracker, never a room dropped.

**Totals.** 1,328 interiors: Morrowind 1,134, Tribunal 96, Bloodmoon 98. By island: Vvardenfell 1,123, Solstheim 96,
Mournhold 93, no entrance area 16. There are 3,619 load doors, none pointing at a missing room. The plan holds 1,134
rooms, every one of the base game: 1,126 are ready, in 39 batches (towns with rooms in the game first, then other
towns, then the rest by region), and the 8 rooms no door reaches follow in the final parity batch (batch 40); about
230 MiB of shared store by the last batch (an estimate from the asset census). All 1,134 of the base game's rooms
are in a batch; none is set aside, and no room is over a limit of the 32 MB minimum. Among the ready rooms: 190 with
water, 56 with lava (3 of them with a pool reaching under the water), 5 Levitate-only and 51 that need more than the
16 MB zone alone (they load on 32 MB). The expansions' rooms are in their later batches: Mournhold 96, Solstheim 98
(three base-game rooms whose door chain starts on Solstheim's exterior, two shipwreck levels and Yasammidan's
shrine, are in the Vvardenfell plan now); all 1,328 rooms are in the plan. First measured result: the 43 Balmora
rooms of the MiniWind sandbox take 15.9 MB on the CHIM room store, against 84.9 MB as room maps.

**Lava under the water** (note `lava_under_water`; set aside until 23 October 2026, now converted: the CHIM room
carves each pool's prism on both sides of the water plane, lava inside the prism and water around it,
[CHIM-ROOM-LAVA-UNDER-WATER-48](../bugs/CHIM-ROOM-LAVA-UNDER-WATER-48.md); numbers in Quake units):

| room | pools | loaded need (bytes) |
| --- | --- | ---: |
| Forgotten Vaults of Anudnabia, Forge of Hilbongard | 1 of 1 pools reach -376.00, water -375.00 | 4,766,460 |
| Indoranyon | 19 of 19 pools reach -204.00, water -200.00 | 6,936,616 |
| Subdun | 1 of 2 pools reach -23.52, water -16.25 | 7,809,572 |

To check in the game: swimming next to the lava, and the lava's damage under the water.

Before v0.0.48 the plan also set aside the water rooms (191), the lava rooms (59), the rooms over the 16 MiB zone
(27) and the Levitate-only rooms (5); by the maintainer's decisions of 23 October 2026 they are converted like any room
and keep a note. The 7 unreachable rooms and the 1 teleport-only room of the base game are the parity batch (below).

### Water

Every interior cell record carries its water height (the cell's water flag and height), the same number the original
game uses: a flat plane across the whole room. Compared with the room's door heights:

- 67 rooms have water at door level (you walk into it);
- 31 are flooded above the doors (you enter under water);
- 72 have it 200 to 1,000 units below the doors;
- 21 have it more than 1,000 units below every door.

Door heights are not floors, so the last two groups are "probably out of sight", not proven.

**How they come back.** A CHIM room map is already a small world (an empty box with six clip walls). It gets the same
water plane, at the room's water height, that a CHIM exterior chunk already carries (the `*water` texture surface and
water contents, the terrain of a chunk in [WORLD_FORMAT.md](WORLD_FORMAT.md)). The room's own walls and floors from
the store draw over it. Done in the builder on 22 October 2026
([CHIM-ROOMS-WATER-LAVA-48](../bugs/CHIM-ROOMS-WATER-LAVA-48.md)): the 13 water rooms of the Vivec rooms stage that
stayed room maps now convert; how and the numbers are in
[INTERIOR_STORE.md](INTERIOR_STORE.md#water-and-lava-in-chim-rooms).

**To check in the game (open):** swimming and surfacing against store collision, and entering a flooded room.

### Lava

Lava is not one line per room. It is placed molten objects: surface meshes whose script hurts a standing actor, the
same rule as the exterior lava census (`tools/lava.py`). Each pool's height and extent come from its own placement,
so a room with pools at different heights gets each one right. A lava name or texture alone does not count (the
lava-rock cave kits use both).

**How they come back.** Each pool keeps what today's room map has: its liquid prism (Quake lava contents, the damage
rule of every lava in the game) with the `*lava` warp face, and its solid bed; the ember and sound entities come over
unchanged. Done in the builder on 22 October 2026; the first CHIM rooms left water and lava rooms out only to keep the
first comparison simple. A pool whose bed reaches under the water level is carved into the water too (lava inside its
prism, water around it; 23 October 2026, three rooms, above).

**To check in the game (open):** standing in lava (damage) and on its bed, and the lava drawn against the store's
floors.

### Over the size limit (27)

Set aside on 22 October 2026 because the room's own set of models and textures was estimated larger than the zone
budget for one room (5.95 MiB). Both figures were wrong ([CHIM-ROOM-ESTIMATE-48](../bugs/CHIM-ROOM-ESTIMATE-48.md)):
the budget was a frame map's at 16 MB (a room has the whole zone, and on the 32 MB minimum the 8 MiB cache bank too),
and the bytes were the disk bytes, 17 % under what the engine loads. Counted again (above, "CHIM room limits"), **all
27 fit the 32 MB minimum** and none is over a limit:

| room | estimate on disk (old) | loaded need (new) | 16 MB zone alone |
| --- | ---: | ---: | --- |
| Assemanu | 8,669,108 | 10,696,724 | over |
| Akulakhan's Chamber | 8,642,412 | 10,695,472 | over |
| Ashalmimilkala, Shrine | 8,044,068 | 10,066,592 | over |
| Yanemus Mine | 7,839,396 | 9,783,152 | over |
| Ald-ruhn, Manor District | 7,739,344 | 9,709,908 | over |
| Ularradallaku, Shrine | 7,441,300 | 9,294,088 | over |
| Abanabi | 7,355,980 | 9,219,920 | over |
| Kumarahaz | 7,404,064 | 9,218,504 | over |
| Sargon | 7,332,956 | 9,073,952 | over |
| Ashurnibibi, Shrine | 7,192,740 | 9,065,028 | over |
| Dun-Ahhe | 7,072,652 | 8,883,996 | over |
| Ashalmawia, Shrine | 7,046,600 | 8,875,844 | over |
| Assarnud | 6,997,408 | 8,827,384 | over |
| Punammu | 6,895,836 | 8,594,344 | over |
| Kushtashpi, Shrine | 6,851,988 | 8,591,596 | over |
| Kogoruhn, Charma's Breath | 6,883,068 | 8,502,840 | over |
| Ibar-Dad | 6,675,376 | 8,458,000 | over |
| Missamsi | 6,785,376 | 8,457,052 | over |
| Corprusarium | 6,714,032 | 8,454,500 | over |
| Ashinabi | 6,789,244 | 8,438,376 | over |
| Bensamsi | 6,744,316 | 8,428,768 | over |
| Elith-Pal Mine | 6,668,120 | 8,289,108 | over |
| Berandas, Underground | 6,569,956 | 8,236,036 | over |
| Mamaea, Sanctum of Awakening | 6,533,908 | 8,085,592 | over |
| Maran-Adon | 6,289,240 | 7,816,848 | over |
| Subdun | 6,291,696 | 7,809,572 | over |
| Sud | 6,273,784 | 7,803,884 | over |

Bytes; the 32 MB room holds 15,384,576. Of all 1,328 rooms, 72 need more than the 16 MB zone alone: they load on the
32 MB minimum, not on the 16 MB baseline or with Options > Extra RAM off. One room is close to the one-block limit:
Akulakhan's Chamber's cave shell is one model of about 7.6 MiB (estimated), which only the 8 MiB bank can hold; two
thirds of it is collision. What to watch and what comes next: [INTERIOR_SECTIONS.md](../INTERIOR_SECTIONS.md#what-worked-for-the-27-rooms-over-the-size-limit-23-october-2026).
Since 23 October 2026 they are in the batches like any room; a room over the 16 MB zone alone has the note
`zone_over_16mb` (`fits_16mb` false).

### Levitate-only (5) and teleport-only (1)

- Sadrith Mora, Tel Naga Upper Hall
- Tel Aruhn, Tower Living Quarters
- Tel Branora, Upper Tower
- Tel Branora, Upper Tower: Therana's Chamber
- Tel Mora, Tower Services

This is an approximate rule over Telvanni rooms by door height (see above), and documented as approximate. Since
23 October 2026 (decided for the project) these rooms are converted in their town's batch, with the note
`levitate_only`: not reachable on foot until the Levitate spell
exists (the scripts step, roadmap step 6). Teleport-only: Magas Volar, reached by script; it is converted in the
parity batch with the state "teleport only", and the scripts step gives it its way in.

### No entrance area (16)

Rooms with island `none`: no exterior door chain reaches them. Each one is tracked by its cell ID, not dropped, and
converted like any room: the base game's 8 in the parity batch (batch 40), the expansions' 8 in their master's later
batch. Each has its own state in the interior tracker, and rooms the original game reaches through a quest get their
way in with the scripts.

| room | state | batch |
| --- | --- | --- |
| Character Stuff Wonderland | test cell | 40 |
| Clutter Warehouse - Everything Must Go! | test cell | 40 |
| ken's test hole | test cell | 40 |
| Mark's Vampire Test Cell | test cell | 40 |
| Redoran interior | test cell | 40 |
| Redoran interior2 | test cell | 40 |
| ToddTest | test cell | 40 |
| Magas Volar | teleport only | 40 |
| Draugr Test | test cell | later: Solstheim |
| Mark's Script Testing Cell | test cell | later: Solstheim |
| Solstheim | no entrance, no script | later: Solstheim |
| Vor Lair, Chambers of Alta Vor | no entrance, no script | later: Solstheim |
| Vor Lair, Interior | no entrance, no script | later: Solstheim |
| Mournhold Temple | no entrance, no script | later: Mournhold |
| Mournhold, Royal Palace | no entrance, no script | later: Mournhold |
| Pelagiad, Ignatius Flaccus' House | no entrance, no script | later: Mournhold |

Three more rooms are teleport-only on an island (a script is their only way in) and are in their master's later batch
with the state "teleport only": two on Mournhold and one on Solstheim.

**Test and developer cells that no door reaches:**

- Character Stuff Wonderland
- Clutter Warehouse - Everything Must Go!
- Draugr Test
- Mark's Script Testing Cell
- Mark's Vampire Test Cell
- Redoran interior
- Redoran interior2
- ToddTest
- ken's test hole

**Reached only by script in the original game:** Magas Volar.

**Expansion cells with no load door** (to check: each one's quest or script role before calling it unused):

- Mournhold Temple
- Mournhold, Royal Palace
- Pelagiad, Ignatius Flaccus' House
- Solstheim
- Vor Lair, Chambers of Alta Vor
- Vor Lair, Interior

What the graph shows about them, and nothing more: no load door in the base game or the expansions leads into any of
these six. Pelagiad, Ignatius Flaccus' House has two doors that lead out to the exterior but none leading in.
Vor Lair, Chambers of Alta Vor and Vor Lair, Interior hold no placed objects at all. Mournhold, Royal Palace holds
one actor and no placed objects. What each is for in the game is to check.

A cell without a door can still be reached by a script (the intro prison ship is one), so on 22 October 2026 the
scripts and dialogue of all three masters were searched for each of these names, as an exact cell name: in a script
command (`PositionCell`, `COC`, `AiTravel`, `GetPCCell` and similar) or in a dialogue line's cell condition.

- Magas Volar: one script sends the player there with `PositionCell` (the teleport-only room above).
- Mournhold Temple and Mournhold, Royal Palace: no script sends the player there. Their names appear only as
  dialogue cell conditions (7 and 2 lines). The original game matches a cell condition by the start of the cell's
  name, so those lines belong to the real rooms whose names start that way ("Mournhold Temple: ...",
  "Mournhold, Royal Palace: ...").
- Pelagiad, Ignatius Flaccus' House, Solstheim, Vor Lair, Chambers of Alta Vor and Vor Lair, Interior: no script
  and no dialogue line names them.

So no quest reaches these six by name. They stay on the tracker under their own state ("no entrance, no script")
rather than being dropped. A script could still reach one of them some other way, for example by moving an object
or an actor there, so this stays open until the scripts step (roadmap step 6) reads every script in full.
