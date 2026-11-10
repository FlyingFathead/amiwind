# SESSION-STALL-AFTER-LONG-FRAME-62: the game stops with its clock frozen after a frame of several seconds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 7 November 2026, in v0.0.62-dev1 |
| Where | scripted FS-UAE sessions, Seyda Neen MiniWind, after a long console frame |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | fixed in v0.0.62-dev1 |
| Severity | medium: a frozen game in play, or a session that cannot finish its check |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | MiniWind v0.0.62-dev1 seyda-enabledraw2 7bb679e |
| From commit | source 7bb679e, engine 7bb679e, CHIM world 7bb679e |
| CHIM engine version | CHIM 0.2.2, engine 7bb679e, world format 0.11 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

## Status: 7 November 2026

Fixed in v0.0.62-dev1. Seen on 7 November 2026 in v0.0.62-dev1, Seyda Neen test images at 32 MB Fast RAM with JIT; 10 of 10 sessions with the long prints ran without a stop after the fix.

## Symptom

The game stops, its clock frozen, a few seconds after a frame that spent several seconds on console output or file reads: three of ten scripted Seyda Neen sessions.

## Where

Scripted emulator sessions of a Seyda Neen test image, after a long console frame.

## How it happened

The session tool reported "game stalled" (real time frozen, the program counter in the idle loop, no file call in progress) within a few seconds of a long frame: twice after an entity print while the camera had just been moved into the falling mage's trigger (frames of 3 to 7 seconds in the command buffer), once after a dialogue result script (a 6.8 second frame of dialogue and script file reads). The same steps without the long print ran through in seven other sessions.

## Why it was not caught

It was found with the v0.0.62 work that made the surrounding feature run; nothing exercised it before.

## Reproduction

See the symptom; the status line names the build it was seen in.

## Repair

The game did not hang: each stop was a long frame that the session judged too early. With the remote console on, every
console print was its own open, seek, write and close on the emulator's remote-console folder, and one entity listing
is about 300 prints, which took 1 to 1.2 seconds on a quiet machine and 3 to 7 seconds on a loaded one. The prints are
now collected and written twice a second (see also
[REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md)), and the session probe waits out long frames.

## Verification

10 of 10 scripted sessions with the long prints ran without a stop.

## Prevention

The MWScript tracker, the census pages and the in-game checklist of the release notes list this until it is repaired.

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
- ROOM-LOAD-LONG-FRAME-63 (no report page): A room load took one 19-second frame in a test session while a gate ran beside it
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE

<!-- END GENERATED CATEGORY -->
