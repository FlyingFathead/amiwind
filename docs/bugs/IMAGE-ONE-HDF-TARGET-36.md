# IMAGE-ONE-HDF-TARGET-36: The game ships on two drive images and three world partitions; the project target is the whole game on one HDF

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.32-dev1 at 2026-10-08 (time not recorded): WORLD-THIRD-PARTITION-32: the world image needs more partitions
- Reported with v0.0.36-dev3 at 2026-10-11 00:43 +0300: two disks and three world partitions; the target is one HDF

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | Image layout of v0.0.36-dev3: two files, disk 1 DH0 + DW0, disk 2 DW1 + DW2 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.45 |
| Severity | medium: all four Amiga limits hold, but the target of one image is not met; the player handles two disks and three world partitions |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3b5e7a9, engine 3b5e7a9, CHIM world 3b5e7a9 |
| CHIM engine version | CHIM 0.1.0, engine 3b5e7a9, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 11 October 2026

Open. PERSISTING, NOT RESOLVED. Found by the maintainer while reading the v0.0.36-dev3 build.

## Symptom

The v0.0.36-dev3 game ships as two image files (4,026,564,608 bytes and 1,610,645,504 bytes). Disk 1 holds the system partition DH0 (cylinders 1-61440) and DW0 (61441-122880); disk 2 holds DW1 (1-40960) and DW2 (40961-49152). That is three world partitions, the same layout as v0.0.35-dev1, whose second disk was 1,879,080,960 bytes. All partitions are under 2 GiB and start below 2 GiB, so the Amiga limits hold, but the project target, the whole game on one HDF, is not met.

## Where

The image layout of v0.0.36-dev3 and the layout step of the builder.

## How it happened

The world data (legacy region maps, audio, video, interiors) is larger than one image of about 3.75 GiB, so the layout packs it into more partitions and a second disk.

## Why it was not caught

The disk-layout gate checks the Amiga limits, not the one-image target, and the image summary does not show which kind of data takes the space.

## Reproduction

Read the layout lines of the dev3 image summary or list the image files.

## Persisting since

Persisting since the third and fourth world partitions of v0.0.32 ([WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md), v0.0.32-dev1, 8 October 2026, open). The project target has been one HDF since the streamer decision of 8 October 2026. Earlier attempts and why they did not hold:

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md) (closed): the four platform limits are gated. That keeps the image legal but does not stop it from growing, see BUILD-PARTITION-GROWTH-UNGATED-36.
- Smaller payload work (excluding video, unreferenced voices) helped test builds only; the full image kept its two disks.

## Repair

Planned. The legacy maps of CHIM cells do not help here: they are removed before packing, so removing them saves build time, not image size. The gap of about 1.5 GiB has to come from elsewhere, and the partition audit measures where. Steps: (1) a per-build payload breakdown by kind (world maps, audio voices, effects and music, video, interiors) printed by the image summary, so it is clear what must shrink to fit one image of about 3.75 GiB; (2) store-once CHIM for the open world; (3) a gate on image size and partition count (BUILD-PARTITION-GROWTH-UNGATED-36).

## Verification

To do: an image summary with the breakdown table, then a build whose total fits one image and one or two partitions under the limits.

## Prevention

The image summary prints the size budget table for every build and a gate reports the distance to the one-image target.

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
- [IMAGE-MEDIA-CATALOGUE-ON-DISK-46](IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md): A 64 MB build report (the media catalogue) shipped on the Amiga boot disk; nothing in the game reads it
- [ROOM-RESIDENT-MODELS-SIZE-48](ROOM-RESIDENT-MODELS-SIZE-48.md): The batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
