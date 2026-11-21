# PRISON-SHIP-SHELL-ONE-MODEL-66: the prison ship hold's shell is one brush model always in view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 13 November 2026, in v0.0.65 |
| Where | The opening: the prison ship's hold (prison.bsp, the shell in_prison_ship) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.65 (last seen) |
| Severity | medium: the first room of every new game: up to 5,000 faces a frame tested for nothing at the light headings; the dips at the heavy headings are the props |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_11_12_v0.0.65_full-v0.0.65-release_20c6b9c |
| From commit | source 20c6b9c, engine 20c6b9c, CHIM world 20c6b9c |
| CHIM engine version | CHIM 0.2.2, engine 20c6b9c, world format unknown |
| Unknown because | measured from the v0.0.65 release build's map and the engine source, not from a playtest receipt |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-13: reported in v0.0.65
- 2026-11-13 06:42 +0200: seen again in v0.0.65: the same on the Seyda Neen deck: the ship ex_de_ship (3,690 faces, one CHIM model) is in view at every heading from its deck, and the silt strider (3,219 faces) at two; --chim-draw-tiles on (off by default) stores both as the large-model ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev1 (13 November 2026)._

## Status: 13 November 2026

Open; a fix is on the v0.0.66 line behind a builder switch, on by default. The frame time on the Raspberry Pi 4B is
not measured yet.

## Symptom

In the prison ship's hold the renderer tests about 5,000 faces a frame at the light headings that are not on screen.
The hold is the first room of every new game and runs slower than its few visible faces would explain.

## Where

The opening: the prison ship's hold, `prison.bsp`, the shell model `in_prison_ship` (7,997 drawn faces). The engine's
brush model loop: `engine/aga/src/r_main.c` `R_DrawBEntitiesOnList`, `R_BmodelCheckBBox`; `engine/aga/src/r_bsp.c`
`R_DrawSubmodelPolygons`.

## How it happened

The hold is a classic room map: qbsp builds only a sealing box (two leaves, one byte of visibility data) and the
mesh converter adds the shell and the 98 props as brush models. The engine tests each brush model's box against the
view once; a model in view sends every face through the back-face test and the edge clipper, with no test per face (the
converted models' own nodes are a point-trace chain and reference no faces). The shell's box is the whole room, so it
is in view from every spot and every heading, and all its faces are tested every frame.

## Why it was not caught

The renderer counters of v0.0.57 showed the faces tested per heading (9,969 to 22,416), but not which model they came
from; the hold was read as a count of props in view.

## Reproduction

Always. A model of the engine's test from the start, Jiub and the guards' places, eight headings each, on the v0.0.65
release map: 14,128 faces tested per view on average; at one of the start's headings 10,663 tested for 901 on screen.

## Repair

`--room-draw-tiles` (default 512): the shell's faces are split into 16 draw tiles of at most 512 faces by their
centres, each a nonsolid brush model with its own box at the shell's placement; the shell keeps its box, its collision
and its entity, and draws nothing itself. The faces are not changed, only reordered within the shell's range
(`tools/bsp_model_tiles.py`). `--room-draw-tiles 0` keeps the shell as one model. Measured with the same model of the
engine's test: 14,128 to 11,551 faces tested per view on average (light headings about 11,000 to about 7,000), the
worst view unchanged (it looks at most of the room). Details and the methods beside it: [ship
interior](../SHIP_INTERIOR.md#the-weight-of-the-hold).

## Verification

`tests/test_bsp_model_tiles.py` (faces unchanged as records, tile boxes hold their faces, the shell's box and hulls
kept, the refusals). Pending: the frame time on the Raspberry Pi 4B at fixed spots in the hold, like for like with the
v0.0.65 image.

## Prevention

The ship interior page records the faces tested per view from the fixed spots, so a room map shell that is one model
again shows in the numbers.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

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
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
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

Related bugs in other categories:

- [PRISON-SHIP-FLOOR-STUCK-67](PRISON-SHIP-FLOOR-STUCK-67.md): On the prison ship the player gets stuck on a floor tile that stands out of the hold floor
- [PRISON-SHIP-TABLE-DARK-TRIANGLE-67](PRISON-SHIP-TABLE-DARK-TRIANGLE-67.md): A large dark triangle lies across the table in the prison ship hold

<!-- END GENERATED CATEGORY -->
