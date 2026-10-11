# Engine profiles

The AGA engine (`engine/aga/`) can be compiled two ways. Which one a build used is recorded in its
engine receipt, its image receipt, its build summary and on the boot check screen.

| Profile | What it compiles | Default |
| --- | --- | --- |
| `c` | AmiWind's C code paths: the GPL C span drawing, the independent chunky-to-planar conversion (`aw_c2p.c`), `-O1` everywhere (`d_sprite.c` at `-O0`) | yes |
| `upstream` | the optimisations of TerribleFire's AmiQuake GCC port (Stephen Leary), including NovaCoder's original routines: upstream's 68k assembly for the turbulent (water and lava) span loop and the chunky-to-planar conversion, compiled at `-O1` like `c`, as upstream's own Makefile builds (`d_sprite.c` at `-O0`) | no (experimental) |

`--engine-opt o2` is a separate experiment: the selective `-O2` that upstream's README describes
(everything at `-O2` except `mathlib.c` and `in_amiga.c` at `-O1`), with either profile.

`--engine-profile c` stays the **regression reference build**: when a renderer bug shows up, build the
same commit with both profiles and A/B them at the same pose.

## Options

The same options exist on `tools/build.py` and on `tools/build_aga.py engine`:

```sh
python tools/build.py ... --engine-profile upstream                  # the upstream profile
python tools/build.py ... --engine-profile upstream --engine-opt o2  # its assembly at the -O2 experiment
python tools/build.py ... --engine-opt o2                             # C paths at the -O2 experiment
```

- `--engine-profile c|upstream` (default `c`).
- `--engine-asm UNITS`: replaces the profile's assembly units: a comma list of `spans`, `turb`,
  `maths`, `c2p`, `fixed`, or `none`, or `all`.
- `--engine-opt o1|o2|upstream` (`upstream` = `o1`, what upstream's Makefile uses): replaces the
  profile's optimisation level.

A mix that matches neither profile is recorded as `custom`. The default `c` build passes no profile
option to the engine stage and no variable to `make`, so its command lines (and its stage key) stay
those of a build without engine profiles. The engine's `Makefile` takes the same choice as
`ENGINE_ASM="turb c2p"` and `ENGINE_OPT=o2`. All profile options are experimental
([EXPERIMENTAL_FLAGS.md](EXPERIMENTAL_FLAGS.md)) until the owner picks a default from measurements.

## The assembly units

The five files come from upstream AmiQuake at revision `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`
under GPL v2 ([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)). Each starts with a three- or
four-line header naming its origin; below it the text is upstream's, except five lines in the two
span files marked `AmiWind:` that assemble to the same machine code (two unused imports commented
out, and `divsl.l dN,dM:dM` written as the identical `divs.l dN,dM`) so that the assembler prints no
notices. The SDK's own `vasmm68k_mot` assembles them, as it does the boot check.

| Unit | File | Replaces | Upstream profile | Notes |
| --- | --- | --- | --- | --- |
| `turb` | `d_scan_68k.s` (`D_DrawTurbulent8Span`) | the C inner loop of `Turbulent8` (water, lava) | yes | a line-by-line translation of the C loop |
| `c2p` | `c2p8.s` | `aw_c2p.c` | yes | NovaCoder's chunky-to-planar routine, copied to Fast RAM per screen buffer with the plane offsets patched in; it converts 32 pixels at a time into consecutive plane bytes, so screens whose plane rows are padded, or a conversion that is not a multiple of 32 pixels, use the C conversion |
| `fixed` | `fixedpoint_asm.s` | nothing in the 68040 build | yes (68020 build only) | the fixed-point library the no-FPU span routines call |
| `spans` | `d_scan_68k.s` (`D_DrawSpans8`; 68020: `d_scan_68k_nofpu.s`) | the C `D_DrawSpans8` | no | the engine draws world spans with `D_DrawSpans16` unless `d_subdiv16` is 0, so this routine never runs at the default setting, upstream's included. Its loop is the shape of Quake's sprite span loop (a 12-byte span array ended by a count of -128, a transparent-texel test and a depth test), not of the linked world span list `D_DrawSpans8` is given: [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](bugs/ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md). Selectable for A/B only |
| `maths` | `mathlib_68k.s` (`AngleVectors`) | `AngleVectors` in `mathlib.c` | no | freezes the game at its first map (measured 11 October 2026); calls `mathieeedoubtrans.library` for sine and cosine instead of the engine's `Q_SinCosDeg`, and drops the AngleVectors FPU counter; upstream's game build does not link it either (its tests and benchmarks do). 68040 only |

The C code stays compiled in every profile (`USE_ASM_SPANS=0`): with upstream's span file linked,
the C functions keep their code as `D_DrawSpans8_C` and `D_DrawTurbulent8Span_C`, and the selected
unit decides which one runs. Without assembly the source compiles exactly as before.

## What is recorded

- `engine-build.json`: `engine_profile` (profile, label, the units asked and linked, the objects,
  the optimisation level, notes, upstream revision and credit), `assembler` (the vasm banner and
  SHA-256) and, from the gate, `engine_profile_checks`.
- The image receipt (`image/build.json`) and the run's `build.json`: `engine_profile`.
- `build-summary.json` and the summary text: `Engine profile: c (C paths, -O1)` or
  `upstream (asm turb,c2p; -O1)`.
- The boot check: a row `Engine profile:       c: C paths, -O1             [i] INFO`
  (`upstream: 68k asm, -O1`, or `custom: asm N, -On`).

## Checks

Every engine build, in every profile, must be free of compiler and assembler warnings, pass the
68040 unimplemented-FPU-instruction check and link exactly the selected assembly objects (read from
the link map). The gate's engine step builds both profiles and the `-O2` experiment
(`upstream` at `o2`) with `build_aga.py engine --check-profiles`, and also builds `c` once more with its `make` variables spelled out (`ENGINE_ASM=` `ENGINE_OPT=o1`):
that binary must have the same SHA-256 as the plain `c` build. `tests/test_engine_profile.py` checks
the default, the records, the boot row and, where GNU make is installed, that the `c` profile's
`make` commands are the plain build's and the `upstream` profile's are upstream's.

When the profiles were added, the `c` engine was byte-identical to the engine of the commit before
them (SHA-256 `da4b4d6353a39f213d4d373166e593305219e798ea25e5c86d9acbca97b616f5`, 1,010,408 bytes,
both). The first `-O2` build then showed four `-Wstringop-truncation` warnings in bounded `strncpy`
copies that `-O1` does not inline; they were fixed in the C source
([ENGINE-O2-STRNCPY-WARNINGS-36](bugs/ENGINE-O2-STRNCPY-WARNINGS-36.md)), which changes the `c`
binary once.

## Optimisation levels

Upstream's README describes a selective `-O2` (most code at `-O2`, `mathlib.c` and `in_amiga.c` at
`-O1` because GCC's `-O2` floating-point optimiser broke view angles and mouse input). Its Makefile
at revision `9c62d90` compiles everything at `-O1` again, since a later commit found `-O2` culling
objects that should be visible; the `upstream` profile therefore builds at `-O1` like upstream does.
`--engine-opt o2` keeps the README's selective `-O2` as a separate experiment. Upstream used an older
GCC; AmiWind's SDK is GCC 16.2, and those floating-point problems are likely the 68881's 80-bit
registers (excess precision), so a later `-O2` pass would start with integer-only files and
`-fexcess-precision=standard` on floating-point files. The frame comparison against `c` below shows
whether any `-O2` problem reaches AmiWind.

## Measurements

11 October 2026, the v0.0.36-dev3 image (CHIM-native Balmora) with each engine variant swapped in, FS-UAE
3.1.66 cycle-exact 68040 at `uae_cpu_multiplier 14` (49.7 MHz), the five Balmora cameras of
[HARDWARE-BENCHMARK.md](HARDWARE-BENCHMARK.md), noon held, day and night off, headlamp off, walking NPCs
held still, `aw_rcount 2`, medians of 10 one-second lines. Emulator numbers are relative. The 3D view time
(`R_RenderView`) is deterministic: the drift rerun of `c` matches the first run to 0.3 ms. The whole frame
(view plus 2D, chunky-to-planar, sound, server and the test harness's remote-console file traffic) drifted by
35 to 74 ms between the two runs of the same `c` binary, so frame differences below that are noise.

| Camera | c view / frame ms | c rerun | upstream | upstream at `-O2` | c at `-O2` |
| --- | --- | --- | --- | --- | --- |
| Balmora 1 | 1,450.2 / 1,569.6 | 1,450.3 / 1,643.2 | 1,451.5 / 1,552.9 | 1,423.0 / 1,501.7 | 1,422.1 / 1,594.3 |
| Balmora 2 | 1,253.0 / 1,376.9 | 1,253.1 / 1,450.3 | 1,253.8 / 1,371.5 | 1,231.9 / 1,312.9 | 1,231.6 / 1,414.1 |
| Balmora 3 | 695.1 / 1,115.3 | 695.3 / 1,161.7 | 694.8 / 1,082.6 | 677.7 / 1,047.9 | 677.6 / 1,136.7 |
| Balmora 4 | 1,001.2 / 1,122.9 | 1,001.5 / 1,189.2 | 1,000.6 / 1,138.2 | 982.6 / 1,066.5 | 982.7 / 1,144.2 |
| Balmora 5 | 864.1 / 984.2 | 864.2 / 1,019.7 | 864.5 / 1,008.9 | 845.9 / 924.9 | 845.2 / 1,007.9 |

- The `upstream` profile (`-O1`, assembly turbulent span and chunky-to-planar) draws the same 3D view in the
  same time as `c` (within 1.3 ms; only camera 4 shows water). Its whole-frame times lie inside the drift of
  the `c` rerun: no measurable gain on this preset.
- `-O2` makes the 3D view 18 to 28 ms faster at every camera (1.7 to 2.5 percent), with or without the
  assembly, reproducibly.
- Frames: every variant's paused frame was compared pixel by pixel with `c`. Camera 3 is identical in every
  variant. At the other cameras the differing pixels are the river's turbulent water and distant NPCs, the
  same places where the `c` rerun differs from `c` (the scene is paused at a slightly different moment); at
  most 45 pixels per frame fall outside that drift mask, all at the edges of those animated areas. A strict
  pixel proof needs a frozen scene (no animated water, NPCs held), still to do.
- All units at once (`--engine-asm all`, the `maths` unit included) froze the game at its first map; the
  `maths` unit alone does the same (JIT preset: the game stops advancing after the first map). It stays out of
  every profile.
