# RENDER-BMODEL-FRAGMENTS-32: Brush models spanning many terrain leaves are clipped face by face down the terrain BSP

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | engine r_bsp.c brush models clipped down the terrain BSP |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: Deep BSP walks take 67-82 percent of Balmora render time. |
| Family | Rendering cost and visibility (`render-performance`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev
- 2026-10-08: Independent review of the open-world plan: All performance figures were taken with the emulator at host speed; flat directories are slow on real FFS; brush models may fragment down the terrain BSP; the loader stages lumps before decoding.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan. Hypothesis from the source; fragment counts not yet measured.

## Symptom

A brush model whose box crosses several world leaves takes the clipped path: each face is
clipped recursively down the terrain BSP and drawn as fragments per leaf. Converted buildings
mostly touch many leaves (362 of 590 in Balmora touch more than 16), so their faces may
fragment several times over; one-leaf models take the cheap path.

## Where

`engine/aga/src/r_bsp.c` (`R_RecursiveClipBPoly`, `R_DrawSolidClippedSubmodelPolygons`), `r_main.c` brush model loop.

## How it happened

Quake's brush models were small and sat in few leaves.

## Why it was not caught

Fragments per face are not counted.

## Reproduction

Count faces submitted against fragments emitted at fixed Balmora cameras.

Measured with renderer counters (8 October 2026, ten cameras): the fragments-per-face part is
wrong (1.03-1.59 fragments per clipped face). The cost is the depth of the walk: each clipped face
visits 27-52 world-BSP nodes in Balmora (up to 233,867 node visits per frame), transforming each
node's plane every time. That path is 67-82 % of render time in Balmora and 39-59 % in Seyda
Neen. The one-leaf path is almost unused in Balmora (0-8 models in view).

## Repair

Measure first; the world streamer's simple grid world puts each model in one or two leaves.

## Verification

Pending.

## Prevention

Fragment counters in the performance overlay.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- [AMBIENT-SOUND-READ-IN-FRAME-68](AMBIENT-SOUND-READ-IN-FRAME-68.md): In a fight, one play frame stalled for half a second while an ambient sound and fight data were read from disk
- [AW-20260928-07](AW-20260928-07.md): Slow opening exterior / excessive residency
- [CHIM-MODEL-FENCE-FACES-64](CHIM-MODEL-FENCE-FACES-64.md): CHIM model faces cannot be alpha-tested, so crossed tree panels cannot be drawn as model variants
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-SOLSTHEIM-TREE-FACES-64](CHIM-SOLSTHEIM-TREE-FACES-64.md): A dense Solstheim forest frame draws about six times the faces of a median Vvardenfell view
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [COMBAT-START-SHEET-READS-61](COMBAT-START-SHEET-READS-61.md): Several NPCs starting a fight at once hold the frame for over half a second
- [CONVERT-HEAVIER-THAN-ORIGINAL-67](CONVERT-HEAVIER-THAN-ORIGINAL-67.md): Some models convert to many more faces than their source triangles: surfaces whose texture repeats hundreds of times are split again and again at the texture extent limit
- [DEMOWIND-54](DEMOWIND-54.md): Requested: DemoWind, a small fullscreen AGA build with only cheap animated effects, browsed one by one
- [DISTRICT-FRAME-RATE-LOW-67](DISTRICT-FRAME-RATE-LOW-67.md): Mournhold's districts draw at 8 to 16 frames a second: the Temple courtyard 8.1, the Great Bazaar 10.7, the Royal Palace courtyard 16
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-CEILF-PER-EDGE-36](ENGINE-CEILF-PER-EDGE-36.md): R_EmitEdge calls the C library ceil twice per edge
- [ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md): The 68040 build converts every drawn surface's gradients to fixed point that nothing reads
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-FPCR-DANCE-36](ENGINE-FPCR-DANCE-36.md): Every float-to-int conversion in the engine saves, changes and restores the FPU control register
- [ENGINE-RTG-SLOW-PATH-52](ENGINE-RTG-SLOW-PATH-52.md): With a graphics card installed the engine picks an RTG screen, then draws it through the slow generic path: the direct CyberGraphX copy is switched off
- [ENGINE-UPSTREAM-ASM-UNUSED-36](ENGINE-UPSTREAM-ASM-UNUSED-36.md): The engine is built without AmiQuake's 68k assembly: spans, fixed point and maths run as C at -O1
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [EVERYWHERE-ROWS-HEAVIER-67](EVERYWHERE-ROWS-HEAVIER-67.md): Suspected: the everywhere recipe's reduction rows give their models more triangles than the converter's own profile
- [FENCE-PLACED-ORIGIN-68](FENCE-PLACED-ORIGIN-68.md): See-through faces of outdoor placed models are not drawn see-through: the spruce needle cards show as solid sheets, and many such faces are not drawn at all
- [FOG-SKY-UNFOGGED-57](FOG-SKY-UNFOGGED-57.md): With the 300 fog distance, buildings 20 m away turn solid fog colour while the sky stays clouds: a ragged patch of sky hangs between rooftops
- FP-ARMS-PARTS-COST-59 (no report page): First-person arms from parts cost about twice the baked arms per frame; their models carry about three times the vertices
- [HEART-CHAMBER-POLYCOUNT-63](HEART-CHAMBER-POLYCOUNT-63.md): Akulakhan's Chamber is to be measured on the polycount heatmap: its room models are likely too heavy
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- [INTERIOR-RECEPTION-AREA-FPS-67](INTERIOR-RECEPTION-AREA-FPS-67.md): Mournhold, Royal Palace: Reception Area runs at 3.0 to 5.7 frames a second on the Pi 4B
- [MODAL-WORLD-29](MODAL-WORLD-29.md): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [POLYCOUNT-CAMPS-ALDRUHN-57](POLYCOUNT-CAMPS-ALDRUHN-57.md): The Ashlander camps and central Ald'ruhn are the hottest cells of the polycount heatmap: the yurts alone carry about half of a camp's faces
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [PRISON-SHIP-SHELL-ONE-MODEL-66](PRISON-SHIP-SHELL-ONE-MODEL-66.md): The prison ship hold's shell is one brush model whose box is the whole room: all its 7,997 faces are tested at every heading, though at most headings a few hundred are on screen
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFACE-CAP-DROPS-FACES-64](RENDER-SURFACE-CAP-DROPS-FACES-64.md): The renderer posts at most 800 surfaces and 2,400 edges a frame and drops further faces silently, so a dense view such as a Solstheim forest loses most of its faces
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- [SKEL-RUNTIME-COST-52](SKEL-RUNTIME-COST-52.md): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SOL-FROSTMOTH-DOCK-FRAME-RATE-68](SOL-FROSTMOTH-DOCK-FRAME-RATE-68.md): Fort Frostmoth's dock on Solstheim runs at about a quarter of the island's usual frame rate when looking over the dock and the ship
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)
- [TREE-SPRITE-DEPTH-23](TREE-SPRITE-DEPTH-23.md): A tree sprite was cut off against the background: a signed depth compared as unsigned
- [VISUAL-EVERYWHERE-ROOMS-67](VISUAL-EVERYWHERE-ROOMS-67.md): The per-model replacements of the everywhere visual recipe reach the outdoor frames only, so rooms draw the heavy original models

<!-- END GENERATED CATEGORY -->
