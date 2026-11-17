# Emulator warp mode, measured

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

These numbers measure FS-UAE's warp mode itself, to decide whether it can run the automated test sessions (the
gameplay journeys of [GAME_RECORDER.md](../GAME_RECORDER.md)) faster. They are not a measurement of the game's speed,
and warp is never used for one ([FS-UAE-DEVELOPMENT.md](../FS-UAE-DEVELOPMENT.md#engine-boot-and-map-load-smoke)).
Register: [EMU-WARP-STARVES-GAME-CPU-67](../bugs/EMU-WARP-STARVES-GAME-CPU-67.md).

## What was run

- **Image:** the v0.0.66 release build (commit ad5e9a0a), its own engine.
- **Emulator:** FS-UAE 3.1.66, an A1200 with a 68040 and its FPU, JIT, the processor at its fastest setting, 32 MB of
  Fast RAM, the disks on the IDE port.
- **Session:** the opening journey, `tests/sessions/journey_opening.txt` (nine steps in two parts), the same script in
  every run, on 17 November 2026, one run at a time.
- **Clocks:** the game's state file read every 5 seconds through the session: the engine's clock (`realtime`, the
  emulated machine's timer), its frame time (`frame_ms`: at most 100 ms are counted for one frame, and the engine
  runs at most 72 frames a second, 13.9 ms), and the in-game clock, each against the host's seconds.
- **Runs:**
  1. without warp;
  2. with `warp_mode = 1`;
  3. with `warp_mode = 1`, a warp limit of 100 emulated frames a second (twice a PAL machine's pace) and the
     deterministic option (against the test console folder's stall that ended run 2);
  4. without warp, with the deterministic option (run 3's baseline).

## Results

| Run | Journey | Engine clock per host second | First load (Seyda Neen) | Frame time |
| --- | --- | --- | --- | --- |
| 1. no warp | PASS 42/42 checks; part A 1,012 s, part B 148 s | 1.00 (956.5 s in 956.6 s) | in play 8 s after the command; the load frame 5.6 s, 5.3 s of it file work | median 16.9 ms in play (13.9 to 38.6 ms by place) |
| 2. warp | stopped at the first load | 31 at the start (467.6 s in the first 15 s) | never finished: the test console folder's stall | 100 ms (the cap); the menu's frames 5.6 to 6.6 s of engine clock each |
| 3. warp, limit 100, deterministic | stopped at the first load | 1.8 at the menu | the load frame 151.0 s of engine clock, 135.8 s of it file work (the same 470 file calls and 282 KB of reads as run 1), about 75 host s; stopped by the session's in-play limit | 13.9 ms at the menu (the 72-a-second cap), 100 ms during the load |
| 4. no warp, deterministic | PASS 42/42 checks; part A 947 s, part B 154 s | 0.95 (849.8 s in 891.1 s) | in play 9 s after the command | median 21.6 ms in play (13.9 to 30.2 ms by place) |

In run 1 the in-game clock moved 0.42 game minutes per host second in play (321 game minutes in 760 host seconds), in
run 4 0.38. The last minutes of run 4 had a test suite running beside them, so its host load was not the same as run
1's.
The start to the main menu took 17 s in runs 1 and 4, 15 s in run 2 and 46 s in run 3.

## What it means

- **Warp only shortens the time the emulated machine is idle.** Where the game works (a load, a busy frame), warp takes
  host time away from the 68040: without a limit nearly all of it, with a limit of twice the machine's pace enough to
  make the start nearly three times and the first load more than ten times slower in host time (the load's work took
  151 s of the engine's clock instead of 5.6 s).
- **The session's own waits are host seconds.** Part A of the opening journey holds 83 fixed waits, about 545 of its
  1,012 seconds; warp cannot shorten them.
- **Plain warp brings the test console folder's stall at once.** Without warp it comes about once in 100 loads
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); with warp it came at the first load,
  since the emulator then runs thousands of frames a second and each one touches the interrupt word that the folder's
  host thread also writes.
- So warp is not used to speed up the test sessions.

## Why warp behaves so

In FS-UAE 3.1.66, `custom.cpp` lines 1399-1407: with warp on, the time base of one emulated frame is 1 without a limit,
and the host's time divided by the limit with one. The processor at its fastest setting runs only within that time
base per emulated frame, and the emulator's own work for each frame (the chip set, the display) is paid for every
frame, so the more frames a second warp runs, the less of each second is left for the 68040. `fsuae-events.c` lines
399-404 apply `warp_mode = 1` on the first frame. The engine itself counts at most 100 ms for one frame, so frames longer
than that do not move the game's logic any faster either.

## What speeds a test session up instead

In the order of their measured share of the opening journey's time:

1. **Waits by condition.** A step waits until the game says it is done (the map is loaded, the journal stage is
   reached), with a limit, instead of a fixed number of host seconds.
2. **Fewer walks where the walk is not what is tested.** Teleports and the console's quest state reach a quest's next
   step directly; walks stay where a follower or the route itself is checked.
3. **Sessions side by side**, within what the machine and the emulator slots allow.
