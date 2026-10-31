# ENGINE-SYNC-IO-MAIN-LOOP-36: Disk reads and writes on the main loop wait without a bound: one lost reply stops the game

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 10 October 2026, in v0.0.36-dev |
| Where | engine: CHIM streaming, sound and voice loads, model reloads, autosave, lamps |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.36-dev (last seen) |
| Severity | high: Any DOS request whose reply never comes freezes the game, as the music read did |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source c8bf614, engine c8bf614, CHIM world c8bf614 |
| CHIM engine version | CHIM 0.1.0, engine c8bf614, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 10 October 2026

Open. Found by the sweep that followed [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): the music stream no longer waits
for its reads, but other parts of the game still read or write files from the main loop and wait for each request
to come back. None of them has been seen to hang; each would hang the same way if a request were lost.

## Symptom

None observed yet. Expected symptom: the game stops on one frame while the audio hardware repeats its last buffer,
as in HANG-IDLE-DUSK-35, whenever a file system request made by one of the sites below never gets its reply.

## Where

The engine's file layer is the C library's stdio (`sys_file_amiga.c`), so every `fopen`, `fread`, `fseek`, `fwrite`
and `remove` is a dos.library call that waits for the file system's reply with no time limit. Sites that run during
play (not only behind a loading screen or on an explicit command), riskiest first:

| Site | What | When |
| --- | --- | --- |
| `chim/chim_world.c` `Chim_PackRead` via `ChimChunks_Tick`, `chim_models.c`, `chim_statics.c` | CHIM chunk catalogues, terrain, models and statics | every frame while the player moves (about 32 KiB per frame, more for urgent chunks) |
| `snd_mem.c` `S_LoadSound` (also from inside the mixer, `snd_mix.c`) | sound effects | first use and after the sound cache entry was evicted |
| `aw_anim.c` voice barks, `aw_speech.c` lip files | NPC combat and idle lines, lip timing | combat events, idle barks, every NPC voice line |
| `model.c` `Mod_Extradata` from `r_alias.c`, `aw_npc_lod.c` | alias models evicted from the cache, NPC level-of-detail models | while rendering, when a model has to be reloaded |
| `aw_save.c` `AW_SaveWrite` | autosave (reads of the save slots, the write, a read-back, deletes) | every 5 minutes and after each scene arrival |
| `aw_lamps.c`, `aw_world.c` `AW_RegionNameAt` | night lamp table, region names | crossing a cell at night; region names with the compass or debug HUD |
| `aw_movie.c` | video frames and movie audio (the audio inside the mixer) | movie mode only (opening) |
| `aw_remote.c`, `console.c` debug log, `aw_log.c` live logs, `aw_testbox.c` | remote console, logs, test harness | only when switched on (off by default); the remote console writes to a host folder twice a second |

Rare and small (acceptable for now): door sounds, combat actor lookups, torch and hand models, intro lines and
the quick character's voices, once-per-map tables on the first frame after a load. Loading screens, startup,
menus, manual save and load, and console commands are acceptable: the player is not playing while they read.

## How it happened

Quake reads files synchronously; on the PC a file read is quick and does not get lost. On the Amiga each read is a
message to the file system task and back, and the soak run of HANG-IDLE-DUSK-35 showed that a reply can be lost
(cause still open). Every synchronous call then waits forever.

## Why it was not caught

No test makes a file system request go unanswered; the soak run that found the music case was the first.

## Reproduction

Not reproduced for these sites. The HANG-IDLE-DUSK-35 soak harness (a debugger stop followed by heavy host-file
traffic) is the candidate trigger.

## Repair

To do, by site class, reusing the asynchronous reader of the music stream (`aw_aread.c`: ACTION_READ packets sent
with `SendPkt()` and collected with `GetMsg()`, never waited for):

1. CHIM streaming: its per-frame budgeted reads become asynchronous requests (the chunk is used when its data has
   arrived; the frame never waits).
2. Sound and voice loads during play: load through the same reader and play the sound once it has arrived, or
   preload voice lines with the scene.
3. Autosave: write in the background or slice it over frames with a bound per frame.
4. Model reloads during rendering: keep the cache from evicting models in view, or load them asynchronously.

## Verification

To do: a fault-injection test per site (the request never answered: the game loop goes on), and the soak run.

## Prevention

A source check that lists file calls reachable from the main loop, so a new synchronous read in play is noticed.

## Post-pin RC2 package observation, 14 October 2026

Exact RC2 package native inspection repeats zone-full chunks 100/107 retries after water and land return. Scoped gameplay and successful AmigaDOS exit do not clear blocking streaming, heavy loading, memory/performance or all-cell traversal issues.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-CROSSING-SYNC-LOAD-43](CHIM-CROSSING-SYNC-LOAD-43.md): Every open-world cell crossing re-reads the world index and every earlier frame header in the main loop, then primes the ring with hundreds of small reads: 0.3-1.1 s pauses
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- ROOM-HLAALO-FATAL-EXIT-57 (no report page): Loading Hlaalo Manor from the console (map bmhlaalo, aw_quick_start map bmhlaalo) ends the game with a fatal exit and no message, after its actors spawn
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
