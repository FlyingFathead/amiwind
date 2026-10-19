# ENGINE-FPU-UNIMPL-31: Every-frame math traps on a real 68040 (sin+cos become cexp)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | engine maths (rotation, AngleVectors, libm trig) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31, v0.0.40-dev1 (last seen) |
| Severity | high: Thousands of 68040-unimplemented FPU instructions per frame would trap on real hardware, severe slowness. |
| Family | FPU and CPU behaviour (68040/68060) (`fpu-cpu`) |
| Playtest version | v0.0.40-dev1 |
| From commit | source 7a783e0, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format unknown |
| Unknown because | Exact native diagnostic source and engine are hash-bound privately; separate engine/world commits are unknown. Later catalogue/layout repairs need a new target/native gate. |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Historical source note, 8 October 2026](#historical-source-note-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Blocking orientation recurrence, 14 October 2026](#blocking-orientation-recurrence-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Historical source note, 8 October 2026

Open; repaired in source on the FPU fixes branch (not yet released). Per-frame
counts measured before and after; the C library's trigonometry is no longer
linked, and the engine build now fails if engine code can reach a
68040-unimplemented FPU instruction outside a justified allowlist. Still open:
text/float conversion paths that run at scene load (see
[ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md)).

## Symptom

The engine links the 68881 build of the C maths library. At -O1 the compiler turns each
`sin(a)`+`cos(a)` pair into `cexp(i*a)`, and each call executes 3-5 instructions the 68040 does
not implement in hardware (`fmovecr`, `fintrz`), which trap to a software handler (or end
the program without one). Measured per frame on the v0.0.31 image (counters below):
3,547 `cexp` calls at Balmora and 4,084 at Seyda Neen, about 10,000-20,000 traps per frame.

## Where

`engine/aga/src/r_bsp.c` (R_RotateBmodel, called once per submodel surface by the edge
drawer), `mathlib.c` (AngleVectors), NPC targeting in `aw_scene.c`, static flames in
`aw_guard_torch.c`, view bob/idle, particles, sky, sprites, QuakeC builtins; the linked
newlib `libm881` (`exp`, `__kernel_cos`, `__kernel_sin`, `__ieee754_rem_pio2`, `cexp`,
`atan`, `__kernel_tan`).

## How it happened

The SDK's only hard-float maths library is the 68020+68881 build; the engine code itself
uses only 68040 instructions, but the library has 84 unimplemented ones, and the
compiler's sin+cos merge routes hot calls through them.

## Why it was not caught

The emulator executes these instructions directly instead of trapping (its strict mode
works only with the JIT off: [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md)), so frame
rates measured in FS-UAE never include the cost, and no build step looked for them.

## Reproduction

`dbg fpucount 1` prints per-frame counts once a second; or disassemble the linked engine
and follow calls from R_RotateBmodel and AngleVectors into `cexp`
(`tools/check_fpu_unimplemented.py` does both).

Engine number conversion (8 October 2026, counters branch, not yet merged): the engine's own
text/number conversion replaces the C library's; 68040-unimplemented instructions in the binary
fell from 40 to 16 (left: `pow`, `fmod`, `sqrt`, `sqrtf`). With the JIT off and strict FPU mode,
the game boots, loads and renders all ten benchmark cameras with zero traps. Not covered: saves,
menus, combat, intro, and denormal operands.

## Repair

Each step reuses a Quake mechanism:

1. R_RotateBmodel: identity for all-zero angles (rotating the view vectors by it is
   skipped), a yaw-only basis when pitch and roll are zero, and a 64-entry cache of the
   basis keyed by entity and angles (GLQuake's R_DrawBrushModel rotates only non-zero
   angles; id's own TODOs in the function asked for a table and a per-entity cache).
2. Table sine/cosine: a quarter-wave table (1,025 floats) filled on first use from a
   Taylor series, read with linear interpolation plus the second-order term; exact at
   multiples of 90 degrees; error below 1.5e-7 (Quake's `sintable` and 16-bit angle
   quantisation). Used by every engine caller, including AngleVectors and the QuakeC
   `sin`/`cos` builtins.
3. NPC targeting once per frame with a distance precheck
   ([NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md)).
4. Static flames: the six constant emitter offsets precomputed (as `anorms.h` holds
   precomputed normals).
5. `-fno-builtin-sin -fno-builtin-cos` (and the float forms): no sin+cos merge; own
   `atan2` (odd series after two range reductions, error below 3e-16) and `tan`.
   No `sin`, `cos`, `cexp`, `atan`, `tan` or `exp` code is linked any more.
6. Float formatting removed from the start-up heap line and the remote state file.
7. Builder check: `tools/check_fpu_unimplemented.py` disassembles the linked engine with
   relocations, builds the call/reference graph from the linker map and fails the engine
   build if an engine function reaches any 68040-unimplemented FPU instruction (the
   full list: FACOS, FASIN, FATAN, FATANH, FCOS, FCOSH, FETOX, FETOXM1, FGETEXP, FGETMAN,
   FINT, FINTRZ, FLOG10, FLOG2, FLOGN, FLOGNP1, FMOD, FMOVECR, FREM, FSCALE, FSIN,
   FSINCOS, FSINH, FTAN, FTANH, FTENTOX, FTWOTOX, and packed-decimal operands) except
   through `tools/fpu-unimplemented-allowlist.json`, which names each library function,
   its allowed callers and why.

## Verification

Same v0.0.31 image (engine overlaid on a fresh copy), same route and pose, emulator with
JIT, warp off, per frame (median of the one-second averages). K = counters only; D1-D5 =
each step added in turn; D8 = all steps.

| Build | Balmora: rotations / from trig | cexp | direction vectors | NPC searches / tested | Seyda Neen: rotations from trig / cexp |
| --- | --- | --- | --- | --- | --- |
| K (counters only) | 1089 / 1089 | 3547 | 93 | 5 / 70 | 1193 / 4084 |
| D1 rotation paths | 1089 / 59 | 339 | 93 | 5 / 70 | 37 / 542 |
| D2 table trig | 1089 / 52 | 0 | 93 | 5 / 70 | 37 / 0 |
| D3 NPC once per frame | 1089 / 59 | 0 | 19 | 1 / 0 | 37 / 0 |
| D4 flame constants | 1089 / 53 | 0 | 19 | 1 / 0 | 37 / 0 |
| D5 no library trig | 1089 / 52 | not linked | 19 | 1 / 0 | 37 / not linked |
| D8 all | 1089 / 59 | not linked | 19 | 1 / 0 | 37 / not linked |

Library code with unimplemented instructions in the binary: 84 instructions in 20
functions before, 40 in 11 after (float formatting and parsing, `pow`, and the
domain-error branches of `fmod`/`sqrt`/`sqrtf`). Emulator frame rates moved only within
the drift of the reference reruns (the emulator never pays for a trap). Strict-mode runs
(JIT off): see ENGINE-FPSP-MISSING-31. Host tests: `aga_rotate_bmodel_test.c`,
`aga_sintable_test.c`, `aga_static_flame_offsets_test.c`, `aga_npc_contact_test.c`,
`tests/test_check_fpu_unimplemented.py`. Pending: release build, real 68040 hardware.

## Prevention

The builder check above runs in every 68040 engine build (result in
`fpu-unimplemented.json` and `engine-build.json`); `dbg fpucount` for per-frame counts.

## Blocking orientation recurrence, 14 October 2026

The first v0.0.40-dev1 target linked, but the mandatory 68040 reachability gate rejected
the first-person block composition path: R_DrawViewModel reaches
AW_HandBlockItemApply and AW_BlockCompose, then the C library asin. The full
report also reaches library sine/cosine range reduction; displaying only its
first paths did not enumerate every unsafe call. The source also called library
atan2 instead of the engine routine. This is a confirmed development regression
caught before native testing, not an observed fault on real hardware.

The [blocking candidate](COMBAT-BLOCKING-36.md) now reuses AmiQuake mathlib.c:
Q_SinCosDeg for rotation bases and Q_atan2 for Euler extraction. Pitch uses
atan2(vertical, horizontal forward length), retaining near-pole information
that a float sine can round to one. The square root receives a nonnegative
sum of squares. Near poles, roll is recovered from the stable right row;
the exact-pole equivalent uses the existing zero-roll convention. No FPU
allowlist is widened and no animation frames or assets are rebuilt.

An executable independent matrix oracle fails against the preceding source and
passes 1,925 translation/orientation cases with the repair, including positive
and negative poles, near poles, composed cancellation and broad rotations.
The actual block catalogue decodes, 21 focused block/hand/math/FPU checks pass,
and one changed 68040 object compiles with safe engine trig references and no
library asin/sin/cos/atan/atan2 references. Its isolated compile also reports the
existing unused header helper under extra unused warnings; production already
suppresses that category.

The subsequent exact candidate passed the complete Amiga target build and
mandatory linked 68040 instruction gate using the safe engine math, without
widening the allowlist. Its full suite ran 4,072 checks: 4,066 passed, zero
unexpected failures or errors, three Windows skips and three separately
tracked expected failures. These are automated results, not real-hardware
or maintainer acceptance. The native diagnostic exposed separate inventory
catalogue and layout failures; refused actual shield grants mean it does not
verify equipped-shield alignment. Repaired native blocking remains pending.

Host orientation tests alone did not expose the target instruction trap path:
they link the host maths library. Keep both the executable orientation oracle
and a fast hot-path source guard, plus the mandatory final linked instruction
gate. Do not describe the rejected executable as a playable accepted build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: FPU and CPU behaviour (68040/68060) (`fpu-cpu`). Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. See [families](README.md#families).

- [ENGINE-060-FSCC-41](ENGINE-060-FSCC-41.md): The engine has 263 fscc instructions (float comparisons as true/false), which the 68060 traps to its support library
- [ENGINE-060-MUL64-41](ENGINE-060-MUL64-41.md): The 68040 engine has 151 64-bit MULS.L/MULU.L instructions (divisions by constants), which the 68060 traps to its support library
- [ENGINE-FLOAT-SHORT-STORE-33](ENGINE-FLOAT-SHORT-STORE-33.md): 68040 engine build stored float-to-short conversions of the animation layout parser into the wrong group
- [ENGINE-FPSP-MISSING-31](ENGINE-FPSP-MISSING-31.md): Boot disk loads no 68040 FPU support library; emulator hides it
- [ENGINE-FPU-DATA-DECODE-33](ENGINE-FPU-DATA-DECODE-33.md): The 68040 FPU check reads a pointer table in the engine code section as fintrz instructions
- [ENGINE-FRAME-TIME-FLOAT-35](ENGINE-FRAME-TIME-FLOAT-35.md): The main loop held the seconds since start in floats: frame times quantise after hours of play
- [ENGINE-GAMMA-POW-35](ENGINE-GAMMA-POW-35.md): The gamma table called the C library pow, which executes FPU instructions a 68040 does not implement
- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [FPU-SUPPORT-MMULIB-SETPATCH-41](FPU-SUPPORT-MMULIB-SETPATCH-41.md): The MMULib 68060.library stops the boot with an alert on the AmiWind boot disk, which runs no SetPatch
- [TEST-FPU-STRICT-JIT-31](TEST-FPU-STRICT-JIT-31.md): Emulator strict FPU mode is silently ignored while JIT is on

Related bugs in other categories:

- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields

<!-- END GENERATED CATEGORY -->
