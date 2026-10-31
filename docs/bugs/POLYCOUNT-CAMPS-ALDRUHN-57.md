# POLYCOUNT-CAMPS-ALDRUHN-57: the Ashlander camps and central Ald'ruhn are the hottest cells of the polycount heatmap

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.56 |
| Where | Urshilaku, Zainab and Ahemmusa Camps; central Ald'ruhn |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.56 (last seen) |
| Severity | medium: the slowest outdoor places on slower machines; the game plays, but the frame rate drops with a few yurts in view |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_10_29_v0.0.56_full-final_b213657 |
| From commit | source b213657, engine b213657, CHIM world b213657 |
| CHIM engine version | CHIM 0.2.2, engine b213657, world format 0.11 |
| Platform or emulator | Amiberry 8.5.0, JIT, 68040+FPU, Raspberry Pi 4 (the v0.0.56 image on the boot stick) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

## Status: 30 October 2026

Repair in the builder: the camps' yurts and props and central Ald'ruhn's buildings get stronger simplifier rows,
with every rim and seam kept. Measured per model; the faces per cell are an estimate until the next build's tracker
measures them, and the frame time on the Raspberry Pi 4 at the camps is still to be taken.

## Symptom

The frame rate drops at the Ashlander camps in the north and the Grazelands and in central Ald'ruhn; a few yurts in
view are enough (the maintainer's playtest on the Raspberry Pi 4 stick, 29 October 2026).

## Where

The CHIM polycount heatmap of the v0.0.56 build (faces placed per cell): Urshilaku Camp 63,288, Ald Velothi 62,234,
Bal Isra 60,840, Tel Aruhn 59,446, Zainab Camp 57,065, Ahemmusa Camp 56,144, Ald'ruhn 55,281.

## How it happened

The original models were made for a graphics card. In the three camps the yurts alone carry about half of the
cell's faces (Urshilaku 45 %, Zainab 51 %, Ahemmusa 57 %): ex_ashl_tent_02 about 2,140 faces a copy, seven to nine
copies a camp, and ex_ashl_tent_03 about 6,460 faces a copy. In Ald'ruhn the Redoran huts, the tavern, the
buildings and their steps, windows and wall corners. The simplifier rows added for MESHOPT-HOT-MODELS-57 used the
default error bound, where the yurts stop early (ex_ashl_tent_02 2,480 to 1,756 triangles), and left
ex_ashl_tent_03 out.

## Why it was not caught

There was no per-cell CHIM face count on the world map until the heatmap of 30 October 2026.

## Reproduction

Always: stand in Urshilaku Camp, Zainab Camp or Ahemmusa Camp, or in central Ald'ruhn.

## Repair

Stronger rows in the everywhere recipe (`config/visual-recipes.json`): ratio 0.1 and an error bound chosen per model
from a sweep (0.25 to 5 % of the model's diagonal), where the face count stops falling; the borders stay locked, so
no rim moves. The seam gate now also checks the whole model: an edge where two parts meet can open when one part is
re-cut, which the part-by-part check could not see (ex_ashl_tent_01 at the default bound, 20 edges); such a part is
put back whole. Every number: [CHIM mesh methods, Stronger rows for the camps and
Ald'ruhn](../chim/MESH_METHODS.md#stronger-rows-for-the-camps-and-aldruhn). Estimated faces per cell: Urshilaku Camp
63,288 to 48,928, Zainab Camp 57,065 to 43,252, Ahemmusa Camp 56,144 to 42,754, Ald'ruhn 55,281 to 44,123.

## Verification

The next build's tracker: faces placed per cell on the heatmap against the v0.0.56 figures above; then a camp in
game at 32 MB Fast, before and after, same pose; then the frame time on the Raspberry Pi 4 at Urshilaku and Zainab
Camp.

## Prevention

The heatmap shows the faces of every cell after every build; a new hot cell is ranked by faces x placements first.

## Related

[PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md) (the same cause: the hold, Seyda Neen, the Dwemer ruins).

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
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
