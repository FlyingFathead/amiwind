# BUILD-LAYOUT-GATE-AFTER-WRITE-33: The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | image step partition and drive writers; the asset-free dry-run image |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Every over-limit layout was still refused, but only after its partitions and drives were written (up to 4 GiB each); the dry-run image was not measured at all. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine c4e14ab |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open, repair ready on branch `v0.0.33-layout-selftest`.

## Symptom

None in a build so far: every layout over an Amiga limit was refused. The cost was in when and where:
the disk-layout gate of
[BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md) measured each drive only after it
was written and read back, so a layout over a limit was refused after up to 4 GiB of partition and
drive images had been written. The asset-free `--dry-run` boot-notice image was not measured at all.

## Where

`tools/world_volumes.py` (world partition writer, drive grouping), the drive loop of the image step in
`tools/build_aga.py`, and `tools/build_dry_run.py`.

## How it happened

The gate was added to the drive loop after `rdbtool` and the readback, the only place where the
written partition table could be read. Nothing measured the layout before that, although every size
and offset is known in advance: a partition's size follows from its payload (`partition_mib`), and
`rdbtool` places partitions back to back after one 32 KiB cylinder. One gap went further than cost:
the world map batcher admits a single map up to its 1.5 GiB partition budget, so a map between 1 GiB
(the file limit) and 1.5 GiB was copied into a partition before the gate refused it. The dry-run image
is written by its own short script, which the change did not touch.

## Why it was not caught

The gate's unit tests call `require_disk_layout` with hand-made receipts; no test sent an over-limit
payload through the packing code, and no test covered the dry-run receipt.

## Reproduction

Before the repair: a world map of 1.2 GiB passes `partition_batches` and is written into a partition
by `xdftool`; the build stops only at the gate after the drive is assembled and read back.

## Repair

- The gate runs on the plan first. `write_partitions` gates every planned world partition (size and
  files) before the first `xdftool` call; the image step plans every drive (`plan_drives`: the boot
  partition, `hardfile_groups`, offsets as `rdbtool` writes them) and gates that plan before the boot
  partition or any drive is written. The drive loop moved into `assemble_drives`, which still gates
  every drive as written and stops when a written partition differs in size from its plan. Partition
  sizes come from one function (`partition_mib`) for the plan and both writers.
- The dry-run image is read back with `verify_combined` after `rdbtool`, gated with
  `require_mountable` and `require_disk_layout`, and `dry-run-build.json` records `disk_layout`.
- `tools/build.py --layout-selftest` (`tools/layout_selftest.py`) sends sparse dummy payloads through
  the same functions and expects refusals for a 2.5 GB file, a 2048 MiB partition, a partition
  starting past 2 GiB and a drive over 4 GiB, a pass for a layout just under every limit, and a tiny
  payload written end to end. The dummies are always removed (also on failure and Ctrl-C).

## Verification

`tests/test_layout_selftest.py`: every case refused with its message, the largest legal layout passes
with the expected offsets, a refused plan never reaches a writer, the packer's own grouping keeps the
forced layouts legal, the writer refuses a 1.2 GiB map before writing, nothing is left behind when a
case raises (including KeyboardInterrupt), the run takes seconds and the dummies occupy almost no disk,
the end-to-end case writes and gates a real drive, and the dry-run image is read back, gated and
refused over a (lowered) limit. The full gate runs the suite.

## Prevention

The self-test is part of the test suite, so the gate is proven end to end in every gate run and in CI.
A new image writer gets its layout from `plan_drives` and `assemble_drives` instead of its own loop.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
