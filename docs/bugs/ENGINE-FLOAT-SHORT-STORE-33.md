# ENGINE-FLOAT-SHORT-STORE-33: 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine/aga/src/aw_anim.c AW_AnimParse (gcc m68k -O1, FPU) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Every group's first frame landed in group 0 on the Amiga while host builds were right; host tests cannot see it |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Worked around in source on v0.0.33-anim-kit, not yet in a build. An island-wide audit of the same pattern
(a float converted straight into a short member of an indexed struct array) is pending.

## Symptom

On the Amiga build every animation group's first frame was stored into group 0: the layout
"idle:0:8 hit:8:3 death:11:6" read back as idle 11, hit 0, death 0, so the frame check refused the
layout and the actor fell back to its idle frames (seen as a test companion that never wore its mover).

## Where

`engine/aga/src/aw_anim.c` `AW_AnimParse`: `t.g[g].base=(short)v[0];` (gcc m68k, -O1, 68040 FPU).

## How it happened

The 68040 build's code for the float-to-short store into an array element indexed by a loop variable
wrote to element 0. The same source compiled for the host (the tests) was right.

## Why it was not caught

The parser's tests run on the host; only an FS-UAE run with a printed layout showed it.

## Reproduction

Engine before the workaround, MiniWind with a react+full resident: `dbg companion test` prints the
mover as missing; the diagnostic dump showed idle 11 8, hit 0 3, death 0 6.

## Repair

Integers first, then one store per field through a pointer to the group.

## Verification

FS-UAE, same sandbox: the companion wears its mover model and walks.

## Prevention

A source test keeps float values out of direct short stores in the parser; the audit over the engine
for the same pattern follows.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

<!-- END GENERATED CATEGORY -->
