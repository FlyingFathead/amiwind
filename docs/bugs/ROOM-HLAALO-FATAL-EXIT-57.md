# ROOM-HLAALO-FATAL-EXIT-57: Loading Hlaalo Manor from the console (map bmhlaalo, aw_quick_start map bmhlaalo) ends the game with a fatal exit and no message, after its actors spawn

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 30 October 2026, in v0.0.57-dev1 |
| Where | Balmora MiniWind, room bmhlaalo (Balmora, Hlaalo Manor) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.57-dev1 (last seen) |
| Severity | medium: the room loads through its door on the v0.0.57 release image; only the console map load ended the game (dev1 MiniWind) |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | 2026_10_30_v0.0.57-dev1_miniwind-balmora-mwscript_27d1257 |
| From commit | source 27d1257, engine 27d1257, CHIM world 27d1257 |
| CHIM engine version | CHIM 0.2.2, engine 27d1257, world format unknown |
| Unknown because | the world format of this MiniWind was not read |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-30: reported in v0.0.57-dev1
- 2026-10-31: seen again in v0.0.57: The door path works on the v0.0.57 release image (7ff625e5, FS-UAE, 32 MB Fast): from Balmora through the upper door (reference 32822, locked: passed with dbg god on, then use) the room bmhlaalo loads (Scene ready: bmhlaalo, 812 ms ...

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [AREA-DATA-CHUNKS-59](AREA-DATA-CHUNKS-59.md): Requested: all game data in area chunks loaded with the area, not island-wide files read during play
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
- [PERF-READAHEAD-29](PERF-READAHEAD-29.md): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [PI-BENCH-DISK-WORST-FRAME-63](PI-BENCH-DISK-WORST-FRAME-63.md): The worst disk frame of the standard Balmora bench on the Pi rose from 48 ms to 73 ms
- [ROOM-LOAD-LONG-FRAME-63](ROOM-LOAD-LONG-FRAME-63.md): A room load took one 19-second frame in a test session while a gate ran beside it
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
