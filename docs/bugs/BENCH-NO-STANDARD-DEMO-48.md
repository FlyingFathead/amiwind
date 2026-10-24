# BENCH-NO-STANDARD-DEMO-48: real Amigas have no standard benchmark

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 24 October 2026, in v0.0.48 |
| Where | docs/REAL_HARDWARE.md, docs/HARDWARE-BENCHMARK.md; the image ships no demo |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48 (last seen) |
| Severity | medium: Real-machine figures (A4000 0.2 fps, A3000 RTG 0.6 to 0.7 fps) cannot be compared: each tester records their own walk |
| Family | Emulator measurement method (`benchmark-method`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 334d2f6 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.49 (24 October 2026)._

## Status: 24 October 2026

Open. The hardware page now names `dbg fps` and the timedemo steps ([AmiWind on real hardware](../REAL_HARDWARE.md)).
The repair is planned for v0.0.50 ([roadmap](../ROADMAP.md#one-standard-timedemo-for-real-amigas-v0049)).

## Symptom

Two real machines have reported a frame rate: an A4000 with a 68060 at 100 MHz (AGA, an earlier build, about 0.2
frames per second) and an A3000 with a 68060 at 80 MHz through RTG on the tester's own modified build (about 0.6 to
0.7 on a short timedemo). The two cannot be compared: each tester recorded their own walk with their own settings. A
tester asked how to show the frame rate and how to measure; the hardware page did not say. The same tester found no
`awbench` in the build: the builder makes it (the build run's `engine/awbench`) but the image does not carry it,
while the hardware page tells testers to run it first.

## Repair

1. `awbench` on the image, beside the game, so a tester has it without building anything.
2. One standard demo in every image: a fixed walk in Balmora and one outdoors, recorded once on the shipped CHIM
   world.
3. One command that plays them with `timedemo` and writes the machine, the settings that change the frame, the frame
   rate and the renderer counters to one file to send back.
4. A results table on the hardware page, machine by machine, and the same demos in the emulator on every development
   build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Emulator measurement method (`benchmark-method`). Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. See [families](README.md#families).

- [BENCH-AWBENCH-BUFFERS-32](BENCH-AWBENCH-BUFFERS-32.md): awbench reported the stale buffer count after AddBuffers
- [BENCH-DISK-BYTES-32](BENCH-DISK-BYTES-32.md): FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads
- [BENCH-FSUAE-FREQ-32](BENCH-FSUAE-FREQ-32.md): FS-UAE ignores uae_cpu_frequency in cycle-exact mode
- [BENCH-FSUAE-JIT-HANG-32](BENCH-FSUAE-JIT-HANG-32.md): An FS-UAE JIT session hung with a Windows-folder hard file mounted
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS
- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed
- [BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md): Emulated disk time drifts about 1.6x between FS-UAE sessions
- [EMU-JIT-FAULT-ADDRESS-36](EMU-JIT-FAULT-ADDRESS-36.md): FS-UAE JIT reports fault addresses during the Vivec stage A boot smoke

<!-- END GENERATED CATEGORY -->
