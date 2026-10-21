# IMAGE-ACTOR-SKIN-REPEATS-46: every actor's skin is stored twice (standing and mover model)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46 |
| Where | id1/progs/a_*.mdl (animation kit standing and mover models, tools/npc_anim.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | low: 64.8 MB of repeated skins; disk only, memory unchanged |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | 2026_10_20_v0.0.46_release_a3fb9b74 |
| From commit | source a3fb9b7, engine a3fb9b7, CHIM world a3fb9b7 |
| CHIM engine version | CHIM 0.2.1, engine a3fb9b7, world format 0.7 |
| Platform or emulator | not in game (builder: payload files of the release run) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

## Symptom

The 865 baked actor models of the v0.0.46 image hold 421 distinct skins in 865 copies: 64.8 MB of the skin
bytes are repeats. Most of it (62.7 MB) is an actor's standing model `a_<id>.mdl` and its mover model
`a_<id>_m.mdl`, which carry the same skin.

## Where

`id1/progs/a_*.mdl` (the animation kit's standing and mover models, `tools/npc_anim.py`).

## How it happened

Quake's alias model format keeps its skin pixels inside the model file. The mover model (more animation
frames, loaded while an actor moves) was written as a whole second model, skin included.

## Why it was not caught

The models were sized against the engine's per-model budget, never compared with each other.

## Reproduction

Any full build: SHA-256 of each `progs/a_*.mdl` skin (bytes 88 to 88 + width x height).

## Repair

`build.py --shared-skins on` (off by default until a playtest image shows the actors right): a skin two or
more actor models repeat is stored once in `progs/skins/<16 hex>.awk`; the models carry a reference in its place
(skin type `AWSK`). The engine's two alias loaders read the pixels from that file into the same place, so the
decoded model is byte-identical and memory does not grow ([PAYLOAD_SHARING.md](../PAYLOAD_SHARING.md)).

## Verification

Host tests (`tests/test_payload_share.py`, `tests/aga_shared_skin_test.c`): the stored form rebuilds the model
byte for byte; the stream loader (both passes) and the file loader decode it to the same cache bytes as the
model with its skin inline; a missing, short or misnamed skin file is refused. Read-only run over the v0.0.46
payload: all 865 actor models decode identically (796 on the stream loader, 69 on the file loader). Dry run:
414 skin files for 858 models, 64,814,328 bytes saved. Not yet played in an image (builds are on hold).

## Prevention

The modular NPC work (actor parts stored once) removes the repeated animation frames as well; until then
`tools/payload_share.py measure` reports the skin repeats of any staged payload.

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
- [IMAGE-DUPLICATE-FILES-46](IMAGE-DUPLICATE-FILES-46.md): 26 MB of byte-identical files on the boot disk (actor models, voice lines, sprites under two names)
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
