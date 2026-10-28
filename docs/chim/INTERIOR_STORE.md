# Interiors on CHIM: CHIM rooms on a shared store

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [Why](#why)
  - [Why not cut today's rooms into a store](#why-not-cut-todays-rooms-into-a-store)
- [Measured so far (22 October 2026)](#measured-so-far-22-october-2026)
- [What it must keep](#what-it-must-keep)
- [The design](#the-design)
- [Formats](#formats)
  - [Placement light level (world format 0.12)](#placement-light-level-world-format-012)
  - [The interior store](#the-interior-store)
  - [The room record](#the-room-record)
  - [The room map's keys](#the-room-maps-keys)
- [Engine changes](#engine-changes)
- [Builder changes](#builder-changes)
- [The A/B](#the-ab)
- [Rooms set aside, and how they come back](#rooms-set-aside-and-how-they-come-back)
  - [Water and lava in CHIM rooms](#water-and-lava-in-chim-rooms)
- [When a room is hard: the method](#when-a-room-is-hard-the-method)

<!-- contents end -->

Status: being built on the v0.0.48 line (branch v0.0.48-interior-store). Decided for the project on 22 October 2026
(the maintainer): interiors move to CHIM, as an option that becomes the default once a Balmora MiniWind A/B shows it
builds, boots and works. Today's per-room Quake maps stay selectable (DON'T DELETE ANY METHOD). Converting every room
starts with the door graph and the batch plan: [DOOR_GRAPH.md](DOOR_GRAPH.md). The builder converts rooms by batch
with `--room-batches` ([rooms by batch](DOOR_GRAPH.md#rooms-by-batch-in-the-builder)).

## Why

Today every interior is its own Quake map that carries its own copy of every mesh and texture it uses. Measured on
22 October 2026 over the 1,324 interiors of Morrowind, Tribunal and Bloodmoon (the asset census functions, unit scale;
private numbers in the maintainer's records):

| storage | bytes |
| --- | ---: |
| a copy per placement | 8.95 GB |
| one map per room, each mesh once per room | 3.46 GB |
| one store for every room, each mesh and texture once | 386 MB |

A room's own set (what it must load) is 2.1 MB for the median room, 6.0 MB for the largest 5 % and 14.75 MB at
most. A mesh is used in 6 rooms at the median; 766 of 3,765 meshes are used in one room only.

### Why not cut today's rooms into a store

The first try (`tools/interior_store.py measure`) cut each placement's model out of the v0.0.47 rooms and stored equal
ones once: 16,950 placements gave 7,313 distinct models (2.2 per model), 244 MB plus 48 MB of per-placement light, no
saving. Today's rooms bake a tilted placement's rotation into its model and split a lit placement's faces on its own
light grid, so equal meshes come out different. Sharing needs one model per mesh with the tilt applied at run time.

## Measured so far (22 October 2026)

**Census** over the 1,324 interiors of Morrowind, Tribunal and Bloodmoon: a copy per placement 8.95 GB; one map per
room (each mesh once per room) 3.46 GB; one store for every room 386 MB. A room's own set is 2.1 MB for the median
room, 6.0 MB for the largest 5 % and 14.75 MB at most (Akulakhan's Chamber); 251 rooms are over 4 MB. A mesh is used
in 6 rooms at the median; 766 of 3,765 meshes are used in one room only. Takeable things per room: 15 at the median,
114 for the busiest 5 %, 588 at most; 39,578 in all, plus 19,364 containers.

**First try, cutting today's rooms** (199 rooms of the v0.0.47 release image, 303 MB): 16,950 placements gave 7,313
distinct models (2.2 per model), 244 MB plus 48 MB of per-placement light: no saving. Measured cause: tilted
placements carry their rotation in their model (two copies of the same mesh differ by up to 0.27 units and in texture
mapping), and lit placements split their faces on their own light grid.

**CHIM rooms** (one model per mesh, turn applied at run time, one light level per placement), built from the 56 rooms
of the interior scene of the v0.0.47 release run: 55 rooms on a store of 20.7 MB plus 0.59 MB of room maps, against
79.3 MB of today's room maps for the same rooms (about 3.7 times smaller). One room with water stayed a room map
then; rooms with water and lava now come over too ("Water and lava in CHIM rooms", below). Every placed mesh of the test rooms sits at the same origin as in today's room map (checked by the builder).

**The builder stage:** 56 rooms in 19 seconds on 20 workers (about 18 cores busy). It took about 5 minutes with the
rooms done one after another. The image step makes the 55 room maps in 2 seconds.

**Not measured yet:** frame time and memory in game, door load time, and the 16, 32, 64 and 128 MB runs. The Balmora
MiniWind A/B (below) is next.

**Known limits of the first version:**

- One light level per placement: flatter than baked lightmaps. Per-object lightmaps come next.
- Water and lava are in the room map's world (below); swimming, lava damage and flooded rooms are not checked in the
  game yet. A pool whose bed reaches under the water level is carved into the water (lava inside its prism, water
  around it; CHIM-ROOM-LAVA-UNDER-WATER-48). A room the stage cannot make (a model over the clipnode budget, say) is
  named in the receipt (`failed_rooms`) and left out instead of failing the stage; a batch room's shell map leaves the
  image with it, so its doors stay inert (CHIM-ROOM-FAIL-STAGE-48).
- Water leaves carry no ambient water sound yet (today's room maps get it from their visibility pass).
- A room has no visibility data and no far cut: its shell world culls nothing, and the engine leaves out only what
  lies outside the view, placement by placement. A model that spans the whole room is therefore drawn whole from
  anywhere in it: the Vivec Arena Pit's bowl (`in_v_arena_01`, 15,760 of the room's 21,898 faces) sent about
  9,400 front faces through the clip path every frame for about 2,350 in view (PERF-ARENA-PIT-SLOW-48). Since
  v0.0.54 a room model wider than `cut_models_over` (config/chim-rooms.json, 512 local units) is stored as tiles of
  the room grain, the exterior's large-model cut ([cut.py](../../tools/chim/cut.py) tile mode), so each tile is
  culled on its own; 0 keeps every model whole (the earlier method). The same file can name a detail budget for room
  meshes (config/chim-detail-budgets.json: fewer visual triangles, the same collision).
- Switching between the exterior store and the interior store drops the kept models. A per-store cache for machines
  with 64 to 128 MB is a follow-up.

## What it must keep

The bar for CHIM rooms, in this order:

1. **No performance lost inside rooms.** Frame time, memory and the renderer counters at the same poses, today's rooms
   against CHIM rooms, at 16 MB and at 128 MB. If CHIM rooms are slower anywhere, that is fixed before they become the
   default, however much disk they save.
2. **No pre-baking that costs disk.** Each mesh and each texture is stored once; a room is a list of placements.
   Per-object lightmaps, later, must be a small light block per placement, never a baked copy of a model.
3. **Door load time.** About 2 seconds when entering or leaving a room is fine, as in Morrowind and OpenMW, with the
   door's sound playing over it.

Memory targets: smooth on 32, 64 and 128 MB expansions. 16 MB must work and may load more often.

## The design

An interior is not part of the outdoors. As in the original game, a load door unloads the outside and loads the room
on its own, behind a loading screen. So a room is its own thing, with its own floors, walls and limits, and nothing
of the exterior world's layout (frames, terrain, chunk grid, streaming) applies to it. What rooms share with the
outdoors is only the engine code that draws, collides with and lights a CHIM model.

- **The interior store** (`chimi/`): every mesh model of every room once (one model per mesh and scale, its tilt
  applied at run time), with its collision pieces, and every texture once. The same model and texture records as
  the exterior world (docs/chim/WORLD_FORMAT.md "Model record", "Placed models (0.8)"), in an index and pack files of
  the same layout, with no frames.
- **A room record** per room (`chimi/rooms/<room>.crm`): the models the room uses (store ids), and its placements:
  model, position, three angles, light level, box. Any size, any coordinates (the engine's wide coordinates), any
  shape: a house, a cave, a ship's hold, a district.
- **The room map** (`maps/<room>.chim`): the room's entities as today (its start, residents, sounds, flames, plant
  sprites, lava) and a small shell world: empty space closed by clip walls at the room's bounds, where today's room
  has its void box. A room with water or lava has them in that world, as a CHIM exterior chunk has them (below,
  "Water and lava in CHIM rooms"). Its worldspawn names the store and the room record. Doors are the room's door banks, unchanged:
  the engine loads `maps/<room>.chim` instead of `maps/<room>.bsp` when it exists (`AW_MapPath`).
- **Loading:** at the door, under the loading plaque, the room loads whole: its models and textures from the store,
  then its placements as drawn entities linked into the shell world, with their collision and light. Nothing streams
  while the player is inside; leaving frees all of it.
- **Floors and walls are the room's own:** its meshes with their collision. Nothing is added under or around them
  except the closed edge.
- **Light, first version: one light level per placement.** The builder computes each placement's level from the
  room's own lights with the light function of today's rooms (`interior_lighting.point_light`), sampled at the
  placement; the engine draws its faces at that level instead of the ambient, plus dynamic lights and self-lit
  textures. Flatter than today's baked lightmaps; per-placement lightmaps on the shared models are the next step.

## Formats

### Placement light level (world format 0.12)

In a placed record (format 0.8 and later) the high byte of the 16-bit flags is the placement's light level: 0 = none
(the placement is lit as before: ambient, dynamic lights, self-lit textures), 1 to 255 = the level its faces are drawn
at, in the units of `r_refdef.ambientlight` (0 to 255). Bits 0 and 1 keep their meaning; bits 2 to 7 stay 0. A file
with a light level is written as 0.12; engines before 0.12 refuse it with the usual message.

World format 0.13 adds the light's colour in bits 2 to 4: 0 = none (the plain colour table), 1 = warm (the torch and
lamp hue, `aw_light_hue`), 2 = red, 3 = orange, 4 = yellow, 5 = green, 6 = cool blue-white, 7 = purple. The engine
draws the placement's faces through that tint's colour table (16 KB, made from the palette the first time a map
draws the tint) and keeps a surface cache per tint as it does per level; `aw_warm_light 0` turns every tint off.
Bits 5 to 7 stay 0. Engines before 0.13 refuse a 0.13 file with the usual message.

### The interior store

`chimi/world.cwi` and its pack files: the exterior world's index layout (header, settings, file table, model
directory, id table, texture directory) with no frame rows; models and textures in pack files as MODL and TEXR
records. Written by the same writer functions as the exterior world.

### The room record

`chimi/rooms/<room>.crm`, big-endian as every CHIM structure:

| part | bytes | content |
| --- | ---: | --- |
| header | 32 | the common CHIM header, kind `ROOM`, count = placements |
| room block | 32 | bounds (6 x f32: mins, maxs), model count (u32), 0 (u32) |
| model list | 4 x models | store model ids, in load order |
| placements | 56 x placements | placed records (format 0.8 layout, light level in the flags), model field = store id |

### The room map's keys

Worldspawn of `maps/<room>.chim`: `"_chim_world" "chimi"` (the store folder, at most 8 characters, `a-z 0-9 _`) and
`"_chim_room" "<room>"` (the record `chimi/rooms/<room>.crm`).

## Engine changes

1. Store by name: the index and pack paths take the folder from the map (`_chim_world`, default `chim`). Changing
   folders drops the resident index and every kept model and texture (ids are per store).
2. Placement light level: read from the flags into an `entity_t` field (appended), used by `R_BuildLightMap` in place
   of the ambient when set; the surface cache keeps the level it built with and rebuilds on a different one.
3. The room loader (`chim_room.c`): with `_chim_room`, read the record, load its models and textures whole, make its
   placements entities with efrags in the shell world, and collide with them through the placed collision path
   (`ClipPlacement`: piece tables, then turned or yawed models); free everything at the next map.
4. Hinged doors: a placement whose reference is an ordinary DOOR without a destination asks the frames' hook
   (`chim_hinged_door`) as the room loads and turns like a frame's door (`ChimRoom_DoorYaw`, `ChimRoom_DoorClip`;
   [DOOR_MAPPING.md](../DOOR_MAPPING.md#ordinary-hinged-doors-v0048-dev2)). The room record keeps every placement's
   reference, which is the hinged door table's key.
5. Rooms that need 32 MB of Fast RAM (CHIM-ROOM-16MB-REFUSAL-48): decided at build time. The image step's room heap
   gate (`tools/chim/heap.py require_room_map_heap`) checks each room's models, textures and record against the zone
   of the built heap less the loading buffer (the 16 MB baseline, or Extra RAM off) and, when they do not fit,
   against what the 32 MB minimum gives a room (its zone and the automatic cache bank, with the largest model within
   one block: the measured room model of [the door graph](DOOR_GRAPH.md), CHIM-ROOM-ESTIMATE-48, 14,336,000 bytes
   since v0.0.51, CHIM-AUTO-BANK-CLIFF-51; since v0.0.52 also what a room that does not fit them grows into,
   ROOM-AKULAKHAN-HEAP-52: 4 MiB of the free Fast RAM, then the game heap's rest past the zone, about 20.6 MB in all;
   the same thresholds the room plan uses for its `zone_over_16mb` note, `tests/test_chim_room_fast_ram.py`).
   The room's need counts the engine's own blocks (the record with its placements, every model and texture, the
   store index, the prefetch table), and a room past one bank is loaded through the engine's own allocator
   (`tools/chim/room_zone.py`), so a room whose large models do not pack fails here, not at its door. The
   `chim-interiors` stage runs the same check on the store as soon as it is written
   (`chim-room-heap-early.json`, the room map at its smallest): a room that cannot fit stops the build there.
   A room that fits only the second is marked: `"_chim_room_fast_mb" "32"` in its room map's worldspawn; the
   build prints how many. At the door, before the door sound or anything loads, the engine reads the mark
   (`aw_scene.c AW_SceneRoomFastMb`) and, on less than 32 MB of Fast RAM or with Extra RAM off, plays the locked
   sound and shows the loading art with one box: "Sorry, but this interior cannot be run with 16MB of Fast RAM."
   and "Press ENTER to return." ENTER returns to the game where the player stood. With 32 MB or more the door loads
   the room as usual. A room that fits neither fails the build.

## Builder changes

1. `tools/chim/interior.py`: from each converted room's own scenery export (the placements, profiles and meshes today's
   room build uses, the meshes in the room map) the store models (placed format, one per mesh and scale), textures and
   light levels.
2. The interior store and the room records, rooms in town order so a room's models lie together in the pack files.
3. The room maps from the room maps' entities (as the town frame maps are made from the region maps,
   `tools/chim/frame_map.py`): every entity carried, the placed meshes checked to be the room record's placements at
   the same origins, actors and arrivals standing.
4. The image checks after the install read CHIM rooms (IMAGE-ROOM-MAPS-LATE-PASSES-48; before, they selected maps
   as `.bsp` or read only the room map's entities, so the Balmora A/B's CHIM rooms image counted 47 converted cells
   against 52, 81 dressing pieces against 99 and 0 actor placements against 93). The entity tracker and the dressing
   track count a room's record placements with its entities. The image fits the room's residents before the check
   (CHIM room actor bake, `tools/room_actor_bake.py`): a room map has no classic floor, so the residents of batch and
   shell rooms would otherwise keep the height the game data gives them, usually a little above the floor. The image
   step's order is: install the CHIM rooms (a shell room's world declares the standing hull, as a room converted whole
   does), fit every room resident, require that every ground resident carries a ground bake, then the actor contact
   check. The check stands the room's actors on its store models, each moved and turned by its record (the model's own
   collision; the engine's piece tables are not read, and the receipt says so per room). The scene stage's early
   check, before the image, only classifies a shell room's residents (`deferred-to-chim-room`): the room has no
   collision until the image installs it. See [room residents](../NPC_GROUND_CONTACT.md#where-a-chim-rooms-residents-are-fitted-v0048)
   and [Actor placement](../ACTOR_PLACEMENT.md). Each room's models and textures are checked against the zone the
   room map leaves (`chim-room-heap.json`; the BSP heap estimate sees only the room map's shell). A direct start in
   a room stands on its store floor. A harvestable plant in a CHIM room exists once, as its harvest entity, as on the
   CHIM world outdoors (CHIM-ROOM-HARVEST-DOUBLE-48): the CHIM rooms stage reads the harvest step's output and
   leaves those placements out of the room record (receipt row `harvest_left_out`), and the image writes the room's
   catalogue `harvest-<room>.txt`, which the engine loads with `maps/<room>.chim`. This holds for rooms converted
   whole and batch shell rooms alike. Without the harvest step (`--no-harvest`) the plants stay placed meshes, and
   the harvest receipt lists them by room (`chim_rooms_not_harvestable`).
5. Build option `--interior-format chim|bsp` (default `chim` once the A/B passes; `bsp` = today's rooms).
6. Water and lava: the stage reads each room's liquids from the brushes its room map compiles (`room.map`: the
   `*water` brush, one `*lava` prism per pool) and checks them against the room's conversion record (water height,
   the pools' tops); the receipt row carries them and the image step writes them into the room map's world.
7. Rooms by batch (v0.0.48, `--room-batches`, default `all` since the maintainer's decision of 23 October 2026; none
   in a MiniWind or with `--interior-format bsp`): the stage `chim-room-batches` converts the rooms of the selected
   batches of `config/room-batches.json` for CHIM only. A room's unit keeps of today's conversion only its scenery
   export, its kept placements (`placements.json`), its plant sprites and a shell room map with its entities. No
   visual world is compiled. The store and the room records are made from these as from any room
   (`kept_placements`). The shell room map has no placed meshes: `room_map` takes the placements from the room record
   (worldspawn key `_chim_room_shell`) and refuses an activated object. The image links every door of a batch room
   both ways. Details: [DOOR_GRAPH.md](DOOR_GRAPH.md#rooms-by-batch-in-the-builder).
8. The town rooms as shells too (v0.0.48, BUILD-SEYDA-BSP-CARRIER-48): in a build with CHIM rooms the builder runs the
   town room stages (`area`, `balmora-interiors`, `chim-rooms-TOWN`) with `--room-form shell`: each room's own
   conversion (its selection, scenery export, plant sprites, liquids and entities) without qbsp, vis and light, the
   placements the compiled room map would have placed (`prepare_area.mesh_placements`, the mesh converter's rule) in
   `placements.json`. A room with an object the engine activates (`aw_activated.h`) is still compiled, named in the
   log: a shell has no CHIM room form for its box yet. `--interior-format bsp` compiles every room as before. The
   prison and the census office stay classic compiled maps (the census office becomes a CHIM room with object state
   later).
9. What a build includes is printed at its end and kept in the CHIM inclusion ledger (`tools/interior_counts.py`,
   BUILD-SUMMARY-INTERIOR-COUNTS-48): the rooms in the plan by stage, the rooms made into CHIM rooms, the rooms kept
   as classic maps with their reasons, the rooms that need 32 MB of Fast RAM (`_chim_room_fast_mb`, from the image's
   `chim-room-heap.json`) and the room residents by animation level.

## The A/B

The same rooms, the same placements, the same build otherwise. What B cannot do yet is said with every number: its
light is one level per placement, not baked lightmaps, and its faces are the mesh's own faces, not today's faces split
on each placement's light grid.

- **Where:** a MiniWind Balmora sandbox (Balmora's 42 interiors), the same build with `--interior-format bsp` (A) and
  `chim` (B).
- **Disk:** image bytes of the interiors, A and B.
- **Memory:** hunk and zone free after each test room has loaded (`dbg mem`), the busiest rooms first.
- **Load time:** door to first frame for each test room, on the 68040 preset, warp off. A couple of seconds is fine:
  entering a room shows a loading screen in Morrowind and OpenMW too (the maintainer, 22 October 2026). What must not
  get worse is the frame time and the memory inside the room.
- **Frame time:** fixed poses per test room, the renderer counters (`dbg rcount`, surface cache builds included) and
  the frame time.
- **Collision:** the tilted placements of the test rooms walked and traced (the in-game check of
  [CHIM-YAW-PLAYER-BOX-TURNS-46](../bugs/CHIM-YAW-PLAYER-BOX-TURNS-46.md)'s repair).
- **Pictures:** the same poses A and B, headlamp off and on, and a clip of a slow turn in each.

## Rooms set aside, and how they come back

The first CHIM rooms are the rooms with no hard case. Of the 1,123 Vvardenfell rooms, 871 are ready and 260 are set
aside (water 191, lava 59, over the room size limit 27, and a few unreachable, Levitate-only or teleport-only). The
numbers, the reasons and the 16 rooms with no entrance area are in [DOOR_GRAPH.md](DOOR_GRAPH.md#rooms-set-aside-and-how-they-come-back).
The design for getting them back:

- **Water.** Done in the builder (CHIM-ROOMS-WATER-LAVA-48): the room map's world gets the water plane a CHIM
  exterior chunk carries, at the cell's own water height, with the room's walls and floors from the store drawn over
  it. Below.
- **Lava.** Done in the builder: each pool keeps the liquid prism and the bed today's room map has, with Quake's own
  lava contents (the damage rule of every lava in the game). Below.
- **Over the size limit.** None, counted again on 23 October 2026 (CHIM-ROOM-ESTIMATE-48): the 27 rooms set aside
  fit the 32 MB minimum, where a room has the whole zone and the 8 MiB cache bank; the old estimate used a frame
  map's 16 MB budget and the bytes on disk. 72 rooms need more than the 16 MB zone alone. What worked and what to
  watch: [interior sections](../INTERIOR_SECTIONS.md#what-worked-for-the-27-rooms-over-the-size-limit-23-october-2026).
- **Levitate-only, teleport-only and quest-reached rooms** come in with the scripts.

### Water and lava in CHIM rooms

The room map's world is written directly, as the exterior chunks write their terrain (`tools/chim/terrain.py`), with
no BSP compiler:

- **Water:** one plane at the room's water height across the whole room box (the original game's interior water is a
  flat plane over the whole cell). Below it a water leaf (swimming), above it open air; the `*water` face on the plane,
  seen from above and below, with no lightmap, as a compiled liquid face. Its texture is the room map's own `*water`.
- **Lava:** each pool's prism, 8 units deep (`tools/lava.py pool_brushes`), cut out of the open air by the same plan
  splits the exterior chunks use (`chim.terrain.lava_plan`): a lava leaf under the `*lava` warp face. The bed under
  each pool (16 units, solid) is one more collision model of the room map, as the room edge is. The `aw_lava` ember
  entities and the lava sound loops are the room map's entities and come over unchanged.
- **Where they come from:** the brushes the room map compiles today (`room.map`), checked against the room's
  conversion record (the water height, each pool's top). A mismatch keeps the room map and says why in the receipt.
- **Still a room map:** a room whose lava lies at or under its water level (one liquid inside the other is not
  carved yet).

Measured on 22 October 2026, rebuilding only the CHIM rooms stage from earlier runs' converted rooms:

- **Balmora MiniWind** (the v0.0.48-dev2 sandbox run): its 43 rooms have no water and no lava, so none was a room map
  before and none changes. The rebuilt store and all 43 room records and room maps are byte-identical to the code
  before this change.
- **Vivec** (the 13 water rooms of the v0.0.47-dev1 Vivec rooms stage, kept as room maps before): all 13 convert. Their
  own store is 8.96 MB (models 8.45 MB, textures 0.50 MB) with 62 KB of room records and 284 KB of room maps, against
  37.2 MB of their compiled room maps (both from the converted rooms, before the image adds residents). Each world adds 2 water faces, 1 node and 2 leaves.
- **Lava:** no room stage of the earlier runs has a lava room; lava is covered by the tests only.

**To check in the game (FS-UAE), open:** swimming, and surfacing against the store collision; entering a flooded
room; standing in lava (damage) and on its bed; water and lava drawn under and over the store's walls and floors.

## When a room is hard: the method

Decided for the project, 22 October 2026, the maintainer: some rooms, like some outdoor cells before them, are harder
than the rest, and how to approach them is part of the work. The same method as the outdoors'
[failure classes](CHIMPORT.md#failure-classes), applied to rooms. It builds on the earlier work for heavy
rooms and maps: the repair order for a room over a limit ([interior sections](../INTERIOR_SECTIONS.md#interiors-over-a-limit-the-order):
plants as sprites, meshes reduced, cuts at doorways, recentring), the [mesh methods](MESH_METHODS.md) (planar merge,
the mesh optimizer with locked borders, only a measured gain kept) and the
[matched A/B protocol](../AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md#matched-ab-protocol).

1. **Classify by mechanism, never room by room.** The reasons the door graph gives (water, lava, over the size limit,
   Levitate-only, teleport-only, unreachable) are the classes. A class gets one fix at the shared layer (the room
   converter, the room map, the engine) and then the whole class is converted again, not one room at a time.
2. **Never drop a room.** A room the builder cannot convert yet is set aside with a named reason and keeps its own
   state on the interior tracker under its ID (the cell's name in the game data). Rooms no door reaches go into a
   final parity batch, so every room of the game exists in the room system.
3. **Reuse what the game already does first.** Before anything new, look for the mechanism the outdoors or today's
   room maps already have: the water plane at the room's waterline, the lava pools with their damage rule, the same
   textures and contents. A new mechanism only when none fits, and then with a design note.
4. **Reproduce small.** Build a MiniWind sandbox of the room's town or area (minutes, not a full build), convert only
   the failing rooms and check that the failure repeats there before changing anything.
5. **Measure like for like.** Compare the room on CHIM rooms with the same room as today's room map: same engine, same
   pose and motion, 16 and 128 MB of fast RAM (32 and 64 MB for the busiest rooms). Frame time, memory, door load time
   each way and the door sound; stills with the headlamp off and on, and a short clip. No performance lost indoors is
   the first condition.
6. **Check what the class is about, in the game.** Water: swimming, surfacing, entering a flooded room. Lava: the
   damage and the surface. Over the size limit: memory and loading at every fast RAM size. Levitate and teleport: the
   way in, once the scripts can do it.
7. **Fix, test, register, gate, then run the class again.** Every finding goes into the bug register the same day; a
   problem seen again is marked as persisting. What the class needed is written here or in the door graph page.
8. **Unknowns stay open.** What is not verified is written as "to check" with the evidence it needs, never assumed.
