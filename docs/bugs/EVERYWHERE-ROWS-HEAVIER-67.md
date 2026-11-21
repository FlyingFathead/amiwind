# EVERYWHERE-ROWS-HEAVIER-67: suspected: the everywhere recipe's reduction rows give their models more triangles than the converter's own profile

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 November 2026, in v0.0.67-dev1 |
| Where | config/visual-recipes.json everywhere recipe, ratio rows; every CHIM frame and room that places their models |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev1 (last seen) |
| Severity | medium: if true, the rows meant to lighten the heaviest models would make 70 of them heavier in every frame that places them |
| Family | Rendering cost and visibility (`render-performance`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_11_17_v0.0.67-dev1_full-v0.0.67-dev1_6458e88 |
| From commit | source 6458e88, engine 6458e88, CHIM world 6458e88 |
| CHIM engine version | CHIM 0.2.2, engine 6458e88, world format 0.11 |
| Platform or emulator | not in game (a count of the converted meshes, measured on the builder's output) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

## Status: 17 November 2026

Not a bug of the builder: checked against the build's own tables, every row checked makes its model lighter in
the CHIM frames. The census took another converter path than the CHIM frames use (below), so its "without the row"
figures were too low.

## Symptom

A census of every placed model computed each model through `tools/mesh_export.py` (`profile_for`, `variants`):
70 of the 81 ratio rows of the everywhere recipe (`config/visual-recipes.json`) came out with more triangles than
the same model without its row. Examples: ex_redoran_tavern_01 243 without its row and 1,233 with it; ex_ar_01 933
and 2,142; ex_t_menhir_l_01 63 and 204 (9,834 placements); ex_t_manor_01 110 and 380; ex_redoran_building_01 352
without its row, while the mesh methods page lists 1,400 faces before its row.

## Where

The ratio rows of the everywhere recipe; every CHIM frame and room that places their models.

## How it could happen

A row replaces the profile's reduction ratio with its own and reduces through meshoptimizer with locked borders,
which stops early on open rims; the converter's own reducer can go lower. Whether the profile the census used is the
one the CHIM frames use is the open question.

## Reproduction

The census numbers above; the check is the build's own tables.

## The check (17 November 2026)

Each model's mesh through the CHIM mesh unit with the profile the CHIM frames give it (`chim.build`: the frame's
scenery group profile through `town_regions.town_model_profile`, stair plates, visible treads and the mesh method
table), once without its row and once with it, on the v0.0.67-dev1 run's staged scenery; beside it the faces the
run's outdoor world store holds for the model at scale 1 (as built, with the row):

| Model | Source triangles | Faces without the row | Faces with the row | In the built world store |
| --- | ---: | ---: | ---: | ---: |
| ex_redoran_tavern_01 | 1,515 | 1,427 | 1,140 | 1,140 |
| ex_ar_01 | 4,226 | 3,987 | 2,137 | 2,137 |
| ex_t_menhir_l_01 | 296 | 295 | 94 | 69, 72, 94 |
| ex_t_manor_01 | 890 | 887 | 380 | 234, 380 |
| ex_redoran_building_01 | 1,830 | 1,746 | 1,000 | 1,000 |
| contain_urn_05 | 242 | 192 | 141 | 141 |

The CHIM frames give these models a profile with no reduction of its own (ratio 1, planar merge): the row is their
only reduction, and it cuts 20 to 68 % of their faces. The census's "without the row" profile was
`tools/mesh_export.py profile_for`, which takes the first path that reduces a mesh (the town converter, the scenery
group, the open-world maps, the rooms); for these models that is the open world's legacy-map profile, which the CHIM
frames do not use. A census of what CHIM draws takes the CHIM profile as above (rooms: the room's scenery group
profile or the rocks' default, `tools/chim/interior.py room_input`).

## Repair

None needed in the builder. The census measures the CHIM profile.

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
- [SOL-FROSTMOTH-DOCK-FRAME-RATE-68](SOL-FROSTMOTH-DOCK-FRAME-RATE-68.md): Fort Frostmoth's dock on Solstheim runs at about a quarter of the island's usual frame rate when looking over the dock and the ship
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)
- [TREE-SPRITE-DEPTH-23](TREE-SPRITE-DEPTH-23.md): A tree sprite was cut off against the background: a signed depth compared as unsigned
- [VISUAL-EVERYWHERE-ROOMS-67](VISUAL-EVERYWHERE-ROOMS-67.md): The per-model replacements of the everywhere visual recipe reach the outdoor frames only, so rooms draw the heavy original models

Related bugs in other categories:

- [RECIPE-ROW-MOVES-COLLISION-57](RECIPE-ROW-MOVES-COLLISION-57.md): A mesh reduction row changed the Imperial ship's collision: the dev4 build stopped at the collision surface gate in Vivec City (64 units)

<!-- END GENERATED CATEGORY -->
