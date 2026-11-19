# CONVERT-HEAVIER-THAN-ORIGINAL-67: some models convert to many more faces than their source triangles

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 November 2026, in v0.0.67-dev1 |
| Where | the mesh converter's extent split (prepare_mesh_bsp, 240 texels per face); every CHIM room and frame that places such a model |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev1 (last seen) |
| Severity | high: a conversion heavier than its source; in Akulakhan's Chamber about 5,700 of the room's 45,562 faces, where the room is already the hardest fit at 32 MB |
| Family | Rendering cost and visibility (`render-performance`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_11_17_v0.0.67-dev1_full-v0.0.67-dev1_6458e88 |
| From commit | source 6458e88, engine 6458e88, CHIM world 6458e88 |
| CHIM engine version | CHIM 0.2.2, engine 6458e88, world format 0.11 |
| Platform or emulator | not in game (counted on the builder's output and the converter) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-17: reported in v0.0.67-dev1
- 2026-11-18 04:24 +0200: seen again in v0.0.67-dev2: Counted by the model census (tools/model_census.py) on the v0.0.67-dev2 line, through the profiles the CHIM frames and rooms start from and the method each uses: 311 models in 324 model and space pairs draw more triangles than their source ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

## Status: 17 November 2026

Open. The cause is proven on the worst models; the repair (keep the extent rule without the growth) comes next,
measured before, change and total.

## Symptom

A conversion must never be heavier than its source, but a census of every placed model found models that the
builder turns into more faces than their source has triangles. Checked on the v0.0.67-dev1 run's room store (faces
one placement draws, with each room's own profile) and through the converter with the rocks' default profile (64
texels a texture repeat), which shows the split on its own:

| Model | Source triangles | Polygons before the extent split | Faces after the split | Faces in the built room store |
| --- | ---: | ---: | ---: | ---: |
| in_dagoth_scaffold00 | 360 | 237 | 3,038 | 1,599 |
| in_dagoth_plate20 | 52 | 40 | 1,556 | 796 |
| in_dagoth_plate00 | 52 | 31 | 1,299 | 661 |
| in_cavern_beam00 | 192 | 98 | 236 | 98 |
| furn_pathspear_04 | 70 | 57 | 81 | 81 |

In Akulakhan's Chamber the scaffold (three placements) and the three plates draw about 5,700 of the room's 45,562
faces ([AKULAKHAN-CHAMBER-32MB-STALL-53](AKULAKHAN-CHAMBER-32MB-STALL-53.md)).

## Where

The mesh converter's extent split (`tools/prepare_mesh_bsp.py`, a face may span at most 240 texels, the engine's
surface limit); every CHIM room and frame that places such a model.

## How it happened

The dagoth scaffold and plates are about 1,400 units tall, and their texture repeats about 1,000 times along that
height: about 45 texels a unit at the converter's 64 texels per repeat. The extent split keeps every face within 240
texels, so each tall polygon is cut every few units: one polygon becomes dozens of faces. A room whose profile maps
fewer texels to a repeat splits less (the store's figures), but still several times the source. The cavern beams
and the path spears grow the same way on a smaller scale (a texture repeated six times across the beam); in the built
rooms the beam stays at 98 faces.

## Reproduction

Always, on any build: the converter's face count of these models against their source triangles.

## Repair

To do: keep the extent rule (it protects the engine's surface cache) without the growth, by the face's texture
density or its texture coordinates, with the shape unchanged; then the same measurement before, change and total,
for the models above and the per-room totals.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- [AW-20260928-07](AW-20260928-07.md): Slow opening exterior / excessive residency
- [CHIM-MODEL-FENCE-FACES-64](CHIM-MODEL-FENCE-FACES-64.md): CHIM model faces cannot be alpha-tested, so crossed tree panels cannot be drawn as model variants
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-SOLSTHEIM-TREE-FACES-64](CHIM-SOLSTHEIM-TREE-FACES-64.md): A dense Solstheim forest frame draws about six times the faces of a median Vvardenfell view
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [COMBAT-START-SHEET-READS-61](COMBAT-START-SHEET-READS-61.md): Several NPCs starting a fight at once hold the frame for over half a second
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
- [PRISON-SHIP-SHELL-ONE-MODEL-66](PRISON-SHIP-SHELL-ONE-MODEL-66.md): The prison ship hold's shell is one brush model whose box is the whole room: all its 7,997 faces are tested at every heading, though at most headings a few hundred are on screen
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFACE-CAP-DROPS-FACES-64](RENDER-SURFACE-CAP-DROPS-FACES-64.md): The renderer posts at most 800 surfaces and 2,400 edges a frame and drops further faces silently, so a dense view such as a Solstheim forest loses most of its faces
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- [SKEL-RUNTIME-COST-52](SKEL-RUNTIME-COST-52.md): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)
- [TREE-SPRITE-DEPTH-23](TREE-SPRITE-DEPTH-23.md): A tree sprite was cut off against the background: a signed depth compared as unsigned
- [VISUAL-EVERYWHERE-ROOMS-67](VISUAL-EVERYWHERE-ROOMS-67.md): The per-model replacements of the everywhere visual recipe reach the outdoor frames only, so rooms draw the heavy original models

Related bugs in other categories:

- [AKULAKHAN-CHAMBER-32MB-STALL-53](AKULAKHAN-CHAMBER-32MB-STALL-53.md): Akulakhan's Chamber does not fit in 32 MB of Fast RAM: its room models need more memory than is free

<!-- END GENERATED CATEGORY -->
