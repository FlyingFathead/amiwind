# ENGINE-FPU-DATA-DECODE-33: The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:engine |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | tools/check_fpu_unimplemented.py (objdump linear sweep over .text with constant tables) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: A layout change fails the engine build on instructions that are data and never execute. |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-dev1-build, not shipped at the time of writing.

## Symptom

The engine stage of the v0.0.33-dev1 build stopped: "Engine code reaches 68040-unimplemented FPU
instructions: AW_ModelVisible". The two merged branches each passed the same check on their own.

## Where

`tools/check_fpu_unimplemented.py`, on the linked engine. The reported addresses lie after the last
function of `aw_fog.o`, in a constant table: on this target, constant data goes into `.text`.

## How it happened

objdump disassembles `.text` linearly, data included. The table holds pointers to strings in
`.text` (0x0003f202, 0x0003f210, ...). Read at a two-byte offset, the words `f202 0003` decode as
`fintrz %fp0,%fp0`. The check counts code after the last global of an object as part of that
global, so the table was reported as `AW_ModelVisible`. Whether it happens depends on where the
linker puts the strings: the merge moved them into the 0x3f2xx range.

## Why it was not caught

The check's tests had no data in their synthetic disassembly.

## Reproduction

Link the engine of commit a01cdab (v0.0.33-dev1-build) and run the check: three `fintrzx` sites at
0x3f49c-0x3f4a4, each inside a longword with a `RELOC32 .text` entry.

## Repair

The check records every relocated longword (objdump -r) and ignores a decoded opcode that lies
inside one: real instructions carry relocations only in their operands, never at their opcode word.

## Verification

Regression test `test_pointer_table_in_text_is_not_an_instruction` (a pointer table passes, a real
`fintrz` right after a relocated operand still fails). The merged engine builds and passes the check;
the remaining unimplemented instructions are the allowlisted ones in libm.

## Prevention

Checks that read a disassembly treat relocation data as ground truth for what is code and what is
data.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

<!-- END GENERATED CATEGORY -->
