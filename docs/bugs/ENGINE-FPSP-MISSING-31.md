# ENGINE-FPSP-MISSING-31: Boot disk loads no 68040 FPU support library; emulator hides it

## Status: 8 October 2026

Open. Measured in the emulator's strict FPU mode: the v0.0.31 engine stops
during start-up; the repaired engine (FPU fixes, not yet released) runs
through start-up and the remote console but still stops at the first scene
load. Real-hardware behaviour not yet verified.

## Symptom

The startup sequence runs only the boot check and the engine (no SetPatch, no 68040.library),
so a real 68040 has no handler for the unimplemented FPU instructions the engine reaches
([ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md)). In the emulator's strict mode the
first such instruction takes the F-line exception (vector 11), which without a support
library ends the program.

## Where

The boot disk startup sequence written by `tools/build_aga.py`; `AmiWindCheck`
(Kickstart 3.1 sets the 68040 FPU flag in AttnFlags without any support library,
so the check passes); every engine path into C library code that contains
`FINTRZ`/`FMOVECR`.

## How it happened

All testing has been in an emulator that executes these instructions itself.

## Why it was not caught

No test runs with the emulator's unimplemented-instruction trapping enabled, and
that mode only works with the JIT off ([TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md)).

## Reproduction

FS-UAE 3.1.66, A1200, 68040 with FPU, `jit_compiler = 0`,
`uae_fpu_no_unimplemented = true`; a small trap reporter installed before the engine
records the first F-line trap (vector, stacked PC, 32 longs of the user stack) instead
of the usual guru, and the PC is mapped with the engine's linker map.

| Engine | First trap | Where |
| --- | --- | --- |
| v0.0.31 release | during start-up, before the console is up | `_dtoa_r` (`FINTRZ`): the `%4.1f megabyte heap` start-up line |
| FPU fixes, before the state-file change | as soon as the remote console starts | `_dtoa_r`: the remote state file's `%.2f`/`%.1f` fields |
| FPU fixes (final) | starting the first scene | `__fixunsdfdi` (`FINTRZ`) called from `__fixdfdi` from `_strtod_l`: text-to-float parsing (`atof`, `sscanf %f`) of scene data |

Review note (8 October 2026): the 68040 also traps on denormalized and unnormalized operands,
whatever the instruction, and Quake math produces denormals; without the support library
that is a crash too. Loading the support library on the boot disk is needed even after the
unimplemented instructions are removed; the strict test should force denormals.

## Repair

In source, not yet released (8 October 2026), both ways:

- Optional FPU support library from the user's own installation
  ([FPU support library](../FPU_SUPPORT_LIBRARY.md)). The builder option
  `--amiga-libs DIR` copies the user's `68040.library`/`68060.library` (found in
  `DIR` or `DIR/LIBS`, any case; `mmu.library` too when beside it) into `LIBS:`
  on the boot disk and records name, size and SHA-256 in the image receipt and
  build summary; without one the build continues and reports "no FPU support
  library". A small loader of our own, `AmiWindFPU` (`engine/aga/boot/fpulib.asm`),
  runs before the boot check and does the one part of `SetPatch` that matters
  here: it opens the library that matches the CPU (68060.library on a 68060,
  found through `AFF_68060` or the 68060-only PCR register, since Kickstart 3.1
  reports a 68060 as a 68040) and keeps it open. Opening is what installs the
  handlers: ramlib loads the library from `LIBS:` and its initialisation installs
  the trap handlers and sets the 68881/68882 emulation flags. The boot check
  names the CPU and shows `FPU support: <library> <version> active [x] OK` or
  `none - see docs (optional) [~] WARN` (never fatal); the engine prints the same
  status at start-up and on `dbg fpu`. AmiWind ships no vendor library.
- Removing the reachable unimplemented instructions continues separately: the
  scene-load parsing (`atof`/`strtod`/`sscanf %f`; Quake's own answer is `Q_atof`)
  and any float formatting still used during play. The builder check
  (`tools/check_fpu_unimplemented.py`) lists every remaining library path and why
  it is allowed.

The bug stays open until a release ships the repair and it is verified with a
real support library (strict emulator mode or real hardware).

## Verification

Strict-mode runs above (8 October 2026). Pending: a strict-mode run that reaches
gameplay, and real hardware.

Loader and boot check, 8 October 2026: FS-UAE 3.1.66, Kickstart 3.1, JIT off,
asset-free dry-run images built by the repository builder with a synthetic test
library of our own (`tests/fpu_test_library.asm`, does nothing but open):

| CPU | Strict mode | Libraries on disk | AmiWindFPU | Boot check |
| --- | --- | --- | --- | --- |
| 68040 | on | 68040 | `68040.library 1.0 open (68040)` | `68040.library 1.0 active [x] OK`, continues |
| 68040 | off | 68040 | same | same |
| 68040 | on | none | not run | `none - see docs (optional) [~] WARN`, continues |
| 68040 | on | 68060 only | `68040.library not opened (68040)` | WARN, continues |
| 68060 | on | 68040 + 68060 | `68060.library 1.0 open (68060)` | CPU `68060`, `68060.library 1.0 active [x] OK` |
| 68060 | on | 68040 only | `68060.library not opened (68060)` | WARN |

No crash in any run. On the 68060 the existing `FPU:` line fails without a real
68060.library (Kickstart 3.1 reports no FPU), so that boot stops as before.
Not covered: a real support library and its trap handling.

## Prevention

A strict-mode run (JIT off, starting with the probe program that proves the mode
traps) in the benchmark sweep; the builder check for reachable instructions.
