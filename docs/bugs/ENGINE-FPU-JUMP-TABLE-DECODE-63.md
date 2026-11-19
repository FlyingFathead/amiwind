# ENGINE-FPU-JUMP-TABLE-DECODE-63: The engine build's FPU check reads a switch's jump table as FPU instructions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 November 2026, in v0.0.63-dev1 |
| Where | the engine build (tools/check_fpu_unimplemented.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.63-dev2 |
| Severity | medium: a false failure stops the engine build; no game effect |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 9e68706 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- COMBAT-PLAYGROUND-JIT-FREEZE-54 (no report page): The combat playground freezes about 4 s into the fight of a group of four with the JIT on
- [DAGOTH-CHAMBER-JIT-FAULT-53](DAGOTH-CHAMBER-JIT-FAULT-53.md): Loading Akulakhan's Chamber freezes with the JIT on and loads fine with the JIT off
- [ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md): The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library
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
