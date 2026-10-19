# EMU-JIT-FAULT-ADDRESS-36: FS-UAE JIT reports fault addresses during the Vivec stage A boot smoke

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | FS-UAE 3.1.66 JIT, Vivec stage A MiniWind boot smoke |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | low: two JIT fault-address lines per run, the game runs on; benign or not is unknown |
| Family | Emulator measurement method (`benchmark-method`) |
| Playtest version | MiniWind v0.0.36-dev3 |
| From commit | source 61a1ea0, engine 61a1ea0, CHIM world 61a1ea0 |
| CHIM engine version | CHIM 0.1.0, engine 61a1ea0, world format 0.5 |
| Build note | run 2026_10_11_v0.0.36-dev3_miniwind-vivec-arena-chim-vivec-stage-a-try4_61a1ea0, boot smoke |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.36 (11 October 2026)._

## Status: 11 October 2026

Open: to check whether these are benign JIT traps or engine accesses to unmapped memory.

## Symptom

Each boot smoke run of the Vivec stage A MiniWind logged two lines in fs-uae.log:
`JIT: Fault address is 0x80f10000 at PC=0x41e01b57` and `... at PC=0x41e049d7` (host PCs differ per run).
The game kept running (Arena loaded, 10 s in the scene, clock running). The dev3 crash probes logged other
fault addresses (0x2bababab, 0x2bababb9).

## Where

FS-UAE 3.1.66 with the JIT on; the 68k PC is not in the log (the PCs are JIT host addresses).

## How it happened

Unknown.

## Why it was not caught

The smoke judges alive/map/clock, not JIT fault lines.

## Reproduction

The boot smoke of that image with `jit_compiler = 1`.

## Repair

Not yet. Run the same image with the JIT off and `uae_log_illegal_mem = 1` to get the 68k PCs and map them
with the engine link map.

## Verification

Pending.

## Prevention

The smoke records JIT fault lines; any new fault address is reported with the result.

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

<!-- END GENERATED CATEGORY -->
