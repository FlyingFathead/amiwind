# ENGINE-FRAME-TIME-FLOAT-35: The main loop held the seconds since start in floats: frame times quantise after hours of play

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src/sys_amiga.c RunGameLoop |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: After about 4.5 hours frame deltas step by 1 ms, after 18 hours by 4 ms: jitter or stalls in long sessions |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b72d32 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-crash-fixes-2, not shipped at the time of writing.

## Symptom

Not reported in play (sessions are short so far). `RunGameLoop` stored `Sys_FloatTime()` (a double: seconds
since start) in `float newtime, oldtime`. A float steps by about 1 ms after 4.5 hours and by about 4 ms after
18 hours, so the frame time passed to `Host_Frame` came in coarse steps: jitter, and frames with a time of 0
that the host skips.

## Where

`engine/aga/src/sys_amiga.c` `RunGameLoop`.

## How it happened

The Amiga port's loop used floats where id's own loops (`sys_linux.c`) use doubles.

## Why it was not caught

Every test and playtest session is far shorter than four hours.

## Reproduction

Play for several hours; or compute the float step at the seconds since start.

## Repair

`newtime` and `oldtime` are doubles, as upstream; only their difference goes to `Host_Frame`, as before. The
68040 and 68060 FPUs subtract doubles natively (no unimplemented-instruction trap; the FPU gate is unchanged).
`realtime` and `host_frametime` were already doubles.

## Verification

`tests/test_engine_crash_paths.py` checks the loop's types and states the float steps at 4.5 and 18 hours.

## Prevention

Time since start is kept in doubles wherever it is stored.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

<!-- END GENERATED CATEGORY -->
