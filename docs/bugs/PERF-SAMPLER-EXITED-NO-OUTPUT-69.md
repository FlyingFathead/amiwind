# PERF-SAMPLER-EXITED-NO-OUTPUT-69: The performance sampler stopped by itself with an error code and no message

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 25 November 2026, in v0.0.69-dev4 |
| Where | the build machine's measuring tools (the performance sampler) |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.69-dev4 (last seen) |
| Severity | low: a gap in the performance measurements until it is started again |
| Family | Emulator measurement method (`benchmark-method`) |
| Playtest version | unknown |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | a measuring service of the build machine, no build involved |
| Platform or emulator | not in game (the measuring tools, not the game) |

<!-- END GENERATED FACTS -->

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
- [EMU-WARP-STARVES-GAME-CPU-67](EMU-WARP-STARVES-GAME-CPU-67.md): In the emulator's warp mode the game gets far less processor time per second of its own clock, so its frames take seconds of game time
- [TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67](TEST-GHOSTGATE-ARRIVAL-FACES-ROCK-67.md): The in-game check's still of Ghostgate shows a slope of rock: the test stood at the place label's point and looked away from the fortress

<!-- END GENERATED CATEGORY -->
