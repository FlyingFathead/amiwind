# EMU-WARP-STARVES-GAME-CPU-67: In the emulator's warp mode the game gets far less processor time per second of its own clock, so its frames take seconds of game time

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 17 November 2026, in v0.0.66 |
| Where | FS-UAE 3.1.66 warp mode (custom.cpp 1399-1407, fsuae-events.c 399-404) with the JIT preset at the fastest processor setting |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.66 (last seen) |
| Severity | low: a test method that would have slowed and stalled the scripted sessions; the game itself is not affected and warp is not used for any measurement |
| Family | Emulator measurement method (`benchmark-method`) |
| Playtest version | 2026_11_17_v0.0.66_full-v0.0.66-release-try2_ad5e9a0 |
| From commit | source and engine ad5e9a0 |
| CHIM engine version | none: legacy engine |
| Build note | the v0.0.66 release image, two scripted sessions of the opening journey: without warp and with warp_mode = 1 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 32 MB Fast, warp_mode 1 |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-17: reported in v0.0.66
- 2026-11-17: v0.0.66: The warp limit measured (the same image and journey): warp_mode = 1 with uae_warp_limit = 100 and the deterministic option.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

## Status: 17 November 2026

Open, low: a finding about the test method, not about the game. Measured on the v0.0.66 release image with the
standard opening journey, FS-UAE 3.1.66 with the JIT 68040 preset at 32 MB of Fast RAM: without warp, with
`warp_mode = 1`, and with `warp_mode = 1` limited to twice a PAL machine's pace. Without warp the game's clock follows
the real one (956.5 s of the engine's clock in 956.6 s) and the journey passed. With warp the emulated machine's clock
races ahead while the game gets only a small part of the processor per second of that clock, so its frames take
seconds of game time each, and the first map load stopped on the test console folder's lost completion
([CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)). With the limit the menu ran at 1.8 times the
real pace, but the start and the first load were several times slower in host time (see Repair). Warp is therefore
not used to speed up the test sessions; every performance check runs without it in any case (decided for the project,
17 November 2026; [FS-UAE-DEVELOPMENT.md](../FS-UAE-DEVELOPMENT.md#engine-boot-and-map-load-smoke)). All numbers:
[performance/EMULATOR-WARP.md](../performance/EMULATOR-WARP.md).

## Symptom

With warp on, the start to the main menu took 15 s against 17 to 18 s without it. In those 15 s the engine's clock ran
467.6 s. The frame time the engine reports showed 100 ms, the most it counts for one frame. The console's long-frame
lines at the menu gave frames of 5.6 to 6.6 s of the engine's clock: about 0.9 s of it in the screen conversion and 2.2
to 3.2 s in file work on the test console's folder. Without warp the menu's frames take 13.9 ms and Seyda Neen's 18 to
26 ms.

## Where

The emulator, not the game. FS-UAE 3.1.66, `custom.cpp` lines 1399-1407: with warp on and no warp limit, the time base
of one emulated frame is set to 1, so the "fastest possible" processor setting runs the 68040 only within that tiny
budget per frame, and the emulator spends its time on the emulated frames themselves instead. `fsuae-events.c` lines
399-404: `warp_mode = 1` is applied on the first frame (unless net play is on).

## How it happened

The game's clock is the emulated machine's own (the vertical blank and the timer device are emulated), so warp makes
that clock run as fast as the host can emulate frames. The game's work per frame is the same, but each emulated frame
now gives the processor almost no time, so one frame of the game spans many emulated frames: seconds of game time. The
engine caps a frame's time at 100 ms, so the game's logic moves on no faster than at its normal frame rate, while the
test console's file calls (served by an emulator thread in host time) count as seconds of game time each.

## Why it was not caught

The test notes of October 2026 recommended warp for booting and reaching a scene fast without a measurement of what it
gives. The first measurement (this one) was made before warp was used for any session.

## Reproduction

Any scripted session with `warp_mode = 1` on the JIT preset with the processor at its fastest setting: read the engine's
clock (`realtime`) and frame time (`frame_ms`) from the test console's state file and the console's long-frame lines.

## Repair

None in the game. A warp limit was measured next (the same day, same image and journey): `warp_mode = 1` with
`uae_warp_limit = 100` (twice a PAL machine's pace) and the emulator's deterministic option against the folder stall.
The menu ran at 1.8 times the real pace with its normal frames, but the start took 46 s (17 s without warp) and the
first load's frame took 151.0 s of the engine's clock, 135.8 s of it file work, against 5.6 s and 5.3 s without warp
for the same 470 file calls: about 75 host seconds against about 6, so the session stopped at its in-play limit. Warp
with or without a limit is therefore not used to speed up the test sessions; what does is in
[performance/EMULATOR-WARP.md](../performance/EMULATOR-WARP.md).

## Verification

The numbers above, from the sessions of the opening journey on the v0.0.66 release image (17 November 2026), kept with
their settings in [performance/EMULATOR-WARP.md](../performance/EMULATOR-WARP.md).

## Prevention

Every emulator speed setting is measured (the session's own clock samples: engine clock and frame time against host
time) before it is used or recommended, and warp is off for every performance check, enforced by the session tools.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-NO-STANDARD-DEMO-48](BENCH-NO-STANDARD-DEMO-48.md): Testers on real hardware have no standard benchmark: no shipped timedemo, and the hardware page did not say how to show the frame rate
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions
- [EMU-JIT-FAULT-ADDRESS-36](EMU-JIT-FAULT-ADDRESS-36.md): FS-UAE JIT reports fault addresses during the Vivec stage A boot smoke
- [PERF-SAMPLER-EXITED-NO-OUTPUT-69](PERF-SAMPLER-EXITED-NO-OUTPUT-69.md): The performance sampler stopped by itself with an error code and no message
- [TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67](TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67.md): The in-game check's still of Ghostgate shows a slope of rock: the test stood at the place label's point and looked away from the fortress

Related bugs in other categories:

- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)

<!-- END GENERATED CATEGORY -->
