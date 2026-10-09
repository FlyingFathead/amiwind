# CHIM engine: shared models, chunk placements and the ring loader

Status: engine slices 1 to 3 for CHIM 0.1.0 (the engine side of the
[world streamer](../WORLD_STREAMER.md)). It reads the CHIM world formats 0.4
to 0.6 written by the CHIM builder ([world format](WORLD_FORMAT.md)) and
refuses any other version whole, saying which it found (0.6 only moves a
large frame's sector files into one folder per sector row, which the index's
file table names): the index
(`chim/world.cwi`: settings, file table, model and texture directories, kept
in the zone), one frame file per 3 x 3 cell frame (chunk directory, sector
table) and the frame's sector files (chunk records, then the models and
textures first needed there, each stored once). Host-tested with
synthetic worlds and with worlds the CHIM builder writes; run in FS-UAE on the
converted Balmora (the town's frame map and world format 0.4 beside its region
maps, both modes in one session); not yet on hardware. All new code is in `engine/aga/src/chim/`; the legacy engine files
only gained small hooks (`aw_scenery.c`, `aw_walk.c`, `aw_scene.c`,
`aw_debug.c`, `sv_phys.c`, `model.c`), each a NULL pointer test unless
`chim/world.cwi` exists.

<!-- contents start -->
## Contents

- [When CHIM runs](#when-chim-runs)
- [Towns](#towns)
- [Quake mechanisms reused](#quake-mechanisms-reused)
- [Limits that do not apply](#limits-that-do-not-apply)
- [Memory](#memory)
- [Loading](#loading)
- [Placements: stored once, drawn once](#placements-stored-once-drawn-once)
- [Streamed statics](#streamed-statics)
- [Vis and culling](#vis-and-culling)
- [The frame world](#the-frame-world)
- [Far terrain](#far-terrain)
- [Frame re-centring (plan, not implemented)](#frame-re-centring-plan-not-implemented)
- [Not yet done](#not-yet-done)
- [Tests](#tests)

<!-- contents end -->

## When CHIM runs

CHIM runs only for a map whose worldspawn has `"_chim_frame" "X Y"` (the CHIM
frame the map's exterior belongs to) and only when `chim/world.cwi` exists.
Without `chim/world.cwi` no hook is installed and the game is the legacy
engine, unchanged (one failed file open at start-up). A map without the key
does not load anything. If a CHIM map cannot start (Hunk too small, a pack
fails its checks) the console says why and the map runs without its chunks.

On a CHIM map the frame's terrain **replaces the map's own world tree** (see
"The frame world"): the map's world brushes are not drawn or collided while
the map runs, and its brush entities (doors and the like, `*1`, `*2`...) keep
working as before. The builder must therefore write a CHIM frame's map with
an empty world whose bounds cover the frame (the server's area nodes are
built from them), and everything structural into the chunks.

## Towns

Any town of the town table (`aw_region.c`: Balmora, Seyda Neen, Vivec and
the rest) runs as one CHIM frame map when `maps/<town>-chim.bsp` exists and
the cvar `chim_towns` is 1 (the default). The region code asks CHIM through
one hook, `aw_chim_town_map`: the town's world model is then the frame map
instead of a region map, no region crossing or prefetch happens, and every
point of the frame counts as inside the town. The server's map name stays
the town's name, so door links to the legacy interiors, sky, fog, lamps,
`dbg tp` and every other per-town table work unchanged. The intro (Seyda
Neen's opening scenes) keeps its region maps. `chim_towns 0` brings back the
region maps for an A/B in one session (the next map load uses them). Nothing
in the hook names a town: a town gets CHIM by its builder writing its frame
map, and the open-world exteriors use the same `_chim_frame` maps.

Seyda Neen's intro docks (world format 0.5) have their own frame map over
the town's frame, `maps/intro_docks-chim.bsp`: while the intro runs, the
region code loads it instead of the legacy docks map when it exists (the
same chunks, the docks' own entities and clip walls). Likewise a door
arrival in Seyda Neen's enclosed courtyard loads `maps/sncourt-chim.bsp`
when it exists (the legacy `sncourt` region); neither crosses regions. Placements flagged
story hidden (0.5) are neither drawn nor solid while the opening story
hides them, by the rule `aw_opening.c` applies to `aw_story_hidden`
(Seyda Neen once the ship is left).

A frame map whose worldspawn has `"_chim_edge" "closed"` (a frame that
touches no other frame, such as the Vivec Arena canton) has clip walls at the
frame's bounds; a walking player who reaches one (within 16 units of a bound)
is told "Area unavailable", at most every 3 seconds. `chim` states whether
the edge is open or closed.

In a world of several frames, placement ids run on across frames in pack
order; the engine finds a frame's first id from the frames before it in the
index's file table, and the placement rows count from it.

A pure-CHIM image has no legacy exterior maps for its CHIM towns (no region
maps, no `balmora.bsp` or `seyda.bsp`, no `intro_docks.bsp` or
`sncourt.bsp`); only the frame maps and the region tables. Every check that a
scene exists (arrivals for `dbg tp`, quick start and doors, saves and loads,
the scene picker, the gallery return, the world map's town checks) goes
through one function, `AW_SceneMapSize` (`aw_region.c`): the scene's own
`maps/<name>.bsp` when it exists, else the town's CHIM frame map. Saves name
the town (`sv.name`), so a save in CHIM Balmora loads in either kind of
image.

Which mode a town runs in is always stated: loading a town prints
`<Town>: CHIM frame map maps/<town>-chim.bsp.` or `<Town>: legacy region map
maps/<region>.bsp.`; start-up prints `CHIM 0.1.0: N of M towns on CHIM`; the
`chim` command lists every town of the table as `CHIM: <map>` or `legacy`
with the reason (no CHIM world, no frame map, `chim_towns 0`). The boot
check's title carries both versions in the short form `AmiWind vX / CHIM vY`
(generated from `VERSION` and `chim/chim.h`); the 68000 boot check runs
before the engine and has no town table, so the per-town modes are in the
console.

Per-region data stays per region. The frame map carries no harvest
catalogue: while a town runs its frame map, the harvest runtime loads the
catalogue of the region the player is in (`harvest-<region map>.txt`, the
region found in the town's region directory with the region hysteresis),
at arrival and again on each region change within the frame, without a map
change (`AW_HarvestFollow`, `AW_RegionAt`). The per-file limits (64
nodes, 256 edges, 8 models) and the saved facts are unchanged. This needs
the frame map in the town's coordinates (frame origin = the town's region
origin), as for door links and arrivals.

## Quake mechanisms reused

| Part | Quake / AmiQuake mechanism | Notes |
| --- | --- | --- |
| Shared model geometry | External brush models like id1's `b_*.bsp`: one model, many placements | One BSP29 brush image per model, decoded by the same `Mod_Load*` section loaders (`model.c`) into a CHIM arena instead of the Hunk (`AW_BrushImage`, `AW_BrushStream*`) |
| Keeping models | `Cache_Alloc` / `Cache_Check` LRU and the `cache_user_t` handle; `Z_*` first-fit allocation with merged free blocks (`zone.c`) | `chim_zone.c`: the same policy and allocator, but blocks never move (`Cache_Move` would break a brush model's internal pointers). Blocks in use are locked and never evicted |
| Placements | Static entities and efrags (`CL_ParseStatic`, `r_efrag.c`) | Each placement is an `entity_t` linked to every world leaf its drawn box touches (`R_SplitEntityOnNode`) and stored for drawing by `R_StoreEfrags` only when one of those leaves is visible. No edict, no signon message, no model index |
| Collision | Brush entity traces (`SV_ClipMoveToEntity`, `SV_RecursiveHullCheck`) | Same hull choice, offset, yaw rotation and `DIST_EPSILON` pull-back; each placement's yaw sine and cosine is computed once at load. Host tests compare every trace with `SV_ClipMoveToEntity` |
| Placement catalogue | `aw_scenery.c` (AmiWind) | CHIM's hooks live in it: chunk placements are its successor and enter, link and clip with it |
| Textures | `Mod_LoadTextures` (miptex to `texture_t`), `R_InitSky` | A brush image's texture lump lists shared texture ids; each texture is loaded once into the zone and locked by every model that uses it |
| Surface cache | Owner backlinks in `d_surf.c` | An evicted model's surfaces are unhooked from the surface cache, as `D_FlushCaches` does for the whole cache at a map change |
| Sliced loading | The 16 KiB section loader (`AW_LoadBrushSection`) | A large image is streamed one section per step, spread over frames; small images are read whole into the loading buffer and decoded from memory (one read, no seeks) |
| Terrain | The world model itself: `R_RecursiveWorldNode`, `R_MarkLeaves` and `Mod_LeafPVS`, `R_LightPoint`, `SV_PointContents`, `SV_RecursiveHullCheck`, `SV_LinkEdict`, `R_AddEfrags`, the world edge cache, hull 0 as `Mod_MakeHull0` builds it | `chim_graft.c` copies the active chunks' terrain subtrees into one pool of world arrays with their indices relocated, under a frame root and an axial grid at chunk edges, and installs it as the map's world model |
| Chunks joining and leaving | A moving entity: `R_RemoveEfrags` / `R_AddEfrags` (client), `SV_LinkEdict` (server) | Only the entities in the leaves that change are linked again; the rest of the world does not move (see "The frame world") |
| Visibility | Quake's PVS rows (zero-run compressed, `Mod_DecompressVis`) | Each chunk's row over the frame's chunks becomes a leaf row of the frame world |
| Actors outside the ring | Morrowind runs only the cells around the player | `SV_Physics` skips moving non-client edicts (step, toss, bounce, fly, missiles) standing outside a grafted chunk: no think, no movement |

There is no Quake mechanism for moving the world origin; see "Frame
re-centring" below.

## Limits that do not apply

- `MAX_MOD_KNOWN` (256) and the edge-cache model limit: shared models never
  take a `mod_known` slot. How many are resident depends on memory only.
- `MAX_MODELS` (a byte on the network): placements never send a model index.
- `MAX_EDICTS` and the 16-leaf limit for edicts (`MAX_ENT_LEAFS`):
  placements are not edicts. Efrags have no per-entity leaf limit; the pool
  grows in pages up to 65,536 links (`AW_EFRAG_LIMIT`).

Limits that still apply: one submodel per CHIM brush image (otherwise the
loader would register `*N` inline models of the map), at most 4,096 chunks
per frame, 8,192 placement records per chunk, 512 textures per image,
`MAX_VISEDICTS` (1,112) entities stored per frame (see "Vis and culling"),
and for the frame world of the active ring: 65,535 surfaces and vertexes
(16-bit indices), 8,192 leaves (`MAX_MAP_LEAFS`), 65,520 nodes and standing
hull clipnodes. A rebuild over a limit is refused with a console line and
the chunks wait ungrafted.

## Memory

The plain-language guide with the measured figures per map, the rules and how to read the numbers:
[build_guide/MEMORY.md](build_guide/MEMORY.md).

Three roles, allocated separately (the [memory placement
requirement](../WORLD_STREAMER.md#memory-placement-requirement)):

- **Zone bank for the map.** A CHIM map takes one block from the Hunk when it
  starts: `chim_zone_kib` (default 6,864 KiB: on Balmora's CHIM frame map
  the largest zone that keeps the engine's 2 MiB Hunk-gap safety at the load
  peak, rounded down to 16 KiB), never closer than
  `chim_reserve_kib` (default 2,048 KiB) to the Hunk's end, at least 128 KiB.
  It is part of the 11 MiB map budget and goes back with the Hunk at the next
  map change. It holds the frame's chunk directory, the loading buffer,
  chunk catalogues, terrain, shared models and textures.
- **The whole-map Hunk rule** (CHIM-ZONE-RESERVE-EARLY-33). The zone is
  taken before the map's entities and the client's per-map allocations
  load, so it leaves room for them: the frame map states what the map loads
  after the zone (worldspawn `"_chim_hunk_rest"` BYTES, written by the
  builder from its heap model), and the zone is at most what the Hunk has
  left less `chim_reserve_kib` and that figure. Once the player is placed,
  the engine measures what the map really loaded after the zone; if the gap
  ended under `chim_reserve_kib` it says so, with the zone that would have
  kept it, and the next load of the same map in the session leaves room for
  the most it has measured there (loads differ by a few KiB). That learning
  applies by default only to frame maps that state the figure
  (`chim_rest_measured 1`): a frame map from before the statement keeps its
  full zone, so its ring still fits, and the gap is only said;
  `chim_rest_measured 2` always learns (the first method), 0 never. `chim` prints the zone, the stated and measured
  figures. The same rule, for the builder's heap gate, is
  `tools/engine_limits.py` `whole_map_zone`.
- **Frame-world pool.** With the incremental frame world (`chim_graft_mode
  1`, the default) one block of twice `chim_pool_kib` (default 384, so 768
  KiB; at most a sixth of the zone) is reserved when the map starts, before any
  model. Its arrays are laid out for the ring when it first arrives (every
  array gets the ring's need times the same factor, within Quake's index
  limits) and chunks take and give back ranges of them. A pool that cannot
  take a chunk is laid out again in place (a repack; one when the ring first
  arrives); a ring that outgrows the block moves to a new block of twice its
  need. Without a reserve (`chim_pool_kib 0`, measurements) blocks are sized
  for the ring and shrink after a long jump. With the full rebuild
  (`chim_graft_mode 0`, the first method, kept selectable) the frame world is
  rebuilt into one of two slots of `chim_pool_kib` each (at most a twelfth of
  the zone) while the other still holds the current one; a frame world that
  outgrows its slot falls back to an allocation per rebuild (Balmora's
  largest full-rebuild frame world is about 402 KB, more than a 384 KiB slot:
  measure with `chim_pool_kib 512` there). The incremental pool's largest
  Balmora high water is about 443 KiB of the 768 KiB block.
- **What a map needs.** `chim` and `dbg rcount` (`zl`) report the bytes of
  locked zone blocks (the active ring's models, terrain and catalogues, the
  frame-world pool, the loading buffer, the index) and their peak: the
  memory a map cannot do without, as against the cache of unlocked blocks
  that always fills the rest of the zone. The builder's CHIM heap model is
  checked against this peak. A cap is said on the console, and
  `chim` prints the block, the arrays' use and capacity, repacks and their
  last reason.
- **Prefetch only into free room.** Chunks beyond the active ring (the
  prefetch margin) are loaded only when twice the bytes they read next fit
  the largest free block, so prefetch never evicts (`chim_prefetch_room 1`).
  `chim_draw_distance` (0: the world's) and `chim_prefetch` (-1: the
  world's) override the ring's radii for measurements.
- **When the zone is full** ([CHIM-CHUNK-LOAD-FAIL-33](../bugs/CHIM-CHUNK-LOAD-FAIL-33.md)). The zone
  never moves a block, so a ring that fits by the sum can still find no
  piece large enough for a house model when locked blocks split the room.
  Three methods, each 0 for the first method:
  `chim_zone_ends` (default 64 KiB): blocks smaller than this come from the
  zone's high end, larger ones first fit from the low end, as Quake's Hunk
  keeps a low and a high end, so small locked blocks (textures, catalogues,
  terrain) do not split the room large models need.
  `chim_release 1`: a chunk within the active radius keeps what it already
  has in the zone while it loads the rest (its catalogue, terrain and
  resident models are locked during the load: the first method could evict
  them, and a chunk whose models did not fit together loaded for ever); when
  it finds no room it releases the active chunk farthest from the player
  that is farther than itself and outside the collision margin (those past
  the active radius first, being the farthest) and tries again; a released
  chunk is not activated again for 50 ticks unless the player comes within
  the collision margin of it; a chunk without ground within the collision
  margin that failed tries again on the next tick; every release lets the
  waiting chunks try again.
  `chim_partial 1`: a chunk whose model has no room is activated without it,
  so its ground and its other placements are there (a reach copy draws such
  a placement when its owner lacks the model); the model follows when there
  is room. A failed load says which part failed and why (a full zone with
  the request and what the zone holds, or bad data), once per chunk and 50
  ticks; the first one of a map also prints the zone's layout (`CHIM zone
  bank 0: ...`, every block with its kind, KiB and `*` when locked). `chim`
  reports the largest run without a lock, the failures by reason, the
  releases and the partial activations. The builder's zone walk gate
  (`tools/chim/zone_sim.py`) runs the engine's own `chim_zone.c` with these
  rules over a walk through every frame and fails when a step leaves the
  player without ground.
- **Loading buffer.** `chim_buffer_kib` (default 32 KiB, at least 18,448
  bytes, the largest section slice). Images up to this size are read whole;
  larger ones are streamed through it. CHIM never uses `Hunk_TempAlloc`, so
  loading does not move or evict Quake's cache (actors, sounds).
- **Cache bank (optional).** `-chimcache <KiB>` allocates extra Fast RAM once
  at start-up (checked, `AvailMem` advisory only). Shared models and textures
  prefer it and survive map changes there. Without it, at the 2 MiB Chip +
  16 MiB Fast baseline, shared models go with the map, as Quake's brush
  models do.

Sizes on the 68k target (measured with the target compiler): `model_t` 400
bytes, `entity_t` 184, a run-time placement 236 (the 48-byte placement
record becomes an entity, its drawn box and its yaw), a chunk header 64 plus
its PVS row, a chunk directory entry 80, a model block 440 plus its decoded
arena, a texture 60 plus its pixels, the efrag 16 per leaf
touched. In the frame world pool: `mnode_t` 40, `mleaf_t` 48, `msurface_t`
48, `mplane_t` 20, a clipnode 8 (hull 0 and hull 1 each), an edge 4 plus its
edge cache word 4, a vertex 12, a surfedge or mark 4. Static data: about 10
KiB of BSS (4.4 KiB of it the list of entities to link again after a
rebuild, 1.1 KiB the vis row being built), about 27 KiB of code.

Per map, CHIM's part of the Hunk is: the zone bank, which holds the chunk
directory (about 80 bytes a chunk), the loading buffer, the catalogues of
loaded chunks (64 + 236 per placement record + 8 per distinct model + the PVS
row), their terrain models, the shared models and textures they place (each
once), and the CHIM model and texture pack directories (12 bytes per entry).
Efrag pages come from the low Hunk as for static entities (16 KiB per 1,024
links). The decoded size of every brush image is bounded before it is loaded
(`AW_BrushBound`, exact for CHIM images in the host tests) and the block is
trimmed to the decoded size afterwards. The frame world pool is one zone block
sized exactly for the grafted chunks; during a rebuild the old and the new
pool exist together.

## Loading

- A placed model's node lump is only its point hull: a chain of convex
  pieces whose outside branches all lead to the next piece (a graph, not a
  tree). It is decoded into hull 0's clipnodes only; a brush entity never
  walks its own nodes to draw, and Quake's `Mod_SetParent` would walk such a
  graph once per path. Chunk terrain keeps its node tree (world geometry).
- Resident models and textures are found by id in tables kept with the
  index (no search of the zone); the ring scheduler sorts the chunks within
  the load radius once per tick and takes the nearest that needs work.
- `chim_debug 1` prints a line per map start, ring prime and frame world
  rebuild.

- Files are opened on demand from the index's file table and up to four stay
  open (least recently used closes); every open checks the size the index
  records. Records are read where the directories say, in ascending order
  within a crossing; the format's whole-sector reads are not used yet.

- On a CHIM map the frame's chunk directory is read once. The player's
  physics (`aw_walk.c`) and the client's link (`aw_scenery.c`) each call the
  ring tick; it runs once per host frame.
- Ring radii come from the world index: chunks within draw distance +
  hysteresis are active (placements linked, models locked); chunks within
  that plus the prefetch margin are loaded; active chunks are released only
  beyond the load radius, so the prefetch margin is also the hysteresis.
- Work is nearest chunk first: catalogue, terrain, missing models, then
  activation. Each frame reads at most `chim_read_kib` (default 32 KiB) plus
  one unit: a whole image that fits the loading buffer, or one section of a
  streamed image. Past that budget only chunks within the world's collision
  margin are loaded (the ground under the player never waits; counted as
  urgent loads).
- Prefetch ahead: while the player moves, the chunks within the load radius
  of a point `chim_lookahead` units ahead (default -1: the world's prefetch
  margin; 0: off) are loaded too, and every candidate is ranked by the nearer
  of its distances to the player and to that point. Activation (drawn,
  solid) stays within the active radius of the player.
- The ring follows the view distance: the active radius is the effective
  view distance (`AW_DrawDistance`) plus the world's hysteresis
  (`chim_draw_distance` > 0 overrides it). On a CHIM map the view distance
  has no town-table cap; its only limit is how far the world's visibility
  data reaches (the builder's draw distance + hysteresis), and `dbg fog
  distance` and `chim` say so.
- When the player is placed (`AW_SceneSpawn`), the ring around the arrival
  point is loaded and grafted before the clearance search traces the ground;
  otherwise the first tick on a map loads the whole ring before the player
  moves.
- Released chunks and unused models stay in the zone, least recently used
  first out; a chunk that cannot be loaded waits 50 ticks and says so.

## Placements: stored once, drawn once

A placement is owned by the chunk holding its origin and copied, as a
48-byte record only, into every other chunk its drawn box touches. The
engine draws and collides each placement exactly once: from its owner chunk
when that chunk is active, otherwise from one active chunk holding a copy.
The record carries the drawn box (the box `aw_scenery.c` computes, rounded
outward), which the engine uses for efrags and the collision broadphase.

## Streamed statics

A frame map's `aw_static` and `aw_flora` entities (sprites and static alias
models: trees, plants, lamps) are spawned by `world.qc` with nothing but
`makestatic`, so the whole town's statics used to load their models into the
Hunk when the map started (Seyda Neen: 229 statics, about 0.95 MB of sprite
models; CHIM-SEYDA-HUNK-GAP-33). The builder tags each of them with
`"_chim_chunk"` (the frame's chunk index that holds the origin) and
`"_chim_box"` (the drawn box, frame-local), and states the count in the
worldspawn (`"_chim_streamed_statics"`). The engine (`chim/chim_statics.c`):

- takes a tagged entity out of `ED_LoadFromFile` before it is spawned and keeps
  it in a list in the zone (locked for the map; room for the stated count);
  untagged entities and tagged ones of any other class spawn as usual;
- keeps `PF_makestatic`'s rules: an `aw_flora` must be a sprite with a finite
  positive `aw_scale`; an `aw_static` is drawn at scale 1 whatever `aw_scale`
  says;
- loads a static's model as part of its chunk's needs (the same scheduler,
  budget, prefetch-room rule and partial activation as the chunk's own
  models): a sprite is decoded once into a zone block (Quake's sprite loader
  with the zone as its allocator, `Mod_LoadSpriteInto`), shared by name and
  locked while any active chunk places it; unlocked it stays as cache. An
  alias model goes through `Mod_ForName`, its data in Quake's cache as every
  actor's;
- places the statics of an active chunk as `CL_ParseStatic` would (model,
  frame, skin, colormap, origin, angles, sprite scale) and links them into the
  leaves their drawn box touches once the chunk is in the frame world;
  removes them when the chunk goes.

A model that is missing or does not decode is said once and its statics stay
out; the chunk is not held back. `chim` prints the list, the linked statics,
the resident models and the zone bytes of their sprites. The builder writes
`"_chim_hunk_rest"` without the tagged statics' models, so the whole-map rule
gives the zone that room again.

## Vis and culling

- Placements are linked as efrags to the leaves they touch, so the PVS and
  the frustum walk (`R_RecursiveWorldNode`) decide what is stored for
  drawing; nothing is linked into the visible list unconditionally (unlike
  `AW_SceneryLink`, which adds its whole catalogue every frame).
- Placement lists (format 0.3): each chunk carries a row of the placements a
  view from it may see. On the client, linked placements outside the row of
  the chunk the camera is in get no efrags (not drawn, still solid); a
  missing or malformed row draws everything. `dbg rcount` shows them as
  `hid`.
- Placements link into the frame world's leaves: the terrain leaves of the
  chunks their box touches (and the empty grid leaves outside the grafted
  chunks). The PVS rows of the chunk the camera is in decide which of those
  leaves are visited, so placements in chunks the builder found hidden are
  not stored for drawing.
- Terrain is world geometry (never a brush entity) and its subtrees are
  shallow; the frame grid adds about two levels per doubling of the ring.
  Buildings and other placed objects do not split the world BSP; they occlude
  only through the builder's PVS rows.
- A placement that touches one leaf takes the cheap brush path
  (`R_DrawSubmodelPolygons`); one that crosses leaves is clipped down the
  world BSP. A shallow world BSP of axial planes on the chunk grid keeps most
  placements in one leaf. Not yet measured with converted data.
- Counters: `chim` prints placements linked, efrags (and how many
  placements touch one leaf, the most leaves of one placement), and for the
  last rendered frame how many placements were sent from visible leaves and
  how many of those stayed unclipped. Use it together with `dbg rcount` on
  the benchmark cameras before and after every CHIM change.
- `MAX_VISEDICTS` (1,112): `R_StoreEfrags` silently stops adding entities
  beyond it. Watch the "sent" counter in dense chunks.

## The frame world

Quake addresses world data by index into the world model's own arrays:
`R_RecursiveWorldNode` draws `cl.worldmodel->surfaces + node->firstsurface`
(16 bits), faces walk `surfedges`, `edges` (16-bit vertex indices) and the
world edge cache by index, `R_MarkLeaves` and `Mod_LeafPVS` number leaves by
their position in `cl.worldmodel->leafs`, `SV_FindTouchedLeafs` stores those
numbers in edicts, and the hulls follow clipnode and plane indices. So the
active chunks' terrain cannot simply be hung under the map's tree by
pointer. `chim_graft.c` builds the frame world instead:

- One zone block holds nodes, leaves (leaf 0 is the shared solid leaf),
  marksurfaces, surfaces, surfedges, edges, vertexes, planes, the standing
  hull's clipnodes, hull 0 (one clipnode per node, as `Mod_MakeHull0`), the
  world edge cache and the leaf PVS rows. Each grafted chunk's decoded
  terrain (its template in the zone) is copied in with every index and
  pointer relocated; texinfo, textures and lightmaps stay in the template.
- Node 0 is a frame root (west of the frame is one empty leaf); below it an
  axial grid splits the chunk range in halves at chunk edges, longer axis
  first; a range with no grafted chunk is one empty leaf.
- Hull 1 is the grid's routing planes over each chunk's standing-hull
  clipnodes; hull 2 (large entities) uses the same tree, because format 0.1
  stores one standing hull.
- Incremental (`chim_graft_mode 1`, the default; CHIM-REBUILD-COST-33):
  every array of the pool has free ranges, the grid's reserve at the front.
  A chunk that joins is copied into free ranges (its nodes' hull 0 and its
  edge cache words with it); a chunk that leaves gives its ranges back (its
  leaves become solid with no parent, its surfaces are cleared, their surface
  cache blocks let go). Nothing else moves: the other chunks keep their
  surfaces (and surface cache blocks), their leaves (and the efrags in them)
  and their leaf numbers. Only the entities in the leaves that changed (the
  leaving chunk's and the grid's empty leaves) are taken out with
  `R_RemoveEfrags` and linked again, and only the edicts with a leaf number
  there or a box over a chunk that joined or left are linked again with
  `SV_LinkEdict`. The grid and the leaf PVS rows (grid leaves and the leaves
  of the chunks each chunk's row sees; free ranges are not visible) are
  rewritten; the view leaf is recomputed. An update is planned first (free
  ranges on a copy, the grid's reserve) and either fits or becomes a repack,
  so it never fails half done.
- Per-frame budget: chunks join nearest first, at most `chim_graft_kib`
  bytes (default 16 KiB) plus one chunk a frame; chunks within the collision
  margin never wait. Chunks waiting for their ground are not linked into the
  grid's empty leaves (they are at the ring's edge). Chunks that leave are
  given back at once (their terrain becomes evictable).
- Full rebuild (`chim_graft_mode 0`, the first method): the pool is rebuilt
  whenever the active set changes. Surfaces carry their surface cache blocks
  to their new place; every efrag in the old leaves is released and linked
  again into the new leaves, every edict gets new leaf numbers through
  `SV_LinkEdict`.
- Either way, no free efrag keeps a pointer into a leaf that is reused or
  freed (`ChimGraft_RemoveEfrags`), and a test walks both methods frame by
  frame and finds the same leaves, contents, vis rows, ground, efrags and
  edict leaves.
- The world holds its own lock on every grafted terrain, so a chunk that
  leaves the ring cannot be evicted while the world still points into it.
- A rebuild that finds no room in the zone is said once and retried after
  25 ticks; new chunks wait ungrafted (their placements are linked, their
  actors stay frozen).
- At the map's end the map's own world model is restored as it was loaded.

`chim_tp X Y` moves the player to an original Morrowind position inside the
frame (local = (world - frame origin) x 0.25): the ring there is loaded and
grafted, then the standing hull is dropped onto the ground.

`dbg rcount` (aw_rcount) appends on a CHIM map, once a second: `chim`
active/grafted/loaded chunks, `pl` placements linked/sent/one-leaf (last
frame), `fz` actors frozen, `rb` frame-world updates in that second and
their total/longest microseconds, `gr` chunks joined/left/repacks and the
most KiB one update copied, `cw` the longest frame of CHIM work (ring tick
and client link, microseconds), `sm` the safety margin (units to the nearest
chunk of the frame without its ground in the frame world, -1: none), `ur`
urgent joins/loads past the budgets so far, `pool` frame world KiB, `zone`
used/free KiB, `ev` evictions, `rd` KiB and reads, `op` file opens. Every
map adds `vd`, entities refused for a full `cl_visedicts`.

`tools/chim/frame_map.py` (the builder's image step) writes the map a town's
frame runs in, `maps/<town>-chim.bsp`: an empty world with the frame's
bounds, the worldspawn with `_chim_frame`, and every entity of the town's
region maps that the chunks do not hold (actors, the player start); see
"Towns" and the world format's "Activation" section.

The `chim` command prints the frame world: grafted chunks, nodes, leaves,
surfaces, bytes, rebuilds and failures, caches moved and released, efrag
owners and edicts linked again.

## Far terrain

The frame world holds the active ring only, so beyond it there is no ground
(CHIM-FAR-TERRAIN-33). `chim/chim_far.c` reads the frame map's sidecar,
`maps/<frame map>.far` ([world format](WORLD_FORMAT.md#far-terrain-sidecar)),
at map start into the low Hunk (13,222 bytes for Balmora's 81 x 81 samples;
refused, with a line, when it would go below `chim_reserve_kib`), applies its
object stamps when `chim_far_objects` is 1 (read above the heights and given
back to the Hunk mark at once) and gives the rest back with the Hunk. After
the fog pass, `aw_fog.c` calls `aw_chim_far_draw`, which draws it past the
fog plane, up to `chim_far_reach` (896, the legacy region overlap; 0: the
whole layer), in the full fog colour with the distant-LAND rasterizer
(`AW_HorizonGrid`, `aw_horizon.c`): depth tested, so resident geometry always
wins, whole blocks culled, triangles facing away skipped. It adds nothing to
the BSP, the PVS or the entity lists. `chim_far 0` draws none (the first
method), `chim_far_cull 0` tests every block; `chim` and the `dbg rcount`
line (`far drawn/blocks tr px fus`) report it. Slow FS-UAE preset: 31 to 44
ms per frame at the default depth (object stamps on) (3 to 5 % of the frame). Design, the legacy
horizon it matches and the measurements: [FAR_TERRAIN.md](FAR_TERRAIN.md).

The same layer is the terrain floor (`chim_terrain_floor`, default 1;
CHIM-GRAFT-REPACK-EMPTY-33, second layer): it is resident for the whole map,
so it holds when the frame world has lost its chunks. `AW_TerrainFloor`
(`aw_walk.c`) asks it once per frame for the player's walk move
(`SV_Physics_Client`, `MOVETYPE_WALK`) and for free-falling `MOVETYPE_STEP`
bodies (`SV_Physics_Step`); a body below the lowest height at its X/Y, with
nothing of the world below it, is lifted onto the ground with one console
line, and the player is held there while the world has no ground under it.
Noclip and flight never ask.

## Frame re-centring (plan, not implemented)

Coordinates must stay within about +-4,096 units. A CHIM frame is 3 x 3
cells with origins relative to its centre, so the first slice keeps one
frame per map and crosses frames by changing map (as region maps do today,
but every 3 cells). To cross frames without a map change, a single audited
function would shift, in one server frame and the same client frame, by a
multiple of the grain: every active chunk's placement origins and boxes
(re-linking their efrags), terrain entities, every edict origin and its
area links, QuakeC vectors that hold positions (doors' `pos1`/`pos2`,
`oldorigin`, movement targets), client entities' message origins and lerp
state, dynamic lights, particles and sound origins. Saves would record the
cell and the frame-local position. QuakeC position fields are the risk and
need an inventory first.

## Not yet done

- Loading the collision part (the clipnodes lump, stored last) only for
  chunks within the collision margin; today every loaded chunk and model is
  read whole.
- Per-placement lighting for interior pieces and per-entity light levels for
  small props (options B and C of the streamer design).
- Run-time scale; placement records with a scale other than 1 do not exist
  in format 0.1.
- Animated (`+`) textures shared between models are drawn as their first
  frame (no sequence linking across the shared pool yet).
- The cost of a full rebuild (CHIM-REBUILD-COST-33): in FS-UAE with the
  JIT, Balmora's rebuilds of 19 to 41 chunks copy 195 to 408 KB and take 0.7
  to 3.5 ms; cycle-exact (JIT off, multiplier 7) 95 to 184 ms per crossing.
  The incremental frame world (default) copies only the chunks that join, a
  budget a frame; host walks copy 99 times fewer chunks on a Balmora-sized
  frame. FS-UAE figures (relative until a hardware number exists) are in
  the bug report.
- Zone headroom (CHIM-ZONE-RING-THRASH-33, fixed for Balmora): the first
  runs (6 MiB zone, frame world allocated per rebuild, prefetch allowed to
  evict) read 41 MB and evicted 6,651 blocks on an 8-chunk walk and back,
  and some rebuilds found no room; a jump across the town then failed. In
  one A/B/C/D sweep with reruns (FS-UAE, JIT): prefetch into free room only
  cut that to 4 MB; a 6.5 MiB zone with the two 512 KiB slots reserved at
  map start to 1.9 MB, 338 evictions, no failed rebuild, the jump lands
  (rerun identical). The Hunk left after the frame map drops from 2.86 MB
  to 2.33 MB (a legacy Balmora region map leaves 3.55 MB). Smaller slots
  (256 KiB, outgrown) were unstable across reruns; a 7 MiB zone without
  slots worked but leaves 1.81 MB. Other towns and the open world need the
  same measurement.
- Reads that are not budgeted finely enough: a frame reads its budget plus
  one unit, and a unit can be one whole lump of a streamed image (a large
  terrain or lighting lump). Hard per-frame bounds need resumable decoders.

## Tests

`tests/test_chim_engine_native.py` compiles the engine sources on the host:

- the zone: allocation, LRU order, locks, banks, a random stress run with an
  integrity check after every operation;
- brush loading: the arena decode equals the Hunk decode and the streamed
  decode (with a legacy load between two steps), the size bound holds,
  images with more than one submodel are refused, an arena overrun stops;
- a synthetic CHIM world through the real hooks: legacy data installs no
  hook and loads nothing; a map without a frame loads nothing; the ring
  primes before the first frame; a model placed twice is read once; each
  placement is drawn exactly once (owner or reach copy) and its efrags are
  in the right leaves; only the leaves the renderer visits send placements;
  every collision trace equals `SV_ClipMoveToEntity`; a large model streams
  over frames within the read budget; a small zone evicts and reloads; the
  cache bank keeps models across a map change; a map change leaves no locked
  block and restores the map's world model;
- the frame world: faces on their node's plane and their vertexes on it,
  marks inside the surfaces, hull 0 agrees with `Mod_PointInLeaf` at 400
  points; ground solid, air empty, the pond chunk water; terrain collides
  through the world's hull and not where no chunk is grafted; the PVS row of
  a chunk shows its neighbours and hides a chunk two away; placements in the
  terrain leaves their box touches; surface caches move with a chunk that
  stays and are released for one that leaves; static efrags and edict leaf
  numbers follow every rebuild; actors outside the grafted chunks are
  frozen; the spawn hook grafts the ring before any trace; a rebuild without
  room is retried and catches up;
- the incremental frame world (CHIM-REBUILD-COST-33): frame by frame on a
  walk with a jump it equals the full rebuild (leaves by chunk and template
  leaf, contents, vis rows, ground traces, placement and static efrags, edict
  leaves), copying only the chunks that join (small and Balmora-sized
  frames); at one chunk a frame the ground under the player is always there
  and the nearest chunk without ground stays beyond the collision margin;
  prefetch reads ahead in the walking direction only with `chim_lookahead`;
  the ring follows the view distance up to the world's visibility reach;
- source contracts for the hooks in `sv_phys.c` and `aw_scene.c`.

The existing slice-load test still proves the legacy Hunk decode.
