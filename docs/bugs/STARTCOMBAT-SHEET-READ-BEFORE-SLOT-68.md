# STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68: A script's StartCombat reads the fighter's sheet from disk before it knows that a fight slot is free

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 22 November 2026, in v0.0.68-dev6 |
| Where | engine: the script host's StartCombat (`engine/aga/src/aw_mwhost.c`) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.68-dev6 (last seen) |
| Severity | low: one wasted file read for every StartCombat that is refused for no slot |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.68-dev6 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (read from the source, no session yet) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.68-dev7 (db15e97a) | 2026-11-22 | gate 12545 of the planning item STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68 | The fight slots are asked before the fighter's sheet is read from disk (aw_mwhost.c fight_start, 9667c3275; a source contract test). |
| shipped | the v0.0.68-dev8 build | v0.0.68-dev8 (db15e97a) | 2026-11-23 | the delivered build holds the commit (the planning item's shipped list) | the fix is in a numbered build; not yet confirmed by a play check |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-22: reported in v0.0.68-dev6
- 2026-11-22: fixed in source: a gated commit, v0.0.68-dev7 (db15e97a); gate 12545 of the planning item STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68: The fight slots are asked before the fighter's sheet is read from disk (aw_mwhost.c fight_start, 9667c3275; a source contract test).
- 2026-11-23: shipped: the v0.0.68-dev8 build, v0.0.68-dev8 (db15e97a); the delivered build holds the commit (the planning item's shipped list): the fix is in a numbered build; not yet confirmed by a play check

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
- [CONTAINER-WRITE-EINVAL-69](CONTAINER-WRITE-EINVAL-69.md): A generated docs page write fails once with an invalid-argument error from the container's view of the drive and succeeds on a second try
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
- [ROOM-FIRST-LOAD-SLOW-67](ROOM-FIRST-LOAD-SLOW-67.md): The first load of a large room takes about ten seconds on the loading screen
- [ROOM-HLAALO-FATAL-EXIT-57](ROOM-HLAALO-FATAL-EXIT-57.md): Loading Hlaalo Manor from the console (map bmhlaalo, aw_quick_start map bmhlaalo) ends the game with a fatal exit and no message, after its actors spawn
- [ROOM-LOAD-LONG-FRAME-63](ROOM-LOAD-LONG-FRAME-63.md): A room load took one 19-second frame in a test session while a gate ran beside it
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68](MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68.md): A script's StartCombat is refused once four fighters are in the fight, and an actor not loaded near the player starts no fight

<!-- END GENERATED CATEGORY -->
