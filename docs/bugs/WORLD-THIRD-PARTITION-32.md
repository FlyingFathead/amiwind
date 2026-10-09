# WORLD-THIRD-PARTITION-32: The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | World disk layout and launchers (fourth partition DW2) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | medium: Launchers and emulator setups were only used with three partitions; WinUAE untested. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found in the v0.0.32-dev1 image build.

## Symptom

With trees and grass the world payload needs a fourth partition, DW2, on the second world drive (v0.0.31 used DH0,
DW0, DW1). The launchers and emulator setups have only been used with the old layout.

## Where

`tools/world_volumes.py`; launcher and emulator configs.

## How it happened

Flora adds about 5,000 sprites and map size.

## Why it was not caught

First from-scratch build with flora.

## Reproduction

dev1 image build.

dev1 smoke test (8 October 2026): the launchers add the world disk with every partition and the
game runs in FS-UAE; WinUAE mounting of DW2 is untested. The static emulator templates list no
world disk at all ([EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md)), and the world
disk image is now slightly over 2 GiB ([WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md)).

## Repair

Not yet: smoke-test that DW2 mounts in FS-UAE and WinUAE with the shipped launchers; record the layout.

## Verification

Pending (dev1 smoke test).

## Prevention

The smoke test checks every partition is mounted.

## Outlook

The need for more than one world partition is an early-development scaling problem, and it is being
worked on. Today's world is stored as thousands of overlapping region maps, and every exterior object is
duplicated into each region that can see it, so the converted world outgrows one partition.

The world streamer (the CHIM engine, from v0.0.33) stores every model, texture and placement once and loads
the world in small chunks. On the first converted town it needs about an eighth of the disk space of the
region maps. The goal for the whole game is a single hard file, so additional partitions beyond one should
stop being an issue as the engine changes. Until then, the launchers and the partition check must handle
however many world partitions a build produces.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB

<!-- END GENERATED CATEGORY -->
