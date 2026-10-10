# CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine frame time on a slow CPU: CHIM Balmora exterior (placements, host frame) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Not a CHIM regression: CHIM is 1.5-2.6x faster than legacy on the slow preset; about 1 frame per second either way (relative). |
| Family | Rendering cost and visibility (`render-performance`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the CHIM world receipt records no commit (CHIM-RECEIPT-COMMIT-33) |
| Build note | measured in the CHIM preview engine on the slow accelerator preset, 9 October 2026 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Not a CHIM regression: CHIM is faster than legacy on the x14 preset in the preview-engine run
(same session, same poses). Slow-hardware optimisation deferred to after v0.0.33 (owner decision).
The measurement used the private CHIM preview engine (0d8bf4f, world format 0.4); the run with
the release-line engine was stopped by the owner before it produced verified poses.

## Symptom

On the slow accelerator preset (FS-UAE, interpreted 68040 with FPU, cycle-exact,
`uae_cpu_multiplier 14` = 49.7 MHz) Balmora on CHIM draws about one frame per second. The same
image with the normal JIT preset draws 20-25 frames per second.

Measured 9 October 2026 (FS-UAE 3.1.66, Docker, fresh boot-disk copies, noon, headlamp off,
`aw_rcount 2`; per-second samples, medians; emulator numbers are relative):

| Preset | Arrival | Crossing 1 | Crossing 2 | Crossing 3 | Walk |
| --- | --- | --- | --- | --- | --- |
| JIT (normal) | 24.5 fps, 40.7 ms | 23.9 fps, 41.7 ms | 19.8 fps, 50.4 ms | 23.1 fps, 43.3 ms | 24.7 fps, 40.5 ms |
| x14 (49.7 MHz) | 0.8 fps, 1142 ms | 0.9 fps, 1020 ms | 0.8 fps, 1127 ms | 0.8 fps, 1188 ms | 0.9 fps, 1094 ms |
| x7 (24.8 MHz) | 0.4 fps, 2175 ms | 0.5 fps, 1910 ms | 0.4 fps, 2146 ms | 0.4 fps, 2277 ms | 0.4 fps, 2072 ms |

Chunk crossings add up to about 0.3 s to the worst frame at x14. The emulated 68040's integer
timing looks plausible (about one cycle per simple instruction); its `MULU.L` and FPU timings
look optimistic, so a real card is likely not faster than these numbers.

### Legacy against CHIM, same session (9 October 2026)

Slow preset x14, the benchmark cameras of HARDWARE-BENCHMARK.md, noon, headlamp off,
`aw_rcount 2`, medians of 10 frames. A = legacy v0.0.32 Balmora (`chim_towns 0` on the preview
disks), B = CHIM, A2 = legacy again (drift control). The 3D view time is deterministic (A and A2
agree to the millisecond); the frame time includes 60-250 ms of remote-console file traffic of the
test session (measured with the remote console off and on RAM:).

| Camera | A frame / view ms | B frame / view ms | A2 frame ms | A clip-walk nodes | B clip-walk nodes | B brush faces tested |
| --- | --- | --- | --- | --- | --- | --- |
| Balmora 1 | 4,135 / 3,948 | 1,614 / 1,359 | 4,124 | 233,886 | 39,126 | 8,429 |
| Balmora 2 | 2,352 / 2,086 | 1,358 / 1,112 | 2,236 | 93,131 | 24,510 | 5,496 |
| Balmora 3 (arrival) | 2,134 / 1,595 | 1,313 / 679 | - (wrong pose) | 84,748 | 20,453 | 4,826 |
| Balmora 4 | 2,289 / 2,038 | 1,106 / 913 | 2,234 | 97,746 | 20,731 | 4,340 |
| Balmora 5 | 2,041 / 1,820 | 1,059 / 828 | 2,029 | 79,906 | 21,918 | 4,428 |

With the remote console off (engine `frame-stalls.csv`): CHIM camera 3 1,053-1,080 ms,
camera 4 993-1,042 ms, legacy camera 3 1,905-2,009 ms. CHIM is 1.5-2.6 times faster per frame.

### Where the time goes (CHIM, x14)

- Brush-model placements (`R_DrawBEntitiesOnList`, clipped path): 439-921 ms, 65-72 percent of
  the 3D view. Fit over ten views: about 12 microseconds per world-BSP node visited by
  `R_RecursiveClipBPoly` and 75-120 per fragment emitted. CHIM walks 4-6 times fewer nodes than
  legacy (RENDER-BMODEL-FRAGMENTS-32), but no placement takes the one-leaf path.
- Edge scan and span drawing: 157-266 ms (spans alone 75-155 ms).
- Fog and day-night sky pass: 146-170 ms (RENDER-FOG-PASS-COST-33).
- Server frame: 226 ms at camera 3, 12 ms at camera 4 (SERVER-FRAME-ARRIVAL-33).
- 2D, HUD and chunky-to-planar: about 80-150 ms; sound mixing under 10 ms; world (terrain) 6-11 ms;
  CHIM streaming work under 2.5 ms (longest frame per second).
- Knobs measured at cameras 3 and 4: `aw_drawdistance 300` saves 250-320 ms; `viewsize 60` 130-170
  ms; `viewsize 80` 40-65 ms; `r_drawflat 1` 50-220 ms; `d_mipcap 2` nothing at a standing camera
  (no surface-cache rebuilds in Balmora).
- Legacy references: Seyda Neen arrival 2.1 s (surface cache 914 blocks a frame,
  RENDER-SURFCACHE-THRASH-32); prison ship intro 2.5 s (798 blocks, 2.3 MB a frame; `d_mipcap 2`:
  1.6 s, `d_mipcap 1`: 2.0 s). "Intro speech: chargenname1 (6543 ms)" is the clip length, not a
  load time.

## Where


Engine frame on a CHIM exterior: brush-model placements (`R_DrawBEntitiesOnList`, clipped path),
edge scan and span drawing, and the host frame outside `R_RenderView`.

## How it happened

CHIM was profiled with the JIT preset only; the frame budget on a 50 MHz 68040 was never set.

## Why it was not caught

No cycle-exact frame-time check of a CHIM town existed before the preview went out.

## Reproduction

Slow preset at x14, `dbg tp -21800 -12300` into Balmora, `aw_rcount 2`, read the rcount line.

## Repair

Deferred to after v0.0.33. Candidates, Quake first: (1) placements that sit in one leaf of a
shallow chunk BSP take Quake's one-leaf path (`R_DrawSubmodelPolygons`, 1/z sorting) instead of
the BSP clip walk, or the walk caches plane distances per vertex (up to half of the brush-model
time); (2) fog and day-night sky folded into the colormap stage instead of a per-pixel pass
(150-210 ms); (3) a slow-CPU preset of existing settings (draw distance 300, view size 80-90,
`d_mipcap 1-2` indoors), 25-40 percent.

## Verification

Pending.

## Prevention

Pending: a cycle-exact frame budget check at fixed Balmora poses.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

Related bugs in other categories:

- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040

<!-- END GENERATED CATEGORY -->
