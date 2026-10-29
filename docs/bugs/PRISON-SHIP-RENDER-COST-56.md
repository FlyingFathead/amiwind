# PRISON-SHIP-RENDER-COST-56: the prison ship's hold draws slower than the Vivec Arena Pit

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.56-dev1 |
| Where | The opening: the prison ship's hold |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.56-dev1 (last seen) |
| Severity | medium: the first room of every new game is the slowest place the maintainer has seen; it plays, but badly on slower machines |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_10_29_v0.0.56-dev1_full-dev1-arenapit_5406920 |
| From commit | source 5406920, engine 5406920, CHIM world 5406920 |
| CHIM engine version | CHIM 0.2.2, engine 5406920, world format 0.11 |
| Platform or emulator | Amiberry 8.5.0, JIT, 68040+FPU, cpu_threaded, Raspberry Pi 4 at 2.0 GHz (the v0.0.56-dev1 image on the boot stick) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56-dev1 (29 October 2026)._

## Status: 29 October 2026

Open; the cause is decided, the fix not started. The maintainer, playing the v0.0.56-dev1 image on the Raspberry Pi
4 boot stick (Amiberry, JIT, the 68k CPU on its own thread): "even in the prison ship where I think the fucking dips
are due to the obscene polycounts. I mean literally the prison ship is fucking heavier than vivec arena's pit". The
goal, his words: "there's no reason on earth why this fucking opening scene shouldn't run at max fps".

## Symptom

The frame rate dips in the prison ship's hold at the start of the game, more than in the Vivec Arena Pit, a much
larger room. Out on the open deck and in Seyda Neen it gets lighter.

## Where

The opening: the prison ship's hold (the first room of a new game). The same kind of place, by the maintainer's
playtests: Seyda Neen ("pretty fucking wild that we can have Vivec at a better FPS than something you'd 'think' is
a trivial little town": open sight lines over the most hand-dressed scenery) and the Dwemer ruins ("just ass in
terms of fps": pipes, gears, railings and machinery). And central Ald'ruhn, on the Pi 4 stick ("ald'ruhn central
tanks performance in terms of FPS but yeah, it is what it is"): the Redoran shells, Skar and the town around them. And an Ashlander camp in the Grazelands (the maintainer, at Seba
Anurnudai's camp: "another fps tanker and it's just yurts ... the polycount in those are just insane probably ... just
those few next to the lady, on the screen now... massive FPS tank"): a handful of yurts in view is enough.

## How it happened

Decided by the maintainer from his playtests: "we know the cause, it's the bethesda polycount from hell, they've
outsourced everything to the gpu back in the day ... I've been playtesting the game enough to see like 'okay,
we're tanking here, so the polycount must be high'". The original models were made for a graphics card; the
software renderer draws every face in view on the CPU, so a room dressed with detailed clutter (the hold's hammocks,
ropes, crates and barrels) costs more than a large room of plain walls. One more sign: the Halloween benchmark,
started by accident inside the hold, was not that slow ("so it's like, the fucking pre-baking inside the prison ship
at least tanks that shit"): its animated cast costs less than the hold's own static models. A part of the faces is
never seen at all: buried under the terrain or hidden inside other models (the maintainer: "we found like a TON of
polygons just hidden in these fucking structures and underneath the terrain"; CHIM-HIDDEN-FACES-33,
CHIM-TERRAIN-ROCK-EXEMPT-38).

## Why it was not caught

The benchmark places are in towns and the Halloween scene; the opening room has no benchmark camera.

## Reproduction

Always, by the maintainer's account: start a new game and look around the hold.

## Repair

The maintainer's reading: "this is purely the fucking polycount now that we've got a zillion objects in and the
prison ship is like filled with fucking hammocks and shit like that". Where to look (same evening): "we have the
polycount heatmap per world cell so it shouldn't be too hard to trace the problem spots because the polycount is what
seems to cause it" / "I mean using the polycount tracker": the Toolkit's polycount tracker colours every world cell by
its face count ([Polycount inspector](../POLYCOUNT_INSPECTOR.md)), so the slow places are found from its hottest cells
and rooms first, then checked in game. The direction: fewer faces drawn, by two
levers. Fewer faces per model: simpler versions of the heaviest original models, made by the builder from the
player's own data (nothing shipped), worst first; the Dwemer ruins reuse a few pieces everywhere, so one simpler
pipe or gear speeds up every ruin. Fewer models drawn: clutter dropped at a distance, and the hidden and buried
faces removed. The census from the data ranks the work: every placed model in the hold, in Seyda Neen and in a
Dwemer ruin with its face count as converted, largest first, against the Arena Pit's; it also shows whether the
hold goes through the normal interior pipeline.

The builder's mesh optimizer already exists (tools/meshopt.py, the meshoptimizer simplifier, used for the static
levels of detail); the hot models and the interiors are not run through it yet. Every model is stored once and placed
by reference, which saves disk and memory but not drawing: each placed copy is drawn face by face.

IMPERATIVE (the maintainer: "the imperative is that we DO NOT break the polygon stitching/seams and such even if we
reduce the count"): no simplified model may open a seam, a crack or a gap where its parts or neighbouring models
meet. The simplifier runs with its borders locked, and a seam check (the shared edges before and after, no new open
edges) passes every simplified model before it ships.

None yet beyond that. Then the numbers: `dbg rcount` and the frame time at fixed cameras in the hold and in the Arena Pit, the
same session, the same preset (32 MB Fast, JIT), so the two rooms are compared like for like; then the fix where the
counters point (faces drawn, overdraw, surface cache, models).

## Verification

None yet. The opening scene at the full frame rate (the maintainer's goal); measured: the hold's frame time at its
cameras, then Seyda Neen's and a Dwemer ruin's, each against its number before the change.

## Prevention

A benchmark camera in the hold, so the opening room is measured with every build.

## Related

[AW-20260928-01](AW-20260928-01.md) (the ship-to-deck change is slow at times), [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- DEMOWIND-54 (no report page): Requested: DemoWind, a small fullscreen AGA build with only cheap animated effects, browsed one by one
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-CEILF-PER-EDGE-36](ENGINE-CEILF-PER-EDGE-36.md): R_EmitEdge calls the C library ceil twice per edge
- [ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md): The 68040 build converts every drawn surface's gradients to fixed point that nothing reads
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-FPCR-DANCE-36](ENGINE-FPCR-DANCE-36.md): Every float-to-int conversion in the engine saves, changes and restores the FPU control register
- ENGINE-RTG-SLOW-PATH-52 (no report page): With a graphics card installed the engine picks an RTG screen, then draws it through the slow generic path: the direct CyberGraphX copy is switched off
- [ENGINE-UPSTREAM-ASM-UNUSED-36](ENGINE-UPSTREAM-ASM-UNUSED-36.md): The engine is built without AmiQuake's 68k assembly: spans, fixed point and maths run as C at -O1
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

Related bugs in other categories:

- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)

<!-- END GENERATED CATEGORY -->
