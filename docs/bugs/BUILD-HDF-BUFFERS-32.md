# BUILD-HDF-BUFFERS-32: Hard disk buffer and MaxTransfer defaults depend on the disk type

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.66-dev5 at 2026-11-15 (time not recorded): Seen in the v0.0.66-dev5 build's image step: the buffers are set by the longest name lookup, DH0 150 (longest lookup 140 header blocks, median 25) and DW0 40 (longest 30, median 7); all 29,385 and 37,006 files fit. The load times in play are not measured yet.
- Reported with v0.0.66-dev7 at 2026-11-15 (time not recorded): The load times in play are measured on the v0.0.66-dev6 image, which has the disk layout of v0.0.66-dev5: see IMAGE-LOADS-SLOWER-66. This replaces the v0.0.66-dev5 report's "not measured yet".
- Reported with v0.0.66-dev2 at 2026-11-15 03:25 +0200: the 30 default buffers of the boot partition were too few for its name lookups once id1/sound moved to the tail of its chain: every sound lookup read all its blocks from the disk again (IMAGE-LOADS-SLOWER-66)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | disk images written by the builder (partition buffers, MaxTransfer) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev5 |
| Severity | medium: Players and benchmarks silently get different disk defaults depending on the disk type. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Fix commit | `3dfd5095` |
| Fixed on | 2026-11-15 |
| Planning item | `IMAGE-LOAD-SOUND-CHAIN-66` |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.66-dev5 (3dfd5095) | 2026-11-15 | gate 10881 passed on 18eb63f1, which holds it | the image step sets every partition's buffers from its longest name lookup and reads them back |
| shipped | a numbered build | v0.0.66-dev5 build 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f | 2026-11-15 | the delivered build | the build holds 3dfd5095 |
| confirmed by a build | a numbered build | v0.0.66-dev5 build 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f | 2026-11-15 | the build log's image step | it set 150 buffers on the boot partition and 40 on the world partition from their longest name lookups (140 and 30 header blocks); a fix of the disk image the builder writes, no play check applies |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev
- 2026-10-08: CHIM world-format follow-up findings: FFS sweep, walk replay and per-placement visibility (branch v0.0.33-chim-format).
- 2026-11-15: seen again in v0.0.66-dev5: Seen in the v0.0.66-dev5 build's image step: the buffers are set by the longest name lookup, DH0 150 (longest lookup 140 header blocks, median 25) and DW0 40 (longest 30, median 7); all 29,385 and 37,006 files fit.
- 2026-11-15: seen again in v0.0.66-dev7: The load times in play are measured on the v0.0.66-dev6 image, which has the disk layout of v0.0.66-dev5: see IMAGE-LOADS-SLOWER-66.
- 2026-11-15: fixed in source: a gated commit, v0.0.66-dev5 (3dfd5095); gate 10881 passed on 18eb63f1, which holds it: the image step sets every partition's buffers from its longest name lookup and reads them back
- 2026-11-15: shipped: a numbered build, v0.0.66-dev5 build 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f; the delivered build: the build holds 3dfd5095
- 2026-11-15: confirmed by a build: a numbered build, v0.0.66-dev5 build 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f; the build log's image step: it set 150 buffers on the boot partition and 40 on the world partition from their longest name lookups (140 and 30 header blocks); a fix of the disk image the builder writes, no play check applies
- 2026-11-15 03:25 +0200: seen again in v0.0.66-dev2: the 30 default buffers of the boot partition were too few for its name lookups once id1/sound moved to the tail of its chain: every sound lookup read all its blocks from the disk again (IMAGE-LOADS-SLOWER-66)

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev4 (15 November 2026)._

## Status: 15 November 2026

Fixed in source (3dfd5095), not built yet. Seen again in v0.0.66-dev2: the boot partition's 30 default buffers were
too few for its name lookups once `id1/sound` had moved to the tail of its hash chain, so every sound lookup read all
its blocks from the disk again (IMAGE-LOADS-SLOWER-66). First found on 8 October 2026 by the CHIM world-format
follow-up (FFS sweep, branch v0.0.33-chim-format).

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

Fixed in source (3dfd5095): the image step sets the buffers of every partition it writes in the
partition table, sized to that partition's longest name lookup: the lookup plus 10, in steps of 10,
at least 30 (the value every partition had) and at most 500 (`tools/ffs_chains.py`). The drive is
read back with them and `build.json` records each partition's buffers with its lookup figures.
Measured on the v0.0.66-dev4 layout: the boot partition gets 150 (its longest lookup reads 140 header
blocks once its chains are relinked, IMAGE-LOADS-SLOWER-66), the CHIM world partition 40. A buffer
holds one 512-byte block, so the boot partition's take about 75 KiB of Fast RAM. MaxTransfer stays at
0xFFFFFF, the value every partition of the image already had; the plain partition hard file is not a
form the image ships in. `AMIWIND_PARTITION_BUFFERS=N` gives every partition N for an A/B build.

In the FFS sweep (8 October 2026), 30, 50 and 100 buffers stayed within the drift of the control run
for seeks; the sizing is for name lookups, which that sweep did not measure.

## Verification

Pending: the buffers in the next build's record and in `awbench disk` on its image, and the Fast RAM
they take at 32 MB.

## Prevention

The drive readback reads every partition's buffers back from the partition table, and the image step
stops when they differ from the planned value; `tests/test_ffs_chains.py` checks that they reach the
partition table.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
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
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- PI-IMAGE-WORK-FOLDER-65 (no report page): The Pi 4B drive image builder stops when its system half comes from the cache: the work folder is never made
- [ROOM-RESIDENT-MODELS-SIZE-48](ROOM-RESIDENT-MODELS-SIZE-48.md): The batch rooms' resident models take 1.66 GB in about 10,800 files, more than all the rooms themselves
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

Related bugs in other categories:

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [IMAGE-LOADS-SLOWER-66](IMAGE-LOADS-SLOWER-66.md): Area loads on the v0.0.66-dev2 image take 1.3 to 2.2 times as long as on v0.0.66-dev1 with the same file work (Vivec 13.6 s against 29.9 s)

<!-- END GENERATED CATEGORY -->
