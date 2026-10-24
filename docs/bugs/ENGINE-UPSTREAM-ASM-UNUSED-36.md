# ENGINE-UPSTREAM-ASM-UNUSED-36: The engine is built without AmiQuake's 68k assembly: spans, fixed point and maths run as C at -O1

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/Makefile: USE_ASM_SPANS=0, no upstream .s files in engine/aga/src |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | high: possible performance loss, narrowed 10 Oct 2026: upstream's default build runs only its turbulent span and chunky-to-planar assembly, at -O1 |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b5e7a9 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Provenance of the five files (read 10 October 2026 from the upstream clone, revision 9c62d90)](#provenance-of-the-five-files-read-10-october-2026-from-the-upstream-clone-revision-9c62d90)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Open, **potentially important regression** (maintainer, 10 October 2026: the whole point of the upstream AmiQuake work is
that it is fast). Found by a source review of the engine against upstream AmiQuake.

### Update, 10 October 2026 (late): engine profiles

The five files are in `engine/aga/src`, linked only by `--engine-profile upstream` (experimental; the default `c`
engine is byte-identical to the one before: [ENGINE_PROFILES.md](../ENGINE_PROFILES.md)). Reading them against the C
they replace narrowed what is at stake:

- At the default `d_subdiv16 1` the world is drawn by `D_DrawSpans16` (C) in upstream too: upstream's assembly
  `D_DrawSpans8` never runs, and its loop has the shape of the sprite span loop
  ([ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md)). Not in the upstream profile.
- `mathlib_68k.s` is not linked by upstream's game build (only its tests and benchmarks), and calls
  `mathieeedoubtrans.library`. Selectable, not in the profile.
- `fixedpoint_asm.s` and `d_scan_68k_nofpu.s` serve the 68020 build only.
- What upstream's default build actually runs from assembly: the turbulent span loop (water, lava) and the
  chunky-to-planar conversion. Those two make the `upstream` profile.
- Correction to the "second, independent loss" below: upstream's Makefile at 9c62d90 compiles everything at `-O1`
  too (`d_sprite.c` at `-O0`); a later commit than its README found `-O2` culling visible objects. So `-O1` is not
  a loss against upstream. The `upstream` profile builds at `-O1`; `--engine-opt o2` keeps the README's selective
  `-O2` as a separate experiment.
- An independent review of the same day reads upstream's `D_DrawSpans8` assembly as broken as well (the register
  holding `t` is overwritten by the texel, only `s` is stepped, depth is compared with the depth step). The bigger
  cheap gains it found are on the C side: [ENGINE-FPCR-DANCE-36](ENGINE-FPCR-DANCE-36.md),
  [ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md),
  [ENGINE-CEILF-PER-EDGE-36](ENGINE-CEILF-PER-EDGE-36.md).

### Measurement, 11 October 2026

Slow 68040 preset, five Balmora cameras, drift rerun ([ENGINE_PROFILES.md](../ENGINE_PROFILES.md#measurements)):
the `upstream` profile is not measurably faster (3D view within 1.3 ms of `c`, whole frame inside the 35 to 74 ms
drift of the `c` rerun); `-O2` saves 18 to 28 ms of the 3D view at every camera (1.7 to 2.5 percent); the `maths`
unit freezes the game. Default stays `c`. The real gains are elsewhere: the C-side costs found the same day
(ENGINE-FPCR-DANCE-36 and its siblings) and AmiWind's own assembly for the edge and clip loops.

## Symptom

No visible symptom: the game runs, but its inner drawing loops are the portable C versions. Upstream AmiQuake ships
hand-written 68k assembly for them (`d_scan_68k.s`, `d_scan_68k_nofpu.s`, `fixedpoint_asm.s`, `mathlib_68k.s`,
`c2p8.s`); AmiWind's engine tree has no `.s` files and builds with `USE_ASM_SPANS=0`, at `-O1` because of compiler
optimiser bugs.

## Provenance of the five files (read 10 October 2026 from the upstream clone, revision 9c62d90)

| File | Lines | Origin stated in the file and its history | Upstream licence statement |
| --- | ---: | --- | --- |
| `d_scan_68k.s` | 364 | "NovaCoder's Optimized Span Drawing Routines, Extracted from AmiQuake v1.36 binary"; added 28 Dec 2025, fixed to match NovaCoder's implementation 30 Dec 2025 | GPL v2 |
| `d_scan_68k_nofpu.s` | 511 | "Based on NovaCoder's FPU-optimized version (d_scan_68k.s)", converted to fixed point; header claims about 1.6 times faster than C | GPL v2 |
| `fixedpoint_asm.s` | 242 | No NovaCoder marks: a fixed-point library for the no-FPU build, added 1 Jan 2026 | GPL v2 |
| `mathlib_68k.s` | 280 | "FPU-optimized math functions from NovaCoder's AmiQuake v1.36, extracted and adapted" (one routine cites an address in the binary) | GPL v2 |
| `c2p8.s` | 455 | NovaCoder's chunky-to-planar routine "disassembled from binary (842 bytes)" with Ghidra | GPL v2 |

Upstream's README states the whole port is GPL v2 "as per original Quake source code license", and argues that
NovaCoder's AmiQuake is itself a port of GPL Quake, so publishing the disassembled routines as readable source is how
the port meets the GPL. AmiWind's licence review of 27 September 2026 was more cautious about code recovered from a
binary. Whether AmiWind follows upstream's reading is the maintainer's decision; `fixedpoint_asm.s` carries no such
question either way.

Project decision, 10 October 2026: AmiWind adopts upstream's GPL v2 reading for all five files
([LICENSING_AND_CREDITS.md](../LICENSING_AND_CREDITS.md)); they are measured before they ship.

(Corrected below the status: upstream's Makefile is `-O1` too.) A second, independent loss in the same place: upstream compiles most of the engine at `-O2` and only `mathlib.c` and
`in_amiga.c` at `-O1` (where GCC's floating-point optimiser miscompiles angle and mouse code), which its README puts
at about 90 % of full `-O2` speed; AmiWind's Makefile compiles everything at `-O1`. The measurement covers both.

## Where

`engine/aga/Makefile` (`DEFINES ... -DUSE_ASM_SPANS=0`, both the default and the `fpu` target) and the absence of the
upstream assembly sources in `engine/aga/src`.

## How it happened

The assembly has been left out since the first repository release (v0.0.16). Part of the reason is recorded in
[LICENSING_AND_CREDITS.md](../LICENSING_AND_CREDITS.md) (renderer adoption review, 27 September 2026): upstream's
`c2p8.s` and `d_scan_68k.s` carry comments saying they were extracted from NovaCoder's v1.36 binary, so they were
excluded from the AmiWind build on provenance grounds, and independent chunky-to-planar and GPL C spans were chosen.
`d_scan_68k_nofpu.s`, `fixedpoint_asm.s` and `mathlib_68k.s` are not mentioned there: they were left out with the
others without a review of their own. A review of 8 October 2026 already listed "USE_ASM_SPANS=1, pixel-identical
first" as a cheap test; it was not run.

## Why it was not caught

Build settings and files were never compared with upstream, and frame-time measurements compared AmiWind builds only.

## Reproduction

Always: `engine/aga/Makefile`; compare `engine/aga/src` with upstream AmiQuake's `src/*.s`.

## Repair

1. Measure what is at stake, in a private build only: the upstream span assembly against the C spans on the
   cycle-exact slow preset at the fixed Balmora cameras, with a drift rerun, images compared pixel by pixel.
2. Review the provenance of every upstream assembly file, one by one (the two marked files stay out of anything
   distributed unless their provenance is cleared).
3. If the gain is real: ship the files whose provenance is clear, and write AmiWind's own 68k assembly for the rest
   (span drawing, fixed point, maths) from the C and the 68040 manuals, as an independent GPL implementation.
4. The C path stays selectable either way.

## Verification

To do: the A/B above, with a drift rerun.

## Prevention

Engine work records which upstream optimisations are in use and which are not; both engine profiles (`c` and
`upstream`) are compiled on every gate; a proposed test always gets a tracker or fixlist entry. If the upstream
assembly proves promising, AmiWind writes its own 68k assembly for the parts that dominate its frame (edge and clip
loops, edge sorting, surface-cache building), as independent GPL code, pixel-identical to the C path.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-CEILF-PER-EDGE-36](ENGINE-CEILF-PER-EDGE-36.md): R_EmitEdge calls the C library ceil twice per edge
- [ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md): The 68040 build converts every drawn surface's gradients to fixed point that nothing reads
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-FPCR-DANCE-36](ENGINE-FPCR-DANCE-36.md): Every float-to-int conversion in the engine saves, changes and restores the FPU control register
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- PERF-ARENA-PIT-SLOW-48 (no report page): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

Related bugs in other categories:

- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies

<!-- END GENERATED CATEGORY -->
