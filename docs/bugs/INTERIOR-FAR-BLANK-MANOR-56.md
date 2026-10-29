# INTERIOR-FAR-BLANK-MANOR-56: in Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.56-dev1 |
| Where | Ald'ruhn, Manor District (interior 90); likely every large interior |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.56-dev1 (last seen) |
| Severity | medium: a large room looks broken at its far end and costs a lot of frame time |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_10_29_v0.0.56-dev1_full-dev1-arenapit_5406920 |
| From commit | source 5406920, engine 5406920, CHIM world 5406920 |
| CHIM engine version | CHIM 0.2.2, engine 5406920, world format 0.11 |
| Platform or emulator | Amiberry 8.5.0, JIT, 68040+FPU, Raspberry Pi 4 at 2.0 GHz (the v0.0.56-dev1 image on the boot stick) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56 (29 October 2026)._

## Status: 29 October 2026

Open. Found by the maintainer on the Raspberry Pi 4 boot stick (v0.0.56-dev1): "manor district: shit's loading in as
blank spots instead of fading into darker grey". Shots of the room were taken on the Pi, interior 90.

## Symptom

In the Manor District (the large room inside Skar where the Redoran manors stand) the parts of the room beyond the
draw distance show as blank spots of the clear colour, then pop in as you come nearer, where they should fade into a
dark grey with distance. The room is also slow (the maintainer: "those blank spots are not supposed to be there and
also that shit takes a ton of processing"): with no fog, nothing limits how far it draws.

Seen again in the vanity camera's orbit the same evening (the maintainer: "just a few more frames in there and it's
fucking ripping itself wide open"; two shots taken on the Pi at that moment): large flat cream-white areas where the
floor and the walls should be, around the walkway and under the shells, not only far away: whole surfaces are not
drawn and the clear colour shows through.

## Where

Ald'ruhn, Manor District (interior 90); likely every large interior.

## How it happened

Not known yet. Interiors have no fog: the cell's fog colour and density are never used (INTERIOR-FOG-UNUSED-51), so
nothing hides the edge where the drawing stops; out of doors the fog does that.

## Why it was not caught

The interior checks look at small rooms, where the draw distance never runs out.

## Reproduction

By the maintainer's account: walk through the Manor District and look along it.

## Repair

None yet. DECIDED by the maintainer: "we should have interior fog enabled in places that are of that size". Large
interiors get fog (the colour of their cell record, else a dark grey) at the draw distance, so far parts fade into it
as outdoors and nothing past it is drawn; small rooms stay as they are. Which rooms count as large comes from their
size in the converted data, listed, not guessed; with FOG-300-DEFAULT-57 the distance follows the same default.

## Verification

None yet. In the Manor District at 32 MB Fast: no blank spots; the far end fades into dark grey.

## Prevention

A large-interior check in the release smoke (the Manor District, the Arena Pit).

## Related

INTERIOR-FOG-UNUSED-51, [CHIM-ROOM-POPIN-51](CHIM-ROOM-POPIN-51.md).

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

Related bugs in other categories:

- INTERIOR-FOG-UNUSED-51 (no report page): Interiors have no fog: the cell's fog colour and density are never used, so misty caves and tinted rooms show none

<!-- END GENERATED CATEGORY -->
