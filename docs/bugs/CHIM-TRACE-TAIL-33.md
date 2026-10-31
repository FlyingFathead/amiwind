# CHIM-TRACE-TAIL-33: A few CHIM collision traces visit thousands of clipnodes

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM collision traces: chunk terrain and placement standing hulls |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Seyda Neen p90 trace 3,040 clipnode visits vs median 171 (offline); paid by player movement and every NPC step and probe on a slow 68040. |
| Family | Rendering cost and visibility (`render-performance`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source fd9e007, engine fd9e007, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine fd9e007, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 9 October 2026

Open. Measured offline during the NPC pathfinding investigation
([NPC pathfinding](../NPC_PATHFINDING.md), [CHIM NPC pathfinding](../chim/CHIM_NPC_PATHFINDING.md)).
Cause not yet known; the engine-side count on the cycle-exact preset is pending.

## Symptom

Most standing-hull traces on a CHIM frame are cheap, but a tail of them visits hundreds to
thousands of collision nodes. Counted offline (clipnode visits per trace, the work
`SV_RecursiveHullCheck` does per hull entered), on CHIM world format 0.5 builder output, 9 October
2026:

| Frame | Trace set | Traces | Visits per trace: median | p90 | mean |
| --- | --- | ---: | ---: | ---: | ---: |
| Seyda Neen | 16-way fan, 32 units, from each grid point | 1,664 | 171 | 3,040 | 2,003 |
| Seyda Neen | same fan raised by one step (8.5 units) | 1,664 | 435 | 5,021 | 2,386 |
| Seyda Neen | player-style steps along the path grid links | 6,730 | 109 | 678 | 329 |
| Balmora | 16-way fan, 32 units | 6,288 | 48 | 179 | 544 |
| Balmora | same fan raised by one step | 6,288 | 55 | 189 | 617 |
| Balmora | player-style steps along the path grid links | 24,951 | 30 | 88 | 95 |

The mean is several times the p90 in both towns, so a small share of traces carries most of the
work. Raising the trace off the ground does not make it cheaper, so it is not only ground contact.

## Where

CHIM collision: the standing hulls (hull 1) of the chunk terrain and of the placed models, traced
as the engine traces a brush entity (`SV_ClipMoveToEntity`, `SV_RecursiveHullCheck` in
`engine/aga/src/world.c`); offline, `chim.collision.FrameScene` with the walkability tracer
(`tools/audit_walkability.py`). Balmora's frame has 512,875 hull nodes over 2,049 brushes (576
chunks and the placements); Seyda Neen's 95,669 over 801.

## How it happened

Unknown. Candidates to measure: placement hulls built as unions of many convex pieces (a trace
inside a building's box walks many split planes), chunk terrain hulls on irregular ground
(CHIM-TERRAIN-HULL-BEVELS-33 changed how terrain is expanded), and traces that enter several
overlapping placement boxes (2.5 hulls per fan trace in Balmora, 4.2 in Seyda Neen).

## Why it was not caught

CHIM collision was checked for correctness (stair gate, actor contact) and its traces were never
counted; the renderer counters do not include server traces.

## Reproduction

On a format 0.5 world: build `FrameScene` for the frame, trace 16 directions of 32 units from
each exterior path grid point (standing on the collision), count node visits per trace and take
the median, p90 and mean. Seyda Neen shows the tail every time (deterministic data).

## Repair

Pending: find which hulls the tail traces walk (per placement model and per chunk), then decide
(simpler hulls for the worst models, bevel or merge planes, tighter boxes).

## Verification

Pending: the same offline counts after a change, and an engine trace counter (traces, clipnode
visits, cycles) on the cycle-exact preset at fixed Balmora and Seyda Neen poses.

## Prevention

Pending: trace counts per frame in the CHIM statistics, and a regression limit on the p90 and
mean visits per trace on the benchmark frames.

Related: the slow-CPU frame time on CHIM (CHIM-SLOWCPU-FRAMETIME-33 on the CHIM branch) is
dominated by rendering, but every trace counts for player movement and for every NPC step and
probe on a 50 MHz 68040.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
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
- [FOG-SKY-UNFOGGED-57](FOG-SKY-UNFOGGED-57.md): With the 300 fog distance, buildings 20 m away turn solid fog colour while the sky stays clouds: a ragged patch of sky hangs between rooftops
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [POLYCOUNT-CAMPS-ALDRUHN-57](POLYCOUNT-CAMPS-ALDRUHN-57.md): The Ashlander camps and central Ald'ruhn are the hottest cells of the polycount heatmap: the yurts alone carry about half of a camp's faces
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

Related bugs in other categories:

- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges

<!-- END GENERATED CATEGORY -->
