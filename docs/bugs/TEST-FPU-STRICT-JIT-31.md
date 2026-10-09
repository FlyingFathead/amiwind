# TEST-FPU-STRICT-JIT-31: Emulator strict FPU mode is silently ignored while JIT is on

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | FS-UAE strict FPU test configuration (JIT on) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Test-method pitfall; the game is unaffected and the workaround is documented. |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open (test method; no game code affected). Workaround in use: strict FPU runs
use `jit_compiler = 0`.

## Symptom

FS-UAE 3.1.66 with `uae_fpu_no_unimplemented = true` (the emulator's "no
unimplemented floating point instructions" mode, which should make a 68040
take the F-line exception for instructions the chip lacks) still executes
`fmovecr`, `fintrz`, `fint`, `fsin` and `fsincos` when the JIT compiler is on.
The emulator only logs "JIT is not compatible with unimplemented CPU/FPU
instruction emulation" and carries on.

## Where

Emulator test configurations (A1200, 68040-NOMMU, 68040 FPU, JIT on), as used
by every headless benchmark so far. The game itself is unaffected.

## How it happened

The JIT translates FPU instructions itself and does not apply the
unimplemented-instruction check; the option is only honoured by the
interpreter.

## Why it was not caught

No run had used the strict mode before ([ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md)),
and the emulator does not refuse the combination.

## Reproduction

An asset-free probe program installs its own task trap handler and executes
one `fadd` (control), `fmovecr #0`, `fintrz`, `fint`, `fsin` and `fsincos`.
Results in the same configuration:

| JIT | strict FPU | result |
| --- | --- | --- |
| on | off | all executed, 0 traps |
| off | off | all executed, 0 traps |
| on | on | all executed, 0 traps (option ignored) |
| off | on | control executed; the 5 others take vector 11 (F-line), 5 traps |

Kickstart 3.1 sets `AFF_FPU40` in AttnFlags without any 68040 support
library, so the boot check passes either way.

## Repair

None needed in the game. Strict FPU runs must turn the JIT off. With the JIT
off the emulator runs about 50 times slower (Balmora `timerefresh` 0.38 fps
against 19-25 fps with the JIT; the engine's frame time then sits at its
100 ms clamp), so strict runs find where a trap happens; they cannot give a
useful frame rate, and JIT-off runs are only compared with each other.

## Verification

Probe results above (8 October 2026).

## Prevention

The strict-mode run recipe states `jit_compiler = 0` and starts with the probe,
which proves the mode is active before the game image is run.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic

<!-- END GENERATED CATEGORY -->
