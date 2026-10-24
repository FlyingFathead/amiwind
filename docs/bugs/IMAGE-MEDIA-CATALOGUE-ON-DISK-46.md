# IMAGE-MEDIA-CATALOGUE-ON-DISK-46: a 64 MB build report shipped on the Amiga disk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46 |
| Where | tools/prepare_media_assets.py stage_catalogue (image step): id1/media/catalogue.json |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: 64,068,821 bytes (4.4 % of the boot payload) of dead weight in every image |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | 2026_10_20_v0.0.46_release_a3fb9b74 |
| From commit | source a3fb9b7, engine a3fb9b7, CHIM world a3fb9b7 |
| CHIM engine version | CHIM 0.2.1, engine a3fb9b7, world format 0.7 |
| Platform or emulator | not in game (builder: payload files of the release run) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

## Symptom

The v0.0.46 image carries `id1/media/catalogue.json` on its boot partition: 64,068,821 bytes, 4.4 % of the
boot payload, which nothing in the game reads.

## Where

The image step's media staging (`tools/prepare_media_assets.py`, `stage_catalogue`), called by
`tools/build_aga.py`.

## How it happened

The media stage's coverage report (every source, its converted output, its lookups) was written into the
payload as a "lookup catalogue" when the complete media import was added, as a record of what the image holds.
The engine never got a reader for it: it finds sounds and videos by their own names and the video list
`id1/intro/videos.awl`. The report grew with every sound and voice line of the game.

## Why it was not caught

Nothing measured the payload by file until the size split of the v0.0.46 image (20 October 2026). The size
guard compares totals between builds, and the file was there from the start.

## Reproduction

Any full build up to v0.0.46: `image/boot/id1/media/catalogue.json`.

## Repair

Checked again before the change: no reader in `engine/` (C and QuakeC), the Toolkit or the release tooling; the
only reader is the harvest stage (`tools/prepare_harvest.py`), which reads the media stage's own copy at build
time. The image step now keeps the report beside the image only (`image/media-coverage.json`); the payload
preflight no longer counts it. `build.py --media-catalogue on` (debugging only) still writes it into the
payload. The release payload classes no longer list it.

## Verification

Unit tests (`tests/test_media_assets.py`, `tests/test_build_defaults.py`): the catalogue is not in the payload by
default, is with the option, and the image command has no `--media-catalogue` by default. Saving on the v0.0.46
payload: 64,068,821 bytes. Not yet checked in a built image (builds are on hold).

## Prevention

The size split of each release image lists its largest files by kind; a payload file no runtime reads is a
finding ([PAYLOAD_SHARING.md](../PAYLOAD_SHARING.md) for the other repeats found the same way).

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
- [IMAGE-BOOT-PAYLOAD-OVER-2GIB-48](IMAGE-BOOT-PAYLOAD-OVER-2GIB-48.md): The v0.0.48-dev2 image stopped in its payload preflight: the boot payload (2.75 GB with the batch room residents and the CHIM interior store) is over one partition and the layout could not split it
- [IMAGE-DUPLICATE-FILES-46](IMAGE-DUPLICATE-FILES-46.md): 26 MB of byte-identical files on the boot disk (actor models, voice lines, sprites under two names)
- [IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48](IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48.md): The image step stopped at its disk layout check: the layout plan left out the actor library it installs (+145 MB on a MiniWind boot partition)
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [ROOM-RESIDENT-MODELS-SIZE-48](ROOM-RESIDENT-MODELS-SIZE-48.md): The batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
