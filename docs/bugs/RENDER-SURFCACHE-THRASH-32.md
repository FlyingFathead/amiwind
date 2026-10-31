# RENDER-SURFCACHE-THRASH-32: Seyda Neen views rebuild the surface cache every frame at a fixed camera

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Seyda Neen views, engine surface cache (d_surf.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.57-dev2 |
| Severity | medium: Surface cache rebuilt every frame at a fixed camera; a performance cost. |
| Family | Rendering cost and visibility (`render-performance`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

With the camera standing still, Seyda Neen 1 allocates 914 surface cache blocks per frame
(812 KB, 0.76 million texels drawn), Seyda Neen 3 625. Balmora allocates 0 at its cameras.
The cache is smaller than these views need, so lit surfaces are rebuilt every frame.

## Where

Engine surface cache (`d_surf.c`, cache size set at start-up).

## How it happened

Unknown: likely many distinct lit brush-model surfaces in view at once.

## Why it was not caught

No per-frame cache counters before this work.

## Reproduction

`dbg rcount 1` at the Seyda Neen cameras in `docs/HARDWARE-BENCHMARK.md`.

## Persisting: the prison ship's hold (v0.0.57-dev1, 30 October 2026)

Seen again in the opening room, the prison ship's hold ([PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md)):
at its heaviest heading 413 surface blocks (1.62 million texels) are allocated and drawn every frame with the
camera still, at the start heading 144 (0.57 million); the two lighter headings 0 once settled. Every block drawn
is also a new allocation (allocations = blocks drawn), so the blocks are not being redrawn in place because a light
changed (a changed light style or a moving light reuses its block): they were pushed out of the cache and come back
every frame. The cache is too small for these views.

The size: `vid_amiga.c` allocates `(width*height/(320*200))*256*1024*2` bytes. The division is an integer
division, so every screen smaller than 128,000 pixels gets one unit: 512 KB, a third of what the hold's heaviest
view draws (1.62 MB). Quake's own rule (`D_SurfaceCacheForRes`, 600 KB at 320 x 200 plus 3 bytes per extra
pixel) is not used.

## Repair

Done in v0.0.57 (30 October 2026): `vid_amiga.c` sizes the cache at 2 MiB at 320 x 200 (the hold's 1.62 MB plus a
margin; scaled up for a larger screen, never below the method before). `-surfcachesize KB` still overrides it; when
2 MiB is not free (below the 32 MB Fast requirement) the game takes the 512 KB of the method before and prints a
line saying so. The extra 1.5 MiB comes from the rest of Fast RAM outside the game heap
([memory](../chim/build_guide/MEMORY.md#the-picture)); the heap and its rules are unchanged.
`tests/test_surfcache_size.py` keeps the default at or above the hold's view plus a fifth.

The design it follows: (1) size the cache from the measured views instead of the truncated formula: the largest
per-frame texel count at the benchmark cameras (the hold 1.62 MB, Seyda Neen 0.76 MB at the time of this page) plus
a margin, as a start-up setting with that default (Quake's `-surfcachesize` already exists as a start-up argument);
(2) its bytes go into the resident registry against the 32 MB Fast machine, with the measured reason; (3) the
check: the same views show 0 allocations per frame once settled, and the frame time before and after, like for
like. The renderer's time split at the hold's heaviest heading (11 ms brush models, 11 ms edges and spans, 7 ms
drawing) puts the cache rebuild inside the drawing share, so the gain is at most that share; it is measured, not
assumed.

## Verification

30 October 2026, FS-UAE, JIT, 32 MB Fast, the v0.0.57-dev1 full image with its own engine (A) and with the
engine of this change (B), the same poses and script (`aw_rcount 1`); the host was busy with other builds in both
runs, at different moments, so only the counters and the drawing share compare like for like:

| View | Surface blocks drawn per frame, A / B | Drawing time per frame, A / B |
| --- | ---: | ---: |
| Prison ship hold, heaviest heading | 413 / 0 | 9-14 ms / 3.2-4.1 ms |
| Prison ship hold, start heading | 111 / 0-1 | 3.9 ms / 1.9 ms |
| Seyda Neen 1 (`dbg tp -11264 -71680`, `aw_aim 90 0`) | 316-318 / 0 | 10-13 ms / 3.9-5.6 ms |
| Seyda Neen, the next view after the second teleport | 409-435 / 1-5 | 14-28 ms / 4.8-5.7 ms |

Once settled, the views allocate nothing more: the cache holds them. The whole frame times moved with the host
load (the brush-model share grew in the B runs), so the frame-time gain is the drawing share above, about 6-10 ms
of a 30-40 ms frame in these views; a quiet-host A/B is still to be taken. In both runs the script stalled after the
second teleport in Seyda Neen (the same in A and B, so not from this change).

## Prevention

Counters in the benchmark route.

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
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
