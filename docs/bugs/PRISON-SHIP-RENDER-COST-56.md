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

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

<!-- contents start -->
## Contents

- [Status: 29 October 2026](#status-29-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Related](#related)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 29 October 2026

Open; the cause is decided, the fix not started. The maintainer, playing the v0.0.56-dev1 image on the Raspberry Pi
4 boot stick (Amiberry, JIT, the 68k CPU on its own thread), noticed that the frame-rate dips in the prison ship
follow the very high polygon counts of its models, and that the prison ship is heavier to draw than the Vivec Arena
Pit. The goal: the opening scene runs at the full frame rate.

## Symptom

The frame rate dips in the prison ship's hold at the start of the game, more than in the Vivec Arena Pit, a much
larger room. Out on the open deck and in Seyda Neen it gets lighter.

## Where

The opening: the prison ship's hold (the first room of a new game). The same kind of place, by the maintainer's
playtests: Seyda Neen, where Vivec runs at a better frame rate than what looks like a trivial little town (open sight
lines over the most hand-dressed scenery), and the Dwemer ruins, which run poorly (pipes, gears, railings and
machinery). And central Ald'ruhn, on the Pi 4 stick, which also lowers the frame rate: the Redoran shells, Skar and
the town around them. And an Ashlander camp in the Grazelands (the maintainer's Pi 4 playtest at Seba Anurnudai's
camp, 29 October 2026): a few yurts in view drop the frame rate sharply, so their polygon counts are probably very
high; a handful of yurts in view is enough.

## How it happened

Decided by the maintainer from his playtests: the cause is the original game's very high polygon counts, which
were left to the graphics card at the time; playing enough shows that a place where the frame rate sinks is a place
where the polygon count is high. The original models were made for a graphics card; the
software renderer draws every face in view on the CPU, so a room dressed with detailed clutter (the hold's hammocks,
ropes, crates and barrels) costs more than a large room of plain walls. One more sign: the Halloween benchmark,
started by accident inside the hold, was not that slow: its animated cast costs less than the hold's own static models. A part of the faces is
never seen at all: buried under the terrain or hidden inside other models (the earlier hidden-face census found a
very large number of polygons inside structures and under the terrain; CHIM-HIDDEN-FACES-33,
CHIM-TERRAIN-ROCK-EXEMPT-38).

## Why it was not caught

The benchmark places are in towns and the Halloween scene; the opening room has no benchmark camera.

## Reproduction

Always, by the maintainer's account: start a new game and look around the hold.

## Repair

The maintainer's reading: this is purely the polygon count, now that so many objects are placed, and the prison ship
is filled with hammocks and similar clutter. Where to look (same evening): the polycount heatmap per world cell
should make it easy to trace the problem spots, because the polygon count is what seems to cause the slowdown; the
Toolkit's polycount tracker colours every world cell by
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

IMPERATIVE (the maintainer's condition: reducing the polygon count must not break the polygon stitching or seams):
no simplified model may open a seam, a crack or a gap where its parts or neighbouring models
meet. The simplifier runs with its borders locked, and a seam check (the shared edges before and after, no new open
edges) passes every simplified model before it ships.

Done in v0.0.57 (MESHOPT-HOT-MODELS-57, 30 October 2026). The ranking by triangles x placements, from the v0.0.56
build's world survey and the master file's room references, and every number: [CHIM mesh methods, Hot
models](../chim/MESH_METHODS.md#hot-models). The seam check is built: `meshopt.seam_check` compares a part's open
edges before and after (no new one, none lost or moved), `simplify_locked` keeps a part whole that would fail it, and
`tests/test_meshopt_seams.py` keeps it; every model measured passes with no torn seam or rim. Simplified through the
everywhere recipe at the default error bound (0.25 % of the model's diagonal): central Ald'ruhn's Redoran huts,
tower and Skar shell (ex_ar_01 4,226 to 2,142 triangles), the Manor District's two shell halves (that room only:
5,529 and 4,781 to 2,431 and 2,857), the Ashlander yurts (ex_ashl_tent_02, 49 placed, 2,480 to 1,756) and a
Dwemer statue (2,365 to 1,280). The hold itself is not helped by this lever: its 26,628 drawn faces are the shell
(7,997, already reduced by its own profile) and many small props with open rims (14 beds, 536 faces each; 15
barrels, 266), which the locked borders keep almost whole even at a coarser error bound. The hold's remaining
levers are fewer props drawn (distance drop, the fog cut) and hidden faces.

Measured in v0.0.57-dev1 (30 October 2026; the v0.0.57-dev1 full image, `map prison`, the start pose, FS-UAE JIT at
32 MB Fast, renderer counters `aw_rcount 1`, four headings, then the same views with `r_drawentities 0`; the host was
busy with other builds, so the times are relative). Per frame, averaged over one-second windows:

| View | Brush models in view | Faces tested / facing | Polygons drawn | Surface cache blocks drawn (texels) | Alias triangles | Frame (renderer) | fps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Heaviest heading | 69 | 22,416 / 11,491 | 8,492 | 413 (1.62 M) | 2 | 24 ms (models 11, edges and spans 11, drawing 7) | 37 |
| Start heading | 33 | 15,060 / 7,825 | 3,042 | 144 (0.57 M) | 1 | 11 ms | 51-55 |
| The two other headings | 13-14 | 9,969-11,629 / 5,269-6,121 | 165-347 | 0 | 0 | 3.6-4.8 ms | 70 (the frame cap) |
| Any heading, brush models off | 0 | 0 | 2-3 | 0 | 0 | 0.8 ms | 71 |

What this says: the hold's cost is its brush models (the ship's shell and its props) and nothing else. The actors
are a rounding error (two alias triangles' worth, the edge and span work of the world itself under 1 ms). Two
things scale with the view: (1) the faces: about 11,500 faces facing the camera in the heaviest view, all on the
one-leaf path (no BSP clipping: `cf 0`), so the cost is per face (back-face test, edges, spans); (2) the surface
cache: in the two heavier views 144 and 413 surface blocks (0.57 and 1.6 million texels) are drawn again every
frame, while the lighter views draw none once settled. Not a light: every block drawn is also a new allocation,
so the blocks were pushed out of the cache, not redrawn in place for a changed light. The cache is 512 KB (an
integer division in its size formula) against the 1.62 MB the heaviest view draws:
[RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md), persisting since v0.0.32, has the design of the fix. The
faces side: a distance drop does little in a room this small (every prop is near), and merging the beds and barrels
into one model per group cuts model passes (69 in view) but not faces; the faces themselves go down
only with simpler prop models or the hidden faces removed, and the mesh optimizer cannot take these props (see
above). So the cheapest step for the hold is the cache size (no change to any model), then a measured look at the
hidden faces of the shell and the props.

Cache size done in v0.0.57 ([RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md)): at the heaviest heading
the hold draws no surface block again per frame (413 before), and the frame went from 27.3 to 19.0 ms in the same
session (v0.0.57-dev1 against dev2, FS-UAE JIT, 32 MB Fast, busy host both).

Hidden faces, measured (30 October 2026, the v0.0.57-dev2 hold map): the existing closed-shell rule
(`tools/cull_bsp_hidden.py`, exterior scenes) proves no face hidden here (it needs closed convex parts, and the
hold's props are open). A second measure, a face buried when every test point just in front of it (the centre
and each corner pulled a quarter towards it, half a unit out) lies inside the point hull of the world or of another
placed model: 503 of 26,614 drawn faces (1.9 %), almost all where the beds touch each other or the shell (up to 37
of a bed's 536). Removing them is not worth a new rule. What is left for the hold's faces: the beds (14 x 536 faces,
open rims the simplifier keeps) and the shell (7,997). A simpler bed made by the builder needs a rule that lets the
rims of a free-standing prop move (no neighbour meets them), checked by the seam gate against the shell and the
other props it touches; that is the next step, measured the same way.

Free rims, measured (30 October 2026, active_de_bed_30, contain_barrel_01 and three Dwemer ruin pieces; ratio 0.1,
bound 1 %): the rims are not what keeps the bed. Its large parts are thin closed shapes; simplified, 456 of its 576
triangles' parts would no longer span their source shape (the shape guard puts them back whole), with the rims
locked or free alike. The barrel is closed (no rim at all): 266 to 244 faces at most. On the Dwemer pieces free rims
save 2-11 % more faces (ex_dwrv_ruin60 747 to 666, enter00 930 to 909, ruin00 563 to 553) while moving 20-144 rim
edges where pieces meet walls and each other. Not worth a rule: the free-rim experiment stays out of the builder.
The beds' faces need a simpler model of their own (a few panels per bed), which is new art and the maintainer's
call, or fewer beds drawn at once.

Then the numbers: `dbg rcount` and the frame time at fixed cameras in the hold and in the Arena Pit, the
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
- [FOG-SKY-UNFOGGED-57](FOG-SKY-UNFOGGED-57.md): With the 300 fog distance, buildings 20 m away turn solid fog colour while the sky stays clouds: a ragged patch of sky hangs between rooftops
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [POLYCOUNT-CAMPS-ALDRUHN-57](POLYCOUNT-CAMPS-ALDRUHN-57.md): The Ashlander camps and central Ald'ruhn are the hottest cells of the polycount heatmap: the yurts alone carry about half of a camp's faces
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
