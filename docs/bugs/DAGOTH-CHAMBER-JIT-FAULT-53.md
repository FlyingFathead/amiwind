# DAGOTH-CHAMBER-JIT-FAULT-53: Loading Akulakhan's Chamber freezes with the JIT on and loads fine with the JIT off

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 27 October 2026, in v0.0.53 |
| Where | room load of Akulakhan's Chamber under the FS-UAE JIT |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.53 (last seen) |
| Severity | high: The last room of the main quest stalls on entry. |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| Playtest version | 2026_10_27_v0.0.53_final_45f4c426 |
| From commit | source 45f4c42, engine 45f4c42, CHIM world 45f4c42 |
| CHIM engine version | CHIM 0.2.2, engine 45f4c42, world format 0.13 |
| Platform or emulator | FS-UAE JIT, 128 MB |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- COMBAT-PLAYGROUND-JIT-FREEZE-54 (no report page): The combat playground freezes about 4 s into the fight of a group of four with the JIT on
- [ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md): The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library
- [ENGINE-060-MUL64-41](ENGINE-060-MUL64-41.md): The 68040 engine has 151 64-bit MULS.L/MULU.L instructions (divisions by constants), which the 68060 traps to its support library
- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-JUMP-TABLE-DECODE-63](ENGINE-FPU-JUMP-TABLE-DECODE-63.md): The engine build's FPU check reads a switch's jump table as FPU instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [FPU-SUPPORT-MMULIB-SETPATCH-41](FPU-SUPPORT-MMULIB-SETPATCH-41.md): The MMULib 68060.library stops the boot with an alert on the AmiWind boot disk, which runs no SetPatch
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

Related bugs in other categories:

- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither

<!-- END GENERATED CATEGORY -->
