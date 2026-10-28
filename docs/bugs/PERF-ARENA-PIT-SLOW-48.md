# PERF-ARENA-PIT-SLOW-48: The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.54-dev1 at 2026-10-27 17:45 +0200: PERSISTING (27 October 2026): the maintainer, on TG 17:31 +0200: the Arena Pit draws a lot of unseen geometry (the upper balconies and far tiers) and tanks the frame rate. Taken by the streaming worker.
- Reported with v0.0.54-dev1 at 2026-10-27 23:25 +0200: Again on v0.0.54-dev1 (27 October 2026): reported by the maintainer at 17:31 +0200; the cause was found at 17:45 +0200 by the streaming worker (an A/B is in progress).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | the Vivec Arena Pit interior (draw and collision cost) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | high: The Arena Pit draws unseen geometry and tanks the frame rate (the maintainer, 27 October). |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine ad8733c |
| CHIM engine version | none: legacy engine |
| Build note | the maintainer's report named no build |
| Platform or emulator | unknown (reported by the maintainer in a message; the build and emulator were not named) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.54 (27 October 2026)._

## Status: 27 October 2026

Open, persisting. The maintainer, on v0.0.54-dev1 (17:31 +0200): the Arena Pit draws a lot of unseen geometry, the
upper balconies and the far tiers, and tanks the frame rate. The cause was found at 17:45 +0200 by the streaming
worker; an A/B comparison is in progress.

## Symptom

The Arena Pit, a large interior, runs at a low frame rate, worst when the balconies and far tiers are in view.

## Where

The Vivec Arena Pit room: its drawn geometry and its collision geometry.

## How it happened

The room is one large model whose upper balconies and far tiers are drawn although they cannot be seen from the floor.

## Why it was not caught

Interiors were checked for load and heap fit, not for the frame cost of unseen geometry.

## Reproduction

Enter the Arena Pit and look across the floor at the tiers, on the slow preset and on the default preset.

## Repair

In progress on the streaming worker's branch; the A/B decides the form.

## Verification

A like-for-like frame time of the same pose before and after, on the default preset at 32 MB Fast.

## Prevention

A frame cost check for large interiors in the build.

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
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
