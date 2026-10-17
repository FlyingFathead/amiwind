# FPU-SUPPORT-MMULIB-SETPATCH-41: The MMULib 68060.library stops the boot with an alert on the AmiWind boot disk, which runs no SetPatch

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41 |
| Where | boot disk with --amiga-libs on a 68060: mmu.library refuses to run before SetPatch |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41 (last seen) |
| Severity | high: a 68060 user who adds this common CPU library gets an alert instead of the game |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| Playtest version | 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source ce7ace6, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.7 |

<!-- END GENERATED FACTS -->

## Symptom

On an emulated 68060 (FS-UAE 3.1.66, Kickstart 3.1), with the `68060.library` 43.1 and `mmu.library` 43.11 of
the MMULib package in `LIBS:` of the boot disk (what `--amiga-libs` copies), the boot stops at an alert: "MuLib
Installation Alert. The mmu.library and the MuTools *MUST* be run *AFTER* SetPatch." The game does not start.

## Where

The boot disk's startup sequence: `AmiWindFPU` opens the CPU library ([FPU support library](../FPU_SUPPORT_LIBRARY.md)),
but the disk runs no `SetPatch` ([ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md)), and MMULib's libraries refuse
to install before it. The library set is one of the builds the builder lists as tested.

## How it happened

`AmiWindFPU` was written to do the one part of `SetPatch` the game needs (open the CPU library and keep it open).
It was checked with a 68040 and with a stand-in library; the MMULib 68060.library was never run on a 68060 boot.

## Why it was not caught

No emulated 68060 boot of a game disk with the library had been run; the FPU support docs said so
("not verified").

## Reproduction

Boot a game disk built with `--amiga-libs` holding the MMULib `68060.library` and `mmu.library` on a 68060
(FS-UAE `cpu = 68060`, `fpu = 68060`, Kickstart 3.1). Measured 16 October 2026 with the v0.0.41 release disks.

## Repair

With the system's own `SetPatch` run before `AmiWindFPU` the same disk boots, the library installs its handlers
and the game runs on the emulated 68060. The builder now copies a `SetPatch` found in the `--amiga-libs` folder
(or its `C` drawer) to `C/` on the boot partition and runs it first; with `mmu.library` and no `SetPatch` it warns
([FPU support library](../FPU_SUPPORT_LIBRARY.md)).

## Verification

Emulated 68060, 17 October 2026: the v0.0.41 disks with `SetPatch`, the MMULib libraries and `AmiWindFPU` in the
order the builder now writes boot and run the game (`FPU support: 68060.library 43.1 open`). Pending: a disk made
by the builder with the option, then a real 68060.

## Prevention

The FPU support check of the builder boots each library set it calls tested on the CPU it is for.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md): The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library
- [ENGINE-060-MUL64-41](ENGINE-060-MUL64-41.md): The 68040 engine has 151 64-bit MULS.L/MULU.L instructions (divisions by constants), which the 68060 traps to its support library
- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

<!-- END GENERATED CATEGORY -->
