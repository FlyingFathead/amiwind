# HANG-IDLE-DUSK-35: The game freezes with the music looping after the player is left idle outdoors

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | engine/aga/src/aw_music.c refill(): synchronous music read in the main loop |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.35 (last seen) |
| Severity | high: The session is lost (emulator restart); it has happened several times on FS-UAE |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3cbe85a, engine 3cbe85a, CHIM world 3cbe85a |
| CHIM engine version | CHIM 0.1.0, engine 3cbe85a, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Related freezes](#related-freezes)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Open; cause found, game side repaired in source. The freeze is a disk read of the music stream that never
completes while the game's main loop waits for it. The same mechanism was already captured in v0.0.30 as
[SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md) and left open; this report holds the analysis for both. The music stream
now reads asynchronously, so a lost read silences the music instead of stopping the game (Repair); the soak run on an
image with this engine and the layer that loses the reply are still to do. The other disk reads during play that can
still wait are listed in [ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md).

## Symptom

With the player left idle for a few minutes on the legacy open-world terrain outside any settlement, the picture
stops, keys and the console have no effect, and the music keeps looping its last fraction of a second. The session
has to be ended. The maintainer saw it several times on FS-UAE playing v0.0.35, the last time around sundown.

## Where

`engine/aga/src/aw_music.c`: `refill()` reads the next block of the soundtrack stream with a synchronous `fread()`.
It is called from `CDAudio_Update()` in the main loop (`Host_Frame`), and when the current buffer runs dry a second
loop (`while (!valid[active] && refill())`) waits for the read before the frame continues. Any read that does not
come back stops the whole game.

What the frozen machine shows (soak run, 10 October 2026; v0.0.35 release image, headless FS-UAE 3.1.66, JIT, one
legacy outdoor pose; the same in all six captured freezes):

- the CPU is in the exec idle loop (STOP, interrupts enabled): no tight loop, no crash; every task is waiting;
- the game's process waits only for its DOS reply signal, inside a 1 KiB `Read()` from the boot partition into a
  buffer of 8-bit PCM: the music refill;
- the boot partition's file system handler is idle with an empty message port, and the game's reply port is empty:
  the request was taken and its reply never came;
- with the main loop stopped nothing refills the audio, so the sound hardware keeps replaying its last buffer: the
  looping music.

The same call chain (exec `Wait` <- dos `Read` <- `read` <- `fread` <- `refill` <- `CDAudio_Update` <- `Host_Frame`
<- `main`) was captured in v0.0.30 during Seyda Neen region loads ([SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md)).

## How it happened

Two parts:

1. **Game side (found):** the music stream is read synchronously inside the main loop. A slow read was expected to
   cost only a short stall; a read that never returns was not considered.
2. **Below the game (open):** why the reply is lost. In the soak harness the freeze needs a stop in the emulator's
   debugger followed by heavy host-file traffic from the remote console (it rewrites its state file twice per
   emulated second, about 35 times faster under warp); without either, no freeze. In v0.0.30 it appeared during
   region loads (map reads and music reads at the same moment). The layer that drops the reply (file system
   handler, hard file device or the emulator's host disk thread) is not identified, and the maintainer's own trigger (an
   emulator pause such as the FS-UAE menu, a host stall) is not shown.

Earlier leads the soak run did **not** confirm as the trigger: dusk and the night lamps switching on (they switch on
at about 16:10 game time; real-speed runs across dusk did not freeze), long play time, and the audio position drift
([AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md), a separate open issue).

## Why it was not caught

- The same blocking read was captured and diagnosed in v0.0.30 ([SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md)), but its
  repair was left as "next steps" and the bug stayed open through five releases. When the freeze came back with a
  different trigger (idle outdoors instead of a region load) it was registered as a new, unexplained bug.
- No soak test left the game idle for minutes across a day/night change, and none repeated the "emulator pause, then
  disk traffic" pattern.
- No test asks the main loop what happens if one disk read never returns.

## Reproduction

Sometimes. Maintainer: stand idle on legacy terrain outside a settlement for several minutes, across sundown (FS-UAE).
Soak harness (same pose for every variant, A/B/C/D with replicas):

| Variant | Emulator speed | Debugger break | Remote console | Ran | Freeze |
| --- | --- | --- | --- | --- | --- |
| warp from 12:00 (four runs) | warp | once, before the soak | on | 4-7 min | yes, all four, at 12:25-12:42 game time |
| warp from 18:00 | warp | once, before the soak | on | 7 min | yes, at 18:42 game time |
| warp from 12:00 | warp | none | on | 21 min | no; then one debugger break: freeze 2 min later |
| warp from 12:00 | warp | once, before the soak | off | 25 min+ | no |
| real speed from 12:00, through dusk | normal, audio on | once, before the soak | on | 45 min | no |
| real speed from 16:40, through dusk | normal, audio on | once, before the soak | on | 25 min | no |

## Repair

Game side, 10 October 2026 (v0.0.36 line): the music stream reads through a new asynchronous reader
(`aw_aread.c`). Each read is an `ACTION_READ` packet sent with `SendPkt()` to the file's handler, with the reader's
own reply port, and collected with `GetMsg()` on a later frame: the standard Amiga packet-level pattern
(asyncio.library), the same idea as the opening demo's v0.0.5 refill scheduler ([AUDIO.md](../AUDIO.md)). Nothing on
the main loop or in the mixer waits for a reply any more:

- one 16 KiB block read is outstanding at a time, into the reader's own buffer, copied into the music queue when it
  arrives; the stream header is checked the same way;
- the mixer's fill loop, which used to read synchronously until the block was full, is bounded and only takes
  replies that are already there; with nothing ready the music is silent for that span;
- a read with no reply for 2 seconds (and at least 8 looks) is logged once in the music event log
  (`read-stalled`) and the console says once "music read stalled; the game goes on without music"; if the reply then
  arrives the stream continues where it stopped (`read-recovered`);
- after 6 seconds the stream is abandoned (`read-abandoned`) and the next track opens on a free reader; the
  abandoned reader keeps its request, buffer and port until the reply comes and only then closes its file (closing it
  earlier would itself wait on the file system); with all three readers waiting the music is off (`stall-off`) until
  the replies return (`stall-recovered`);
- at exit the reader waits at most one second for outstanding replies, then leaves them to the handler (its reply
  port ignores the arrival, its memory is never freed);
- the death track is looked up once at start, so dying no longer reads the music catalogue during play.

`aw_music_status` and `music-profile.txt` count stalls, recoveries, abandoned streams and silent spans.

Still open: which layer loses the reply (file system handler, hard file device, emulator host thread), and every
other synchronous file call on the main loop, registered as
[ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md).

## Verification

Host tests (the actual player source with a reader whose replies can be held back): with the reply late, about
3 seconds of buffered music play on, then silence, one stall line, and the stream resumes from the same position
when the reply arrives; with the reply never coming, about 20 seconds of game frames run without waiting, three
streams are abandoned, the music goes off, one console line in total, and the music returns when the replies come
back. The existing player checks (track order, tails, history, title, opening hold, loading-screen music) pass with
whole-block reads. The Amiga engine compiles without warnings.

To do: the soak run (variant A: warp, one debugger break, remote console) on an image with this engine passes
without the game stopping, and an hour of idle across dusk.

## Prevention

The soak run (idle across a day/night change) becomes part of the playtest checks. The music player's host tests
hold replies back (late and never) and fail if the game loop waits, if the stall is logged more than once, or if the
music does not come back. The other synchronous file calls on the main loop are listed in
[ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md).
- An open bug whose mechanism is known gets its repair scheduled and is reviewed at every release
  ([SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md) sat open from v0.0.30 to v0.0.35).

## Related freezes

Same mechanism, confirmed by a debugger capture:

- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): freeze during Seyda Neen region loads, the same music read that never
  returns (v0.0.30, about 5 in 70 automated runs).

Same symptom, suspected to be the same mechanism, not captured:

- [AW-20260928-02](AW-20260928-02.md): freeze with looping music at the dock and menu after leaving the ship.
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): freeze after a remote teleport with the remote console on
  (the same remote console traffic the soak run needs).

Freezes or stalls with a possible link, cause unknown:

- [AW-20260928-01](AW-20260928-01.md): the prison ship to deck change is sometimes very slow or freezes.
- [LOADER-STALL-32](LOADER-STALL-32.md): one stall while loading the Mages Guild.
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): an emulator session stopped with a hard file on host
  storage.

Other disk reads during play that can still wait the same way:
[ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md).

Not the cause, separate open issue: [AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-CROSSING-SYNC-LOAD-43](CHIM-CROSSING-SYNC-LOAD-43.md): Every open-world cell crossing re-reads the world index and every earlier frame header in the main loop, then primes the ring with hundreds of small reads: 0.3-1.1 s pauses
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [ENGINE-FOPEN-TEXT-MODE-35](ENGINE-FOPEN-TEXT-MODE-35.md): Binary files (paks, maps) were opened in text mode
- [ENGINE-PAK-HEADER-TRUST-35](ENGINE-PAK-HEADER-TRUST-35.md): The pak loader trusted the header: a negative or oversized directory length sized a read into a 128 KiB stack array, and entry offsets were never checked
- [ENGINE-SYNC-IO-MAIN-LOOP-36](ENGINE-SYNC-IO-MAIN-LOOP-36.md): Disk reads and writes on the main loop wait without a bound: one lost reply stops the game
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md): The mixer estimates the audio DMA position from the EClock, not from the hardware, so the two can drift apart over a long session
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship

<!-- END GENERATED CATEGORY -->
