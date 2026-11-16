# IMAGE-LOADS-SLOWER-66: Area loads on the v0.0.66-dev2 image take 1.3 to 2.2 times as long as on v0.0.66-dev1 with the same file work (Vivec 13.6 s against 29.9 s)

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.66-dev5 at 2026-11-15 (time not recorded): The v0.0.66-dev5 build's image step relinked the hard disk name lookups busiest-first: 86 of 4,559 chains on the program partition (DH0), median lookup 73 -> 25 header blocks, longest 169 -> 140, files within 30 buffers 3,613 -> 16,306 of 29,385; the buffers are 150 on DH0 and 40 on the world partition (DW0). The area load times on the v0.0.66-dev5 image are not measured yet, so the entry stays open.
- Reported with v0.0.66-dev7 at 2026-11-15 (time not recorded): Measured on the v0.0.66-dev6 image, which has the disk layout of v0.0.66-dev5 (see the status): the sound stage of a map load is far below the v0.0.66-dev2 figures at Seyda Neen, Balmora and Vivec, and below the v0.0.66-dev1 figures except one of the two Balmora loads (147 ms against 139 ms). This replaces the v0.0.66-dev5 report's "not measured yet".
- Reported with v0.0.66-dev4 at 2026-11-15 09:40 +0200: the v0.0.66-dev4 image has the same layout: id1/sound is entry 28 of 28 of its chain on the boot partition, and 370 lookups of sounds outside the pool read 34 header blocks (median), none within the 30 buffers (measured on the image, no session)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 November 2026, in v0.0.66-dev2 |
| Where | the v0.0.66-dev2 boot partition: the order in which the image step creates the folders and files of id1 (sound is entry 28 of its hash chain), and the partition's 30 buffers |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev5 |
| Severity | medium: every sound the game loads reads its whole name lookup from disk: 0.3 to 0.8 s more per area load at 32 MB Fast, and a longer pause when a sound is first played |
| Family | Loading and disk reads (`disk-loading`) |
| Fix commit | `3dfd5095` |
| Fixed on | 2026-11-15 |
| Planning item | `IMAGE-LOAD-SOUND-CHAIN-66` |
| Playtest version | v0.0.66-dev2 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.66-dev4 (15 November 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 15 November 2026](#status-15-november-2026)
- [Symptom](#symptom)
- [The sessions side by side](#the-sessions-side-by-side)
- [Cause](#cause)
- [Where](#where)
- [What was checked](#what-was-checked)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 15 November 2026

Fixed in source (3dfd5095), not built yet: the image step only, no world stage and no engine change (Repair, below).
The verification is the sound loading of the next build's area loads.

In short: on the v0.0.66-dev2 boot partition no sound file lookup fits the file system's 30 buffers any more, so every
sound the game loads reads its whole lookup from disk. The sound loading of an area load takes 3.5 to 5.6 times as long
for the same sounds. Most of the gap in the total load times below came from the load beside the sessions, not from the
image. The v0.0.66-dev4 image has the same layout (measured on the image).

## Symptom

In the two delivery sessions, every area load of the v0.0.66-dev2 image took longer than the same load on the
v0.0.66-dev1 image. The time from the start of the load to the player's arrival ("Scene ready"), at 32 MB Fast:

| Load | v0.0.66-dev1 | v0.0.66-dev2 |
| --- | --- | --- |
| Balmora, the boot smoke's second and third load | 6.3 s, 6.2 s | 8.2 s, 7.8 s |
| Seyda Neen (smoke hops) | 7.1 s | 10.0 s |
| Vivec (smoke hops) | 13.6 s | 29.9 s |
| Khuul (smoke hops) | 5.2 s | 10.8 s |

The longest frame of the Vivec load does the same file work on both images: 639 and 641 file lookups (15 not found),
255 reads of 724 KB. On v0.0.66-dev2:

- the disk wait of that frame is 26.1 s against 12.2 s;
- the client's model and sound precache is 13.0 s against 4.2 s, of which the sound loading is 1.7 s against 0.16 s.

On every Balmora load of the boot smoke the sound loading takes 499 to 513 ms against 76 to 79 ms.

Through the smoke hops this made the next `dbg tp` arrive while the load before was still running
(DBG-TP-DURING-LOAD-66).

## The sessions side by side

The same scripted loads were then run on both images, and once with the v0.0.66-dev2 engine on the v0.0.66-dev1 image,
with each long frame naming its stages, their bytes and their call counts. The total load times followed the other work
running beside each session, both ways: the v0.0.66-dev1 image loaded Vivec in 32.0 s with a second emulator session
beside it, the v0.0.66-dev2 image in 18.5 s without one. The sound loading did not:

| Sound loading of the load | v0.0.66-dev1 | v0.0.66-dev2 | dev1 image, dev2 engine |
| --- | --- | --- | --- |
| Seyda Neen: 24 sounds, 244 KB | 139 ms | 480 ms | 90 ms |
| Balmora: 25 sounds, 297 KB | 139 ms | 777 ms | 99 ms |
| Vivec: 51 sounds, 641 KB | 306 ms | 1,078 ms | 156 ms |

The same sounds and bytes take 3.5 to 5.6 times as long on the v0.0.66-dev2 image, and the v0.0.66-dev2 engine is as
fast as ever on the v0.0.66-dev1 image: the cause is in the image's data, not in the engine. Model loading is not
slower. Almost all of each long frame is disk wait.

## Cause

The Fast File System finds a name by reading the header block of every entry ahead of it in one hash chain of the
directory, level by level. The boot partition keeps 30 buffers for those blocks. A lookup that reads 30 blocks or fewer
can be served from the buffers when it repeats; one that reads more misses on every block, because each walk throws out
the blocks the next walk starts with.

- The image writer adds each entry at the head of its chain. A folder made before the loose files of its parent ends at
  the tail of its chain.
- `id1` holds 1,966 entries on v0.0.66-dev2 against 1,781. The chain that holds `sound` has eight entries more, all
  ahead of it: `sound` is entry 28 of 28 there, where it was entry 20 of 20. `progs` moved from 20 to 21.
- The header blocks one lookup reads, counted over every file of the boot partition:

| Lookup | v0.0.66-dev1 | v0.0.66-dev2 |
| --- | --- | --- |
| a sound outside the pool (284 and 369 files): median, fit in 30 buffers | 25, all of them | 33, none |
| a pooled sound (7,092 and 7,086): median, fit | 72, 8.1 % | 80, none |
| a model or other file under `progs` (11,327 and 13,322): median, fit | 98, 5.7 % | 112, 4.3 % |

On v0.0.66-dev1 the sound lookups fit the buffers and repeated from memory. On v0.0.66-dev2 none fits, so each one reads
31 to 158 blocks from disk. Model lookups missed on both images, so they did not change.

## Where

The v0.0.66-dev2 boot partition: the order in which the image step creates the folders and files of `id1`, and the
partition's 30 buffers (BUILD-HDF-BUFFERS-32).

## What was checked

- The sound files: the 7,368 sound files both images hold are the same size, all 11,025 Hz 8-bit mono; v0.0.66-dev2
  adds 87.
- The directories: `id1/progs` 6,833 entries against 7,757 (+14 %), `id1/sound/pool` 7,092 against 7,086, `id1` 1,781
  against 1,966.
- The boot partition: 26,532 files in 1,755 MiB against 29,256 files in 2,015 MiB.
- The file alias table: 646 names against 682.
- The emulator settings of the sessions: identical.
- The sound files on the disk: none is split into more than one run of blocks on either image, and the pool lies at the
  same place of the partition (35 to 45 % into it).
- The partition settings: identical on both images (30 buffers, MaxTransfer 0xFFFFFF, mask 0x7FFFFFFE, the same file
  system type).

## Repair

Fixed in source (3dfd5095), in the image step only:

1. Once a partition is written, every directory hash chain on it is relinked busiest first: an entry with more files
   under it comes first (a file counts as one), and entries with as many keep the order they were written in. Only the
   chain links and their checksums change, no block moves, and the partition is read back after
   (`tools/ffs_chains.py`, called by the boot, world and CHIM partition writers). The rule names no folder.
2. Every partition gets the buffers its longest name lookup needs, in the partition table: that lookup plus 10, in
   steps of 10, at least 30 and at most 500 (BUILD-HDF-BUFFERS-32). The drive readback checks them, and `build.json`
   records them with the lookup figures of each partition.
3. `tests/test_ffs_chains.py`: on a small image the writer makes, a lookup of a file in the sound folder, which shares
   its chain with 40 loose files of `id1`, fits 30 buffers; the same check fails on the old order. The relink moves no
   block and changes no file.

Measured on the v0.0.66-dev4 boot partition through that code, without a build (header blocks per lookup, the root
block counted; median and longest):

| Lookup | As written | Busiest first |
| --- | --- | --- |
| A sound outside the pool (370 files) | 34, 42; none within 30 buffers | 6, 14; all within 30 |
| A pooled sound (7,086) | 81, 159 | 54, 132 |
| A model or other file under `progs` (13,322) | 113, 169 | 20, 140 |
| Every file (29,385) | 73, 169 | 25, 140 |

`id1/sound`, `id1/progs` and `id1/maps` now head their chains, where they were the last of 28, 21 and 29 entries. The
boot partition gets 150 buffers, so the repeated lookup of every file fits them; the CHIM world partition gets 40. On a
copy of the boot partition the relink rewrote 232 header blocks and nothing else, and every file read back the same.

For an A/B build, `AMIWIND_CHAIN_ORDER=as-written` and `AMIWIND_PARTITION_BUFFERS=30` in the image step's environment
keep the methods before. See [storage](../STORAGE.md#directory-hash-chains-and-disk-buffers).

## Verification

Pending: the sound loading of the same three loads of the next build against the v0.0.66-dev1 figures (139, 139 and
306 ms), the buffers in its build record, and the Fast RAM they take at 32 MB.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- AREA-DATA-CHUNKS-59 (no report page): Requested: all game data in area chunks loaded with the area, not island-wide files read during play
- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-CROSSING-SYNC-LOAD-43](CHIM-CROSSING-SYNC-LOAD-43.md): Every open-world cell crossing re-reads the world index and every earlier frame header in the main loop, then primes the ring with hundreds of small reads: 0.3-1.1 s pauses
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- COMBAT-SETTINGS-REREAD-63 (no report page): A combat settings file that lacks some keys is read again on every actor spawn
- DIALOGUE-HEADER-OVERREAD-58 (no report page): Dialogue table header check read past a buffer shorter than the header
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md): Disk reads and writes on the main loop wait without a bound: one lost reply stops the game
- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [HEART-CHAMBER-LOAD-HANG-62](HEART-CHAMBER-LOAD-HANG-62.md): The game stops on the Loading screen when teleporting to the heart chamber, with the music still playing
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- [MWSCRIPT-RESULT-LONG-FRAME-62](MWSCRIPT-RESULT-LONG-FRAME-62.md): Running a dialogue result script holds one frame for 4.6 to 8.4 seconds while the script file is read
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- PI-BENCH-DISK-WORST-FRAME-63 (no report page): The worst disk frame of the standard Balmora bench on the Pi rose from 48 ms to 73 ms
- ROOM-HLAALO-FATAL-EXIT-57 (no report page): Loading Hlaalo Manor from the console (map bmhlaalo, aw_quick_start map bmhlaalo) ends the game with a fatal exit and no message, after its actors spawn
- [ROOM-LOAD-LONG-FRAME-63](ROOM-LOAD-LONG-FRAME-63.md): A room load took one 19-second frame in a test session while a gate ran beside it
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [DBG-TP-DURING-LOAD-66](DBG-TP-DURING-LOAD-66.md): A dbg tp typed while a load is still running is lost: a town name does nothing, a place says no map holds the point, a room prints its name and stays
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk

<!-- END GENERATED CATEGORY -->
