# ROOM-LOAD-LONG-FRAME-63: a room load takes one frame of many seconds

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.66-dev10 at 2026-11-16 09:47 +0200: Seen again (the endgame session ENDGAME-HEART-SESSION-66, run1 on the v0.0.66-dev10 image): loading Akulakhan's Chamber took one frame of 41,930 ms (disk 40,917 ms; 86 files, the store chunks chimi/p00 to p07 among them), FS-UAE 32 MB Fast; the host load is not in the session's logs.
- Reported with v0.0.66-dev10 at 2026-11-16 10:34 +0200: the endgame session ENDGAME-HEART-SESSION-66, run2 on the v0.0.66-dev10 image: Akulakhan's Chamber again in one frame of 41,212 ms (disk 39,001 ms), and Dagoth Ur, Facility Cavern after it in one frame of 19,284 ms (disk 18,637 ms).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 10 November 2026, in v0.0.63 |
| Where | the Andrano tomb room load, FS-UAE at 32 MB Fast |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.63, v0.0.66-dev10 (last seen) |
| Severity | low: one slow load under host load; the load finished |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.63 |
| From commit | source and engine e1fd058 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-10: reported in v0.0.63
- 2026-11-16 09:47 +0200: seen again in v0.0.66-dev10: Seen again (the endgame session ENDGAME-HEART-SESSION-66, run1 on the v0.0.66-dev10 image): loading Akulakhan's Chamber took one frame of 41,930 ms (disk 40,917 ms; 86 files, the store chunks chimi/p00 to p07 among them), FS-UAE 32 MB ...
- 2026-11-16 10:34 +0200: seen again in v0.0.66-dev10: the endgame session ENDGAME-HEART-SESSION-66, run2 on the v0.0.66-dev10 image: Akulakhan's Chamber again in one frame of 41,212 ms (disk 39,001 ms), and Dagoth Ur, Facility Cavern after it in one frame of 19,284 ms (disk 18,637 ms).

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev10 (16 November 2026)._

## Status: 16 November 2026

Open. First seen on the Andrano tomb room (19.3 s in one frame, a gate running beside the test session). Seen again
in the endgame session on the v0.0.66-dev10 image, in FS-UAE at 32 MB Fast:

| Room | Frame | Of it, disk |
| --- | --- | --- |
| Akulakhan's Chamber (first run) | 41,930 ms | 40,917 ms |
| Akulakhan's Chamber (second run) | 41,212 ms | 39,001 ms |
| Dagoth Ur, Facility Cavern (second run) | 19,284 ms | 18,637 ms |

## Symptom

The loading screen holds one frame for the whole room load, most of it spent waiting on the disk.

## Where

Room loads of CHIM rooms. In Akulakhan's Chamber the frame read 86 to 90 files, the store chunks among them.

## How it happened

Not known yet. The time is almost all disk: the files read in that frame are to be listed with their sizes and
seeks, and timed on the Pi.

## Reproduction

`dbg tp heartchamber` from Seyda Neen at 32 MB Fast; the console's long-frame line names the frame.

## Repair

None yet.

## Verification

Not verified yet.

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
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68](STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68.md): A script's StartCombat reads the fighter's sheet from disk before it knows that a fight slot is free
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
