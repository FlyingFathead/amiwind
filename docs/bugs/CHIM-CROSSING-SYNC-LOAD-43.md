# CHIM-CROSSING-SYNC-LOAD-43: Every open-world cell crossing re-reads the world index and every earlier frame header in the main loop, then primes the ring with hundreds of small reads: 0.3-1.1 s pauses

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | chim_world.c MapBegin/ReadIndex, chim_chunks.c ChimChunks_Begin and the ring prime, every map change |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | high: A pause of 0.3 to 1.1 s at every cell border outdoors (each exterior cell is its own frame map); the cost grows with the number of CHIM frames in the world |
| Family | Loading and disk reads (`disk-loading`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Reported by the maintainer on v0.0.43-dev2 (18 October 2026, 128 MB of Fast RAM): travelling through the open world
gives small load pauses ("yoinks") of about half a second, up to a second, where the game seems to stop while the
music plays on; the same route felt smoother in v0.0.42; towns such as Balmora feel fine
([CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md), reported twice).

## Where

Outdoors every exterior cell is its own CHIM frame map (1,295 of them in dev2, 1,115 in v0.0.42), so a cell border
is a map change. Each map change runs, inside one frame of the main loop:

1. `chim_world.c` `MapBegin`: `ReadIndex` reads and decodes the whole world index, `chim/world.cwi` (4.3 MB in dev2:
   33,000 file rows, 23,000 model rows), again for every map, although every map of the world reads the same file.
2. `chim_chunks.c` `ChimChunks_Begin`: the frame's first placement id is the sum of the placement counts of every
   earlier frame in the file table, so it opens every earlier frame's file and reads its header, up to about 1,300
   file opens per crossing, and finds each chunk's sector row with a linear search of the whole file table.
3. Two frames later, `ChimChunks_Prime`: the ring around the arrival is loaded before play, 50 to 55 chunks with
   their models and textures, in 300 to 580 separate small reads.

The music does not stop because the loader keeps the music fed between reads (`model.c` `AW_LoadAudioTick`): the
game loop itself is blocked.

## How it happened

The index and the frame walk were written for a world of a few town frames, where a map change was rare. The
regional CHIMport made every exterior cell a frame (v0.0.41-v0.0.43): a crossing every 15-20 s of walking, and the
index and the frame walk grow with the number of frames.

## Why it was not caught

The frame time was measured once a second (dbg rcount `pk`), which shows that a second had a long frame but not
what ran in it, and the map-load lines ("Scene ready: N ms") were not compared between releases on one route.

## Reproduction

FS-UAE, JIT, 128 MiB (or 16 MiB) Fast RAM: start the demo at Seyda Neen, noclip, heading 30 degrees, fly forward
180 s (12 cell crossings) with `chim spikes 100` (from this change): every crossing prints two spike lines, the map
start and the ring prime, with their parts.

Measured on 18 October 2026 (JIT, relative times, "Scene ready" per crossing; the private session tables keep the
lines):

| Build | RAM | Route: crossing median / max ms | seconds with a frame of 300 ms or more (of 178) |
| --- | --- | --- | --- |
| v0.0.42 release | 128 MiB | 357 / 489 | 3 |
| v0.0.43-dev2 | 128 MiB | 452-563 / 724-1,087 | 11-13 |
| v0.0.42 release | 16 MiB | 629 / 921 | 15 |
| v0.0.43-dev2 | 16 MiB | 573-654 / 807-2,051 | 12-19 |

Per crossing in dev2 (spike lines, 128 MiB): map start 280-750 ms, of it the index 92-184 ms and the rest of the
CHIM start 230-510 ms; ring prime 90-530 ms, 240-1,360 KiB in 290-580 reads. The heavier the arriving frame, the
longer its prime (frame 6,-5, 4 MB: 532 ms with 77 model loads; frame 3,-6, 0.3 MB: 112 ms). The legacy maps still
in the route cost 250-770 ms each (their map file 74-208 ms).

Why dev2 is worse than v0.0.42 on the same route: the engine is the same (no engine change between the two
commits); the world is larger (1,295 against 1,115 frames, index 4.3 against 4.0 MB), so the index decode and the
frame walk of every crossing take longer, and more of the route's cells are CHIM frames, whose map start costs more
than a light legacy map.

## Repair

v0.0.43 (branch v0.0.43-prefetch), with extra Fast RAM only (CHIM's cache banks, which survive map changes):

- **The world index stays in spare RAM** across maps and is checked against the file's size and head at each map
  start (`ReadIndex`): no read and no decode on a crossing.
- **Each frame's placement count is kept** the first time it is read, so the first placement id needs no file
  opens; the frame's sector rows come from one pass over the file table (`ChimChunks_Begin`). Same values.
- **Prefetch into spare RAM** (`chim/chim_prefetch.c`): the files of the cells the player is likely to enter are
  read ahead, 32 KiB in a frame where the ring read nothing, into the cache banks; a later read of the same bytes is
  copied from RAM (`Chim_PackRead`). Which cells: the current cell's quadrant names the nearest corner; the 2x2
  block meeting there is read first, the neighbour the heading's ray enters first leading (the largest first when
  the RAM is short for the block), then the current cell, then the rest of the 3x3 ring. The block moves only when
  the player is 1,024 units past the cell's midline. Read-ahead blocks are evicted before anything else when a real
  load needs memory (`chim_zone.c` `Victim`) and dropped on their own only for cells more than half a cell beyond the
  ring. At most 24 MiB and a quarter of the banks.
- **Frame spikes** (`chim spikes MS`, `aw_spike.c`): one console line for every frame of MS ms or more with what ran
  in it, and `chim spikes report`.

`chim prefetch 0` is the first method (every read from the disk, the index read with each map). Without banks
that survive a map change (the 16 MiB machine) nothing of this runs.

## Verification

18 October 2026, FS-UAE (68040 JIT, two sessions in parallel, busy host: compare within the table, not with other
days), the dev2 image as built (A) against the dev2 data with this engine, prefetch off (B) and on (C); the same
scripted runs: the open-world route (Seyda Neen, heading 30 degrees, 180 s), a square around the corner of cells 2,-7,
3,-7, 2,-6 and 3,-6 (four laps of 12 s), one heavy crossing (cell 10,0, 5.1 MB of frame files, into 11,0, 4.9 MB) and one
light crossing (0,-17 into 1,-17, 0.1 MB each). "Scene ready" per crossing, median / max ms:

| 128 MiB | Route | Seconds with a frame of 300 ms or more (of 178) | Corner | Heavy | Light |
| --- | --- | --- | --- | --- | --- |
| v0.0.42 release | 473 / 632 | 10 | 348 / 385 | 766 | 138 |
| A: dev2 as built (two runs) | 452-454 / 650-724 | 10-11 | 413-426 / 483-499 | 598-909 | 321-481 |
| B: this engine, prefetch off (24 MiB heap) | 445 / 630 | 8 | 366 / 465 | 676 | 387 |
| C: this engine, prefetch on (three runs) | 209-260 / 477-811 | 2-5 | 146-239 / 168-343 | 214-245 | 137-190 |

| 16 MiB | Route | Seconds with a frame of 300 ms or more | Corner |
| --- | --- | --- | --- |
| v0.0.42 release | 655 / 1,151 | 16 | 564 / 620 |
| A: dev2 as built | 654 / 2,051 | 19 | 610 / 836 |
| this engine (nothing to prefetch into, three runs) | 543-584 / 697-766 | 9-12 | 503-812 |

With the prefetch on, a crossing's map start no longer shows as a long frame (index 4-12 ms, the CHIM start 27-51 ms
instead of 230-510); the ring prime reads from RAM (290-440 reads served per crossing) and takes 60-140 ms on light
and middle cells, 210-480 ms where the arriving cell's models were never loaded (frame 6,-5: 77 model loads). Over one
session 17,000-18,000 reads came from RAM, 66 MB were read ahead in 1,850 slices (about 1 ms each in JIT, 25 ms at
worst), nothing read ahead was evicted for a real load, and circling the corner (16 crossings) read nothing again
from the disk for the four cells' files. The
legacy maps still in dev2's route are not helped (250-450 ms). At 16 MiB the engine runs the first method: no
read-ahead, the index read with every map, the same picture (a still at Seyda Neen is pixel-identical to dev2 as
built). The same poses with the prefetch off and on gave the same picture except one idle NPC's animation frame.

Slow preset (FS-UAE 68040 cycle-exact, standing in cell 2,-7 for 240 s at about 1.2 frames a second, 128 MiB): a
slice took 8 ms on average and 43 ms at worst; slices ran in a third of the frames until the nine cells around were
read (12.5 MB in 359 slices); the median frame was 824 ms with the prefetch on and 826 ms with it off. That run first
found a fault, fixed before this branch was gated: while the player had not moved since the map started the
prefetch planned again every frame and walked the whole file table, 66 ms a frame on the slow preset.

Long trip: five laps of Balmora, the Caldera area, Vivec and Seyda Neen (128 MiB, prefetch off and on): the Hunk use
at each spot was the same every lap and the engine's small zone kept the same free bytes (36,600; 36,800 with the
final engine) and blocks; 300 map
changes between two cells left both unchanged (its largest free run moves between 13 and 26 KB as Quake's allocator
walks the zone, without a trend): no memory accumulates.

Gate 2989 (all six parts, 4,753 tests). Unit tests: tests/test_chim_engine_native.py ChimPrefetchTests (16 MiB
baseline off, the plan and its order, byte-identical reads from RAM, hysteresis on a corner and along an edge,
read-ahead evicted first, the budget), tests/test_heap_size.py AutoHeapTests.

## Prevention

`chim spikes` names the work of every long frame, so a pause is tied to its mechanism in one run; the FS-UAE route
check (open world, town, a four-cell corner, one heavy and one light crossing) compares builds by crossing.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md): Disk reads and writes on the main loop wait without a bound: one lost reply stops the game
- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
