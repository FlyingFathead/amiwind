# HEART-CHAMBER-LOAD-HANG-62: The game stops on the Loading screen when teleporting to the heart chamber

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 7 November 2026, in v0.0.61 |
| Where | Load of the heart chamber room (debug teleport to heartchamber) |
| Reproduction | always |
| Duplicate of | [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md) |
| Persists in | v0.0.61 (last seen) |
| Severity | critical: the load never finishes and the session is stranded: nothing recovers it and the room cannot be reached |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.61 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format unknown |
| Unknown because | a playtest report on the delivered release image; the commit of the running build was not read back |
| Platform or emulator | FS-UAE on Linux, the delivered v0.0.61 release image (playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

## Status: 7 November 2026

Open. Seen on the v0.0.61 release image in FS-UAE on Linux. No earlier entry was found under heart, load hang or Loading; related entries are CHIM-SEYDA-BALMORA-LOAD-HANG-43 and LOADER-STALL-32.

## Symptom

The debug teleport to the heart chamber stops on the Loading screen. The music keeps playing, so the machine is running, but the load does not finish. The console says the room record or models cannot be loaded. After that the session is stranded: the teleport command says no game is running, the scene command says a scene is still loading, and nothing recovers the session.

## Where

The load of the heart chamber room, one of the largest rooms of the game.

## How it happened

Not known yet. The places to look at are memory at the load, a missing or oversized room file, and a lost disk completion as in CHIM-SEYDA-BALMORA-LOAD-HANG-43.

## Why it was not caught

No check loads every place the debug teleport names.

## Reproduction

Run the debug teleport to the heart chamber on a full image at 32 MB Fast RAM.

## Repair

None yet. The load log and the remote console at the stall are to be read first.

## Verification

Not verified yet.

## Prevention

A load check of every place name of the debug teleport.

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

- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [LOAD-FATAL-ERRORS-67](LOAD-FATAL-ERRORS-67.md): Memory that runs out or a damaged map file while a place loads ends the game instead of going back where the player was

<!-- END GENERATED CATEGORY -->
