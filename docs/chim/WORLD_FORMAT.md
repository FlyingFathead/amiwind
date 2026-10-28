# CHIM world format

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [File types](#file-types)
- [Summary](#summary)
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
- [Terrain references (0.7, experimental)](#terrain-references-07-experimental)
- [Compact terrain records (0.10, experimental)](#compact-terrain-records-010-experimental)
- [Generated terrain records (0.11, experimental)](#generated-terrain-records-011-experimental)
- [Placement light, stores and room records (0.12)](#placement-light-stores-and-room-records-012)
- [Placed models (0.8, experimental)](#placed-models-08-experimental)
- [Reach index (0.9, experimental)](#reach-index-09-experimental)
- [Actor table (experimental)](#actor-table-experimental)
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
  - [Frame maps are .chim files](#frame-maps-are-chim-files)
  - [Walkable area of the special maps](#walkable-area-of-the-special-maps)
- [Far terrain sidecar](#far-terrain-sidecar)
- [Shared ocean chunk](#shared-ocean-chunk)
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

CHIM is the world streamer that replaces today's overlapping region maps (the
legacy builder). This page specifies the files the CHIM builder writes and the
engine will read: every shared model, texture and terrain face stored once,
every placement stored once and pointing at a shared model, in small sector
files that a classic Amiga FFS disk reads whole, front to back. The builder
writes world format 0.5, or 0.7 when terrain references are on (0.8 and 0.9 only
to 0.11 only behind experimental options); the engine reads 0.4 to 0.11 ("Version rules" below). A short overview for newcomers, with
the roadmap of the format: [CHIM file format](../CHIM_FILE_FORMAT.md).

## File types

**We use `.chim` as the format for CHIM maps to avoid confusion: the format is no longer
directly compatible with the Quake `.bsp` format.**

Three kinds of files make up an area on CHIM. `.bsp` is a regular Quake map; `.chim`
is a CHIM map, the CHIM version of the Quake map format (the modified BSP format);
the CHIM world files are CHIM's own binary format. The builder, the tools and the
Toolkit tell a CHIM map by its `"_chim_frame"` key, never by its file name
(`tools/map_files.py`), and read it with a CHIM reader, never as a Quake map.

| File | Name | Format | What it holds |
| --- | --- | --- | --- |
| Quake map | `maps/<name>.bsp` | Regular Quake BSP29 map (little-endian), compiled by qbsp, vis and light | The legacy open world (region maps such as `maps/vfNNNN.bsp`) and every interior. An interior cut into sub-cell sections is one BSP29 map per section, joined by `interior-sections.txt` (`AWIS1`: each section's box and the portals where two sections meet). |
| CHIM map | `maps/<town>-chim.chim`, `maps/intro_docks-chim.chim`, `maps/vfNNNN.chim` (a cell on CHIM inside the legacy open world, in place of `vfNNNN.bsp`) | CHIM's own map format, the modified BSP format. Today it is laid out like a BSP29 file (the version word 29 and 15 lumps, in the CHIM brush image's lump order with the clipnodes last), but it is not a playable Quake map and is only valid with its CHIM world. Planned: its own header and loader ([.chim map format](CHIM_MAP_FORMAT.md)). | An empty shell: a world with no faces (one node, two empty leaves, an empty standing hull, no visibility), the map's entities (characters, doors, the start, the frame's static flames `aw_flame`, streamed statics with `"_chim_chunk"` and `"_chim_box"`), collision-only clip models (the frame's boundary walls) and the worldspawn keys `"_chim_frame" "CX CY"` (the frame it belongs to), `"_chim_hunk_rest"` and `"_chim_streamed_statics"`. Builds before v0.0.36 named it `.bsp`; `--chim-frame-ext bsp` still does ("Frame maps are .chim files" below). |
| CHIM index | `chim/world.cwi` | CHIM world, big-endian, kind `INDX` | Settings, the file table (every frame and sector file with its size and CRC-32), the model directory, the model name order, the texture directory and the names ("Index" below). |
| CHIM frame file | `chim/frames/x-03/y-02/frame.ccf` (one per frame of 3 x 3 cells) | CHIM world, kind `FRAM` | The frame block (centre cell, origin, chunk grid), the chunk directory in pack order and the sector table ("Frame file"). |
| CHIM sector file | `chim/frames/x-03/y-02/s00.ccs` ... `s63.ccs` | CHIM world, kind `SECT` | The records of 3 x 3 chunks, read whole: chunk records (`CHNK`: 48-byte placement records, the visibility rows and the chunk's ground as a small world subtree, or in 0.7 a 32-byte terrain reference), terrain records (`TERR`, 0.7: chunk ground stored once in chunk-local units), shared models (`MODL`: brush images in BSP29 lumps, little-endian) and textures (`TEXR`: Quake miptex), each stored once in the sector that first needs it ("Sector file" and the record sections). |
| Far terrain | `maps/<frame map>.far` (builder output `far/<cx>_<cy>.far`) | Its own format (`CHFL`, version 2, big-endian), beside the frame map like a Quake `.lit`; not part of the CHIM world | The land outline beyond the chunk ring, drawn past the fog ("Far terrain sidecar"). |
| Shared ocean chunk | one content-keyed file, kind `OCEN` | CHIM structures; no index lists it | One chunk of water over a flat seabed that every sea cell will reference; the engine does not read it yet ("Shared ocean chunk"). |
| Texture effect | `tools/chim/effects/<name>.chimfx` | Text, a builder input | Changes chosen textures on purpose; the receipt lists what it changed. The world holds only the changed textures ([texture effects](TEXTURE_EFFECTS.md)). |
| Builder reports | `chim-heap.json`, `chim-receipt.json`, `chim-validate.json`, `chim-source.json`, `chim-stairs.json`, `chim-regions.json`, `chim-timing.json` next to `chim/`; the image step adds `chim-frame-heap.json` | JSON | The heap gate per frame (peak, budget, headroom, positions over budget, the load ring), the receipt (versions, settings, texture effects), validation, the source manifest, the stair gate, the region ownership table (`aw-chim-ownership-1`) and stage timings. |

Not in the format yet: the walkable graph for characters (designed as a `NAVG` sector record,
[CHIM NPC pathfinding](CHIM_NPC_PATHFINDING.md)) and whole-rotation placement records (planned
below). The Toolkit's 3D Map Inspector opens all three kinds: a `.bsp`, a `.chim` (its entities as
markers, with the frame it names) and a CHIM world folder, with the heap gate's memory overlay
([3D Map Inspector](../POLYCOUNT_INSPECTOR.md#chim-maps-and-chim-worlds)).

## Summary

| | |
| --- | --- |
| World format | Written by default since v0.0.47: 0.11 generated terrain records (`--chim-terrain-pack generate` with terrain references, `--chim-terrain-refs on`); selectable: 0.10 compact terrain records (`--chim-terrain-pack compact`), 0.7 terrain references with BSP29 terrain records (`--chim-terrain-pack bsp29`), 0.5 (`--chim-terrain-refs off`); experimental and off by default: 0.8 placed models (`--chim-placement-format 0.8`), 0.9 placed models with reach references (`--chim-reach-index refs`). The engine reads 0.4 to 0.11 (`chim/chim_format.h`). History: 0.11 generated terrain records; 0.10 compact terrain records; 0.9 reach references; 0.8 placed models; 0.7 terrain references; 0.6 one folder per sector row for frames of more than 64 sectors (read by the engine, not yet written by the builder); 0.5 story-hidden placements and irregular ground; 0.4 regular terrain grids only and no story-hidden placements; 0.3 chunk standing hulls without the neighbouring ground; 0.2 no placement lists; 0.1 one model pack, one texture pack and one chunk pack per frame. Major 0 = still in development. |
| CHIM version | 0.2.2 with AmiWind v0.0.48, compatibility line 0.2.1: it reads the worlds and caches 0.2.1 built (the table: [CHIM compatibility](README.md#compatibility)) (0.2.1 with v0.0.41; 0.2.0 with v0.0.36; 0.1.0 first shipped with AmiWind v0.0.33); its own number, kept in the `CHIM_VERSION` file at the repository root, the one source: `tools/project_version.py` (`chim_version()`) and the builder receipts read it, and `generate_native` writes `chim_version.h` (`#define CHIM_VERSION`; the engine's `chim/chim.h` includes it) and the boot check's "AmiWind vX / CHIM vY" |
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

On the image (`tools/build.py --builder chim`), the world is a world volume
of its own: the image step (`tools/build_aga.py image --chim-world`) writes it
onto its own partition under `id1/chim/`, and `world/volumes.awv` counts it.
With the compact layout (the default, `tools/layout_plan.py`) it is `DW0`
(volume `AW_WORLD0`) and also holds the open-world frame maps (`id1/maps/`,
written after the world, so the world stays in pack order); with
`--disk-layout legacy` it is the next free world volume `DW<n>` after the
volumes of the open-world maps. The engine adds
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
  origins), or empty. The engine does not read them from the model: from v0.0.48 every frame map carries the
  flames of its frame's placements, made from these (`tools/chim/flames.py`; CHIM-EXTERIOR-FLAMES-MISSING-48).

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

#### Planned: tilt per placement (next release, CHIM-TILT-VARIANTS-SPLIT-33)

Today a placement turns its model by yaw only, so every placement tilted off the vertical (pitch or roll)
gets its own model: the base island has 50,108 tilted placements of 1,476 meshes in 39,103 models, and
the Vivec Temple ring holds 22 coda-flower models where one would do. The planned record carries the
whole rotation, as a Quake entity's `angles` do:

- the record grows to 56 bytes: pitch and roll as two more f32 (Quake `angles[0]` and `angles[2]`) after
  the flags, a format version step that the engine checks (older worlds keep 48-byte records);
- one model per mesh (and scale): the variant key no longer holds the tilt;
- the drawn box is the model's bounds turned by all three angles;
- the engine draws the placement with its full angles (`R_RotateBmodel` already turns brush models in
  three axes), and the chunk clip turns a trace into the model's frame with `AngleVectors` (as
  `SV_ClipMoveToEntity` does), in place of the yaw sine and cosine;
- the Python collision mirror (`chim.collision`) and the stair and walk gates follow the same rule.

Quake turns the trace, not the standing box: a tilted model's standing hull is exact for the point hull
and approximate for the standing box (it stays axis-aligned in the model's frame). The walk and stair
gates measure that on tilted placements before the change ships.

### Terrain image (a world subtree)

A brush image in local coordinates whose nodes and leaves are a piece of the
world BSP, for the chunk's tiles:

- tree: axial splits on tile edges (alternating x and y, halving the tile
  range), then per tile the vertical plane through its diagonal when it is two
  triangles, then the ground plane of each triangle (back: solid leaf 0),
  then, where the ground dips below the water level, the water plane (back:
  water leaf, front: air leaf). Node 0 is the root; dmodel head node 0 is the
  root (the world's point hull is its node tree), head node 1 the standing
  hull. Leaf bounds reach the frame ceiling above the ground: 2048, or, in a
  frame whose ground comes within 512 units of it (Red Mountain, up to 4,730),
  the highest ground plus a 4,096-unit flight band rounded up to 1,024 (9,216
  there), so every node and leaf box holds its faces; every non-solid leaf
  lists its tile's faces as marksurfaces; no visibility lump (visibility is
  the chunk's PVS row);
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

## Terrain references (0.7, experimental)

A world built with terrain references (`tools/chim_build.py --terrain-refs on`, `tools/build.py
--chim-terrain-refs on`; off by default) stores every chunk's terrain once per content and lets each
chunk name it, as models and textures are stored once and named by placements. Neighbouring CHIM region
frames ([CHIM_REGIONS.md](CHIM_REGIONS.md)) overlap by their terrain margins; with references the
overlap is stored once, and flat sea floor anywhere is one record. Such a world is written as format
0.7; every other world stays 0.5, byte for byte. An engine older than 0.7 refuses a 0.7 world by its
minor version, with its usual message.

- The terrain image of a chunk is built in **chunk-local** units: the chunk's low corner at 0, 0 (the
  same tree, faces, texture vectors and standing hull, moved). It is a sector record of kind `TERR`
  (id = the terrain record's number in the world, 0..n-1 in pack order), stored in the sector that first
  meets it (records in the order `CHNK`, `TERR`, `MODL`, `TEXR`). Two chunks with the same ground have
  byte-identical records, whatever frame or position they are in.
- A chunk whose terrain is a reference has the magic `CHK1` and, where the terrain image would be, a
  reference block (32 bytes, big-endian): u32 terrain id, u16 file row of the record's sector file,
  u16 reserved (0), u32 offset of the record in that file, u32 record bytes, u32 render bytes, f32 shift
  x, y, z in local units. Its directory entry counts the head, rows and block as render bytes and 0
  collision bytes.
- The engine loads the record named by the block and, when it grafts the chunk into the frame world,
  moves its copy by the shift: plane distances (`dist += normal . shift`), vertexes, node and leaf
  bounds, each lit face's texture minimums (`+ texture axis . shift`), and the chunk's box. The builder
  only makes references whose shift is whole units and moves every texture axis by a multiple of 16
  texels, so the moved texture minimums equal the ones measured on moved vertexes (water and sky faces
  keep their fixed values). Everything else (texinfo, faces, edges, lightmaps, clipnodes) does not
  depend on the position.
- Each chunk keeps its own decoded copy in the zone, as before: memory and the heap gate are unchanged
  by references (sharing one decoded record between chunks is a later step). A record homed in another
  frame's sector file costs one more file seek when it loads.
- An edge chunk of a frame gets the whole ring of its standing hull from the ground one tile past the
  frame (the same content as the same chunk inside a neighbouring frame); the source manifest carries
  those heights (`terrain_outer`), and the validator checks the hull against them.
- Tools read a referenced chunk as the engine places it (`chim.validate.load_world` moves the record by
  the shift: `chim.format.translate_image`), so every gate (validation, stairs, heap, zone walk, border
  audit) runs on the world in frame coordinates. The validator also checks that every reference points at
  a `TERR` record of the stated size and every `TERR` record is referenced.

Measured on scratch worlds of CHIM region frames (one cell each, 896-unit terrain margin;
CHIM-REGION-MARGIN-STORAGE-36), against the open-world maps they replace:

| Cells | Open-world maps | Copies, routed hull | Copies, compiled hull | References, compiled hull |
| --- | ---: | ---: | ---: | ---: |
| 7 (3 coast, 4 sea floor) | 2,105,504 | 9,012,728 | 4,908,676 | 1,912,960 |
| 6 (coast) | 2,768,088 | 10,024,380 | 5,089,260 | 2,586,432 |

The compiled standing hull (`--terrain-hull compiled`: qbsp's exact union of the same pieces, the hull
Seyda Neen's irregular ground already uses) takes about half the bytes; references take the margins
shared between neighbours and every repeated chunk. File counts do not change.

## Compact terrain records (0.10, experimental)

A world built with `tools/chim_build.py --terrain-refs on --terrain-pack compact` (`tools/build.py
--chim-terrain-pack compact`; `generate` by default since v0.0.47, `bsp29` before) may store a `TERR` record in a compact form that the engine expands
back into the very same BSP29 bytes before its usual loaders read them (`chim/chim_terc.c`; builder
`tools/chim/terc.py`). Such a world is written as format 0.10; a default build writes the same bytes as before. The
engine reads 0.4 to 0.10; an engine older than 0.10 refuses a 0.10 world by its minor version. In a 0.10 world every
chunk head names its placement record size (0: 48 bytes, 56: placed), so the option combines with either placement
format.

- **Record.** Still a sector record of kind `TERR`, told apart by its first four bytes: `TRC1` instead of the BSP29
  version. Head (16 bytes, big-endian): `TRC1`, u32 image bytes, u32 render bytes, u16 15, u16 0; then 15 entries of
  8 bytes in the image's file order (u8 method, u8 0, u16 0, u32 payload bytes); then the payloads, each on a 4-byte
  boundary. The payloads keep the image's little-endian bytes: expanding is byte shuffling, no arithmetic.
- **Methods** (each exact; a lump none of them holds is stored as it is): planes with an axial normal (bit for bit
  the unit vector on an axis, either sign, zeros of either sign) as a one-byte code and the 4-byte distance instead
  of 20 bytes; a light lump of one value (the terrain's uniform light) as its length and that value; clipnodes and
  nodes whose plane numbers fit 16 bits with a 16-bit plane number (6 and 22 bytes instead of 8 and 24).
- **Which records.** Only a record that comes out smaller and whose compact form plus its image fit the engine's
  smallest loading buffer (18,448 bytes): the engine reads it to the end of that buffer and expands it to the start,
  then loads it as any image. Larger records stay BSP29 images in the same world.
- **Tools** expand a compact record when they read it (`chim.validate`), so every reader and gate sees the same image
  as in a plain world.

Measured (host tests, `tests/test_chim_terc.py`: the builder's own world with terrain references written plain and
compact): every compact record expands to the plain world's record byte for byte, in Python and in the engine's
expander (natively); the validator reads both worlds into the same chunks; the engine's seam walk on the compact
world prints the same lines as on the plain one. On the v0.0.46 world (read only, all 97,369 terrain records): every
record packs and expands back exactly (and 9,359 of them, every tenth, through the engine's C expander); 93,509
records come out compact, 3,860 (65.6 MB) are too large for the buffer and stay; the terrain records go from 489.4 MB
to 450.8 MB (-38.6 MB, 7.9 %; -42.4 MB if every record were compact). The planes save 8.7 MB (85 % of the terrain's
6.8 million planes are slanted and keep their 20 bytes), clipnodes 23.1 MB, nodes 4.0 MB, light 7.8 MB.
The texinfo rows (9.5 MB, 19 distinct island-wide) would need a world-level table and are not packed.

## Generated terrain records (0.11, experimental)

A world built with `tools/chim_build.py --terrain-refs on --terrain-pack generate` (`tools/build.py
--chim-terrain-pack generate`; the default since v0.0.47, decided for the project, 2026-10-21) stores a regular-path terrain record (the builder's tile rule) as its corner heights and the facts the builder
decided (record version 1), and a record of the converter's own triangles (shoreline insertion, 32-unit detail
tiles) as its 32-unit samples and the triangles (record version 2); the engine generates the render part when the
chunk joins (`chim/chim_thgt.c`; builder `tools/chim/thgt.py`): the same BSP29 bytes as the
record it replaces, then loaded as before. Every other record is written as in a 0.10 world (compact, or as it is).
Such a world is written as format 0.11; the engine reads 0.4 to 0.11; a default build writes the same bytes as before.

- **Generated:** the vertexes, edges, surfedges, faces, texture mappings, leaves, marksurfaces, nodes (tree, bounds,
  faces), the uniform light lump and the model, by the builder's own regular-path rule (axial splits on the tile grid,
  the tile diagonal where a tile is two triangles, the ground plane node, the cut of a ground polygon whose texture
  span passes 240 texels 224 texels from its low line, the water plane node and the water face where a tile lies under
  water, the ground polygon cut where the water line crosses it). Version 2: each tile split on its triangles'
  edges as the builder splits it (the cut through a triangle edge that cuts the fewest triangles, then the most
  even one, until one ground plane is left), the corners of each region from the triangle corners or from their
  plane, then the ground plane, water and texture splits as above.
- **Stored:** the corner heights (f32), per tile its texture slot and four facts (one quad or two triangles; under
  water; the texture axis of each ground polygon), the plane of every node, the plane lump and the standing hull as
  the compact record packs them, the texture references, the light value and size. The planes are stored so the
  generation needs no floating-point arithmetic beyond copies, sums of whole units, comparisons (floor and ceil are
  taken from the bits) and one formula, the point where an edge crosses a cut (`p + (q - p) * d / (d - e)`, in double
  precision as the builder computes it; on the Amiga the generator sets the FPU to double rounding precision and
  restores it after): an Amiga's FPU gives the same bytes as the builder's computer (not yet measured on a 68040 or
  68060). The standing hull is qbsp's
  compiled union of the tile prisms and stays stored.
- **Record:** a sector record of kind `TERR` starting with `THG1`: head (72 bytes, big-endian: image and render
  bytes, version 1, tiles across and along, nodes, the box, floor, ceiling, water level, tile step, light size and
  value, water texture slot, the sizes of the plane, clipnode and texture-reference payloads, the standing hull's
  root), the heights, the tile facts, the node planes (u16), the texture references, then the plane and clipnode
  payloads. Version 2 (version field 2): the 32-unit samples of the chunk (f32), per tile its texture slot and
  triangle count, every triangle as three sample indices in the builder's order, then as version 1. The triangles
  come from the frame's ground when the world is packed; lava records are not generated (their prisms are not in
  the record). The engine's generator has fixed buffers (16 corners per polygon, 64 pieces per region, 6,144 piece
  corners alive at once); the builder refuses a record that would need more. Only a record whose generation equals the stored record byte for byte, that comes out smaller, and that
  fits the engine's smallest loading buffer with its image is written so.

Measured (host tests, `tests/test_chim_thgt.py`: the builder's own world with terrain references written plain and
generated, with regular and with irregular ground): every generated record gives back the plain record byte for byte, in Python and in the engine's generator
(natively); the validator reads both worlds into the same chunks; the engine's seam walk prints the same lines. On the
v0.0.46 world (read only, all 97,369 terrain records): 83,236 records are generated as version 1 (353.2 MB of records
stored in 167.4 MB) and 12,582 as version 2 (91.5 MB as compact records today, 40.6 MB generated: 11,820 of the
13,284 records holding the converter's own triangles, 736 of the 738 shore records the version-1 rule refused, 26
others); the engine's generator gives back every tenth of each (8,333 and 1,270) byte for byte; the terrain records
go from 489.4 MB to 247.6 MB with the rest compact (-241.8 MB, 49.4 %; 450.8 MB with the compact pack alone). Not
generated: 563 lava records, 886 whose record and image together do not fit the engine's loading buffer (18,448
bytes; 292 would fit 20,480, 586 would fit 24,576), and 100 whose generation differs from the stored record in its
texture mappings (a face given the texture axes of another base direction than its plane; the cause is not found).
The work per generated version-1 chunk (mean of the
8,333): 8 tiles, 15.5 ground polygons, 6 grid and water splits, 0.3 texture splits, 32 vertexes, 13 faces, 17 nodes,
11 leaves, about 3.4 KB of image written, in two passes (count, then write); no 68040 or 68060 timing yet. The zone holds the same decoded chunk as before (the same image); the loading buffer holds the record and
the image, as for a compact record.

## Placement light, stores and room records (0.12)

For interiors on CHIM ([INTERIOR_STORE.md](INTERIOR_STORE.md)). A world or room record that uses any of this is
written as format 0.12; the engine reads 0.4 to 0.12, and an engine before 0.12 refuses it with the usual message.

- **Placement light level.** In a placed record (0.8 layout) the high byte of the 16-bit flags (bits 8 to 15) is the
  placement's light level: 0 = none (lit as before: ambient, dynamic lights, self-lit textures), 1 to 255 = the level
  its faces are drawn at instead of the ambient, in the units of `r_refdef.ambientlight`. Bits 0 and 1 keep their
  meaning; bits 2 to 7 stay 0. Before 0.12 the high byte is not read. Engine: `ChimFormat_RecordLight`
  (`chim/chim_format.c`) into `entity_t.aw_light` (appended); `d_edge.c` hands it to `D_CacheSurface` in
  `r_drawsurf.light`, `R_BuildLightMap` starts from it, and `surfcache_t.light` keeps the level a surface was built
  with, so another level rebuilds it. In an exterior world (from v0.0.48, experimental, `--chim-placement-light
  sources`: the light the original's light sources give the placement, `tools/chim/placement_light.py`) the level is
  added to the daylight-dimmed ambient instead, never past the full-day ambient (`R_SkyExterior`; `r_lamps 0` turns
  it off); an exterior world with levels is written as format 0.12 and needs placed records (0.8 and later).
- **Store folders.** Every pack path is `<store>/<relative>`; the store is named by the map's worldspawn key
  `"_chim_world" "<store>"` (1 to 8 of `a-z`, `0-9`, `_`; absent: `chim`, the exterior world). Changing stores drops
  the resident index, every kept model and texture and the read-ahead blocks (ids are per store). An interior store
  (`chimi/`) is an index with the exterior layout and no frame rows, its models and textures in pack files.
- **Room records.** `<store>/rooms/<room>.crm` (room names: 1 to 22 of `a-z`, `0-9`, `_`, `-`), big-endian:

| part | bytes | content |
| --- | ---: | --- |
| header | 32 | the common header: kind `ROOM`, count = placements, directory = 64 (the model list), data = 64 + 4 x models (the placements), file bytes |
| room block | 32 | mins (3 x f32), maxs (3 x f32), model count (u32), 0 (u32) |
| model list | 4 x models | store model ids (u32), in load order |
| placements | 56 x placements | placed records (0.8 layout, the light level in the flags); the model field is a store id from the list |

  A record with placements lists at least one model; a minor before 0.8 (no placed records), bounds that are not
  numbers or with mins over maxs, a non-zero reserved word or offsets that do not match the counts are refused whole
  (`ChimFormat_Room`).
- **Room maps.** A map whose worldspawn has `"_chim_room" "<room>"` is a room map: under the loading plaque the engine
  reads the record, loads every model it lists whole from the store (with their textures) and keeps them locked, links
  each placement with efrags into the map's own world and collides with it through the placed collision path (piece
  table, then the turned or yawed model); no frame, terrain or chunk ring. Everything goes at the next map
  (`chim/chim_room.c`).

## Placed models (0.8, experimental)

A world built with `tools/chim_build.py --placement-format 0.8` (`tools/build.py --chim-placement-format 0.8`;
0.7 by default) stores one model per mesh and scale, and puts the whole rotation into the placement record
([CHIM-TILT-VARIANTS-SPLIT-33](../bugs/CHIM-TILT-VARIANTS-SPLIT-33.md)). Until then a tilted placement got a model
of its own with the tilt baked in, and only the yaw was left to the record. Such a world is written as format 0.8;
a default build writes the same bytes as before (0.5, or 0.7 with terrain references). The engine reads 0.4 to
0.8; an engine older than 0.8 refuses a 0.8 world by its minor version, with its usual message.

- **Placement record: 56 bytes.** The 48 bytes of the record above, then the pitch and the roll (f32, degrees).
  The three angles are Quake's entity angles (pitch, yaw, roll): the renderer turns the model with them as it
  turns any brush entity (`r_bsp.c` R_BuildBmodelRotation), so drawing a tilted placement needs no new engine
  code. The builder converts the game's rotation (Z, then Y, then X of the negated angles) once and checks the
  turn of the stored angles against it (within 1e-5); a placement that turns about Z only keeps the 0.7 record's
  yaw exactly and pitch and roll 0. The drawn box is the model's bounds turned by all three angles.
- **Chunk head.** The last u16 of the chunk head (0 until 0.7) is the size of the chunk's placement records: 56.
- **Models.** A placed model is built untilted (scale, the visual offset and the flattening shift baked as
  before), so one model serves every tilt of a mesh at one scale. Lump 4 of its brush image (visibility, which a
  placed model never uses) holds its **piece table**: the convex collision pieces of the mesh, unexpanded, in
  the model's frame (big-endian: `PCS1`, pieces, table bytes, 0; per piece a 36-byte entry with its plane,
  corner and edge counts, its box and the offset of its data; then per piece its planes as 4 x f32 with
  n.x < d inside, its corners as 3 x f32 and its edges as 3 x u16: the two planes that meet there and one
  corner). The stored point and standing hulls stay in the image.
- **Collision.** The engine turns each record's angles into a matrix once, when the chunk's catalogue is read
  (the renderer's own arithmetic, so a placement collides where it is drawn). A trace expands only the pieces
  its swept box meets: the piece turned into the world and moved out by the world-aligned player box, with
  every facet of the Minkowski sum (own planes, axial and edge bevels), then traced as a point
  (`chim_placed_clip.c`). That is the exact expansion the builder bakes for a tilted variant, and the box no
  longer turns with a yawed model ([CHIM-YAW-PLAYER-BOX-TURNS-46](../bugs/CHIM-YAW-PLAYER-BOX-TURNS-46.md)). A
  model whose table cannot be used (a piece of more than 128 planes, or a trace that meets more than the
  2,048-plane scratch) keeps its stored hull: by the yaw path for a yaw-only record, turned by the matrix
  otherwise (the box then turns with the model).
- **What keeps its tilt.** A model that clips its faces to the terrain (a visual recipe's `clip_to_terrain`)
  keeps the 0.7 variant with its tilt baked, its records carry its yaw only. The large-model cut works by tiles
  only (`cut_mode tiles`): the tiles of the untilted model turn with the placement's angles.
- **Python tools** read either record size (`chim.placed.read_chunk`); the validator checks the turned boxes.
  The Python collision mirror (`chim/collision.py`, the stair walk's code) still reads only a record's yaw: it is
  left unchanged so the stored walks keep their keys, and it does not collide a tilted 0.8 placement as the engine
  does. A 0.8 world is not walked or ground-checked by it yet.

Measured (host tests, synthetic boxes through the real units; `tests/test_chim_placed_format.py`): the drawn
vertices of every placement agree with 0.7 within 0.02 units; the placed collision equals the exact expansion of
the turned pieces on every trace (2,700 of 2,700, largest difference 0.004 units); against 0.7's stored hulls,
point traces agree on every placement, box traces on every placement whose record has no yaw, and differ on
yawed ones by the turning box. Estimated on the v0.0.46 world (read-only, its model directory and point hulls):
32,714 models become 8,105, model records 735.8 MB become about 229.3 MB plus about 42.9 MB of piece tables,
placement records grow from 52.2 MB to 60.9 MB. Nothing of it is seen in game yet: that needs a build.

## Reach index (0.9, experimental)

A world built with `tools/chim_build.py --placement-format 0.8 --reach-index refs` (`tools/build.py
--chim-placement-format 0.8 --chim-reach-index refs`; `copies` by default) keeps each placement record once per
frame ([CHIM-PLACEMENT-MARGIN-COPIES-46](../bugs/CHIM-PLACEMENT-MARGIN-COPIES-46.md)). Until then every chunk
that a placement's drawn box touches, besides its owner chunk, held a whole copy of the owner record (a reach copy,
48 or 56 bytes). Such a world is written as format 0.9: format 0.8 (placed models, 56-byte records) with reach
references. It needs the placement format 0.8 (the builder refuses it otherwise). A default build writes the same
bytes as before. The engine reads 0.4 to 0.9; an engine older than 0.9 refuses a 0.9 world by its minor version.

- **Chunk record.** Magic `CHK2` (terrain image inline, as `CHK0`) or `CHK3` (terrain reference block, as `CHK1`).
  The head's reach count is the number of references and its last u16 the record size (56), as in 0.8. The owned
  records (by id) are followed by the **reach references**, 4 bytes each, big-endian: u16 owner chunk (its index
  in the frame, pack order), u16 the record's position among that chunk's owned records. They come in placement id
  order, which is owner chunk and record order. Then the PVS row, the placement row and the terrain, as before.
- **Same frame only.** A reference names a record of the same frame, so it never opens another frame's files.
  Everything else (index, frame file, sector files, models, textures, terrain records, ids and their order) is the
  0.8 layout: model and texture ids are handed out as before, reach placements included.
- **Engine.** When a chunk's catalogue is read, a reference whose owner chunk's catalogue is already in the zone
  is copied from it (no read); otherwise the record is read from the owner chunk's own record list: one read per
  owner chunk, from the first to the last record the chunk's references name there (`chim_chunks.c`
  ReachRecord). Either way the chunk's run-time placements are the ones a 0.8 world gives: same ids, models,
  owners, origins, angles, drawn boxes and matrices. The dbg pin re-reads a reach placement's record through
  its owner.
- **Python tools** read the references with `chim.reach` and resolve them per frame (`resolve_frame`), so the
  validator and every tool that reads a world through it see the records a 0.8 frame stores as copies. The
  validator refuses a reference that names no owned record, or a record its named chunk does not own.

What it does not do: a placement is still stored once per **frame** that owns it, so an object in the
overlapping margins of neighbouring region frames is stored in each of them (about 3.5 frames per object on
the v0.0.46 world). Storing it once for the whole island needs chunks cut on one island grid with pages and a
table of placements that cross chunks, which this format does not have yet.

Measured (host tests on synthetic boxes through the real units, `tests/test_chim_reach_index.py`;
`tests/test_chim_engine_native.py` for the engine): every chunk of a 0.9 world holds, once resolved, the
records of the same chunk of the 0.8 world; model, texture and terrain records are byte-identical; each chunk
record is 52 bytes shorter per reach entry; the engine's catalogue of every loaded chunk (ids, models, owners,
origins, angles, drawn boxes, matrices), the dbg pin and the placed collision give the same results in both
worlds, with the references copied from the zone and with every one read from disk.

Estimated on the v0.0.46 world (read only, its 308,754 chunk records): 469,266 owned records and 619,074 reach
copies. Placement bytes in 0.8 60.9 MB (34.7 MB of reach copies), in 0.9 28.8 MB (2.5 MB of references); the
0.7 records of today take 52.2 MB. The cost is on reading: when no owner catalogue is in the zone, reading
every chunk's catalogue once takes 78.7 MB in 985,500 reads against 68.4 MB in 517,059 reads with copies
(468,441 owner record runs, 193,142 of them in another sector file of the frame).

How often the owner chunk's catalogue is already in the zone, measured with the zone walk simulator
(`tools/chim/zone_sim.py`: the engine's zone allocator and ring rules, block sizes of the target) on the v0.0.46
world, the same walks for both forms: the 12 legs of the crossing route (each across its border, a fresh zone at
the frame change) and four straight walks of eight cells across region frames, 4,328 steps. Each frame on its
own zone (the type 1 window, several frames in one zone, is not simulated). 128 MB: the zone plus the 97 MiB of
cache banks the engine takes with 128 MiB, look-ahead x3.

| Memory | Catalogue loads | Reach entries | Owner in the zone | Bytes read, 0.9 / 0.8 | Reads, 0.9 / 0.8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16 MB | 4,363 | 15,039 | 42.2 % | 1.45 MB / 1.60 MB | 17,318 / 8,341 |
| 128 MB | 7,342 | 25,341 | 44.5 % | 2.38 MB / 2.67 MB | 28,640 / 14,029 |

So 0.9 reads about 10 % fewer bytes per catalogue but about twice as many times: the references are a read
of their own, and more than half of them need a run of their owner's records, a third of those in another
sector file. On a classic FFS disk a read costs more than its bytes; nothing of it is seen in game yet.

Three ways to make it cheaper on reads, priced on the same walks (file reads and bytes of every catalogue
load; 0.8 copies on the same schedule as the reference):

| Variant | Reads 16 MB | Bytes 16 MB | Reads 128 MB | Bytes 128 MB |
| --- | ---: | ---: | ---: | ---: |
| 0.8 copies | 8,341 | 1,596,608 | 14,029 | 2,670,224 |
| 0.9 as written | 17,318 | 1,450,012 | 28,640 | 2,384,964 |
| (a) owned records and references in one read | 14,781 | 1,450,012 | 24,425 | 2,384,964 |
| (b) owner chunks loaded before the chunks that reference them, with (a) | 13,914 | 1,387,260 | 22,253 | 2,228,080 |
| 0.8 copies on the schedule of (b) | 8,837 | 1,724,696 | 14,801 | 2,864,288 |
| (c) a whole copy where the owner chunk was resident less than 75 % of the time on the other walks, with (a) | 8,408 | 1,589,364 | 14,175 | 2,642,896 |
| (b) and (c) at 75 % | 8,909 | 1,711,256 | 14,961 | 2,821,704 |

(c)'s threshold is taken from the other walk group (the long walks judge the crossing legs and the legs judge the
walks), never from the walk it is judged on; 25 %, 50 % and 90 % give the same picture. None of them reads as
seldom as 0.8 copies while saving bytes: (a) and (b) still pay a read for every absent owner, and (c) can only
avoid those reads by turning nearly every reference back into a copy (97 % to 98 % of them at 75 %), which leaves 0.5 %
to 1 % of the bytes saved for 1 % more reads. Whether an owner is resident depends on the direction the player
comes from (the ring loads nearest first), so no rule fixed in the data separates the references that will find
their owner. Format 0.8 copies stay the recommended form; 0.9 stays experimental and off.

## Actor table (experimental)

An image built with `tools/build.py --chim-actor-table on` (`build_aga.py image --chim-actor-table on`; the
builder's default since v0.0.47, decided for the project, 2026-10-21; `off` writes none) carries `maps/chim-actors.cca`: every exterior NPC and creature reference of the game data in one
island-wide table outside the frames ([CHIM-EXTERIOR-ACTORS-MISSING-46](../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md)).
The type 1 window takes a joining frame's actors from it with `chim actors table 1`: the engine's own setting is
off and not saved (the actors of the frame maps, as before), so an image built with the table ends
`id1/default-game.cfg` with that line (`build_aga.py` `stage_chim_actor_table_config`; `chim actors table 0` in the
console gives the actors of the frame maps back). Written by `tools/chim/actors.py`, read by `chim/chim_actor_table.c` and `aw_actors.c`.

Until v0.0.54 that line did nothing: the game runs `default-game.cfg` before any map starts, and the engine's
`chim actors` command stopped while no map ran before it reached its settings, so from v0.0.47 to v0.0.53 every
joining frame took the actors of its frame map and the 5,082 levelled creature references of the exterior were never
rolled ([CHIM-ACTOR-TABLE-SETTING-DROPPED-47](../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md), found 27 October 2026).
From v0.0.54 the settings (`table`, `budget`, `warm`, `seed`, `trace`) take before a map runs
(`tests/test_actor_table_setting.py`). What changes with it: a joining frame's actors all come from the table,
NPCs included, in place of the frame map's actor rows (the region frames' placed rows are in the table as built
rows, flag 2, so they keep their placed positions); the frame a map starts on still spawns its own map's rows. The
table path ran only in tests and by hand before; a difference against the frame maps' NPC rows is a finding.

The rooms' levelled creatures (from v0.0.54): the table's levelled lists are every list the exterior or a room
references (`tools/chim/actors.py` `table_list_order`, one order for the table and the room stage; 58 lists give
the 1,270 levelled references of Morrowind.esm's rooms), and its bases every creature those lists can give, with the
actor library's models (a mesh only the rooms' lists reach is baked with the skeletal method). A room map carries
each levelled reference as an `aw_levelled` entity: `aw_ref` the reference number, `sounds` the list's index in that
order, origin and angle as the room's creatures. The engine takes such an entity while the map loads
(`pr_edict.c` hands it to `aw_actors.c`), rolls it as an outdoor levelled reference (the player's level, the pick
kept under the reference, so the room gives the same creature again, or nothing) and spawns the creature there.

- **Records** (24 bytes, big-endian): u32 key (the reference number & 0xFFFFFF), u16 base, u16 flags, f32 origin
  x, y, z in the local units of the reference's own cell (the cell centre at 0, 0: the frame-local units of that
  cell's region frame), f32 yaw (degrees). Flag 1: the origin is the builder's baked ground point; flag 2: the
  record is a built actor row of a frame map (its position as placed there), else the game data's position.
- **Bases** (12 bytes): u32 text offset, u16 text bytes (0: no actor model in this build), u16 kind (NPC,
  creature, levelled creature list, dead resident), u32 FNV-1a of the base record's id.
- **Cells** (16 bytes per exterior cell with actors, in 4 x 4-cell page order): i16 x, i16 y, u32 first record,
  u32 records; a cell's records are contiguous.
- **Base text**: the key/value pairs of the built actor row without its per-placement fields; the engine parses
  it as the entity (`ED_ParseEdict`) and sets the origin, angles, reference and baked ground from the record.
- Header (48 bytes): `ACT1`, u16 0, u16 version (1 or 2), u32 48, then counts and offsets of the cells, records
  and bases, the text offset, the file size, and (version 2) the offset of the list section (0 in version 1).
- **Levelled creature lists** (version 2, what the image step writes since v0.0.47): a levelled reference's base
  (kind 2) has no text and its offset field is the index of its list; every creature a used list can give has a
  creature base of its own. List section: u32 lists, then per list 8 bytes (u32 first entry, u16 entries, u8
  chance none 0-100, u8 flags: bit 0 "calculate from all levels at or below the player's"), then the entries, 4
  bytes each in the record's order (u16 level, u16 target: a base index, `0x8000 | list` for a list inside a list,
  `0xFFFF` for an entry that names no record).

How the engine resolves a levelled reference (`ChimActors_LevelledPick`, the rule read from OpenMW 0.51's levelled
list code, our own implementation; the builder's `levelled_pick` is the same and the tests compare them roll by
roll): when the reference's cell joins, one roll at the player's level: chance none first (a roll 0-99 below it
gives nothing); the candidates are every entry at or below the level when the list calculates from all levels,
else only the entries at the highest level at or below it; no candidate gives nothing; one candidate is picked
uniformly; a list picked is rolled again at the same level. The pick is kept in the change list under the
reference, so a later join spawns the same creature (or nothing), and the creature keeps the list reference's id
for its death and moves. The random numbers come from the reference's key and a session seed (`chim actors seed
N`); OpenMW draws them from the game's generator and saves the pick. Not done: the respawn (OpenMW rolls a list
again at a cell load once its creature has been dead for the corpse delay, 72 game hours in the game data).

What it does not do: only an actor whose model a build made has base text (today the town residents); every
other NPC and every creature is in the table without a model, and the engine counts it as not spawnable (a
levelled reference that gives such a creature too). A creature model library (`tools/creature_library.py`, one
model per creature mesh, not part of any build yet) can give the creature bases their text
(`tools/chim/actors.py --library`). The frame maps keep their actors in every case.

**Instance scales** (version 3, what the image step writes when an exterior reference has a scale other than 1:
the game data has 5): after the list section, u32 count, then per scaled record u32 record index and f32 scale
(by record index). The engine sets the spawned entity's `aw_scale` and draws it at that scale: the server sends
a live alias entity's scale other than 1 in its update (bit `U_AW_SCALE`, a float after the angles) and the client
scales it as it scales statics (the alias transform's entity scale). The original also scales the creature a
levelled list gives by the list reference's scale. The previous method stays selectable: when the creature
library has models baked at a scale (`tools/actor_library.py --scaled-variants`, keys `id@S`), a scaled creature
reference takes a base naming that model, a scaled levelled reference a copy of its list whose creatures do, and
the record carries flag 4 (the base's model is already at the record's scale: the engine does not scale it
again).

**In saves** (v0.0.47, experimental): the change list goes into the save as AWS4 feature bit 8, so a levelled
list's pick, a death, where an actor was left with its health, and a fight survive a save and a load. Per entry 36
bytes, sorted by key: u32 key (the game's reference; bit 31 marks a builder-made object, the intro roles; bits 24-30
are always 0, the pieces of a cut object share their source's state), u16 flags (dead, moved, fight, follow, pick,
scene), u16 pick, i32 cell (x in the high half, y in the low) or a scene id, f32 island position x, y, z, f32 yaw,
f32 health, f32 game hours when captured. A save holds at most 2,048 entries (a full list makes a save of about
75 KB, so the size limit of a save is now 256 KiB). An older reader refuses a save with the list; a save without it
is the same bytes as before, and old saves load as before (their actor rows read as "moved + health" entries of
their scene). Following actors are saved but not re-attached at a load; no respawn yet.

Measured on the game data (read only, 21 October 2026): the exterior uses 61 of the game's 116 levelled creature
lists (676 entries; every one calculates from all levels, 25 have a chance none, none holds another list, none
names a missing record); they can give 49 creature records at player levels 1 to 30 (17 at level 1). The list
section is 3,196 bytes; the version 2 table 205,180 bytes, 633 bases.

Measured on the v0.0.46 release image's frame maps and the game data (read only): 5,981 references (566 NPC,
333 creature, 5,082 levelled creature lists) in 1,058 cells, 601 bases, 201,600 bytes (records 143,544, cell
directory 16,928, bases 7,212, base text 33,866). 91 records are built rows: 90 living town residents, which can spawn, and one dead resident. Per 2 x 2-cell
window: at most 50 actors (p99 38), with doors, containers, items and activators at most 312 (p99 186).

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

Project rule (8 October 2026): CHIM must keep Quake's visibility working, never
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
    deferred until a frame holds more statics than the engine's static-entity limit (maintainer
    decision, 8 October 2026). Seyda Neen's region maps hold 229 such statics.
- Frame maps: `maps/seyda-chim.chim` (the town) and `maps/intro_docks-chim.chim`, both naming the
  same frame. The docks map is checked one way: its statics must be in the frame, and the frame
  holds the rest of the town as well. It copies the docks' own entities and turns the route
  boundary of the legacy docks map into four clip walls: `func_wall` brush models with a
  standing hull and no faces (Quake's clip brushes). The region maps' per-region worldspawn key
  `aw_render_pool` (terrain-culled faces, CHIM-HIDDEN-FACES-33) is left out and recorded.
- Parity reference: the recorded v0.0.31 Seyda Neen maps that v0.0.32 ships
  (BUILD-SEYDA-REGEN-30). The legacy region cut cannot be regenerated from scratch
  (BUILD-SEYDA-CULL-STABLE-32).
- A CHIM build ships Seyda Neen on CHIM only, with the strict heap gate and no exception
  (project decision, 8 October 2026). The legacy Seyda Neen maps stay buildable and selectable
  with `--builder legacy`.

The sea is the water plane at z = 0 that every chunk already carries. The sky
and sea enclosure brushes of the legacy town map are not copied: the resident
layer draws them. Parity is the same two-way gate as for the other towns:
statics, alias models and sprites of the final `sn` maps against the CHIM
records, harvest catalogues `AWH4` only, and the frame origin. Seyda's legacy
private stages (BUILD-SEYDA-REGEN-30) and its heap overlap
(HEAP-SEYDA-OVERLAP-32) stop applying once Seyda runs on CHIM.

## Planned: all of Vivec (M3) and the open world (M4)

Maintainer direction (8 October 2026): builds go pure CHIM. Every exterior comes from the CHIM builder;
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

- The union of the eight Vivec district frames, in Morrowind units, is x 12,800..52,736 and
  y -113,664..-70,144. That is 39 x 43 chunks, rounded to 13 x 15 sectors: 195 sector files.
- Stage A's Arena frame lies inside it, so stage B replaces stage A's frame; the Arena area stays
  selectable.
- Source: the town converter once per district (`import_town.collect`), with references merged
  by reference number. Shared meshes must have equal visual profiles in every district, or the
  build stops.
- Memory, measured per district frame (9 October 2026, the large-model cut on at 512 units, tiles;
  active ring against the 6,242,304-byte chunk room). The district frames overlap, so each one also
  holds its neighbours' edges; one city frame changes where the peaks sit, not what a ring around a
  position holds:

  | District frame | Active ring peak | |
  | --- | ---: | --- |
  | Arena | 5,337,232 | fits (6,492,688 whole) |
  | Foreign Quarter | 4,762,912 | fits |
  | Hlaalu | 5,722,112 | fits |
  | Redoran | 4,947,728 | fits |
  | Telvanni | 3,705,424 | fits |
  | St. Delyn | 7,776,368 | over |
  | St. Olms | 7,746,288 | over |
  | Temple | 8,254,320 | over |

  Every frame over the room peaks in the Temple district: the two Vivec statues (727 and 526 KB), the
  Ministry of Truth's tiles, the dock and the High Fane. Named detail budgets
  (`config/chim-detail-budgets.json`, not applied by default) bring the Temple frame to 6,776,624
  ('vivec') and 6,423,456 bytes ('vivec-wide'), still 181,152 over. The rest is a project decision: deeper
  budgets, simpler distant detail beyond about 300 units, or a stated closer view in that district.
  Project decision (9 October 2026): simplify the dense meshes, with the open rim locked. Budget 'vivec-deep'
  ('vivec-wide' plus the coda flowers at 150 triangles, the Ministry of Truth at 1,500, the statues at 900,
  and the High Fane's main body at 700) fits the Temple frame at the full 540 view: active ring peak
  6,222,288 B, 20,016 B of headroom, stair gate passing. No closer view and no distant detail level are
  needed. It becomes the Vivec default after the in-game and OpenMW A/B shots.
- Frame plan (9 October 2026): one city frame, not grid frames.
  - Grid frames (the M4 grid, 3 x 3 cells) would cover the city with six frames, but until the engine's
    ring spans frames (M4), every frame edge inside the city is a hand-over: a map load and a visible end
    of the world mid-street. One city frame keeps the walk through Vivec seamless with today's engine.
  - The eight district frames overlap; one frame holds every placement once (no district stored twice)
    and one ring at every position.
  - What one city frame needs:
    1. format 0.6 row folders: 195 sector files exceed the 72-entry directory rule in one frame folder
       (the 0.6 reader is in the engine; the writer is ready and waits for this frame);
    2. BLOCKED (CHIM-FRAME-COORD-RANGE-33): the engine's hand-over bound for table frames keeps core
       boxes and arrivals within 4,000 local units (`aw_world.c` valid_town). That bound is Quake's
       coordinate range, not a format limit: positions travel as shorts of eighths of a unit, so they
       wrap past about 4,096. The district cores span 8,192 by 9,216 units, so one frame cannot hold
       the walk. The options are two frames (for example, Temple, St. Delyn and St. Olms in the south
       and the rest in the north), a wider coordinate protocol (an engine-wide change), or M4 frames
       that span;
    3. one `vivec` area merging the eight districts' sources by reference number, and one `vivec` town
       row with `vivec-chim.chim`, the districts' doors and arrivals and `dbg tp` names by district; the
       eight district rows and their legacy maps stay selectable;
    4. 1,677 chunks, within the engine's 4,096.
  - Memory is the same either way: the ring is centred on the player, so the Temple district's peak is
    there in both plans (the per-district figures above).

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
5. Names: `vivec_arena-chim.chim` (stage A) and, in stage B, the Vivec frame map's name for the
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
- Where it is set: the area's own config (`cut_models_over`, `cut_mode`, `cut_keep_whole`), which the
  builder records per area in the receipt (`area_cut`); `chim_build --cut-models-over` sets one value for
  every area and wins. The Vivec Arena sets 512 (M3 stage A); Balmora and Seyda Neen set nothing and keep
  every model whole.
- Flora stays whole (`cut_keep_whole`, default the `f/flora_` meshes; project decision 10 October 2026): around
  Vivec 24 wide trees and 31 parasols are wider than 512 units, and tiling them is not measured yet.

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
area the world holds: `maps/<town>-chim.chim`, where `<town>` is the town's map
name in `config/towns.json` (`tools/chim/frame_map.py`). When CHIM is on, the
engine loads this map instead of the town's region maps. `chim_towns 0` in the
engine loads the region maps instead, for A/B comparisons. The region maps,
door links, sky, fog and the `dbg tp` names keep the town name. The legacy
region maps stay as they are and remain selectable. A legacy build writes no
frame map.

### Frame maps are .chim files

A frame map is a BSP29 file, but it is not a playable map without its CHIM world:
it holds an empty world, the map's entities, collision-only boxes and the
`"_chim_frame"` key; all its geometry is in `id1/chim/`. So it uses the `.chim`
extension: `maps/<town>-chim.chim`, `maps/intro_docks-chim.chim`, and for a CHIM
region frame `maps/vfNNNN.chim` in place of `maps/vfNNNN.bsp`
([CHIM_REGIONS.md](CHIM_REGIONS.md)). The bytes are the same BSP29 file; Quake's
model loader picks the loader from the file header, not the extension.

- The engine finds every map through one resolver (`aw_mappath.c`, `AW_MapPath`):
  `maps/<name>.chim` when the image has a CHIM world (`chim/world.cwi`) and that
  file exists, else `maps/<name>.bsp`. Map names, saves, the region directory,
  door links and the HUD keep using the name without an extension.
- A frame map that cannot run is refused with a console message instead of
  loading as an empty map: a map with `"_chim_frame"` in an image without a CHIM
  world, a `.chim` file without the key, or a frame whose CHIM world cannot be
  read or has no pack for it.
- The builder's tools tell a frame map by its `"_chim_frame"` key and, for
  region frames, the build's ownership table (`aw-chim-ownership-1`), never by
  its file name (`tools/map_files.py`).
- `tools/build.py --chim-frame-ext bsp` writes frame maps as `.bsp` files, as
  builds before v0.0.36 did; the engine reads both. `tools/chim/frame_ext_migrate.py`
  renames frame maps of earlier builds in a workspace to `.chim` (a hard link
  under the new name: nothing is copied or rebuilt; dry run by default).

- Worldspawn: the town's worldspawn, identical in every region map, plus the
  key `"_chim_frame" "CX CY"`: two decimal integers, the cell of the frame's
  `FRAM` row in `world.cwi` (Balmora: `"-3 -2"`).
- World: empty, with no faces. One node splits the frame into two empty
  leaves, the standing hull is empty everywhere, and there is no visibility
  data, so every leaf sees every other. The bounds cover the frame:
  frame-local x and y from the frame record, z from 256 units below the
  lowest chunk to the frame's terrain ceiling (2048, raised over high ground
  as for the chunks). The player start is traced down from that top, never
  from inside the ground. Ground and objects come from the chunks.
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

## Shared ocean chunk

Most of the map has no LAND record: the sea around the island and between its
parts. OpenMW gives such a cell a flat heightfield at -2048 units
(`ESM::Land::DEFAULT_HEIGHT`) and creates it with water at the sea level; the
legacy region maps sample the same depth (-512 local units) under a water
brush at 0. Every such cell is the same, so the CHIM builder makes it once:
one chunk of water over a flat seabed (`tools/chim/ocean.py`), made by the
same chunk terrain code as every other chunk (ground plane, water plane and
leaves, the standing hull of the chunk and its ring of tiles), but in
chunk-local coordinates, its low corner at 0, 0. Being flat it tiles the
plane: chunk (i, j) of an ocean cell is this chunk moved by i and j chunk
widths.

The chunk is its own file, kind `OCEN`. No index lists it and no frame names
it, so a format 0.5 world reader never meets one; given one, the 0.5 readers
refuse it (unknown kind). Layout, big-endian as every CHIM structure:

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | 32 bytes | common header, kind `OCEN`, major 0, minor 5; count = 1 + textures |
| 32 | f32 | water level, local units (0) |
| 36 | f32 | seabed, local units (-512) |
| 40 | f32 | seabed, Morrowind units (-2048) |
| 44 | f32 | local units per Morrowind unit (0.25) |
| 48 | u16, u16 | chunk grain (256) and terrain step (128), local units |
| 52 | u16, u16 | textures, reserved |
| 56 | u32, u32 | the chunk record's render and collision bytes |
| 64 | u32, u32 | CRC-32 of the chunk record; CRC-32 of the texture records (in file order, unpadded) |
| 72 | 16-byte rows | record directory, as in a sector file: `CHNK` 0, then `TEXR` 0..n-1 |
| then | records | 4-byte aligned: one chunk record (no placements, no PVS row: Quake's "no visibility data", everything visible), then the miptexes |

The terrain image's lump 2 holds the file's own texture ids (0..n-1): the
seabed's default land texture (`g0`) and `*water`, moved off the sky bank as
every CHIM texture. The file is stored once (a content-keyed unit; with the
storage pool, one pooled object) and every ocean cell is a reference to it
(`aw-chim-ocean-ref-1`: the cell, its centre, the chunk's SHA-256 and size,
the tiling: 8 x 8 chunks from local -1024, -1024). Measured on the base
master (10 October 2026): 10,528 bytes, 4 ground faces, 8 water faces, 146
clipnodes, standing-hull chains at most 8 deep; 867 cells reference it.

The engine does not read `OCEN` files yet: the open-world frames
([OPEN_WORLD_FRAMES.md](OPEN_WORLD_FRAMES.md)) will place it for the sea
cells. Until then the far terrain layer draws the sea as flat water at the
water level where a frame's margin has no LAND (`tools/chim/far.py`).

`chim.ocean.validate_ocean` checks a chunk file: it reads back (CRCs, record
tiling), the brush and world-tree rules every chunk passes, solid under the
seabed, water up to the water level and air above it, the standing hull
solid just under and empty just over the seabed at the chunk's edges and
beyond them (seamless when copies lie side by side), and seabed and water
faces (up and down) each covering the chunk once.

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
- **One pool for the step.** `chim_build.py --pool stage` (the default since
  v0.0.42) keeps one worker pool from the world conversion to the last gate
  (`build_parallel.stage_pool`): every map of the step (units, validation,
  heap gate, zone walk, stair walk) runs on the same warm workers, and the
  pool starts again only when a map needs more workers, a worker died or the
  environment changed (each restart is printed with its reason; the step
  ends with one line: workers, starts, maps, tasks). The validation's
  whole-world cross-checks (owners, reach copies, drawn boxes, PVS and
  placement rows) and the variant audit run as frame and mesh units on that
  pool, the heap gate scans the slices of its big frames and its small
  frames in one map, largest first, and the gates after the validation use
  the world it read instead of reading every file again. Each of these
  prints one progress line per frame (`[done/total frames] CHIM validation:
  <frame>: N failures`, likewise the heap gate, the zone walk and the world
  frames). `--pool batch` is the method before v0.0.42 (a pool per map, the
  cross-checks on one core); the reports are byte for byte the same
  (`tests/test_chim_check_pool.py`, `tests/test_stage_pool.py`).
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
Seyda Neen's frame maps are checked against the Seyda Neen region maps the
builder converts from your data (without the terrain visual cull: these maps
never ship, `--seyda-terrain-cull off`). From v0.0.35 the recorded v0.0.31 Seyda Neen
maps (`--seyda-recorded DIR`) are optional and NOT RECOMMENDED since v0.0.31 (legacy: the shipped
image holds only `seyda-chim.chim` and its far layer for Seyda Neen); given, they are the reference
instead (v0.0.33 stopped a CHIM build with Seyda Neen without them).

See [Which Seyda Neen is in my build?](../LINUX_BUILD.md#which-seyda-neen-is-in-my-build) for which Seyda Neen an image holds.

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
