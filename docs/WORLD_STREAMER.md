# World streamer: every asset stored once

**Decision (owner, 8 October 2026):** AmiWind gets a world streamer in which no
asset is duplicated. Mesh geometry, collision hulls and textures are stored
once and placed by reference, the way Morrowind places its meshes; only
per-placement data (origin, angles, scale, and per-placement lighting where it
is kept) is stored per placement. Today's overlapping region maps remain only
as the baseline this design is measured against.

<!-- contents start -->
## Contents

- [Why](#why)
- [Quake first: the mechanisms the streamer reuses](#quake-first-the-mechanisms-the-streamer-reuses)
- [How choices](#how-choices)
  - [Chunk size](#chunk-size)
  - [Resident set](#resident-set)
  - [Sharing geometry between instances in the engine](#sharing-geometry-between-instances-in-the-engine)
  - [Collision for instances](#collision-for-instances)
- [Disk budget](#disk-budget)
- [Doors, changelevel and region switching](#doors-changelevel-and-region-switching)
- [Heap accounting](#heap-accounting)
- [Memory placement (requirement)](#memory-placement-requirement)
- [Visibility and culling (requirement)](#visibility-and-culling-requirement)
- [Disk layout](#disk-layout)
- [Failure modes to test](#failure-modes-to-test)
- [Measuring it](#measuring-it)
  - [Census](#census)
- [Build speed is a CHIM requirement](#build-speed-is-a-chim-requirement)
- [Staged plan](#staged-plan)
- [Temporary legacy bypasses that end with CHIM](#temporary-legacy-bypasses-that-end-with-chim)
- [Engine changes and their size (estimate)](#engine-changes-and-their-size-estimate)

<!-- contents end -->

Open and fixed CHIM bugs, by part and with the build each was found in, are on the
[CHIM Engine tracker](bugs/CHIM_TRACKER.md), generated from the bug register.
This design is **CHIM**: the overview (the name, versions, design rules,
milestones and credits) is in [CHIM](chim/README.md), and every idea that is
designed, measured or held back is in [CHIM ideas](chim/IDEAS.md). What CHIM has
done so far, feature by feature with the measured gains, is in the
[CHIM feature tracker](chim/FEATURES.md).

Status: the CHIM engine and builder run Balmora and Seyda Neen (private playtests,
CHIM 0.1.0, world format 0.5). The numbers behind the relative results below come from the shipped town maps and
the whole-world estimate and stay with the private build records, because they
are derived from the owner's game data.

## Why

Every exterior region today is a self-contained Quake map: a 768-unit core plus
an overlap of at least `sqrt(2) x draw distance + hysteresis + 32` on every
side. Each placed object is stored about ten times
([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md)), every map
carries its own copy of every texture it uses, vis gives no useful culling
outdoors ([town visibility](performance/TOWN-VISIBILITY.md)), and every region
crossing reads a whole map ([Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md)).
Interiors bake light per object, so every placement of a piece is a separate
copy of its geometry.

## Quake first: the mechanisms the streamer reuses

| Part | Quake / AmiQuake mechanism | What changes |
| --- | --- | --- |
| Shared object geometry | External brush models (id1's `maps/b_*.bsp`), loaded by `Mod_ForName`, found by name in `mod_known`; inline models shared by many `func_wall` placements inside one exterior map today | One model per converted variant, shared by every placement in the game, not only inside one map. |
| Placements | The immutable placement catalogue in `aw_scenery.c`: one render entity and box per placement, drawn through `cl_visedicts`, clipped by `AW_SceneryClip` | Catalogues per chunk; a placement record names a shared model. |
| Collision for instances | Quake hulls per brush model, traced in model space with the entity's origin and yaw (`SV_ClipMoveToEntity`, brush entities) | One hull set per unique model; the placement transform is applied at trace time, as brush entities already work. Pitch, roll and scale cannot be applied to a Quake hull, because hulls are pre-expanded by the player box: tilted or scaled placements keep their own hull variant. |
| Keeping models across crossings | `Cache_Alloc` / `Cache_Check` LRU policy; Quake's `Z_*` memory zone (non-moving first fit, merging free blocks) for the allocator | Brush models live on the Hunk and are dropped at every map change (`Mod_ClearAll` marks them `NL_UNREFERENCED`; `Host_ClearMemory` frees the Hunk to its low mark). Cache blocks are moved by `Cache_Move` when the Hunk grows, and brush models hold pointers, so they cannot live in Cache blocks as they are. A non-moving model zone with a Cache-style LRU list keeps them. |
| Terrain chunks | BSP29 brush models read by the existing `Mod_Load*` section loaders | A chunk holds terrain, terrain collision and its placement catalogue; no visibility lump outdoors. |
| Draw order | Edge renderer: brush entity surfaces sorted by world key and 1/z (`r_bsp.c`, `r_edge.c`) | As with today's building `func_wall`s. A later step can splice chunk roots under fixed axial grid nodes so `R_RenderWorld` walks them in exact BSP order. |
| Lighting outdoors | Light entities, the ericw `light` compiler, lightstyles (`R_AnimateLight`) | Terrain chunks are lit with neighbouring geometry present as shadow casters (`_shadow` brush entities). Exterior objects are already shared and carry no per-placement lightmaps; that stays. |
| Lighting indoors | Per-object baked lightmaps today | See "Lighting choices for instances" below. |
| Prefetch | The read-ahead experiment in `aw_stream.c` (a Cache block filled 8 KiB per frame) | Becomes a queue of chunk and model reads with a per-frame byte budget. |
| Distant view | The fogged terrain horizon pass ([distant terrain](DISTANT_TERRAIN.md)) | Fed from a resident whole-island heightfield. |
| Interiors | One Quake map per interior, `changelevel` through doors | Kept as maps (interior walls and floors stay world brushes, because indoors vis works); props become shared models with per-placement lighting. |

No Quake mechanism exists for a floating coordinate origin: the 4096-unit
coordinate limit needs the active area re-centred when the player moves far
(see "Coordinates").

## How choices

### Chunk size

Measured grains: 2048 (one Morrowind cell), 1024, 512 and 256 units.

- The resident set is "everything within draw distance + hysteresis of the
  owned chunk". At 1024 and 512 units that ring covers about the same area as
  a region map's coverage today, so the resident heap does not fall; with
  instanced per-chunk copies it rises.
- At 256 units (an eighth of a cell) with shared models, the median ring
  needs a little over half of today's median town map in the measured town,
  and the worst town ring falls below today's worst region.
- Objects are assigned by origin. The origin rule makes a chunk's content box
  grow by its objects' overhang (up to about 700 units in a town) and pulls
  extra chunks into the ring; the bounds rule (clip terrain pieces at chunk
  edges; place an object in every chunk its bounds touch, by reference only)
  keeps the ring tight. Placements are references, so the bounds rule costs a
  few bytes per extra reference, not a copy.

Choice: 256-unit chunks, bounds rule.

### Resident set

- Always resident: a whole-island heightfield (17 x 17 samples per LAND cell,
  well under 1 MB), water table, sky, sea plane, region and door tables, the
  texture directory and the model directory.
- Not resident: distant object shells for the whole island. Beyond the draw
  distance the renderer paints fully fogged colour, so silhouettes are not
  drawn; a whole-island shell set would cost megabytes for nothing visible.
  Shells (the mold prototype) remain an option for the outer band of the ring.
- Ring: render parts of every chunk within draw distance + hysteresis
  (+ a 256-unit prefetch margin), collision parts only within the 224-unit
  collision margin; shared models stay resident while any resident chunk
  places them, then age out LRU.

### Sharing geometry between instances in the engine

| Option | Engine work | Memory | Visual |
| --- | --- | --- | --- |
| A. One brush model per variant, no per-placement lightmaps (exterior today) | Model zone and library loading only | Geometry once per ring | Objects lit as their variant is lit today |
| B. Shared vertexes, edges and surfaces with a per-entity lightmap table | `msurface_t` lightmap pointer looked up per entity; the surface cache (`d_surf.c`) keyed by surface and entity | Geometry once; lightmaps per placement | Baked light per placement (interiors as today) |
| C. Shared model, per-entity light level (like alias models: `R_LightPoint` at the origin) | A light level per placement in the span drawer | Geometry once, no lightmaps | Flat per-object light; fine for small props, poor for walls |
| D. Run-time scale and tilt for rendering | Scale in `R_RotateBmodel` / bmodel transform; texture and lightmap extents scale with it | One geometry per mesh instead of per (mesh, scale, tilt) | Same; collision still needs a hull per scale and tilt |

Choice: A outdoors; B for interior pieces that are walls, floors and large
furniture, C for small interior props; D after A and B work, because scale and
tilt variants multiply the number of models several times over.

### Collision for instances

One hull set (hull 1 and hull 2) per unique model, placed with origin and yaw at
trace time, as `func_wall` brush entities already are. Tilted and scaled
placements keep their own hull variants (a Quake hull is expanded by the player
box in model space and cannot be rotated off-axis or scaled). Terrain collision
is part of each chunk. Only chunks within the collision margin have their
collision parts loaded.

## Disk budget

Owner limits: classic FFS partitions below 2 GiB, drive images below 4 GiB
([build output](BUILD_OUTPUT.md); the limits, the savings measured so far and the size budget of the whole game are in [disk space](chim/DISK_SPACE.md)); two drive images are the absolute maximum
for the whole game, and the real target is close to the original game's art
and world data plus our terrain and lightmaps.

Estimated for the whole game (Vvardenfell, Tribunal and Solstheim, exteriors
and interiors, every object with a mesh), map payload only:

- Today's region maps: more than ten times the original's whole
  Data Files folder; several drive images. Exterior geometry, repeated in
  every overlapping region, is about two thirds of it; textures repeated per
  map are larger than the original's entire texture set.
- Streamer with interiors kept as today: interiors become most of the bytes
  (they repeat every placed piece with its baked light); fits in two drive
  images.
- Streamer with instanced interiors (option B / C): about one fifteenth of
  today, one partition-pair of one drive image including sound, music and
  video. What remains, in order: per-placement interior lightmaps, interior
  geometry (one model per variant), terrain geometry, exterior geometry, hulls.
- Run-time scale and tilt (option D) removes most of the remaining object
  geometry: the game uses several times more (mesh, scale, tilt) variants than
  meshes.
- Further levers toward the original's size: coarser interior lightmaps
  (32-unit luxels quarter them), error-bounded terrain simplification (flat
  ground does not need full LAND resolution), C instead of B for small props.

## Doors, changelevel and region switching

- Exterior to interior: unchanged `changelevel`; exterior chunks go with the
  Hunk, the model zone may keep shared models that interiors also place.
- Interior to exterior: the arrival position selects the owned chunk; the ring
  is loaded before the first frame.
- Between exterior chunks: no map change and no server restart. The region
  directory (`aw_world.c`, `world/regions.awr`) becomes a chunk index; the
  continuity list in [cell changing](CELL_CHANGING.md) still applies to doors.
- Coordinates: the server keeps a local frame (a 3 x 3 cell frame fits inside
  +-4096). Entering another frame shifts every resident chunk, placement and
  edict by the frame offset in one step without reading anything.

## Heap accounting

The map budget stays 11,534,336 bytes with the fixed debits of
`check_world_map_heap.py`. The streamer's part is: resident layer + render
parts of the ring + collision parts within the margin + shared models placed
by the ring + texture pool (union of the ring's textures) + placement records +
the largest lump being read. Island-wide, the estimate moves almost every
over-budget exterior under budget at 256 units; it under-predicts the measured
town by about 10-20 % (more at the worst ring), and prefetch adds about a
quarter, so a few dense towns and Solstheim's largest settlements stay near
the limit and need the far-band shells or a shorter fog distance there.

## Memory placement (requirement)

Expansion memory is not uniform: an Amiga can have Fast RAM on the CPU card and on
Zorro III cards, at different speeds, and `MEMF_FAST` does not say which is which. The
streamer therefore never asks for one large heap, which could land entirely in the
slowest bank and make every frame slower. It uses three separately allocated roles:

| Role | Contents | Placement |
| --- | --- | --- |
| Core working memory | Data touched every frame: rendering, collision, active entities | The fastest Fast RAM; allocated first, at the baseline size |
| Caches | Resident chunks, shared models and textures, decoded data | Any Fast RAM, slower banks allowed; grown in steps, shrunk when an allocation fails, evicted to make room |
| Loading buffers | Disk reads and decoding scratch | Sized for the transition peak (current and incoming area at once) |

The baseline (2 MiB Chip RAM, 16 MiB Fast RAM) must always work with the core alone.
Extra memory is used only when the player allows it, and only for caches, so it means
fewer loading pauses, never heavier frames. Free-memory queries (`AvailMem`) are advisory:
every allocation must still be checked. Chip RAM needs (display, sound) are separate.

## Visibility and culling (requirement)

The streamer must not lose what Quake's visibility data gives (decided 8 October 2026). Converted
buildings were brush entities that `vis` ignores, and an entity linked to more than 16 leaves
counts as visible everywhere, so 589 of 590 Balmora building models were drawn every frame
([Town visibility](performance/TOWN-VISIBILITY.md)). For the streamer:

- Every placement is linked to the leaves it touches (Quake's efrags for static entities), so the
  potentially visible set culls it; placements that would span more than 16 leaves are flagged.
- Chunk geometry keeps structural world brushes, so `vis` can occlude; nothing becomes a brush
  entity just to make it movable or shareable.
- Per-chunk BSPs stay shallow: clipping building faces through a deep world BSP is 67-82 % of a
  Balmora frame ([RENDER-BMODEL-FRAGMENTS-32](bugs/RENDER-BMODEL-FRAGMENTS-32.md)).
- Every change is checked with the renderer counters (`dbg rcount`: entities sent, faces
  clipped, BSP nodes per face, surface cache builds), before and after, and a regression test
  keeps the counts on the benchmark cameras from getting worse.

## Disk layout

- Model pack: every shared model once, with a directory by name.
- Texture pack: every texture once.
- Chunk packs: one per 3 x 3 cell frame, a directory of chunk offsets, then
  each chunk's render part before its collision part; one open per frame, then
  seeks.
- Packs split at partition boundaries like today's world volumes.

Measured on FFS (8 October 2026, FS-UAE, 30 buffers): 16 KiB reads at random
offsets in an 8 MB file ran at 0.44 MB/s (36 ms per seek, 11.6 % of the CPU
left for other tasks), against 17 MB/s reading straight through
([STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md)). FFS finds a position in a
large file by walking its list of extension blocks, so seeking gets dearer as
the file grows. Packs are therefore written in the order they are read
(spatially, render part before collision part), a crossing reads one
contiguous run, and pack size and buffer count are measured, not assumed. Real
hardware numbers are still needed.

## Failure modes to test

- Seams and T-junctions where terrain is clipped at chunk edges.
- Popping: an object reaching into view from a chunk outside the ring.
- Light seams at chunk edges (neighbours must cast shadows during the bake).
- Load hitches on slow IDE: the worst crossings (entering a town, many new
  models) are one to two megabytes; at 1-2 MB/s that is longer than the time
  to walk 256 units, so reads are sliced between frames and start early.
- Model slots: `MAX_MODELS` (256, a byte on the wire) and the 256-entry
  `mod_known` / edge cache limit. A 256-unit ring with shared models places
  fewer distinct models than today's largest region; per-chunk copies would
  exceed 256 in dense towns.
- Fragmentation of the model zone; a compaction pass is the fallback.
- Load time and hitches can only be judged in the emulator and on hardware;
  the real A1200 IDE range assumed here is 1-5 MB/s.

## Measuring it

`tools/world_chunk_estimate.py` (measurement only) reads one town's region
maps and region table and reports the duplication factor (placements stored
over unique placements), chunk sizes, the resident heap per ring centre and
bytes per crossing, in `instanced` or `library` (shared models) mode:

```text
python3 tools/world_chunk_estimate.py MAPDIR REGIONS.txt --sdk SDK \
    --grain 256 --mode library --rule bounds --out chunks.json
```

### Census

`tools/asset_census.py` (also `build_aga.py census`) measures the whole game
asset by asset: unique meshes, hulls and textures in AmiWind form, scale and
tilt variants, per-chunk rings at 256, 512 and 1024 units with a street walk
through a town's doors, light per placement from converted interiors, terrain
as compiled and as a heightfield, and the disk total against one drive image.
Results and recommendations: [ASSET_CENSUS.md](ASSET_CENSUS.md). In short: the
whole game fits one drive image; tilt, not scale, multiplies the variants;
hulls are the largest kind of world data.

## Build speed is a CHIM requirement

Development must not wait on the builder. The CHIM builder uses the same
profiler as today's builder (per-stage CPU, cores against jobs, critical path,
idle-core warnings) and records an input fingerprint and output manifest per
pack, so a change rebuilds only the packs it reaches; releases still build from
scratch. Every builder change is measured with `tools/build_profile.py report
--compare` before and after. See [BUILD_PROFILE.md](BUILD_PROFILE.md).

## Staged plan

1. Measure (done for one town and the island estimate).
2. Converter: model pack, texture pack, chunk packs and index for one town,
   with a check that every placement, every model and every terrain face is
   stored exactly once. Done for Balmora:
   [CHIM world format](chim/WORLD_FORMAT.md).
3. Engine: model zone with LRU, library models kept across map changes, chunk
   loader through the existing section loaders, per-chunk placement
   catalogues, collision parts, frame re-centring.
4. FS-UAE: the Seyda Neen crossing route, A/B/C/D: today's regions, shared
   models with regions kept, the streamer at 512 and at 256 units, plus a drift
   rerun of A.
5. Interiors: shared props with per-placement lighting (B and C).

## Temporary legacy bypasses that end with CHIM

- Seyda Neen heap: the recorded maps sn019, sn026 and sn035 pass the strict world-map heap gate
  through a temporary pre-CHIM bypass (`config/heap-bypass.json`, HEAP-SEYDA-OVERLAP-32): a
  temporary bypass for the legacy builder, removed when Seyda Neen moves to CHIM. Milestone M2
  (Seyda Neen on CHIM) must pass the strict gate without it; the builder refuses the bypass for
  maps built by CHIM.

## Engine changes and their size (estimate)

| Change | Where | Size |
| --- | --- | --- |
| Non-moving model zone with LRU list and compaction fallback | `zone.c`-style allocator | ~300 lines |
| Load a brush model into the zone instead of the Hunk; release it | `model.c` section loaders behind an allocation hook | ~400 lines |
| Library models kept across map changes, own slot pool | `Mod_ForName`, `Mod_ClearAll`, model slots | ~200 lines |
| Per-chunk placement catalogues (add, remove, render, clip) | `aw_scenery.c` | ~200 lines |
| Chunk terrain as brush entities; later a composed world tree | `r_bsp.c`, `cl_main.c` | ~150-400 lines |
| Ring scheduler, prefetch queue, per-frame read budget | `aw_stream.c`, `aw_world.c` | ~300 lines |
| Frame re-centring of chunks, placements and edicts | server and client | ~200 lines |
| Resident heightfield for the horizon pass | distant terrain pass | ~200 lines |
| Per-entity lightmap table and surface cache key (option B) | `r_surf.c`, `d_surf.c`, `model.h` | ~300 lines |
| Per-entity light level for shared props (option C) | span drawer, entity setup | ~100 lines |

About 2,500 lines of engine C, plus the converter work, which is the larger
part.
