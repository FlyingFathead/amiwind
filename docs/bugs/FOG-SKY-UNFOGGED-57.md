# FOG-SKY-UNFOGGED-57: With the 300 fog distance, buildings 20 m away turn solid fog colour while the sky stays clouds: a ragged patch of sky hangs between rooftops

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 30 October 2026, in v0.0.57-dev3 |
| Where | Seyda Neen start street looking north (local 16 44 60, cell -2,-9): aw_fog.c colour fog vs the sky |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.57 |
| Severity | high: the first street of a new game shows sky cut-outs between pale building shapes |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | v0.0.57-dev3 full |
| From commit | source 8297a0b, engine 8297a0b, CHIM world 8297a0b |
| CHIM engine version | CHIM 0.2.2, engine 8297a0b, world format unknown |
| Unknown because | the world format of the dev3 image was not read for this entry |
| Platform or emulator | FS-UAE, JIT, 68040+FPU, 32 MB Fast |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.57-dev4 (30 October 2026)._

## Status: 30 October 2026

Fixed in the source on the v0.0.57 alive branch (the sky haze, `aw_sky_haze`, on by default); in-game A/B below.

## Symptom

At the Seyda Neen start street, looking north, the buildings at the end of the street are drawn as flat shapes in
the pale fog colour up to the top of the view, and the cloud sky shows only in the gaps between their rooflines: a
ragged patch of sky seems to hang in the middle of the street.

## Where

Every exterior with the v0.0.57 default draw distance of 300 (FOG-300-DEFAULT-57). The colour fog
(`engine/aga/src/aw_fog.c`) and the day/night sky tables (`engine/aga/src/r_sky.c`).

## Cause

The colour fog reaches its full strength at the draw distance, so with 300 a building about 20 m away is drawn
entirely in the fog colour. The sky was never fogged: it stays clouds right down to the scenery. Same pose on the
v0.0.57-dev3 image: at 540 the same buildings are textured and the sky reads normally; with the colour fog off both
are normal. The same mechanism as HORIZON-HOLES-31 (fogged scenery against an unfogged sky), made common by the
shorter default.

## Fix

- The sky fades toward the fog colour as the draw distance gets shorter, the way OpenMW blends its sky into the fog:
  no change at 540 and beyond (the HORSTATOR APPROVED horizon as before), rising linearly to 13 of the 15 fog levels
  at 260 and nearer (11 at the default 300; first 9, one step stronger after the A/B still showed the cloud patch faintly). Exteriors only; interiors keep their own fog.
- No per-pixel work is added: the fog pass already costs 150 to 210 ms a frame on a slow 68040
  (RENDER-FOG-PASS-COST-33). The level is folded into the sky's own colour tables (`sky_gradient` in `r_sky.c`) once,
  when the level or the sky's phase changes, and the pass reads those tables as before.
- `aw_sky_haze 0` (console alias `skyhaze`) keeps the sky as before.
- Kept by `tests/test_sky_haze.py`.

## Measured (30 October 2026)

Like for like: one engine, the v0.0.57-dev3 image, the Seyda Neen start street, 32 MB Fast, the slow-CPU emulator
preset, headlamp off, the same view in every variant; only the sky table differs. Averages of the renderer timing
(`aw_rcount 1`):

| Variant | Frame | Sky | Fog pass |
| --- | --- | --- | --- |
| A: draw distance 300, `aw_sky_haze 0` (the sky as before) | 1,461 ms | 6.44 ms | 132.79 ms |
| B: draw distance 300, `aw_sky_haze 1` (new) | 1,509 ms (one 2.2 s frame in its window) | 6.41 ms | 132.79 ms |
| C: draw distance 540 (no haze) | 2,148 ms | 5.15 ms | 111.78 ms |

The sky and the fog pass cost the same with and without the haze. Emulator numbers are relative; the verdict on
the 300 default comes from the Raspberry Pi 4B.

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

- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky

<!-- END GENERATED CATEGORY -->
