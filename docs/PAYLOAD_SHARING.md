# Storing repeated payload content once

_Last updated with AmiWind v0.0.47-dev2 (21 October 2026)._

The boot disk of a full image repeats some content byte for byte: the same sound under several names, the
same actor model under two names, and the same skin in an actor's standing model and its mover model. Amiga
FFS has no links, so a repeated file costs its full size every time. Two builder methods store such content
once. Both are **on by default since v0.0.47** (decided for the project, 2026-10-21; v0.0.47-dev2 was the first
image built with them); `--file-aliases off` and `--shared-skins off` store every copy as before
([EXPERIMENTAL_FLAGS.md](EXPERIMENTAL_FLAGS.md)).

## What is not done yet

- The figures below are measured on the files of the v0.0.46 release payload with the new rules (a dry run, no
  image built); v0.0.47-dev2 is the first image built with both methods.
- Load time is not measured. A shared skin is one more file opened when an actor model loads (the same bytes
  are read). An alias is one more failed file lookup on each search path before the stored copy is opened.
- The soundtrack is not aliased: the music player opens its tracks by path, not through the file search, and
  two tracks of v0.0.46 are identical (2.5 MB).
- The NPC gallery's models repeat about 1.5 MB in small files (under 4 KB each); they are left as files, since
  each alias costs a few bytes of game memory.

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

## Tests

`tests/test_payload_share.py`: the stored forms rebuild every original byte; the engine's alias reader reads
the builder's table (and ignores a damaged one); a shared-skin model decodes to the same cache bytes as the
model with its skin inline, on both loaders. The same skin check decodes all 865 actor models of the v0.0.46
payload identically (796 through the stream loader, 69 through the file loader), read only.
