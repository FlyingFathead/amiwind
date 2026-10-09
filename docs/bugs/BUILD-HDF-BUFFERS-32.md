# BUILD-HDF-BUFFERS-32: Hard disk buffer and MaxTransfer defaults depend on the disk type

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | disk images written by the builder (partition buffers, MaxTransfer) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Players and benchmarks silently get different disk defaults depending on the disk type. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the CHIM world-format follow-up (FFS sweep, branch v0.0.33-chim-format).

## Symptom

The same file system gets different defaults depending on how the hard file is made: partitions in
an RDB disk written with rdbtool get 30 buffers and MaxTransfer 0xffffff; a plain partition hard
file mounted by FS-UAE gets 50 buffers and MaxTransfer 0x7fffffff. Benchmarks and players can
therefore run with different settings without knowing it.

## Where

Disk images written by the builder (`tools/build_aga.py`, rdbtool partitions); FS-UAE hard file
settings.

## How it happened

Neither the builder nor the benchmark profiles set the buffer count or MaxTransfer; each tool used
its own default.

## Why it was not caught

`awbench disk` started reporting buffers and MaxTransfer only with the CHIM benchmark work.

## Reproduction

`awbench disk` on an RDB world disk and on a plain partition hard file: compare `buffers=` and
`maxtransfer=`.

## Repair

Not yet: the builder sets buffers (and MaxTransfer) explicitly on every partition it writes and
records them in the build receipt. In the FFS sweep, 30, 50 and 100 buffers stayed within the drift
of the control run for seeks, so the value is a consistency question first.

## Verification

Pending.

## Prevention

A builder test that every partition carries the configured buffer count and MaxTransfer.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

Related bugs in other categories:

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers

<!-- END GENERATED CATEGORY -->
