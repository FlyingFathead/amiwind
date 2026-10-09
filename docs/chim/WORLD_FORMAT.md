# CHIM world format 0.5

CHIM is the world streamer that replaces today's overlapping region maps (the
legacy builder). This page specifies the files the CHIM builder writes and the
engine will read: every shared model, texture and terrain face stored once,
every placement stored once and pointing at a shared model, in small sector
files that a classic Amiga FFS disk reads whole, front to back.

<!-- contents start -->
## Contents

- [Principles](#principles)
- [Quake mechanisms reused](#quake-mechanisms-reused)
- [Disk layout](#disk-layout)
- [Byte order and alignment](#byte-order-and-alignment)
- [Common header (32 bytes, every file)](#common-header-32-bytes-every-file)
- [Index (`world.cwi`)](#index-worldcwi)
- [Frame file (`FRAM`, one per 3 x 3 cell frame)](#frame-file-fram-one-per-3-x-3-cell-frame)
- [Sector file (`SECT`)](#sector-file-sect)
- [Texture records](#texture-records)
- [Model records](#model-records)
- [Chunk records](#chunk-records)
  - [Placement record (48 bytes, big-endian)](#placement-record-48-bytes-big-endian)
  - [Terrain image (a world subtree)](#terrain-image-a-world-subtree)
- [Collision reference and the stair rule](#collision-reference-and-the-stair-rule)
- [Visibility and culling](#visibility-and-culling)
- [Ids and order](#ids-and-order)
- [Worlds of several frames (several areas)](#worlds-of-several-frames-several-areas)
- [Seyda Neen (0.5, M2)](#seyda-neen-05-m2)
- [Planned: all of Vivec (M3) and the open world (M4)](#planned-all-of-vivec-m3-and-the-open-world-m4)
- [Large-model cut (chunk pieces)](#large-model-cut-chunk-pieces)
- [The heap gate (0.5)](#the-heap-gate-05)
  - [The frame-map heap (image step)](#the-frame-map-heap-image-step)
- [How the engine loads it (staged plan step 3)](#how-the-engine-loads-it-staged-plan-step-3)
- [Activation: the frame map](#activation-the-frame-map)
  - [Walkable area of the special maps](#walkable-area-of-the-special-maps)
- [Far terrain sidecar](#far-terrain-sidecar)
- [Validation](#validation)
- [Statistics](#statistics)
- [The builder: fast and incremental](#the-builder-fast-and-incremental)
  - [A CHIM build ships no legacy exterior maps](#a-chim-build-ships-no-legacy-exterior-maps)
- [Measured: Balmora (format 0.2, 8 October 2026)](#measured-balmora-format-02-8-october-2026)
  - [What a read costs on FFS (measured)](#what-a-read-costs-on-ffs-measured)
  - [The walk replayed (measured)](#the-walk-replayed-measured)
  - [The walk](#the-walk)
- [Open decisions](#open-decisions)
- [Version rules](#version-rules)

<!-- contents end -->

| | |
| --- | --- |
| World format | 0.5 (major 0 = not yet read by any released engine); 0.4 had regular terrain grids only and no story-hidden placements, 0.3 chunk standing hulls without the neighbouring ground, 0.2 no placement lists, 0.1 one model pack, one texture pack and one chunk pack per frame |
| CHIM version | 0.1.0, first shipped with AmiWind v0.0.33; its own number, kept in the `CHIM_VERSION` file at the repository root, the one source: `tools/project_version.py` (`chim_version()`) and the builder receipts read it, and `generate_native` writes `chim_version.h` (`#define CHIM_VERSION`; the engine's `chim/chim.h` includes it) and the boot check's "AmiWind vX / CHIM vY" |
| Builder | `tools/chim_build.py` (package `tools/chim/`), receipts say `builder: "chim"` |
| Validator | `tools/chim/validate.py` |
| Scope of 0.5 | town exterior frames (Balmora, the Vivec Arena, Seyda Neen with the intro docks): terrain (regular or irregular), water, every placed static object with a mesh |
| Design | [World streamer](../WORLD_STREAMER.md), [asset census](../ASSET_CENSUS.md) |

Not in 0.5 (kept by today's tables and the server): actors (NPCs and creatures
stay QuakeC edicts), doors' destinations (the door bank), night lamps
(`world/lamps.awl`), fog, sky and sea plane (the resident layer), interiors
(Quake maps behind doors), the whole-island heightfield. Placements whose
drawn box leaves the frame are clamped to the frame's chunks; reach across
frames needs the owning frame in the record (a later format).

## Principles

1. **Stored once.** One brush image per model variant, one miptex per texture
   (identical content shares one entry), one owner record per placement, every
   terrain tile in exactly one chunk.
2. **Placed by reference.** A placement record names a model by id. The few
   records that chunks other than the owner also need (the bounds rule) are
   32-byte copies of the record, never geometry.
3. **Read whole, in the order it is stored.** A frame is cut into sectors of
   3 x 3 chunks; each sector is one file holding its chunks and every model
   and texture first needed there, so entering a sector is one read of one
   small file. Files are written whole, one after the other, in the order a
   walk meets them (Hilbert order). On FFS a seek costs about one
   extension-block step per 36 KiB travelled, so a random position in a large
   file is slow while a whole small file reads at full speed
   ([STREAM-FFS-SEEK-32](../bugs/STREAM-FFS-SEEK-32.md), "What a read costs"
   below).
4. **Quake first.** Model and terrain data are BSP29 lumps that the engine's
   existing loaders decode; CHIM adds only directories and placement records.

## Quake mechanisms reused

| CHIM part | Quake / AmiQuake mechanism | Reused as is / what changes |
| --- | --- | --- |
| Shared model | External brush model (id1 `maps/b_*.bsp`), `Mod_LoadBrushModel` | A model is a BSP29 lump set with one dmodel; decoded by the same `Mod_Load*` section decoders through `AW_LoadBrushSection` (`model.c`). |
| Reading a model or chunk | AmiWind's streamed BSP load (`AW_TryStreamBrush`: a file position base plus lump offsets, 16 KiB slices decoded straight into the Hunk) | Base = record offset in the sector file; lumps are in the decoder's order, so the read is sequential. |
| Model textures | `Mod_LoadTextures` / `Mod_LoadTexinfo` (`loadmodel->textures[]`) | Lump 2 lists global texture ids; a CHIM texture decoder fills `textures[]` from the resident texture pool; `Mod_LoadTexinfo` is unchanged. |
| Texture pool | miptex_t as in a BSP texture lump, `R_InitTextures`, animated/`*`/`sky` names | Each miptex once, little-endian as in a map; the per-texture part of `Mod_LoadTextures` decodes it. |
| Self-lit, liquid, sky behaviour | Texture names (`emitN_` in `r_surf.c R_EmissiveLevel`, `*`, `sky`) and texinfo flag `TEX_SPECIAL` | Kept in the miptex name and texinfo flags. |
| Placements | AmiWind's immutable placement catalogue (`aw_scenery.c`): render entity + drawn box, no edict | One catalogue per resident chunk instead of per map; the record carries model id, origin and yaw. |
| One placement in several chunks | Efrags: an entity linked into several leaves is drawn once per frame (`r_efrag.c`, `visframe != r_framecount`) | Reach copies carry the global placement id; the engine marks it per frame, as efrags do. |
| Placements culled by visibility | Efrags and static entities: an entity is linked into the leaves its box touches (`R_SplitEntityOnNode`) and drawn only when one of them is marked visible | The record stores the drawn box and the number of non-solid leaves it reaches; more than 16 (`MAX_ENT_LEAFS`, visible everywhere for an edict) is flagged. |
| Collision of a model | Brush-entity hulls traced in model space with origin and yaw (`SV_ClipMoveToEntity`), hull 1 = standing box (`player_hull.py`) | One hull set per variant (scale and tilt baked, yaw at trace time), as `func_wall` today. |
| Terrain of a chunk | The world model: nodes with faces on their planes, leaves with contents (empty, solid, water) and marksurfaces, hull 0 = the node tree, hull 1 = clipnodes | A shallow world subtree per chunk, written directly from the LAND heights (no qbsp); the engine grafts the chunk roots under its frame grid, so terrain is world geometry, never a brush entity. Water contents (swimming) come from the water leaves. |
| Terrain light | Lightmaps per face (`R_BuildLightMap`), shared identical blocks in the light lump | Every ground face points at one block of the uniform bake value. |
| Keeping models across chunk changes | `Cache_Alloc` / `Cache_Check` LRU policy, `Z_*` non-moving zone | Engine work (staged plan step 3): brush models hold pointers, so they live in a non-moving model zone with a Cache-style LRU. |
| Visibility | The PVS: one compressed bit row per cluster (`Mod_DecompressVis` zero runs), `R_MarkLeaves` marks what may be seen | One row per chunk over the chunks of its frame (Quake 2 calls them clusters); the builder computes it from the ground and the solid volumes of placed objects (see "Visibility and culling"). |

No Quake mechanism stores many brush models in one file with a directory:
Quake's PAK is a flat file directory without spatial order, and a `.bsp` holds
one world. The sector files below are CHIM's own, kept minimal.

## Disk layout

```text
chim/world.cwi                    index: settings, file table, model and texture directories
chim/frames/x-03/y-02/frame.ccf   frame of cell (-3, -2): chunk directory, sector table
chim/frames/x-03/y-02/s00.ccs     sector 0 of that frame (s00 ... s63 for 8 x 8 sectors)
```

Classic FFS rules, hard requirements checked by the validator:

- every file at most 1 GiB (FFS files must stay well under 2 GiB); a sector
  file is a few hundred kilobytes (Balmora's largest: 1.4 MB);
- every name at most 30 characters;
- at most 72 entries per directory (one FFS directory block has 72 hash
  chains): one directory per frame column (`x-03`), one per frame inside it
  (`y-02`) holding the frame file and its 64 sector files;
- files are written whole, one after the other, in this order: index, then
  per frame its frame file and its sector files in pack order (frames in
  Hilbert order of their centre cells). The disk image builder must copy
  `chim/` in the same order, after every other file, so each file occupies
  one contiguous run of blocks.

On the image (`tools/build.py --builder chim`), the world is one more world
volume: the image step (`tools/build_aga.py image --chim-world`) writes it
onto its own partition `DW<n>` (volume `AW_WORLD<n>`, the next free world
volume) under `id1/chim/`, and `world/volumes.awv` counts it. The engine adds
`AW_WORLD0:id1` ... `AW_WORLD<n>:id1` to its search path, so `chim/world.cwi`
opens like any other game file. `tools/chim/disk.py` writes the partition in
pack order and reads every file back. It then runs the disk-layout gate on
the written partition; the build stops if the gate fails:

- names, directory entries and file sizes as above;
- every file is whole: no block of another file lies inside its span
  (directory, root and bitmap blocks may);
- the files lie in pack order, counted from the start of the packed region
  (right after the largest gap between file blocks, which is the free rest of
  the disk), wrapping at the end of the partition.

The gate's report goes into the image's `build.json` (`chim_world`), with the
builder, CHIM and format versions. Balmora (8 October 2026): 66 files, the
largest 1.4 MB, the longest name 9 characters, at most 65 entries in one
directory (a frame folder: frame file and 64 sector files, 7 under the
limit), every sector file one run of blocks.

## Byte order and alignment

- CHIM structures (headers, directories, placement records, index): **big
  endian**, the 68k's own order; read without swapping.
- Brush images (models, chunk terrain): **little-endian BSP29**, exactly as in
  a Quake map, because the reused decoders call `LittleLong`/`LittleFloat`.
  (A later format may pre-swap them; see "Open decisions".)
- Every record, lump and directory entry starts on a 4-byte boundary; padding bytes
  are zero.

## Common header (32 bytes, every file)

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | char[4] | `CHIM` |
| 4 | char[4] | kind: `INDX`, `FRAM`, `SECT` |
| 8 | u16, u16 | format major, minor (0, 5) |
| 12 | u32 | header bytes (32) |
| 16 | u32 | entry count |
| 20 | u32 | directory offset |
| 24 | u32 | data offset (first record) |
| 28 | u32 | file bytes (must equal the file size) |

An engine refuses a major it does not know, with a message naming both
versions.

## Index (`world.cwi`)

Header; settings (40 bytes); table of contents (32 bytes); file table (60-byte
rows); model directory (24-byte rows, model id order); a u32 table of model ids
sorted by name (binary search by name); texture directory (24-byte rows,
texture id order); names (NUL terminated, UTF-8). The engine reads it at start
and keeps it.

Settings: f32 draw distance (540), f32 hysteresis (96), f32 collision margin
(224), f32 prefetch margin (256), u16 chunk grain (256), u8 terrain light
value (12), u8 reserved, u32 placements, u32 models, u32 textures, u32 frames,
u16 sector size in chunks (3), u16 reserved.

Table of contents: u32 offsets and counts of the file table, model directory,
name order table, texture directory and names.

File row: char[4] kind (`FRAM` or `SECT`), u16 sector index in its frame, i16
frame centre cell x, i16 cell y, u16 reserved, u32 bytes, u32 CRC-32 (zlib
polynomial), u32 records, u32 reserved, char[32] path below `chim/`, NUL
padded (at most 31 characters).

Model row: u16 file row (its home sector), u16 reserved, u32 offset in that
file, u32 bytes, u32 render bytes, u32 name offset, u32 FNV-1a hash of the
name. Texture row: u16 file row, u16 reserved, u32 offset, u32 bytes, u32 name
offset, u32 name hash, u16 width, u16 height.

## Frame file (`FRAM`, one per 3 x 3 cell frame)

Header; frame block (32 bytes): i16 centre cell x, y; f32 frame origin x, y in
Morrowind units (local coordinates are `(world - origin) x 0.25`); f32 low
corner x, y in local units; u16 grain, u16 chunks across (x), u16 chunks
along (y), u16 sector size in chunks; u32 placements owned in this frame. Then
the chunk directory, 28-byte entries in **pack order**: u16 chunk x, u16 chunk
y, u16 sector, u16 reserved, u32 offset of the chunk record in the sector file,
u32 render bytes, u32 collision bytes, u16 owned placements, u16 reach copies,
i16 lowest and highest drawn z. A chunk's index is its position in this
directory. Then the sector table, 12-byte entries in pack order: u16 sector x,
u16 sector y, u32 bytes, u32 CRC-32.

Pack order: the frame's sectors in Hilbert order, and inside each sector its
3 x 3 chunks in Hilbert order (`format.sector_order`).

## Sector file (`SECT`)

Header; record directory (16-byte entries): char[4] kind (`CHNK`, `MODL`,
`TEXR`), u32 id (chunk index, model id, texture id), u32 offset, u32 bytes;
then the records, each starting on a 4-byte boundary right after the previous
one (the records tile the file exactly). Order: the sector's chunks in pack
order, then the models first needed in this sector (id order), then the
textures first needed here (id order).

A model's or texture's **home sector** is the sector in which a walk through
the frame's chunks in pack order first meets it (see "Ids and order"). Every
model and texture is stored once, in its home sector; a ring that needs a
model homed in a sector outside the ring reads that one record.

## Texture records

Each a Quake `miptex_t` (16-byte name, width, height, four mip offsets, four
mip levels of 8-bit pixels in the game palette), little-endian.

- The miptex name is what the engine sees: `surfaceN`, `emitG_N` (self-lit
  level G), `flatN` (flattened window panels), the ground materials `gN` and
  `*water`. N is the texture id.
- The identity name (in the index) records where the texture came from (mesh
  texture, size, tint, glow, or ground material).
- Two sources with the same engine class (self-lit level, liquid, sky, plain)
  and the same pixels in every mip level are one texture.
- Pixels are made as the legacy maps' are. Each material is quantized by the
  converter's own function (`prepare_mesh_bsp.material_image`). Every pixel is
  then moved off the seven palette entries that the image's sky overlay
  repaints as sky colours (83, 95, 133, 140, 156, 221 and 222), with the
  overlay's own mapping (`sky_palette_overlay.remap_miptex`). This is applied
  whenever the palette passes the overlay's guard: each banked colour lies
  within two units of its replacement, so a pixel's colour never changes
  visibly. Without the move, CHIM texels on banked entries were drawn as
  bright sky colours (CHIM-TEXTURE-SPECKS-33). Balmora had 1,140 such texels;
  in bm028, 333 bright specks against legacy's 5. Since the fix, no texel of a
  CHIM texture lies on a banked entry, and every visible bm028 texture equals
  its legacy counterpart. `tools/chim/validate.py --palette` (passed by
  `chim_build.py --validate`) refuses a world with texels on banked entries.
- Opt-in texture effects ([TEXTURE_EFFECTS.md](TEXTURE_EFFECTS.md), none by
  default) change the textures they target after that move; the receipt's
  `texture_effects` lists each effect and the textures it changed, and the
  validator exempts exactly those from the sky-bank check.

## Model records

A model's name is its variant: mesh path below `meshes/` without `.nif`,
`@s` scale, `@t` tilt (x, y rotation, plus yaw when tilted, because tilt and
yaw do not commute), `@f` window flattening shift, `@v` visual offset; for
example `x/ex_hlaalu_b_01@s1`. Two variants that produce byte-identical images
are one model (the receipt lists the aliases).

Each record is a **brush image**: a BSP29 header (version 29, 15 lump
offsets relative to the image start) and the lumps in this file order:

```text
vertexes, edges, surfedges, textures, lighting, planes, texinfo, faces,
marksurfaces, visibility, leafs, models, nodes, entities | clipnodes
```

That is the order `Mod_LoadBrushModel` decodes them, except that the
clipnodes (the standing hull: collision only) come last. Everything before
them is the **render part** (`render bytes` in the model directory); a loader
can decode the render part now and the collision part only when a chunk
within the collision margin places the model.

Contents (the legacy converter's rules, `prepare_mesh_bsp`):

- **faces, texinfo, vertexes, edges, surfedges, planes**: the variant's faces in
  the model frame (scale and tilt applied, yaw left for the entity), texture
  vectors in texels, vertices shared within the model, edge 0 unused, face
  planes first in the plane lump (16-bit face plane indices), planes of type 3;
- **textures** (lump 2): `i32 count` and `count` global texture ids; texinfo
  miptex fields are indices into this list;
- **lighting**: empty; exterior objects carry no lightmaps (as today);
- **leafs**: leaf 0 solid, leaf 1 empty; no marksurfaces, no visibility;
- **nodes**: the point hull (hull 0), one run of planes per convex collision
  piece; outside a plane goes on to the next piece, inside all is solid;
- **clipnodes**: the standing hull (hull 1, also named as hulls 2 and 3, which
  the engine never traces), the same pieces expanded by the standing box, or
  the exact union compiled by qbsp for hollow exact-bevel shells;
- **models**: one dmodel: bounds (in the model frame, +-1 unit), origin 0, head
  nodes (point root, standing root, standing root, standing root), no vis
  leafs, all faces;
- **entities**: the model's flame emitters (`aw_flame` with model-frame
  origins), or empty.

## Chunk records

Each chunk record (in its sector file):

```text
chunk head (24)      'CHK0', u16 owned, u16 reach, u32 image offset, u32 image render bytes,
                     u16 PVS row bytes, u16 leaves in the terrain subtree (leaf 0 not counted),
                     u16 placement row bytes, u16 reserved
placement records    owned (by id), then reach copies (by id), 48 bytes each
PVS row              compressed visibility row over the frame's chunks (Quake vis compression)
placement row        compressed bit row over the frame's placements (bit k = placement id
                     lowest-in-frame + k): the placements a view from this chunk may see
terrain image        world subtree (render lumps)        } render part
                     terrain clipnodes                   } collision part
```

### Placement record (48 bytes, big-endian)

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | u32 | placement id (global; 0..n-1 in pack order of the owner chunks) |
| 4 | u32 | Morrowind reference number (`FRMR`) |
| 8 | u32 | model id |
| 12 | f32 x3 | origin, local units |
| 24 | f32 | yaw in degrees (Quake `angles[1]`) |
| 28 | u16 | owner chunk index |
| 30 | i8, i8 | source cell relative to the frame's centre cell |
| 32 | i16 x3, i16 x3 | drawn box mins, maxs (local units, rounded outward) |
| 44 | u16 | non-solid leaves the drawn box reaches, over every chunk it touches |
| 46 | u16 | flags: bit 0 = more than 16 leaves (`MAX_ENT_LEAFS`); bit 1 (0.5) = story hidden |

The save key of a placement is (source cell, reference number), the same key
Morrowind uses. The owner chunk holds the placement's origin; the record in
the owner chunk is the **owner record**. Every other chunk that the drawn box
touches holds an identical **reach copy**. The drawn box is the engine's
(`AW_SceneryCapture`): the eight corners of the model's bounds turned by the
yaw, one unit outward, stored so the engine can link the placement into
leaves before its model is loaded. A chunk is resident whenever it is inside
the ring, so a placement that can be seen from the ring is always in a
resident chunk; the engine draws it once per frame by its placement id.

### Terrain image (a world subtree)

A brush image in local coordinates whose nodes and leaves are a piece of the
world BSP, for the chunk's tiles:

- tree: axial splits on tile edges (alternating x and y, halving the tile
  range), then per tile the vertical plane through its diagonal when it is two
  triangles, then the ground plane of each triangle (back: solid leaf 0),
  then, where the ground dips below the water level, the water plane (back:
  water leaf, front: air leaf). Node 0 is the root; dmodel head node 0 is the
  root (the world's point hull is its node tree), head node 1 the standing
  hull. Leaf bounds reach the frame ceiling (2048) above the ground; every
  non-solid leaf lists its tile's faces as marksurfaces; no visibility lump
  (visibility is the chunk's PVS row);
- faces sit on their node's plane, `side` set for faces seen from the plane's
  back (the downward water face), as in a Quake world;
- tiles of the converter's terrain step (128 units, every fourth LAND sample),
  heights and materials from the legacy samplers (`import_town.terrain_at`,
  `terrain_material` with its repairs); chunk edges lie on the tile grid, so
  every tile is in exactly one chunk;
- per tile one quad when its two triangles are coplanar, otherwise two
  triangles (corners 0-1-2 and 0-2-3, as the converter's brushes), split at
  240 texels like converted meshes; texture vectors are qbsp's world
  projection (scale 1, no shift);
- water: where the ground lies below the water level (0), the part of each
  tile face below it, flattened to the water level, twice: facing up and
  facing down (as qbsp emits liquid faces), texture `*water`, `TEX_SPECIAL`,
  no lightmap; the water leaves give the water contents (swimming), as in a
  Quake world;
- light: every ground face has style 0 and lightmap offset 0 into one shared
  block of the uniform bake value (today's terrain bake has no light sources:
  `light -minlight 24` stores 12 in every sample);
- collision: the point hull is the node tree itself; the standing hull is
  each tile polygon extruded down to the converter's floor (-1024) as one
  convex piece, expanded by the standing box as for models;
- seamless standing hull (0.4): the engine grafts each chunk's standing hull
  under routing planes at the chunk edges, so a point is classified only by
  the chunk it lies in. Each chunk's standing hull therefore also holds the
  pieces of every tile of the frame that the standing box reaches from inside
  the chunk (one ring of tiles around it while a tile is wider than the box,
  7.32 units), and the ground of the neighbour is felt at the border. The
  pieces are routed, not chained end to end: axial clipnodes at the expanded
  pieces' edges split the chunk until a part meets at most eight pieces (or
  no cut helps), and each part chains only the pieces that reach it. Each
  piece is expanded exactly: the Minkowski sum with the standing box, edge
  bevels included, as Quake's `ExpandBrush` does. With face planes alone a
  box rested up to 8 units above convex ridges
  (CHIM-TERRAIN-HULL-BEVELS-33). That fix changed the hull's contents only,
  not the layout or the contract, so the format stayed 0.4. Balmora
  (128-unit tiles, 60 sampled chunks, 200 point tests each, exact
  expansion), clipnode bytes per chunk and clipnodes visited per point test
  (mean, p95):

  | Standing hull | Bytes | Visits |
  | --- | ---: | --- |
  | 0.3: own tiles, one chain (not seamless) | 610 | 19.5, 38 |
  | own tiles and ring, one chain | 2,284 | 50.8, 116 |
  | own tiles and ring, routed, at most 8 per part (0.4) | 5,076 | 19.9, 30 |
  | own tiles and ring, routed, at most 2 per part | 9,315 | 15.2, 22 |

  The whole Balmora world is 21.3 MB on disk (17.5 MB in 0.3), and the
  largest resident ring is 5.55 MB. Validator: near every chunk edge, a box
  whose bottom lies 0.25 units below the highest ground under it, the
  neighbour's included, is solid in the chunk's standing hull, and a box
  0.25 units above that height is empty.

## Collision reference and the stair rule

Reference behaviour (Morrowind, as OpenMW 0.51 reimplements it): collision is
against the authored triangles or the NIF RootCollisionNode, never convex
hulls. The player steps up 34 units (8.5 here, Quake's STEPSIZE), walks slopes
up to 46 degrees (`AW_WALKABLE_Z` 0.69, about 46.4 degrees) and steps down 62
units (15.5 here).

Placed models' hulls come from the converter's shared pieces
(`mesh_geometry.collision_pieces`, through `prepare_mesh_bsp._prepare_model`).
The shared stair rule (COLLISION-STAIR-SLOPE-32) therefore applies to CHIM as
it does to the legacy maps, with no CHIM copy. Where a convex proxy invents a
face steeper than walkable over authored treads with risers of at most 8.5
units, the piece becomes the authored collision: the RootCollisionNode, or
else the exact tread plates. A clip ramp at the stair's own slope is the
fallback. The setting `stair_mitigation` (build config) or
`--stair-mitigation` reaches the CHIM stage as `AMIWIND_STAIR_MITIGATION`.
It is part of every unit's fingerprint, it is on by default, and receipts
record it.

The change is in contents only, with no format change. The stair gate runs
on every CHIM world the builder validates (`tools/chim_build.py --validate`,
so every `--builder chim` build): the legacy gate's own step and ramp finder
and walker (`stair_walk.check_polys`), on each frame's own collision
(`chim.collision.FrameScene`: the chunks' and placements' standing hulls,
traced like a region map, including across chunk borders), with the world
contents of the chunks' point hulls (water is skipped). Each frame is cut into
cores of 1,024 units (each step is tested once, in the core holding its riser)
that run in parallel on the build's worker pool. The report is
`chim-stairs.json` (as the legacy `stair-walk.json`), and the build fails if a
flight of stairs (3 or more steps, 2 or more vertical risers) cannot be walked
up and down. With the stair rule off (debugging builds only) the gate is
skipped and the report says so.

Measured (8 October 2026, 4 workers): Balmora's world made before the stair
rule (format 0.4) in 52 s: 3,733 steps and ramps, 295 flight steps passed,
1 failed (start in solid, a world made without the rule).

## Visibility and culling

Owner rule (8 October 2026): CHIM must keep Quake's visibility working, never
turn everything into brush entities, and keep the BSP shallow. How the format
does that:

1. **Structural geometry is world geometry.** Chunk terrain is a world
   subtree (nodes, leaves with contents, marksurfaces), grafted by the engine
   under a fixed axial grid over the frame's chunks (split the chunk range in
   halves, longer axis first, at chunk edges). Nothing structural becomes a
   `func_wall` brush entity.
2. **Placements link to leaves.** Every placement record carries its drawn box
   and the number of non-solid leaves it reaches; the engine links it into
   those leaves like an efrag and draws it only when one is marked visible.
   Records that reach more than 16 leaves are flagged; for them the engine
   tests the chunks the placement touches (its owner and reach chunks)
   instead of a leaf list, so no placement is "visible everywhere".
3. **Potential visibility per chunk.** Each chunk carries one compressed PVS
   row over the chunks of its frame, Quake's vis mechanism at chunk
   granularity. The builder computes it: chunk B is in A's row when any sight
   line from a standing or raised eye in A (3 x 3 points, 33 and 97 units
   above the ground) to a point of B's content (3 x 3 points at 8 units, eye
   height and the top of the tallest drawn box in B) clears the ground and
   the solid volumes of placed objects (a 16-unit grid of vertical intervals
   surely inside something solid), or the reverse line does. Solid volumes
   are the convex collision pieces of solid objects and, for buildings with
   hollow collision shells (kept open so their underpasses stay walkable),
   the space their closed render mesh encloses: a point is enclosed when rays
   in the four horizontal directions and straight up all meet the mesh (an
   open-bottomed house still encloses its rooms; an awning, an arch or a
   courtyard open to the sky does not), sampled on an 8-unit voxel grid in the
   model frame and eroded by 24 units so that a whole 16-unit cell is inside
   (`tools/chim/occluders.py`, CHIM-PVS-HOLLOW-33). A chunk always sees itself
   and its eight neighbours; rows are symmetric and never reach beyond the
   ring. **Placement lists** (0.3) apply the same test per
   placement: a placement is in a chunk's list when a sight line from the
   chunk's eyes reaches one of 13 points of its drawn box (five on the top
   face, four side midpoints at a quarter and half its height); placements
   touching the chunk or its eight neighbours are always in it, nothing beyond
   the ring ever is. The engine draws only placements in the list of the
   player's chunk. This is sampled, not an exact portal flow: it can miss a narrow gap,
   so FS-UAE counters must confirm there is no popping before the rows are
   trusted to cull.
4. **Shallow trees.** A chunk subtree is a handful of levels (axial tile
   splits, diagonal, ground, water), and the frame grid adds about ten, so a
   brush model's faces are clipped through 15-20 nodes instead of the 27-52
   nodes per face measured in Balmora's region maps
   ([RENDER-BMODEL-FRAGMENTS-32](../bugs/RENDER-BMODEL-FRAGMENTS-32.md)).
5. **Measured, every build.** The validator reports, per chunk as the
   player's chunk: the visible share of the ring and of the frame, world faces
   (ground and water) against entity faces (models placed by the visible
   chunks), placements sent and placements over 16 leaves, leaves and chunks
   per placement, and the depth of chunk subtrees and of the frame grid.

What is not done yet: buildings themselves do not split the world BSP (a
building occludes only through the PVS rows), and a row says whether a chunk
may be seen, not which of its placements: see the measurements below and the
open decisions.

## Ids and order

1. Placements are assigned to owner chunks; the chunks are walked in pack
   order and their owned placements numbered by reference number.
2. Walking the chunks in pack order, each chunk's ground textures, then each
   placement record's model (owned then reach, by id) and that model's
   textures get the next free id when first met, and the sector being walked
   becomes their home. Two texture keys with identical content are one
   texture; an image that would list it twice lists it once.
3. Files are written in pack order, so ids grow along the disk.

## Worlds of several frames (several areas)

One world holds a frame per area (`tools/chim_build.py --area A --area B`,
`chim_areas` in the build config). No new record is needed: the index's file
table lists, per frame, its frame file and its sector files.

- Frames are laid out in Hilbert order of their cells, and the order of the
  areas given does not change a byte.
- Placement ids run on across frames. A frame's placement rows (PVL) count
  from its first id (`owned_total` placements).
- Model and texture ids follow the pack walk over every frame, and the home
  rule spans frames. A model or texture first met in an earlier frame is not
  stored again. Identical content is stored once across all areas.
- Names are unique in the world. A different model or texture under a name
  that another frame already uses gets `#2`, `#3` and so on (each area has its
  own ground materials under the same keys).
- Frames must not overlap: the builder refuses two areas whose ground boxes
  overlap, or two frames on one cell, because a placement or tile would be
  stored twice. Four Vivec districts overlap each other; a world with more of
  Vivec than the Arena needs one Vivec frame.
- The source manifest (`chim-source.json`) has one section per frame
  (`frames`: town, cell, placements, doors, terrain), and the validator checks
  each frame against its own section. The walk is measured per frame
  (`walks`), and a camera is counted in the frame that holds it.
- Placements that reach across a frame's edge are still clamped to its edge
  chunks (open decision "Reach across frames").

Measured (8 October 2026), Balmora and the Vivec Arena in one world:

- 2 frames, 1,893 placements, 622 models and 244 textures, each stored once.
- 28.2 MB in total: Balmora's frame and sector files 21.2 MB, the Arena's
  7.0 MB, the shared index 56 KB.
- 0 validator failures.
- Balmora built alone with the same code is byte-identical to before.

## Seyda Neen (0.5, M2)

Seyda Neen's exterior does not come from the town converter that Balmora and
the Vivec districts use. The scene and bsp stages build one complete town map
(`prepare_quake`: `seyda.map`; `prepare_mesh_bsp`: meshes appended), and the
image step cuts it into region maps `sn000`... (`prepare_seyda_regions`:
placements kept whole by their placed box, terrain culled against the
canonical LAND). Three things the 0.4 format could not hold, and how 0.5 holds them
(`tools/chim/seyda.py`, `tools/chim_build.py --area seyda --legacy-run RUN`):

1. Terrain that is not a regular grid. Seyda's ground uses 128-unit tiles with
   shoreline samples inserted (`prepare_world_regions.terrain_triangles`) and
   a fine 32-unit patch at the port (`prepare_quake.town_ground_triangles`).
   0.5 builds a chunk's ground from the converter's own triangles: each
   triangle belongs to the chunk holding its centroid, and chunk edges stay on
   the 128-unit tile edges so no triangle crosses one. The subtree splits on
   tile edges first, then on each triangle's edges, then the ground plane. The
   standing hull prisms are those triangles, plus the ring of triangles from
   the neighbouring tiles. The validator checks the ground against the source
   triangles (stored in the source manifest) instead of the regular grid.
2. Alias-model and sprite statics. Small models are `aw_static` alias models
   (`progs/*.mdl`, generated by the scene stage), and the town flora is
   sprites (`progs/aw_flora/f_*.spr`). 0.5 adds static records per chunk,
   after the placement records: reference number, model path index,
   frame-local origin and angles, scale, flags. The index gets a directory of
   model paths, each path stored once; the files themselves stay game files.
   Ownership and reach copies follow the bounds rule, as for placements, and
   the ids follow on from the placement ids, so the placement rows (PVL) cull
   them too. Solid ones get collision-only models (`MODL` records without
   faces) as ordinary placements, as the legacy collision-only pieces are. The
   engine draws them as static entities linked into the grafted leaves
   (efrags), streamed with their chunks. They do not count against
   `MAX_STATIC_ENTITIES` (512) the way entities in the frame map would: all of
   a town's sprites could exceed it.
3. A CHIM source stage for Seyda. It reads the same inputs as the legacy
   chain:
   - the scene stage's scenery index (`scenery/scenery-index.json`) and the
     placements it converts;
   - the bsp stage's converter profiles, per model;
   - the scene stage's generated alias models;
   - the LAND grid (`generated/seyda-neen/terrain-source.json`);
   - the town flora selection (`install_town_flora`, sprites included).

   It writes one frame at Seyda's cell. The frame origin is
   `prepare_quake.CENTRE` x 0.25, which is what the region maps, door
   arrivals, harvest catalogues and saves use; the frame map's origin gate
   checks it. The frame box is `GROUND_BOUNDS` (the town bounds plus the
   768-unit LAND apron), rounded out to the chunk grain. The intro docks
   (`intro_docks`) lie inside the same frame. Their map becomes the frame's
   second frame map (the docks' own entities), from the same chunks.

What was built (8 October 2026), against the plan above:

- Irregular ground: as planned (`tools/chim/ground.py`, `chunk_terrain(tiles=...)`). The chunk
  subtree splits each irregular tile on the vertical planes of its triangles' edges (the edge
  that cuts the fewest pieces, then the most even split) until one plane of one material is
  left. The source manifest stores the triangles (`terrain_triangles`, `terrain_size`). The
  validator checks coverage, heights, water and the standing hull seams against them. The
  frame is `GROUND_BOUNDS` rounded out to whole sectors (21 x 21 chunks). Tiles outside
  `GROUND_BOUNDS` use the same sampler over the canonical LAND of the whole island (the
  world-survey stage). The canonical LAND must equal the scene stage's audit on every audited
  cell. The frame's edge is the real coast and hills, not the audit's ocean fallback (-512).
  Ground textures come from `town.wad`, and from the world terrain's own textures for
  materials only the canonical LAND uses.
- Statics: the bsp stage's selection, profiles and converter. Two more inputs, as the later scene
  stages add them to the town map:
  - the opening references (`prepare_opening_refs.opening_references`, one reading of the
    master). Placements on the ship's disable list carry **flag bit 1, story hidden**, which is
    the legacy `aw_story_hidden` key that `aw_opening.c` hides. The tutorial barrel is
    converted and placed;
  - the town flora that the image installs, with the region layout's entries. Meshes are
    placements. A sprite with solid source collision gets a collision-only placement, its
    model without faces. The sprite itself stays a point entity of the region maps, which the
    frame map carries as an ordinary Quake static entity. Sprite records in the chunks are
    deferred until a frame holds more statics than the engine's static-entity limit (owner
    decision, 8 October 2026). Seyda Neen's region maps hold 229 such statics.
- Frame maps: `maps/seyda-chim.bsp` (the town) and `maps/intro_docks-chim.bsp`, both naming the
  same frame. The docks map is checked one way: its statics must be in the frame, and the frame
  holds the rest of the town as well. It copies the docks' own entities and turns the route
  boundary of the legacy docks map into four clip walls: `func_wall` brush models with a
  standing hull and no faces (Quake's clip brushes). The region maps' per-region worldspawn key
  `aw_render_pool` (terrain-culled faces, CHIM-HIDDEN-FACES-33) is left out and recorded.
- Parity reference: the recorded v0.0.31 Seyda Neen maps that v0.0.32 ships
  (BUILD-SEYDA-REGEN-30). The legacy region cut cannot be regenerated from scratch
  (BUILD-SEYDA-CULL-STABLE-32).
- A CHIM build ships Seyda Neen on CHIM only, with the strict heap gate and no exception
  (owner decision, 8 October 2026). The legacy Seyda Neen maps stay buildable and selectable
  with `--builder legacy`.

The sea is the water plane at z = 0 that every chunk already carries. The sky
and sea enclosure brushes of the legacy town map are not copied: the resident
layer draws them. Parity is the same two-way gate as for the other towns:
statics, alias models and sprites of the final `sn` maps against the CHIM
records, harvest catalogues `AWH4` only, and the frame origin. Seyda's legacy
private stages (BUILD-SEYDA-REGEN-30) and its heap overlap
(HEAP-SEYDA-OVERLAP-32) stop applying once Seyda runs on CHIM.

## Planned: all of Vivec (M3) and the open world (M4)

Owner direction (8 October 2026): builds go pure CHIM. Every exterior comes from the CHIM builder;
the legacy region maps stay in the code, selectable, but unused. Pure CHIM therefore needs the
whole game's exteriors. Interiors stay Quake maps behind doors. Plan, before code:

**M3, Vivec on CHIM: design (9 October 2026).** v0.0.33 ships when the areas v0.0.32 ships all
run on CHIM: Seyda Neen, Balmora and the Vivec Arena. So M3 has two stages, each built, gated
and A/B-checked before the next: (A) the Arena canton, with v0.0.32 parity; (B) all of Vivec in
one frame. The legacy Arena preview (`vivec_arena` region maps) stays buildable and selectable
(`--builder legacy`); nothing is deleted.

*Stage A: the Arena canton.*

- The frame is the existing `vivec_arena` area (`config/vivec_arena.json`): centre (36352, -87040),
  local bounds ±1536, which gives 12 x 12 chunks, 4 x 4 sectors and 16 sector files plus the frame
  file in one frame folder. That is the 0.5 layout, so stage A needs no format change.
- Placements are what the Arena region maps hold (`town_regions.town_references`). Canton bodies
  whose footprint reaches into the frame are stored whole and drawn whole: the straight cut of
  the legacy preview (VIVEC-ARENA-FRAME-EDGE-32) goes away for anything inside the view.
- Parity with v0.0.32's preview, each one a gate:
  - Residents: the walkway residents are `aw_npc` entities, which the frame map carries from the
    final Arena maps. A new frame-map check drops every carried actor onto the frame's own
    collision (`chim.collision.FrameScene`, the standing box) and compares it with the legacy
    ground contact (`check_actor_ground`, VIVEC-ARENA-ACTORS-32). A resident that would float or
    sink stops the build. Actors stay ordinary actor records, independent of how their model is
    made, so a later modular-NPC recipe replaces only the model.
  - Arrival: the town's arrival point (`config/vivec_arena.json` `arrival`) must be a standing
    spot on the frame's collision, using the engine's own arrival search
    (`arrival_spot`, VIVEC-ARENA-TP-ARRIVAL-32) on `FrameScene`.
  - Frame edge: the Arena frame touches no other frame. The frame map gets four clip walls at
    the frame bounds, as the intro docks map has, and the worldspawn key `"_chim_edge" "closed"`
    so the engine shows "Area unavailable" when the player reaches one.
  - Doors: the door bank (`scene-doors-vivec_arena.txt`) is unchanged, and the engine's scene
    fallbacks (`AW_SceneMapSize`) cover arrivals, saves, `dbg tp` and doors. Their names
    (`vivec_arena`, `vivec_arena-chim`) are checked by a test.
- Stairs and walkways: the shared stair rule including the stairs-2 walk fixes; the stair gate
  runs on the frame. The Arena's seat tiers and ramps are the reason the gate's time must come
  down first (CHIM-STAIRGATE-SLOW-33: a spatial index for the frame scene and per-core walk
  counts).
- Textures: the sky-bank gate (CHIM-TEXTURE-SPECKS-33) runs on every CHIM world.
- Ground: the Arena is on the town converter's regular grid, so it keeps the routed terrain hull.
  The compiled hull is only for irregular ground (CHIM-SEYDA-MEMORY-33).
- A/B: the same poses (the arrival point, the walkway residents, the St. Delyn walkway at the
  former cut, the Arena entrance) in the legacy preview, on CHIM and in OpenMW. Renderer counters
  before and after (entities sent, faces drawn and clipped, BSP nodes per face).

*Memory, the engine's real rule (CHIM-CHUNK-LOAD-FAIL-33).*

- A chunk is activated, with its catalogue, terrain and models locked, within the active radius
  (636: view 540 plus hysteresis 96). It is released only past the load radius (892: plus the
  prefetch margin 256).
- The zone (6,864 KiB) never moves a block, so the question is not only whether the total fits
  but whether each block finds a free run once others are locked.
- The heap gate therefore reports, and will gate on, three numbers per frame:
  - the active ring at any position (0.5's gate);
  - everything a moving player can hold locked, i.e. the load ring;
  - the largest single block (the biggest model a ring needs: Balmora's houses 258-292 KB, the
    silt strider 478 KB) against the free space left by the rest.
- Measured on Balmora with the load ring: peak 7,661,472 bytes, and 661 of 9,216 positions over
  the chunk room of 6,242,304. The gate's policy follows the engine. Once the chunk-load repair
  (branch v0.0.33-chim-chunkload: ground before buildings, release policy, allocation) lands,
  `tools/engine_limits.py` states which ring the engine keeps locked and how it places blocks,
  and the gate reads it. It never keeps its own copy.
- What a frame cut does NOT change: the ring is centred on the player, so where frames meet has
  no effect on the peak at a position. Dense places fit only by spending less there:
  - simpler models (LOD) and shared texinfo (about 125 bytes per face, of which texinfo 44);
  - a measured, stated view budget per frame (no artificial clamps: the frame records the reach
    its data can hold, and the engine states it);
  - or a larger zone.
  A cost predictor over the whole-island metrics (cells: faces, placements, unique models and
  textures, terrain) is calibrated on the measured worlds (Seyda Neen 5,683,920 B and Balmora
  6,239,776 B, active ring). It flags such places before anything is built; the heap gate stays
  the final word.

*Vis (MANDATORY #1).* Every placement is linked to the leaves its box touches. Canton bodies are
huge and span far more than 16 leaves, so the engine tests their chunk lists instead. Canton
bodies and the Temple are also the first real occluders CHIM meets: closed, solid masses that
hide whole streets of placements. The visibility rows and placement lists are measured per
chunk (visible share, placements per view), and the FS-UAE counters must not get worse than
the legacy preview at the A/B poses.

*Stage B: all of Vivec, as one frame.*

- The union of the nine Vivec district frames, in Morrowind units, is x 12,800..52,736 and
  y -113,664..-70,144. That is 39 x 43 chunks, rounded to 13 x 15 sectors: 195 sector files.
- Stage A's Arena frame lies inside it, so stage B replaces stage A's frame; the Arena area stays
  selectable.
- Source: the town converter once per district (`import_town.collect`), with references merged
  by reference number. Shared meshes must have equal visual profiles in every district, or the
  build stops.

*Format 0.6 (stage B).* The only change is the folder layout of a large frame.

- 195 sector files exceed the 72 entries of a classic FFS directory block, so sectors go into
  one subfolder per sector row: `frames/x+04/y-11/r07/s03.ccs`. Each row folder holds at most
  15 files, and the frame file stays in the frame folder.
- Index paths stay under 31 characters (the example has 28). The file table already names
  every file by path, so the record layout is unchanged.
- Files are still written whole in pack order, sectors in Hilbert order, row folders included.
  The disk-layout gate checks names, entries per directory, whole files and order.
- A frame of at most 64 sectors keeps the 0.5 layout, so the version bump changes nothing for
  Balmora or Seyda.
- Writer and reader change together. The format version becomes 0.6 in the same merge as the
  engine reader, the validator check and a reader test.

*What the engine (E) needs:*

1. Format 0.6: a sector path may contain a row folder. The engine takes paths from the index's
   file table, so this may already work; a host test on a 0.6 world proves it. Accept minor 6.
2. `"_chim_edge" "closed"` in a frame map's worldspawn: show "Area unavailable" when the player
   touches the frame's boundary clip walls (as the legacy preview's edge does).
3. The memory policy stated through `tools/engine_limits.py`: which ring stays locked, and the
   allocation rule after the chunk-load repair, so the builder's gate follows it.
4. The renderer counters at the stage A poses, legacy preview against CHIM, for the table.
5. Names: `vivec_arena-chim.bsp` (stage A) and, in stage B, the Vivec frame map's name for the
   district scenes (`dbg tp` names from the town table, VIVEC-ARENA-TP-ARRIVAL-32).

**M4, the open world, on a fixed grid of frames.** The open world needs a different frame model:

- The island is about 42 x 46 cells, 86,016 x 94,208 local units. That exceeds the ±32,767 range
  of the shorts in node and leaf bounds, so the open world cannot be one frame with one origin.
- Frames become a fixed grid of 3 x 3 cells (6,144 local units, 24 x 24 chunks, 8 x 8 sectors:
  the 0.4 layout as it is). The grid is anchored so that Balmora's frame (cells -4..-2,
  -3..-1) is one of its tiles, which puts frame centres at cells (3i, 3j + 1). Each frame keeps
  its own origin, its centre x 0.25.
- Towns stop being frame shapes. A town is the content of the grid frames that hold its cells:
  its per-cell inputs and its rules (visual profiles, window flattening, town flora) apply by
  cell. Seyda Neen and Vivec are re-cut onto the grid. M2 and M3 stay as their own frames until
  M4 replaces them; nothing is deleted.
- Sources come per cell from the same inputs the legacy world uses. Ground is the canonical
  LAND (world-survey `terrain-source.npz`, `prepare_world_regions.terrain_triangles`).
  Statics are the world scenery export (`world_scenery.py`, by cell), flora is the world flora
  (`prepare_world_flora`), and the towns' sources cover their own cells. The CHIM source
  stage reads these scene inputs, never the legacy region maps. Seyda Neen's dependency on the
  legacy scene stage goes away when its cells come from the per-cell inputs.
- Format 0.6 (first draft):
  - placement records gain an owner-frame field, so a placement reaches into a neighbouring
    frame's chunks ("Reach across frames", open decision);
  - every frame's chunk standing hulls are cut at frame edges as they are at chunk edges, and
    the frame-grid neighbours' tiles are in the edge chunks' collision ring.
- Engine (E): the ring spans frames. Up to four frames are resident (the player's and those
  within the load radius). The frame world grafts chunks of several frames, re-centred on the
  player's frame, and the origin shifts when the player crosses a frame edge, between frames
  (no map load: "DON'T BLOCK THE TRAFFIC"). Each frame map then holds the frame's point
  entities (actors, flora sprites) and is read on its own.

**First M4 slice:** Balmora and the two grid frames east and west of it, cells -7..1 by -3..-1 (a
strip of three frames). It shows:
- frame crossing with no stop;
- standing across frame edges;
- placements reaching across an edge;
- the heap ring at a frame corner;
- disk bytes against the 2,532 legacy world maps of the same cells.

To show it, MiniWind needs:
- the world-survey, world-scenery and world-flora stages for those cells;
- the CHIM stage with the strip's three frames;
- the engine's multi-frame ring;
- one frame map per frame, holding the frame's actors and flora sprites;
- `dbg tp` names for the strip.

M5 (the whole island) is this grid at full size; its index scales with the number of frames,
and its PAKs stay sharded under 1 GiB.

## Large-model cut (chunk pieces)

A model wider than the area setting `cut_models_over` (local units; 0, the default, keeps every model
whole; 512 for district-size bodies) is stored as chunk-sized pieces (`tools/chim/cut.py`,
CHIM-ARENA-MEMORY-33). Only the pieces in the ring are then resident, and the largest single block is a
piece, not a whole canton body.

- Mode `tiles` (default, `cut_mode`): the model is cut once in its own frame into tiles of one chunk's
  size. Every face and every convex collision piece goes whole to the tile holding its centre, so the
  polygons and the collision solid are exactly the model's. Each tile is its own model, shared by every
  placement of the model (stored once, like the whole model was). A placement puts each tile at its
  origin plus the turned tile centre, with its own yaw; the chunk holding that point owns the tile.
- Mode `clip`: each placement is cut by the frame's chunk grid, faces clipped at the chunk lines and
  convex pieces clipped by the chunk column (exact bevels on clipped pieces). Pieces stay inside their
  chunks but are not shared between placements, and clipped slopes read as stair steps. Mode
  `partition`: per placement, whole faces and pieces by centre. Both stay selectable.
- Placement numbers stay unique: a piece's number keeps the source reference in its low 24 bits and the
  piece index above them (`chim.cut.piece_ref` / `source_ref`). Checks that compare with the source (the
  validator, the frame map's statics parity, the stair gate, which also groups faces into flights by
  source reference) map it back. The frame map's origin check skips cut placements.
- A hollow shell's occluder (its closed render mesh's solid columns, CHIM-PVS-HOLLOW-33) is carried whole
  by the first piece.
- Vis: pieces are chunk-sized, so each touches few leaves (under MAX_ENT_LEAFS) and is culled on its own.

Measured on the Vivec Arena frame (9 October 2026, `--cut-models-over 512`, tiles): active ring 6,492,688
to 5,337,232 bytes (it now fits the 6,242,304-byte chunk room), largest block 2,514,432 to 450,704
bytes, stair gate passed (3,533 steps; 3,535 with whole cantons). Cutting per placement instead (mode
`partition`) gave 8,389,936 bytes: the Arena frame places `ex_vivec_c_04` several times, and per-placement
pieces are no longer shared.

## The heap gate (0.5)

`tools/chim/heap.py`, run by `tools/chim_build.py --validate --sdk SDK` (every `--builder chim`
build). It is strict: there is no exception list.

- For every chunk of every frame, taken as the player's chunk, the gate adds up the bytes of
  the active ring (draw distance plus hysteresis) that must be resident at once:
  - the ring's chunk records;
  - the models their owned and reach records place;
  - those models' textures;
  - one placement-catalogue entry per placement.
- Decoded sizes use the strict world-map heap gate's own model (`check_world_map_heap`). The
  target ABI sizes are probed with the Amiga compiler from the engine headers, with one Hunk
  allocation per lump (16-byte alignment plus the header), as `Mod_LoadBrushModel` makes them.
- The largest ring must fit the engine's CHIM zone bank (`chim_zone_kib`, 6,864 KiB, read from
  the engine source) minus its two frame-world slots (`chim_pool_kib`, 2 x 384 KiB).
- The report `chim-heap.json` gives the peak, the chunk where it happens and the headroom, per
  frame.

### The frame-map heap (image step)

With the frame maps written, the image step checks each one's whole-map heap
(`chim.heap.require_frame_map_heap`, report `chim-frame-heap.json`), on the
build's own heap size (`engine-build.json` `heap_mb`):

- The zone the engine can take beside the map is
  `engine_limits.whole_map_zone`: the Hunk, minus the start-up Hunk and the
  frame map's BSP (before the zone), minus the map's `"_chim_hunk_rest"`
  (after the zone), minus the 2 MiB reserve. It is never more than
  `chim_zone_kib`.
- The frame's rings are counted as in the heap gate above, plus the models
  of each chunk's streamed statics. The engine decodes a streamed model once
  into the zone, keyed by name and referenced by the active chunks that
  place it, like the ring's models (`STREAMED_MODELS = 'shared'`). A copy
  per chunk (`'chunk'`) stays selectable as the larger figure.
- The gated ring is the active ring. The engine locks only the active ring;
  prefetch beyond it loads into free room only and never evicts, so the load
  ring is best-effort cache. Both rings and the largest single block are
  always reported.

Seyda Neen, measured on 9 October 2026 (world `seyda-009`, default heap):

| | before streaming | streamed, copy per chunk | streamed, shared |
| --- | --- | --- | --- |
| after the zone (`_chim_hunk_rest`) | 2,580,400 (engine, measured) | 1,589,344 | 1,589,344 |
| zone | 5,888 KiB (engine, measured) | 6,864 KiB (the full zone) | 6,864 KiB |
| active ring, town map | 5,683,920 | 6,130,912 | 5,905,568 |
| load ring, town map | 6,417,728 | 7,361,696 | 6,672,816 |
| chunk room (zone minus 2 x 384 KiB) | 5,259,264 | 6,209,536 | 6,209,536 |

Before streaming, Seyda's active ring did not fit the zone the whole-map rule
left. Now it fits with 303,968 B of headroom (shared, the engine's way;
78,624 B with a copy per chunk). The load ring is larger than the chunk room
and is filled only as far as free room allows.

## How the engine loads it (staged plan step 3)

- At start: read `world.cwi` (settings, file table, model and texture
  directories) and keep it.
- Entering a frame: read its frame file (chunk directory, sector table).
- Ring change: every sector with a chunk inside the ring is read whole (one
  file, one run); a model or texture that a ring chunk needs and whose home
  sector is not in the ring is read on its own from its home sector file.
  Within a crossing every file is read in ascending order.
- A brush image is decoded by `Mod_LoadBrushModel`'s section decoders with
  `aw_bsp_base` = record offset; only the texture lump needs a CHIM decoder
  (global ids to `texture_t` pointers).
- Brush models currently live on the Hunk and die at every map change; CHIM
  needs the non-moving model zone with an LRU list (design note, ~300 lines)
  before models can outlive a chunk.

## Activation: the frame map

With `tools/build.py --builder chim`, the image step writes one frame map per
area the world holds: `maps/<town>-chim.bsp`, where `<town>` is the town's map
name in `config/towns.json` (`tools/chim/frame_map.py`). When CHIM is on, the
engine loads this map instead of the town's region maps. `chim_towns 0` in the
engine loads the region maps instead, for A/B comparisons. The region maps,
door links, sky, fog and the `dbg tp` names keep the town name. The legacy
region maps stay as they are and remain selectable. A legacy build writes no
frame map.

- Worldspawn: the town's worldspawn, identical in every region map, plus the
  key `"_chim_frame" "CX CY"`: two decimal integers, the cell of the frame's
  `FRAM` row in `world.cwi` (Balmora: `"-3 -2"`).
- World: empty, with no faces. One node splits the frame into two empty
  leaves, the standing hull is empty everywhere, and there is no visibility
  data, so every leaf sees every other. The bounds cover the frame:
  frame-local x and y from the frame record, z from 256 units below the
  lowest chunk to the terrain ceiling. Ground and objects come from the
  chunks.
- Entities: everything the chunks do not hold, copied with its frame-local
  coordinates. The region maps use the same coordinates:
  (Morrowind position - town centre) x 0.25.

  | Class in the region maps | In the frame map |
  | --- | --- |
  | `worldspawn` | merged; it must be identical in every region map |
  | `info_player_start` | the town's default region's start (the region whose core holds the region table's default point) |
  | `func_wall` with `aw_ref` | not copied: a static object held by the chunks |
  | `aw_static`, `aw_flora` (sprites and models that `makestatic` draws) | copied once and tagged to stream with their chunk (below) |
  | other point entities (`aw_npc` ...) | copied once; the same `aw_ref` (or the same keys) in several region maps must be identical |

- Streamed statics (CHIM-SEYDA-MEMORY-33). An `aw_static` or `aw_flora` keeps
  every key that `PF_makestatic` reads (`model`, `origin`, `angles`, `frame`,
  `skin`, `aw_scale`) and gets two more:
  - `"_chim_chunk" "N"`: the index, in the frame's chunk directory, of the
    chunk that holds its origin. A cell without a chunk (open water) gives
    the nearest chunk.
  - `"_chim_box" "x0 y0 z0 x1 y1 z1"`: its drawn box in frame-local
    integers. That is the origin plus or minus the model's bounding radius
    (the sprite or alias header's), rounded outwards; for an `aw_flora`
    times its `aw_scale`. `PF_makestatic` sends `aw_scale` for `aw_flora`
    only, and the client refuses a scaled static that is not a sprite, so the
    image step refuses an `aw_flora` that is not a sprite or whose `aw_scale`
    is not a finite positive number.

  The worldspawn states `"_chim_streamed_statics" "<count>"`. Streaming is
  a build setting, `chim_stream_statics` (on by default;
  `--no-chim-stream-statics` for debugging; exported as
  `AMIWIND_CHIM_STREAM_STATICS`). Every frame map, streaming or not, states
  `"_chim_hunk_rest" "<bytes>"`: the client's per-map Hunk
  (`engine_limits.MEASURED_HUNK`), plus each sprite of an entity that is not
  streamed (`Mod_LoadSpriteModel` allocates on the Hunk; alias models go to
  the Cache) with 512 bytes for its Hunk blocks beyond the file, plus a
  24 KiB margin. After the zone, beyond the client and the sprites, the
  engine measured 20,256 B on Balmora and 26,432 B on Seyda Neen, including a
  12,768-byte temporary block at the load peak (CHIM-ZONE-RESERVE-EARLY-33).
  24 KiB covers Balmora with 4,320 B to spare, and stays below the point
  where Balmora's zone would drop a 16 KiB step and its active ring would no
  longer fit (about 6,300 B over the measured load). Seyda Neen's figure is
  1,856 B higher; the engine measures it and keeps it after the first load. The engine skips the tagged entities at load. It builds the
  same static entities when their chunk becomes active and frees them with
  it.

  Seyda Neen: 229 statics stream in the town map (954,414 B of models), 46
  in the intro docks (469,142 B) and 8 in the courtyard (217,781 B). Before,
  they cost the Hunk about 978 KB at load (measured by the engine).

  The image step stops on anything else: another brush entity, a static of
  the region maps missing from the CHIM world, a CHIM static missing from the
  region maps, or entities that differ between regions. It also stops when
  the town's coordinates differ. The frame's origin (its centre x 0.25) must
  be the origin of the town's region maps, which door arrivals, the region
  directory, harvest catalogues and saves all use. Every static that both
  sides hold must sit at the same frame-local origin, within 0.01 units.
  Balmora: origin (-5120, -3072); 15,371 static entities (1,473 statics)
  compared, the largest offset 0.0001. The record in
  `build.json` (`chim_world.frame_maps`) counts every class (in the region
  maps, written, rule) and the references the entity tracker's reader finds
  in the frame map. Balmora: 20 entities (worldspawn, the start of `bm019`,
  18 `aw_npc`).
- Payload parity: the CHIM world holds exactly the statics of the town's
  final region maps. The CHIM builder applies the same edits as the image
  step, using the same functions:
  - it leaves out the harvest step's placements, which the image removes as
    baked statics (`harvest_build.source_placements`);
  - it adds the town flora that the image installs as meshes
    (`install_town_flora.town_entries`, `world_scenery.region_references`,
    the flora mesh profile `prepare_world_flora.mesh_profile`, from the flora
    archive).

  Town flora shown as sprites has no CHIM form yet and stops the CHIM build
  (planned: "Planned for 0.5: Seyda Neen (M2)"). The town's placements are
  the ones its legacy region maps hold: converted bounds reaching into the
  town bounds (`town_regions.town_references`, shared with the legacy
  coverage audit).
  The frame map's check in both directions is the parity gate. Balmora: 1,488
  town statics, minus 20 harvest placements, plus 5 town-flora meshes, gives
  1,473, equal to the final region maps.
- Harvest plants stay per region under CHIM. The harvest runtime keeps
  loading the town's region catalogues (`harvest-<region>.txt`). The frame
  map has no harvest catalogue of its own. Every catalogue of a CHIM town must
  be `AWH4` (shared alias models, representation 4); the image step stops
  otherwise. A brush catalogue (representation 0) binds its plants to the
  region map's `func_wall` edicts by `aw_ref`, and the frame map has no such
  edicts. Balmora: 17 catalogues, all `AWH4`.
- Exteriors outside the towns (open world) will use the same kind of map,
  one per frame.

### Walkable area of the special maps

The intro docks and the Census courtyard (`SPECIALS`) are bounded maps: the
player walks a small area inside four clip walls. The image step floods each
one's reachable floor on the CHIM frame (`walkable_area`, every 16 units,
from the map's start). The flood follows the player's own level: a step up of
at most `STEP_HEIGHT`, then down to the next walkable floor, so ground under
roofs, decks and gangways counts. A drop of more than 64 units is a ledge and
is not followed. The map is refused when:
- a reachable place borders a sample with no floor within 2,048 units (a hole
  in the collision);
- an escort route goal of the intro is farther from reachable floor on CHIM
  than on the legacy map, plus 24 units. The second goal is the Census door,
  inside the wall's solid on both: 107.2 units from the nearest floor on both;
- CHIM reaches less than 95 % of the floor the legacy map lets the player
  reach.
Seyda Neen, measured on 9 October 2026: intro docks 7,311 places reached
(legacy 7,157, 98.6 % of them on CHIM), courtyard 671 (legacy 603, all of
them), no holes.
## Far terrain sidecar
Each frame map may have its frame's far terrain beside it,
`maps/<frame map>.far` (CHIM-FAR-TERRAIN-33; design and measurements in
[FAR_TERRAIN.md](FAR_TERRAIN.md)): the land outline beyond the chunk ring,
which the engine draws past the fog plane in the fog colour. Like a Quake
`.lit` file next to its map, it is not part of the CHIM world: the index
does not list it, it is outside `chim/`, it has its own version, and the
world format version does not change with it. The builder writes one per
frame into its output (`far/<cx>_<cy>.far`, `tools/chim/far.py`); the image
step copies it beside every frame map of that frame (Seyda Neen's intro docks
and courtyard maps included) after checking its frame cell.
Big-endian, 40-byte header, the heights, then (version 2) the object stamps:
| Offset | Type | Field |
| ---: | --- | --- |
| 0 | char[4] | `CHFL` |
| 4 | u16 | version (2; the engine also reads 1, which has no stamps) |
| 6 | u16 | header bytes (40) |
| 8 | i16, i16 | the frame's centre cell (must equal the frame map's `_chim_frame`) |
| 12 | f32, f32 | world position of sample (0, 0), Morrowind units |
| 20 | f32 | step between samples, Morrowind units (512) |
| 24 | f32 | local units per Morrowind unit (0.25) |
| 28 | u16, u16 | samples across (x) and along (y), 2 to 1,025 each |
| 32 | u16 | block: quads per block side, 1 to 16 (16; the engine culls per block) |
| 34 | u16 | object stamps (0 in version 1) |
| 36 | u32 | CRC-32 (zlib polynomial) of every byte after the header |
| 40 | i16[ny][nx] | heights in local units, rows by y: the LAND height at the sample, or the water level (0) where the ground is lower or the cell has no LAND |
| after the heights | u32[stamps], i16[stamps] | sample indices (`j x nx + i`, strictly ascending, below `nx x ny`), then the height each is raised to: the top of the drawn box of a large placement (at least 64 local units wide both ways and 64 above the ground) over its footprint, or over the sample nearest its centre |
Then zero bytes up to a multiple of 4 when there are stamps. The file is
exactly `40 + 2 x nx x ny` bytes without stamps, and `40 + 2 x nx x ny + 6 x
stamps` rounded up to a multiple of 4 with them. The grid covers the frame
plus one cell on every side, snapped to the cell grid (Balmora: 81 x 81
samples, 1,719 stamps, 23,476 bytes). Local position of sample (i, j):
`((x0 + i x step) - frame origin x) x scale`, likewise for y, as every CHIM
position.

## Validation

`tools/chim/validate.py OUT` proves, from the files alone plus the builder's
source manifest (`chim-source.json`: every converted placement, the tile
corner heights, the doors for the walk):

- every placement has exactly one owner record, in the chunk holding its
  origin, and reach copies identical to it in exactly the other chunks its
  drawn box touches; the stored box equals the box from the model's bounds;
  the stored leaf count equals the leaves the box reaches in the chunk
  subtrees, and the 16-leaf flag matches; placement ids are 0..n-1 once each;
  the set of placements equals the source's;
- every chunk subtree obeys the Quake world rules (leaf 0 solid, contents
  empty/solid/water, every face on exactly one node and on its plane,
  marksurfaces in range, head node 0 the root); every PVS row decompresses,
  holds the chunk and its neighbours, is symmetric and stays inside the ring;
  every placement row decompresses, holds every placement touching the chunk
  or its neighbours and nothing outside the ring;
- every model and every texture is stored once (unique content, unique names)
  and used; every brush image is well formed (indices in range, edge 0 unused,
  render part before the collision lumps) and every face passes the engine's
  256-texel surface check under every FPU rule (`surface_grid.check_lumps`);
- every terrain tile is in exactly one chunk and stored once: 49 sample
  points per tile are each covered by exactly one ground face, every ground
  face lies on the source heights, and every point below the water level is
  covered by exactly one upward water face (none above it);
- the index lists exactly the files on disk with their sizes and CRCs; every
  sector file is tiled exactly by its records (each chunk, model and texture
  stored in exactly one record) in the order chunks, models, textures; the
  frame and index directories point at those records; chunks and sectors are
  in pack order; every model and texture is stored in its home sector and ids
  follow the first-met order; render parts precede collision parts; every
  file obeys the FFS rules.

It then measures: bytes by kind; today's region maps for the same frame
(`--legacy-maps`, `--legacy-regions`); a walk through every load door of the
town (nearest-neighbour tour, the census route) with the loading rules above:
bytes, read runs, files and estimated time per chunk crossing (cost model),
resident bytes, with 0, 1 and 2 MiB of extra LRU cache; and today's region
map reads on the same walk with the same cost model.

## Statistics

`tools/chim/stats.py OUT` writes `chim-stats.json` from a validated world: faces per
model, placement, chunk and benchmark camera, the heaviest models and chunks, disk
bytes against today's region maps, the resident ring, bytes per crossing and the
build time per section. The schema is in [STATS.md](STATS.md).

## The builder: fast and incremental

The CHIM builder is built for short edit-build cycles:

- **Units.** Each mesh, model variant, texture, chunk terrain and block of
  visibility rows is a unit with a fingerprint (the hashes of its inputs, of
  the tool sources that make it and of the build switches). A unit whose
  fingerprint is in the unit cache (`OUT/work/chim-units`) is reused; the
  receipt and the log count built and reused units per kind, and
  `--no-cache` builds everything again. `--rebuild-mesh SOURCE` builds one
  mesh's units again (as after a converter change for it).
- **Parallel.** Units run through `build_parallel.ordered_map` with exactly
  `--jobs` workers; results never depend on the worker count (tests compare
  serial and parallel output byte for byte).
- **Files.** The files are assembled from the units in a fraction of a second
  and a file whose bytes did not change is not written again.
- **Timers.** Every stage runs in a `section(name)` timer (wall and CPU
  seconds, workers included), reported in the receipt.

Balmora, 8 workers (host times in one 8-CPU container; no emulator involved):

| Build | Wall | CPU | Units built / reused |
| --- | ---: | ---: | --- |
| From scratch (source stage included) | 35.0 s | 117 s | all built: 226 meshes, 531 variants, 157 textures, 576 chunks, 32 visibility blocks |
| Nothing changed | 3.5 s | 2.6 s | all reused; no file rewritten |
| One mesh changed | 3.9 s | 3.3 s | 1 mesh and 1 variant built, the rest reused |

(Measured with format 0.1; format 0.2 changes only the assembly, which takes
a fraction of a second. A build removes CHIM files of an older layout from
its output and lists them in the receipt.)

Of the from-scratch time, the legacy source stage (audit and scenery export)
is 17 s, model variants 6 s, visibility rows 5 s, meshes 3.4 s, chunk terrain
1.8 s.

### A CHIM build ships no legacy exterior maps

In a CHIM build (`tools/build.py --builder chim --chim-area A [--chim-area B]`)
no legacy exterior map of a CHIM area reaches the image. The image step writes
each CHIM town's frame maps from its final region maps, removes those maps
(`chim.frame_map.remove_legacy_areas`) and, right before the volumes are packed,
fails the build if any legacy exterior map of a CHIM area is in the payload
(`chim.frame_map.require_no_legacy_areas`; `build.json`
`chim_world.legacy_check`, with the removed files in
`chim_world.removed_legacy`). Extra towns that are not CHIM areas (the Vivec
Arena) leave a CHIM image whole: exterior maps, region and door tables and
harvest catalogues (`chim.frame_map.remove_towns_not_on_chim`, reason "not on
CHIM yet"); the engine finds no such destination. The open world ships with
the legacy builder's maps until it is on CHIM. After these changes the map
optimizer's receipt follows the new map set (`optimize_world_maps.rebind_chim_maps`).
Interiors stay Quake maps, built as before.
Seyda Neen's frame maps are checked against the recorded v0.0.31 Seyda Neen
maps, given as an input folder (`--seyda-recorded DIR`); a CHIM build with
Seyda Neen stops before any work without it.

The plan still runs some legacy exterior stages because later steps read their
outputs: the town's region conversion (the frame maps copy their actors and
player starts from it), the open-world chain (the image's open-world overlay
and the town flora) and the extra towns (their interiors come from the same
converter run). `tools/chim/plan.py` names each one with its reader, and every
CHIM build records them (`build-state.json` `chim_plan`). Moving those readers
off the legacy chain is tracked as CHIM-LEGACY-CHAIN-33; `--builder legacy`
keeps its plan and outputs unchanged (`tests/test_chim_no_legacy.py`).

## Measured: Balmora (format 0.2, 8 October 2026)

(Format 0.3 adds the placement rows: 20 KB more, 17.50 MB in all; the walk's
numbers move by less than 0.1 %.)

Counts and bytes are measured from the files the builder wrote (the
validator passed every check). Times are the cost model's estimates from
emulator measurements (relative, not hardware).

| | CHIM 0.2 | Today's 64 region maps |
| --- | ---: | ---: |
| Bytes on disk | 17.5 MB in 66 files (index 46 KB, frame file 17 KB, 64 sector files, largest 1.4 MB) | 162.1 MB (9.3 times as much) |
| Models (unique variants of 226 meshes) | 531, 15.1 MB (render 14.0 MB, collision 1.1 MB) | every region repeats its own |
| Textures | 180 (from 182 keys), 0.35 MB | every region repeats its own |
| Chunks | 576 x 256 units, 1.95 MB; largest 5.5 KB render + 0.5 KB collision | |
| Placements | 1,488 owner records, 2,124 reach copies (48 bytes each) | each face about 7.3 times ([sub-cell redundancy](../SUBCELL_REDUNDANCY.md)) |
| Terrain | 2,304 tiles, 4,530 ground faces, 666 water faces | |
| Largest model | 366 KB | |

### What a read costs on FFS (measured)

`awbench seek` (FS-UAE, cycle-approximate 68040, an FFS partition made by the
builder's xdftool path on a Docker volume, 8 and 128 MB files; relative numbers, not
hardware; a sweep of fill, fragmentation, buffers, RDB, partition size and host
storage is in [the hardware benchmark guide](../HARDWARE-BENCHMARK.md): only the hard
file's place on the PC changes the results):
a plain 16 KiB request costs 0.7-1.4 ms; a forward skip of 4-64 KiB costs no
more; skips of 256 KiB and 1 MiB cost 3-7 and 8-11 ms; a random position costs
23 ms in the 8 MB file and 264 ms in the 128 MB file. FFS walks its chain of
extension blocks (one per 36 KiB) from the current position when seeking
forward and from the file start when seeking backward, so the cost of a seek
grows with the distance, and in a large file with the offset.

### The walk replayed (measured)

The validator writes the walk's reads per crossing (`--replay-dir`); `tools/chim/disk.py`
writes the world onto an FFS partition the builder's way (xdftool, files in pack
order, readback); `awbench replay` performs the reads in FS-UAE and times each
crossing. Today's 18 map loads of the same walk were replayed from two partitions
holding the 64 region maps: alone in `maps/` (L1), and among 2,677 one-byte files
named like the rest of the shipped `maps/` folder (L2, realistic directory hash
chains). All five replays ran in one session (CHIM with 1 MiB of extra cache, without
extra cache, L1, L2, CHIM again as drift control); 64 KiB read requests:

| Cycle-approximate 68040 | CHIM, 1 MiB | CHIM, no extra cache | Today, L1 | Today, L2 | CHIM, 1 MiB again |
| --- | ---: | ---: | ---: | ---: | ---: |
| Per crossing, median / largest | 21 / 71 ms | 27 / 87 ms | 94 / 112 ms | 120 / 147 ms | 23 / 76 ms |
| Whole walk | 1.65 s | 2.20 s | 1.64 s | 2.09 s | 1.74 s |
| Entering the town | 96 ms | 107 ms | | | 91 ms |

The emulator moves disk bytes almost for free (about 90 MB/s), so these times are
mostly file-system work: a CHIM crossing costs a quarter of a map load, the walk as a
whole costs about the same as the legacy loads from a lone folder and less than from
the crowded real one (its directory lookups alone cost about 20 ms per open). The
same replays in an earlier session gave the same ratios at about 0.6 times these
times: emulated disk time drifts between sessions, so only runs of one session
compare (A/B/C/D with a drift control).

The cost model fitted to the replays (`tools/chim/readcost.py`, the validator's
default; 210 crossings, R^2 0.82): 0.0113 ms per KiB, 0.092 ms per extension block
walked, 1.25 ms per file opened, 0.98 ms per read run, forward gaps up to 64 KiB
free. Within a session it follows the measured crossings closely (correlation
0.98); its scale moves with the session. The model fitted to the `awbench seek`
patterns alone counts each 16 KiB request's overhead as bytes and overstated long
reads about sixfold.

On a real drive the bytes cost more. With the same model but bytes at 2 MB/s (an
assumption for an A1200 IDE port in PIO mode, not a measurement) the walk reads for
20.9 s with CHIM (1 MiB of extra cache; 76 ms per crossing, median) against 35.1 s
for today's maps (2.1 s per map load): a hardware `awbench replay` decides.

### The walk

All 70 load doors of the town (16,007 units, 84 chunks, 83 crossings; ring 45
chunks), with 0 / 1 / 2 MiB of extra cache. Times are the replay-fitted model's
estimates (emulator, relative); the measured replays are above.

| | 0.2 (sector files) | Today's region maps |
| --- | ---: | ---: |
| Read runs per crossing, median / largest | 4 / 17; 3 / 15; 3 / 15 | 1 |
| Files per crossing, median | 3; 2; 1 | 1 |
| Estimated time per crossing, median | 16 / 10 / 6 ms | 50 ms |
| Estimated time per crossing, largest | 58 / 51 / 51 ms | 52 ms |
| Estimated time for the whole walk | 1.47 / 1.11 / 0.97 s | 0.83 s (18 crossings) |
| Bytes read on the walk | 50.2 / 40.7 / 32.1 MB | 73.5 MB |
| Bytes per crossing, median | 379 / 264 / 213 KB | 4.43 MB |
| Resident, median / largest | 4.8 / 6.2 MB | one map |
| Entering the town (first ring) | 3.5 MB, 68 ms | one map |

Format 0.1 (one 15 MB model pack) read 27.6 / 18.7 / 14.5 MB on the same walk but in
11 / 9 / 6.5 runs per crossing, most of its time walking the pack's extension chain.

Sector files trade bytes for seeks: a crossing reads more (whole sectors) but
in one run per file and with almost no extension-block walking, so with 1 MiB
of extra cache a crossing is 3 runs, a quarter of a map load, and the whole
walk reads for about as long as today's maps although it crosses 4.6 times as
often (see the replay above). The price is about 1.2 MB more resident data than
reading chunk by chunk. Sector size was chosen by simulation over the same walk (2 x 2: 144
files per frame, more than an FFS directory holds; 4 x 4: 7.5 MB resident;
3 x 3: the balance).

Visibility (per chunk as the player's chunk):

| | |
| --- | ---: |
| Chunk subtree depth (nodes on the longest path) | 5 (median 4); frame grid 10; world 15 at most |
| Visible share of the ring, mean / lowest | 99.7 % / 82.6 % (30 of 8,836 tested pairs blocked), with and without building-mesh occluders |
| Occluders | 1,464 solid collision pieces; 51 hollow-shell buildings through their closed meshes (+2,665 solid 16-unit cells, +7 %) |
| Visible share of the frame, mean | 6.8 % (the ring does the culling) |
| Ground and water faces per view, median / largest | 351 / 577 |
| Faces of placed models per view, median / largest | 13,535 / 54,406 (world faces are 2.2 % of all) |
| Placements per view, median / largest | 95 / 451 |
| Placements over 16 leaves | 160 of 1,488; 17 per view (median), 32 at most |
| Leaves per placement, median / 95 % / largest | 3 / 30 / 237 |
| Chunks per placement, median / 95 % / largest | 1 / 6 / 36 |

Outdoors the ground hides almost nothing inside the ring, and adding the
buildings' enclosed space as occluders (30 Hlaalu house and temple variants:
about 60 % of their bounding boxes enclosed, a third left after erosion)
blocked no further chunk pair: a chunk counts as visible when anything in it
can be seen, and in Balmora 90 % of the chunks hold content (a roof, a wall
reaching in from a neighbour) more than 128 units above their lowest ground
(74 %: more than 256 units), which shows over the houses in between.

Placement lists (0.3) test each placement instead. Of 51,224 placement tests
(placements in a chunk's ring but not next to it), 5,875 (11.5 %) were
blocked:

| | Chunk rows | Placement lists | Placement lists, standing eye only |
| --- | ---: | ---: | ---: |
| Placements per view, median / largest | 95 / 451 | 86 / 414 | 83 / 386 |
| Faces of placed models per view, median / largest | 13,535 / 54,406 | 12,170 / 50,143 | 11,476 / 48,146 |
| Placements over all views | 100 % | 91.5 % | 85.6 % |
| Faces over all views | 100 % | 92.2 % | 87.1 % |

The cameras of the [hardware benchmark guide](../HARDWARE-BENCHMARK.md)
(placements / faces of placed models; chunk rows send the whole ring there):

| Camera | Ring and chunk rows | Placement lists | Standing eye only |
| --- | ---: | ---: | ---: |
| Balmora 1 | 447 / 52,401 | 380 / 47,065 | 358 / 45,454 |
| Balmora 2 | 404 / 46,530 | 394 / 45,798 | 386 / 45,295 |
| Balmora 3 | 341 / 39,784 | 325 / 38,982 | 299 / 37,036 |
| Balmora 4 | 271 / 35,745 | 264 / 35,371 | 256 / 34,472 |
| Balmora 5 | 192 / 27,651 | 189 / 27,323 | 187 / 27,173 |

The lists cut 2-15 % of the placements and 1-10 % of the faces on these
cameras. A town view from street level still sees most of the ring: the raised
eye (97 units, kept so jumps and stairs do not pop placements in) sees over
the houses, the 13 box points include roof tops that show over the next roof,
and occluders are eroded 24 units inside the walls. The work per view stays
the placed models, as the renderer counters found
([What a town frame is spent on](../performance/LESSONS_LEARNED.md)); distance
detail (simpler far shapes, fog) cuts the rest.

## Open decisions

| Question | Options | Recommendation |
| --- | --- | --- |
| Byte order of brush images | (a) little-endian as in maps, decoders swap (0.2); (b) pre-swapped big-endian with swapping compiled out for CHIM images | (a) until the loader is profiled on the 68040; swapping is load-time only. |
| Run-time scale and tilt (design option D) | Variants per (mesh, scale, tilt) (0.2) or one model per mesh with scale and tilt in the record | Measure with the engine first; the census says it removes most model bytes island-wide, but hulls stay per scale and tilt. |
| Terrain representation | Faces written per chunk (0.2) or a heightfield generated at load | Faces now (no engine work, exact parity); the heightfield when its 68040 generation time is measured. |
| Sector size | 2 x 2, 3 x 3 (0.2), 4 x 4 chunks | 3 x 3: 3 runs per crossing with 1 MiB of cache, 6.2 MB resident at most, 64 files per frame directory; confirm with a real-drive replay. |
| Model directory size island-wide | One global directory in the index (0.2: 24 bytes per model, ~0.8 MB for ~33,000 variants) or per-frame directories | Per-frame directories once more than one frame exists, or run-time scale and tilt (fewer models). |
| Check the cost model on hardware | Emulator replays (0.2: the model follows them within a session) or a hardware `awbench replay` | One replay of the walk on a real accelerated A1200 drive: the emulator cannot price disk bytes. |
| Reach across frames | Clamp to the frame (0.2) or reach copies in neighbouring frames with an owner frame field | Worlds of several frames exist since 0.4 (frames side by side do not overlap); add an owner frame field when frames that touch (the open world) need it. |
| Visibility rows | Sampled sight lines per chunk (0.2); Quake's vis on the stitched frame world with occluder brushes (exact portal flow, needs qbsp per frame and occluders as world brushes) | Sampled rows now, checked against engine counters (faces and placements drawn) on fixed cameras; vis on the frame world if popping shows up. |
| Culling grain in towns | Chunk rows; placement lists (0.3: 8.5 % fewer placements, 7.8 % fewer faces per view in Balmora) | Keep both (rows for terrain, lists for placements); the bigger lever is distance detail. |
| Eye height of the lists | Standing and raised eye (0.3); standing eye only (14 % fewer placements per view) with a fallback to the ring while airborne or on stairs | Measure popping with the engine first; then decide. |
| Building occluders | Solid collision pieces and closed building meshes (0.2); occluder brushes in the chunk subtree | Keep the meshes; occluder brushes only when vis itself runs on the frame. |

## Version rules

- The world format version is in every file header; the CHIM version and the
  format version are in every receipt (`builder: "chim"`, `chim_version`,
  `world_format`).
- A change of any record layout or rule above changes the format version;
  major changes are refused by an older engine.
