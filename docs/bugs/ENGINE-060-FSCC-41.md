# ENGINE-060-FSCC-41: The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41-dev5 |
| Where | engine binary (GCC -m68040 code); tools/check_fpu_unimplemented.py checks the 68040 set only |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41-dev5 (last seen) |
| Severity | medium: each fscc costs hundreds of cycles on a 68060; harmful only if some sit in per-pixel or per-surface code |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev5_full-regional-bc-ac_c2aaf80 |
| From commit | source c2aaf80, engine c2aaf80, CHIM world c2aaf80 |
| CHIM engine version | CHIM 0.2.1, engine c2aaf80, world format 0.7 |
| Platform or emulator | not in game (static scan of the engine binary; no 68060 run yet) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Symptom
A static scan of the v0.0.41-dev5 engine found 263 `fscc` instructions, e.g. `ftst %fp0` followed by
`fsgt d0`: GCC's code for turning a floating-point comparison into a true or false value. The 68040 runs `fscc` in
hardware; the 68060 does not and traps every one to `68060.library`, which emulates it in hundreds of cycles.

## Where
The engine binary built with `-m68040`. `tools/check_fpu_unimplemented.py` checks the 68040's unimplemented set
(68040 User's Manual); the 68060's extra traps (`fdbcc`, `fscc`, `ftrapcc`, `fmovem` with a dynamic register list)
are not checked. The same scan found no 64-bit integer multiply or divide; its `movep` hits are data inside the
code section, not instructions.

## How it happened
The engine is compiled for the 68040, where `fscc` is cheap; the 68060 only became a first-class target later.

## Why it was not caught
The FPU check covers one CPU, the 68040.

## Reproduction
Disassemble the engine (`m68k-amigaos-objdump -d`) and count `fs<condition>` instructions with a data register.

## Repair

1. The FPU check has a 68060 mode (`tools/check_fpu_unimplemented.py --cpu 68060`): every 68060-trapping
   instruction by kind and engine function, through the link map; every 68040 build records its 68060 traps.
   On the v0.0.42 line (engine byte-identical to v0.0.41): 309 `fscc` in 171 engine functions.
2. The 68060 engine (`--engine-cpu 68060`, GCC's 68060 instruction selection) has no `fscc` and no 64-bit
   multiply in engine code ([engine profiles](../ENGINE_PROFILES.md#the-68060-targeted-build)).
3. From v0.0.42 the game disk carries it as `AmiWind060` beside the 68040 engine, and `AmiWindCPU` picks it at
   boot on a 68060 ([68060](../68060.md#both-engines-on-the-game-disk)).

## Verification

Counted on an emulated 68060 (FS-UAE, JIT off, the instructions trap as on the chip; the `awtraps` counter),
17 October 2026, v0.0.41 release disks, the Balmora benchmark cameras and the Mages Guild: the 68040 engine
takes 72,914 to 424,064 traps per frame, 67 to 76 % of them `fscc` in `R_RecursiveClipBPoly` and 20 to 29 % in
`R_EmitEdge`; the 68060 engine takes 1.5 to 3.8 (the C library's `rand`)
([table](../68060.md#trapped-instructions-per-frame)). The two-engine disk booted on an emulated 68060 and
picked the 68060 engine. Still to do: the time this saves on a real 68060.

## Prevention
Every CPU the project targets has its own unimplemented-instruction check in the build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- COMBAT-PLAYGROUND-JIT-FREEZE-54 (no report page): The combat playground freezes about 4 s into the fight of a group of four with the JIT on
- DAGOTH-CHAMBER-JIT-FAULT-53 (no report page): Loading Akulakhan's Chamber freezes with the JIT on and loads fine with the JIT off
- [ENGINE-060-MUL64-41](ENGINE-060-MUL64-41.md): The 68040 engine has 151 64-bit MULS.L/MULU.L instructions (divisions by constants), which the 68060 traps to its support library
- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [FPU-SUPPORT-MMULIB-SETPATCH-41](FPU-SUPPORT-MMULIB-SETPATCH-41.md): The MMULib 68060.library stops the boot with an alert on the AmiWind boot disk, which runs no SetPatch
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

<!-- END GENERATED CATEGORY -->
