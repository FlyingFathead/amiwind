# PERF-READAHEAD-29: Outdoor cell/sub-cell crossing pauses and lost read-ahead

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | unknown, in v0.0.29-dev4 |
| Where | Outdoor cell/sub-cell crossing, read-ahead buffer |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.29-dev4 (last seen) |
| Severity | medium: Crossing pauses and the prefetched buffer is lost; a performance fault. |
| Family | Loading and disk reads (`disk-loading`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-06: PERF-READAHEAD-29: cell crossing pauses and premature prefetch cancellation (part 1 of 4): 6 October follow-on evidence: one unmeasured sn054-to-sn048 trace filled 131,072 bytes for the matching destination, then recorded high-hunk move ...
- 2026-10-06: PERF-READAHEAD-29: cell crossing pauses and premature prefetch cancellation (part 2 of 4): Read-ahead finding: with128KiB/1.5-second lookahead, method2 filled its prefix on all four crossings, but only one later load reused any bytes ...
- 2026-10-06: PERF-READAHEAD-29: cell crossing pauses and premature prefetch cancellation (part 3 of 4): Next attribution: allocator fixtures demonstrate that hunk pressure can move a resident prefix or evict it before copy.
- 2026-10-06: PERF-READAHEAD-29: cell crossing pauses and premature prefetch cancellation (part 4 of 4): Resolution path: extend the matched native route on patched source versus unchanged baseline, with direction and boundary cases, and compare prefix ...
- 2026-10-18 18:26 +0300: seen again in v0.0.43-dev2: maintainer: crossing between heavy CHIM cells gives a noticeable hiccup; the first presentation of the next frame map loads in the main loop (prefetch work in progress)

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [AREA-DATA-CHUNKS-59](AREA-DATA-CHUNKS-59.md): Requested: all game data in area chunks loaded with the area, not island-wide files read during play
- [AREA-TABLES-SLOW-READ-ON-LOAD-68](AREA-TABLES-SLOW-READ-ON-LOAD-68.md): Loading a Solstheim frame spent about two and a half seconds reading eight kilobytes of area tables
- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-CROSSING-SYNC-LOAD-43](CHIM-CROSSING-SYNC-LOAD-43.md): Every open-world cell crossing re-reads the world index and every earlier frame header in the main loop, then primes the ring with hundreds of small reads: 0.3-1.1 s pauses
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [COMBAT-SETTINGS-REREAD-63](COMBAT-SETTINGS-REREAD-63.md): A combat settings file that lacks some keys is read again on every actor spawn
- DIALOGUE-HEADER-OVERREAD-58 (no report page): Dialogue table header check read past a buffer shorter than the header
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md): Disk reads and writes on the main loop wait without a bound: one lost reply stops the game
- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [HEART-CHAMBER-LOAD-HANG-62](HEART-CHAMBER-LOAD-HANG-62.md): The game stops on the Loading screen when teleporting to the heart chamber, with the music still playing
- [IMAGE-LOADS-SLOWER-66](IMAGE-LOADS-SLOWER-66.md): Area loads on the v0.0.66-dev2 image take 1.3 to 2.2 times as long as on v0.0.66-dev1 with the same file work (Vivec 13.6 s against 29.9 s)
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- [MWSCRIPT-RESULT-LONG-FRAME-62](MWSCRIPT-RESULT-LONG-FRAME-62.md): Running a dialogue result script holds one frame for 4.6 to 8.4 seconds while the script file is read
- [PI-BENCH-DISK-WORST-FRAME-63](PI-BENCH-DISK-WORST-FRAME-63.md): The worst disk frame of the standard Balmora bench on the Pi rose from 48 ms to 73 ms
- [ROOM-FIRST-LOAD-SLOW-67](ROOM-FIRST-LOAD-SLOW-67.md): The first load of a large room takes about ten seconds on the loading screen
- [ROOM-HLAALO-FATAL-EXIT-57](ROOM-HLAALO-FATAL-EXIT-57.md): Loading Hlaalo Manor from the console (map bmhlaalo, aw_quick_start map bmhlaalo) ends the game with a fatal exit and no message, after its actors spawn
- [ROOM-LOAD-LONG-FRAME-63](ROOM-LOAD-LONG-FRAME-63.md): A room load took one 19-second frame in a test session while a gate ran beside it
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68](STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68.md): A script's StartCombat reads the fighter's sheet from disk before it knows that a fight slot is free
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
