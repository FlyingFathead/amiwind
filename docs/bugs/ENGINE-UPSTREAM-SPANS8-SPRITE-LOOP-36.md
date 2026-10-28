# ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36: Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/src/d_scan_68k.s and d_scan_68k_nofpu.s (upstream AmiQuake 9c62d90), D_DrawSpans8 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | low: not linked by the default or the upstream engine profile; only --engine-asm spans with d_subdiv16 0 would run it |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine e35345a |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 10 October 2026

Open. Kept out of the `upstream` engine profile ([ENGINE_PROFILES.md](../ENGINE_PROFILES.md)); selectable with
`--engine-asm spans` for A/B only. Found while adding the upstream assembly to the engine
([ENGINE-UPSTREAM-ASM-UNUSED-36](ENGINE-UPSTREAM-ASM-UNUSED-36.md)).

## Symptom

None in a default build. Upstream's `d_scan_68k.s` (and its no-FPU sibling) exports `D_DrawSpans8`, but its loop
does what Quake's sprite span loop `D_SpriteDrawSpans` does: it steps through a contiguous array of 12-byte spans
(`u`, `v`, `count`) until a count of -128 (`DS_SPAN_LIST_END`), skips texel 255 and tests and writes the depth
buffer. `D_DrawSpans8` is called with the 16-byte world span list linked through `pnext`, which the routine never
follows. Inside the loop only `s` is stepped; the register holding `t` is overwritten with the texel, and the depth
value is a constant.

## Where

`engine/aga/src/d_scan_68k.s` and `d_scan_68k_nofpu.s` (upstream AmiQuake revision 9c62d90), `D_DrawSpans8`;
selected in `d_init.c` only when `d_subdiv16` is 0 (default 1: `D_DrawSpans16` draws the world).

## How it happened

Upstream recovered the routine from NovaCoder's AmiQuake v1.36 binary and named it after the hottest span routine.
Because `d_subdiv16` defaults to 1, the routine is never called in upstream's own default build either, so the
mismatch did not show.

## Why it was not caught

The upstream engine never runs it at default settings; AmiWind had not linked upstream's assembly before 10
October 2026.

## Reproduction

Source reading: compare the loop's span stride (12 bytes), end marker (-128) and its texel and depth tests with
`D_SpriteDrawSpans` in `d_sprite.c` and with `espan_t` in `r_shared.h`.

## Repair

None needed for the shipped paths: the `spans` unit is not in either engine profile. If a 68k span routine is
wanted, write AmiWind's own from the C `D_DrawSpans16`/`D_DrawSpans8` and measure it.

## Verification

`tests/test_engine_profile.py` keeps `spans` out of the upstream profile.

## Prevention

Every upstream assembly unit is checked against the C function it replaces (inputs, data layout, loop) before it
joins a profile, and measured with a pixel comparison.

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
- ENGINE-RTG-SLOW-PATH-52 (no report page): With a graphics card installed the engine picks an RTG screen, then draws it through the slow generic path: the direct CyberGraphX copy is switched off
- [ENGINE-UPSTREAM-ASM-UNUSED-36](ENGINE-UPSTREAM-ASM-UNUSED-36.md): The engine is built without AmiQuake's 68k assembly: spans, fixed point and maths run as C at -O1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
