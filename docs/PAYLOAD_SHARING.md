# Storing repeated payload content once

_Last updated with AmiWind v0.0.63-dev2 (9 November 2026)._

The boot disk of a full image repeats some content byte for byte: the same sound under several names, the
same actor model under two names, the same skin in an actor's standing model and its mover model, the same
texture coordinates and triangles in every actor model built on one body, and the same 16 x 16 pixel squares in
many actor skins. Amiga FFS has no links, so a repeated file or block costs its full size every time. Four
builder methods store such content once. File aliases and shared skins are **on by default since v0.0.47**
(decided for the project, 2026-10-21; v0.0.47-dev2 was the first image built with them); shared shapes are **on
by default from v0.0.63**. `--file-aliases off`, `--shared-skins off` and `--shared-shapes off` store every copy
as before. Skin tiles are **experimental and off by default** (`--skin-tiles on`) until their load time is
measured on the Pi 4B ([EXPERIMENTAL_FLAGS.md](EXPERIMENTAL_FLAGS.md)).

## What is not done yet

- The v0.0.46 figures below are a dry run over that release payload; v0.0.47-dev2 was the first image built
  with file aliases and shared skins. The shared-shape figures are measured on the v0.0.62 release payload,
  read only; no image has been built with it yet.
- Load time is not measured. A shared skin or a shared shape is one more file opened when an actor model loads
  (the same bytes are read). An alias is one more failed file lookup on each search path before the stored copy
  is opened. The place-load time with shared shapes is to be measured on the Pi 4B and on FS-UAE at 32 MB Fast
  before the v0.0.63 release.
- Skin tiles change how an actor skin is read: about 78 short reads (at most 167) in up to 6 tile files in
  place of one read of the skin. On a desktop machine with the files cached, reading and rebuilding a tiled
  actor model takes about 0.19 ms against 0.02 ms for the whole model; on a file system where every call is
  slow (a shared folder) it took about 50 ms against 0.05 ms. Each read is a separate call on the Amiga too, so
  the method stays off until a build with `--skin-tiles on` shows the place-load time on the Pi 4B and on
  FS-UAE at 32 MB Fast within 5 % of the same build without it. Fewer reads per load (a place reading the shared
  tiles of all its actors once) is the next step if it is not.
- The soundtrack is not aliased: the music player opens its tracks by path, not through the file search, and
  two tracks of v0.0.46 are identical (2.5 MB).
- The NPC gallery's models repeat about 1.5 MB in small files (under 4 KB each); they are left as files, since
  each alias costs a few bytes of game memory.
- Since v0.0.62 every actor appearance has a skin of its own, so whole-skin sharing finds almost nothing to
  share now (17 skins, 2.9 MB on the v0.0.62 payload). It stays on: it costs nothing when nothing repeats.

## File aliases (`build.py --file-aliases on`)

The image step's last payload pass (`tools/payload_share.py`, after every check that reads the payload by name
or size) hashes the models, sounds, sprites, animation layouts and item tags of `id1/` (SHA-256 of the content,
files of 4 KB or more). Of each group of identical files the first name in the engine's order stays a file;
the others are removed and listed in `id1/file-aliases.txt`:

    AWALIAS1 <stored files> <aliases>
    <stored name>                  (one line each)
    <alias>TAB<stored index>       (one line each, sorted case-insensitively, a-z read as A-Z)

The engine reads the table once at start (`common.c`, `COM_InitFileAliases`). When its file search finds no
file of a name, it looks the name up there and opens the stored copy instead. A payload without the table
behaves exactly as before; a damaged or unsorted table is ignored as a whole. Game memory: the table text plus 8
bytes per alias and 4 per stored file (about 26 KB for the v0.0.46 payload).

## Shared actor skins (`build.py --shared-skins on`)

An actor model (`progs/a_*.mdl`, one skin, at most 512 KiB) whose skin pixels another actor model repeats keeps
its header and, in place of the pixels, the skin type `AWSK`, the first 16 hex digits of the pixels' SHA-256
and the pixel count. The pixels are stored once in `progs/skins/<16 hex>.awk`. Both alias loaders of the engine
(`model.c`, `model_alias_stream.inc`) read the pixels from that file into the place they had, so the decoded
model is byte-identical to the model with its skin inline and no more memory is held. A missing or damaged skin
file stops the load of that model with its name.

## Shared actor shapes (`build.py --shared-shapes on`)

Every actor built on the same body has the same texture coordinates (the ST block, 12 bytes per vertex) and the
same triangles (16 bytes per triangle); only its skin and its frames differ. An actor model (`progs/*.mdl`: the
residents, the creatures, the player bodies and the view models; one skin, at most 512 KiB) whose two blocks
another model repeats keeps, in their place right after its skin, `AWSH`, the first 16 hex digits of the blocks'
SHA-256, the ST byte count and the triangle byte count (28 bytes). The blocks are stored once, ST then
triangles, in `progs/shapes/<16 hex>.aws1`. The pass runs after the shared skins (a model can carry both
references) and before the file aliases. Both alias loaders read the blocks from that file into the place they
had before decoding (`AW_SharedShapeExpand`, `model_alias_stream.inc`), so the decoded model is byte-identical,
resident memory is unchanged and the size check of an extended model (`model-budgets.txt`) sees the whole
model's bytes. A missing or damaged shape file stops the load of that model with its name. Models named in an
NPC level-of-detail manifest (`progs/npc-lod.txt`) keep their blocks, since the engine checks those files'
sizes against it.

## Actor skin tiles (`build.py --skin-tiles on`, experimental)

Since v0.0.62 every actor appearance has a skin of its own, so whole skins no longer repeat; their parts do:
three of every four 16 x 16 pixel squares of the actor skins are found in another skin or elsewhere in the same
skin. An actor model (`progs/a_*.mdl`, `progs/n_*.mdl`; one inline skin whose width and height are multiples of
16; at most 512 KiB) keeps, in place of its pixels, the skin type `AWTL`, the first 16 hex digits of the tile
pool's SHA-256, the pixel count, the tile count and one 32-bit tile number per tile. Every distinct tile is
stored once, 16 rows of 16 bytes, in one pool split into chunk files of 65,536 tiles (16 MiB) each,
`progs/tiles/<16 hex>-<chunk>.awtp`: a tile number's high 16 bits name the chunk, the low 16 bits the tile in it.
Tiles used by two or more skins come first, the most used first; then each skin's own tiles, one skin after the
other, so a load reads them in few runs. The pass runs after the shared shapes (a model can carry both) and
before the file aliases. Models named in an NPC level-of-detail manifest keep their pixels.

The engine's file loader rebuilds the model before decoding (`model.c` `AW_TiledSkinExpand`): it sorts the
skin's tile numbers, reads them in runs of up to 64 tiles through a 16 KiB buffer, reading through holes of up
to 8 tiles rather than seeking, and copies each tile to its place. The decoded model is byte-identical and
resident memory is unchanged; while a model loads, its whole form (at most 512 KiB), a sort table (8 bytes per
tile, about 11 KB) and the 16 KiB buffer are held for a moment, the same staging the file loader uses for
small models. The stream loader leaves a tiled skin to the file loader. A missing or short tile file stops the
load of that model with its name.

## Measured on the v0.0.46 release payload

Same files, before and after, `payload_share.py measure` over the staged boot payload (`id1/`, 1,455,708,076
bytes):

| Method | Files | Bytes saved |
| --- | --- | ---: |
| Media catalogue left off the disk (the default now, [MEDIA_IMPORT.md](MEDIA_IMPORT.md)) | 1 file fewer | 64,068,821 |
| `--shared-skins on` | 414 skin files for 858 actor models | 64,814,328 |
| `--file-aliases on` | 550 files fewer, table 20,788 bytes | 21,057,445 |
| Both sharing methods together | | 81,612,533 |

Both together save less than the two added up: identical actor models are first made smaller by the skin pass.

## Measured on the v0.0.62 release payload

`payload_share.py identity` over the boot payload of the v0.0.62 release image, read only (2,709 models in
`progs/`):

| Method | Files | Bytes saved |
| --- | --- | ---: |
| `--shared-shapes on` | 219 shape files for 2,588 actor models | 78,381,384 |

## Measured on the v0.0.63-dev1 payload

`payload_share.py measure --skin-tiles` over the boot payload of the v0.0.63-dev1 image (shared shapes already
applied), read only; not in an image yet:

| Method | Files | Bytes saved |
| --- | --- | ---: |
| `--skin-tiles on` | 7 tile files (421,753 tiles, 108.0 MB) for 2,522 actor models | 318,790,160 |

The actor skins hold 1,693,728 tiles (433.6 MB). Pools cut per body shape and kept to 65,535 tiles (16-bit tile
numbers) saved only 159 MB, because most repeated tiles are shared across bodies; one pool with 32-bit numbers
(about 5.4 KB per skin) keeps all of the sharing. A load reads 78 runs on average (95th percentile 129, at most
167) and about 200 KB of tiles, in 4.1 chunk files on average (at most 6).

## Tests

`tests/test_payload_share.py`: the stored forms rebuild every original byte; the engine's alias reader reads
the builder's table (and ignores a damaged one); a shared-skin model and a shared-shape model (also one with a
shared skin as well) decode to the same cache bytes as the model with its blocks inline, on both loaders. The
same skin check decoded all 865 actor models of the v0.0.46 payload identically (796 through the stream loader,
69 through the file loader), read only. The shape check (`tests/aga_shared_shape_test.c`, the models listed in
`AMIWIND_SHAPE_MODELS`) decoded all 2,588 shared-shape actor models of the v0.0.62 payload byte-identically on
the engine's own loaders, and `payload_share.py identity` rebuilt every one of them byte for byte. The tile check
(`tests/aga_tiled_skin_test.c`, a tiled payload named in `AMIWIND_TILE_PAYLOAD`) rebuilt all 2,522 tiled actor
models of the v0.0.63-dev1 payload byte-identically with the engine's own reader, also with a shared shape
(either expansion first), and refuses a missing or short tile file and a bad pool name.
