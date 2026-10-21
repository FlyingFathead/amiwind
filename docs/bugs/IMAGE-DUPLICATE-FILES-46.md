# IMAGE-DUPLICATE-FILES-46: 26 MB of byte-identical files on the boot disk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46 |
| Where | image boot payload id1/: progs/a_*.mdl, sound/npc and sound/pool, progs/*.spr, gallery |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | low: 25,925,758 bytes of repeats; disk only, no effect in game |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | 2026_10_20_v0.0.46_release_a3fb9b74 |
| From commit | source a3fb9b7, engine a3fb9b7, CHIM world a3fb9b7 |
| CHIM engine version | CHIM 0.2.1, engine a3fb9b7, world format 0.7 |
| Platform or emulator | not in game (builder: payload files of the release run) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

## Symptom

The boot partition of the v0.0.46 image holds 581 groups of byte-identical files: 25,925,758 bytes in 3,952
extra copies (SHA-256 of every file of the staged payload).

## Where

The boot payload (`id1/`): actor models (`progs/a_*.mdl`, 11.8 MB in 30 copies), voice lines under two names
(`sound/npc/` and `sound/pool/`, 8.0 MB), the soundtrack (two identical tracks, 2.5 MB), NPC gallery models (1.5
MB in 2,971 small copies), sprites, animation layouts and item tags.

## How it happened

Each stage names its outputs by what they are for (an actor's model by the actor, a voice line by its record),
not by their content, and Amiga FFS has no links: two names are two full copies.

## Why it was not caught

The hashed pool shares identical outputs on the build volume, so the repeats cost nothing there; only the
image's file system stores them twice. No check compared the payload's files by content.

## Reproduction

Any full build: SHA-256 of every file under `image/boot`.

## Repair

`build.py --file-aliases on` (off by default until an image is played with it): the image step's last payload
pass stores each identical file once and lists the other names in `id1/file-aliases.txt`; the engine's file
search opens the stored copy for a name it does not find ([PAYLOAD_SHARING.md](../PAYLOAD_SHARING.md)). Kinds
the engine opens through its file search, 4 KB or more. Not covered: the soundtrack (the music player opens
tracks by path, 2.5 MB) and the small gallery copies (1.5 MB; each alias costs game memory).

## Verification

Host tests (`tests/test_payload_share.py`): every name still reads its bytes; the engine's table reader reads
the builder's table, case-insensitively, and ignores a damaged or unsorted one. Dry run on the v0.0.46 payload:
550 files fewer, 21,057,445 bytes saved (table 20,788 bytes, about 26 KB of game memory). Not yet played in an
image (builds are on hold).

## Prevention

`tools/payload_share.py measure` reports the repeats of any staged payload in seconds.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43](BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43.md): The first build with every exterior on CHIM stops in the image preflight: with no classic world maps left, the disk layout check refuses with a message that names no file or limit
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [IMAGE-ACTOR-SKIN-REPEATS-46](IMAGE-ACTOR-SKIN-REPEATS-46.md): Every actor skin is stored twice (standing and mover model): 65 MB of repeated skin pixels
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
