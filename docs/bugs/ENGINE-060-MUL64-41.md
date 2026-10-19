# ENGINE-060-MUL64-41: The 68040 engine has 151 64-bit MULS.L/MULU.L instructions (divisions by constants), which the 68060 traps to its support library

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41 |
| Where | engine binary (GCC -m68040 code), 68 engine functions |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41 (last seen) |
| Severity | medium: each costs an integer-instruction trap on a 68060; per-frame count measured in the emulated 68060 run |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source ce7ace6, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41 (17 October 2026)._

## Symptom

The engine built for the 68040 (`-m68040 -m68881`) holds 156 64-bit multiplies (`MULS.L`/`MULU.L` with a
`Dh:Dl` result), 151 of them in 68 engine functions. GCC uses them to divide an integer by a constant (multiply
by a magic number, keep the upper half), for example `x / 3`, `x / 10`, `x / 60`. The 68040 runs them in
hardware; the 68060 does not and traps each one to its support library (unimplemented integer instruction).

## Where

The engine binary of the 68040 build: `R_SetSkyFrame`, `R_SkyNearest`, `R_RotateBmodel`, `AW_BrushBound`, the
music, clock, movie and CHIM graft code among them (the full list is in the 68060 report of
`tools/check_fpu_unimplemented.py --cpu 68060`). The C library and libgcc add 5 more and eight 64-bit divides.

## How it happened

The engine is compiled for the 68040, where these multiplies are cheap. The first 68060 scan
([ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md)) reported none: this SDK's objdump prints the 64-bit form as
three operands (`mulsl #k,d1,d2`, against `mulsl #k,d1` for the 32-bit one), which that scan did not recognise.

## Why it was not caught

No check covered the 68060's integer traps until the 68060 mode of the FPU check (it now classifies the
three-operand form as `mul64`, with tests of the spelling).

## Reproduction

`tools/check_fpu_unimplemented.py --cpu 68060 --binary AmiWind --map AmiQuakeGCC.map --report r.json`:
kind `mul64`. Measured per frame on an emulated 68060 in [the 68060 page](../68060.md#trapped-instructions-per-frame).

## Repair

The 68060-targeted build (`--engine-cpu 68060`, [engine profiles](../ENGINE_PROFILES.md#the-68060-targeted-build))
has none in engine code: GCC's 68060 code divides by constants without them. Six remain in the C library and
libgcc, which the build takes from the 68040 set (`tools/fpu-unimplemented-allowlist-68060.json`).
The 68040 build is unchanged.

## Verification

Static: the 68060 check of the `--engine-cpu 68060` build finds no `mul64` in engine code. Emulated 68060:
see the trap counts per frame on the 68060 page.

## Prevention

The FPU check's 68060 mode runs in every build (the 68040 build records its 68060 traps in
`fpu-unimplemented-68060.json`; the gate builds the 68060 variant with its own check).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md): The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library
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
