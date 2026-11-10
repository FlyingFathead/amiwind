# COMBAT-START-SHEET-READS-61: Several NPCs starting a fight at once hold the frame for over half a second

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 6 November 2026, in v0.0.61-dev2 |
| Where | Combat: fight starts (Arrille's Tradehouse, a theft seen by its residents) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61-dev2 (last seen) |
| Severity | medium: one frame of about 0.64 s on FS-UAE at 32 MB Fast when four residents turn on the player; a frame in play should stay under 0.5 s |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | v0.0.61-dev2 MiniWind seyda (branch v0.0.61-crime) |
| From commit | source 844545e, engine 28d167f, CHIM world 844545e |
| CHIM engine version | CHIM 0.2.2, engine 28d167f, world format unknown |
| Unknown because | a MiniWind test image with the gated engine of the branch; the world format is the image's |
| Platform or emulator | FS-UAE, JIT, 68040 preset, 32 MB Fast |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev2 (6 November 2026)._

## Status: 6 November 2026

Open, v0.0.61.

## Symptom

When a theft is seen in Arrille's Tradehouse, four residents turn on the player in the same moment, and that frame
lasts about 0.64 s on FS-UAE at 32 MB Fast.

## Where

The start of a fight (the combat layer), here started by the crime rules for the witnesses of a theft; the same path
starts any fight.

## How it happened

The crime rules themselves take 14 to 20 ms in that room (seven NPCs tested, seven world traces). The rest of the
frame is the fights starting: each one reads the fighter's sheet from combat/actors.txt on disk (four reads), the two
witnesses' Thief lines load their voice files, and the battle music starts.

## Why it was not caught

A fight usually starts one actor at a time; the frame was measured when a theft started four at once.

## Reproduction

In Arrille's Tradehouse, take an item of Arrille's in front of his counter (`aw_placed crime take 331544`): the console
reports a long frame of about 640 ms with combat/actors.txt read four times.

## Repair

Planned: a fight starts from the actor's stat block that the area load already holds in memory (docs/ACTOR_STATS.md),
so no sheet is read from disk in play.

## Verification

To do: the same theft with no frame over 0.5 s.

## Prevention

To do: a check that the fight start reads no file.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- CHIM-MODEL-FENCE-FACES-64 (no report page): CHIM model faces cannot be alpha-tested, so crossed tree panels cannot be drawn as model variants
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- CHIM-SOLSTHEIM-TREE-FACES-64 (no report page): A dense Solstheim forest frame draws about six times the faces of a median Vvardenfell view
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
- FP-ARMS-PARTS-COST-59 (no report page): First-person arms from parts cost about twice the baked arms per frame; their models carry about three times the vertices
- HEART-CHAMBER-POLYCOUNT-63 (no report page): Akulakhan's Chamber is to be measured on the polycount heatmap: its room models are likely too heavy
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- [INTERIOR-MORAG-TONG-FPS-43](INTERIOR-MORAG-TONG-FPS-43.md): The Morag Tong Guild interior runs at a very low frame rate
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [POLYCOUNT-CAMPS-ALDRUHN-57](POLYCOUNT-CAMPS-ALDRUHN-57.md): The Ashlander camps and central Ald'ruhn are the hottest cells of the polycount heatmap: the yurts alone carry about half of a camp's faces
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- RENDER-SURFACE-CAP-DROPS-FACES-64 (no report page): The renderer posts at most 800 surfaces and 2,400 edges a frame and drops further faces silently, so a dense view such as a Solstheim forest loses most of its faces
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
