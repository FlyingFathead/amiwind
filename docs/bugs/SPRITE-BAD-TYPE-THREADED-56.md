# SPRITE-BAD-TYPE-THREADED-56: R_DrawSprite "Bad sprite type" ends a load on Amiberry with the threaded CPU

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.56-dev1 |
| Where | Amiberry 8.5.0 on a Raspberry Pi 4 with cpu_threaded=true; dbg aw hors 0, Seyda Neen |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.56-dev1 (last seen) |
| Severity | critical: the game stops for good during a load (the maintainer: 'yeah that's a critical bug for sure'); the cause, emulator mode or engine, is not known yet |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_10_29_v0.0.56-dev1_full-dev1-arenapit_5406920 |
| From commit | source 5406920, engine 5406920, CHIM world 5406920 |
| CHIM engine version | CHIM 0.2.2, engine 5406920, world format 0.11 |
| Platform or emulator | Amiberry 8.5.0, JIT, 68040+FPU, cpu_threaded=true, JIT cache 16384 KB, Raspberry Pi 4 at 2.0 GHz |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56-dev1 (29 October 2026)._

## Status: 29 October 2026

Open. Seen once, by the maintainer on the Raspberry Pi 4 boot stick: `dbg aw hors 0` (his test character in the
middle of Seyda Neen) stayed on "Loading..." ("yeah I think we're stuck in the fucking Loading screen now"), and
when Amiberry was restarted the screen showed the error: "it said something about a badsprite type" / "in your exit
stuff". The maintainer: "yeah that's a critical bug for sure". With the threaded CPU switched off again, the same
`dbg aw hors 0` loaded at the first try ("ok now it loaded back into dbg aw hors 0"): one run, not yet the proof.

## Symptom

The load never finishes. The engine has stopped with `Sys_Error ("R_DrawSprite: Bad sprite type %d")`; the
loading screen stays, and the message shows only when the emulator closes.

## Where

Amiberry 8.5.0 on a Raspberry Pi 4 (JIT, 68040+FPU, JIT cache 16384 KB) with `cpu_threaded=true`, the 68k CPU on its
own thread, an experimental Amiberry mode switched on for speed the same evening; `dbg aw hors 0`, Seyda Neen.

## How it happened

Not known yet. The renderer reached a sprite model whose header holds a type that is not one of the five Quake
sprite types: the model's memory was overwritten or freed while still linked. Two causes are open:

- the emulator: the threaded CPU mode is experimental, and a race between the CPU thread and the emulator's other
  threads can corrupt memory the game wrote; the earlier loads that evening finished, slowly;
- the engine: a sprite model freed or moved by a load while an entity still points at it, the shape of
  CHIM-FRAME-EDGE-EFRAG-CRASH-36 ("R_StoreEfrags: Bad entity type"), which only showed now.

A recording of the hang (90 s, once a second): no reads from the stick after the first second, both Amiberry
threads at 100%.

## Why it was not caught

The emulator presets the gates and smoke tests use have no threaded CPU, and no smoke test loads `dbg aw hors 0`.

## Reproduction

Once so far: on the stick with `cpu_threaded=true`, `dbg aw hors 0`.

## Repair

None yet. The threaded CPU is off again on the stick and in the stick's preset. Next: the same load without it, a
few times (if it never fails, the emulator mode is the cause), and the same load on FS-UAE at 32 MB Fast (if it
fails there, the engine is). If the engine: find which sprite model the entity points at after the load, as for
the efrag crash.

## Verification

`dbg aw hors 0` loads every time on the stick and on FS-UAE.

## Prevention

A smoke hop to `dbg aw hors 0`, and the threaded CPU only after loads are proven with it.

## Related

[CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md).

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
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
