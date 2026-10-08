# Renderer counters (`dbg rcount`)

Counts are the main currency for comparing builds: they do not depend on the emulator
profile or the host PC, while frame times do
([BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md)). The engine counts what its
renderer does every frame and reports per-frame averages once a second.

## Using it

| Command | Effect |
| --- | --- |
| `dbg rcount 1` (`aw_rcount 1`) | once a second: a `rcount ...` line in the console, and the same line in the remote state file |
| `dbg rcount 2` | the state file line only (no console text over the measured view) |
| `dbg rcount 0` | off (default; nothing is timed) |

With the remote console on (`aw_remote 1`, see the headless test notes) the state file
`state.txt` carries the latest line as `rcount ...`.

## The line

```
rcount 23 frames fps10 222 | bm 654/540/80/76/4 bf 9470/4584 cf 4512 frag 6222/233867 lf 72 wf 654
  | q 6948/4764/1042 e 16737/306/9603 s 4765 sp 4913 | sc 0/0 scb 0/0 al 1
  | us 600/35100/5300/3600/300/42900/45000 pk 60700
```

All figures are averages per frame over the last second, except `frames`, `fps10`
(frames per second times ten) and `pk` (slowest frame).

| Field | Meaning |
| --- | --- |
| `bm` passes/visible/in view/clipped/one leaf | brush model passes considered in `R_DrawBEntitiesOnList` (entities plus render-range views); passed the distance/fog test; not fully outside the view frustum; drawn on the clipped path (box spans world nodes); drawn on the one-leaf path |
| `bf` tested/front | brush model faces given the backface test, and those facing the camera |
| `cf` | front faces on the clipped path (`R_DrawSolidClippedSubmodelPolygons`) |
| `frag` fragments/nodes | fragments emitted by `R_RecursiveClipBPoly` (calls of `R_RenderBmodelFace`) / world BSP nodes it visited |
| `lf` | front faces on the one-leaf path (`R_DrawSubmodelPolygons`) |
| `wf` | world faces sent to `R_RenderFace` |
| `q` faceclip/poly/drawn | Quake's own `r_speeds` counts: faces clipped, faces that reached the edge list, surfaces drawn |
| `e` new/cached/used | edges emitted, edges reused from the edge cache, edge records in use |
| `s`, `sp` | span surfaces in use, spans generated |
| `sc` allocations/bytes | surface cache allocations (`D_SCAlloc`) |
| `scb` blocks/texels | surface cache blocks drawn (`D_CacheSurface` misses) and their texels |
| `al` | alias models drawn (`r_amodels_drawn`, the hands included) |
| `us` | microseconds: `R_RenderWorld` / brush models (`R_DrawBEntitiesOnList`) / `R_ScanEdges` including span drawing / `D_DrawSurfaces` alone / alias models (`R_DrawEntitiesOnList`) / the whole `R_RenderView` / the host frame |

The counters are plain integer increments, like Quake's `c_faceclip` and
`r_polycount`; the timers run only while `dbg rcount` is on. The output uses integer
formatting only.

## Ten fixed cameras (8 October 2026)

v0.0.32-dev engine (`dbg rcount`) overlaid on a copy of the v0.0.31 image, playtest
profile (JIT, unlimited speed, see [FS-UAE-PLAYTESTING.md](../FS-UAE-PLAYTESTING.md)),
noon, day/night cycle off, headlamp off, medians of 17-19 one-second lines per
camera. Camera positions: [HARDWARE-BENCHMARK.md](../HARDWARE-BENCHMARK.md#frame-time-in-the-game).
Counts were identical in a repeat run and in the no-JIT and cycle-approximate
benchmark profiles; the times are relative to this profile only (the same cameras at
the benchmark profile, 2.7-8.1 seconds per frame: [FS-UAE-PLAYTESTING.md](../FS-UAE-PLAYTESTING.md#benchmark-profile)).

| Camera | bm passes/visible/in view/clipped/one leaf | front faces | clipped-path faces | fragments (per face) | BSP nodes visited (per face) | one-leaf faces | world faces | edges new | spans | surface cache blocks drawn (texels) | brush models ms | scan ms | view ms | frame ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Balmora 1 | 654/540/80/76/4 | 4,584 | 4,512 | 6,222 (1.38) | 233,867 (51.8) | 72 | 654 | 16,737 | 4,913 | 0 | 35.1 | 5.3 | 42.9 | 45.0 |
| Balmora 2 | 590/459/60/52/8 | 3,549 | 3,366 | 4,849 (1.44) | 93,122 (27.7) | 183 | 472 | 13,429 | 3,923 | 0 | 15.3 | 4.4 | 22.9 | 24.3 |
| Balmora 3 | 634/623/44/44/0 | 2,623 | 2,623 | 3,975 (1.52) | 84,748 (32.3) | 0 | 490 | 7,434 | 3,498 | 0 | 13.2 | 3.0 | 17.3 | 21.4 |
| Balmora 4 | 555/350/45/39/6 | 2,522 | 2,386 | 3,784 (1.59) | 97,745 (41.0) | 136 | 545 | 12,001 | 4,278 | 0 | 18.1 | 4.8 | 26.4 | 28.3 |
| Balmora 5 | 512/191/43/41/2 | 2,963 | 2,955 | 4,354 (1.47) | 79,907 (27.0) | 8 | 498 | 12,640 | 3,897 | 0 | 15.5 | 4.2 | 23.0 | 24.4 |
| Seyda Neen 1 | 645/642/154/84/70 | 6,736 | 5,733 | 5,998 (1.05) | 18,997 (3.3) | 1,003 | 279 | 10,460 | 5,853 | 914 (764,337) | 7.4 | 8.5 | 19.2 | 22.1 |
| Seyda Neen 2 | 592/591/92/79/13 | 5,305 | 4,895 | 5,098 (1.04) | 16,713 (3.4) | 410 | 267 | 9,985 | 2,325 | 0 | 6.3 | 3.1 | 12.0 | 15.1 |
| Seyda Neen 3 | 907/898/190/138/52 | 10,844 | 9,358 | 9,725 (1.04) | 28,456 (3.0) | 1,486 | 303 | 24,017 | 3,917 | 625 (552,975) | 12.4 | 8.1 | 23.0 | 25.1 |
| Seyda Neen 4 | 770/756/130/130/0 | 6,642 | 6,642 | 6,911 (1.04) | 33,555 (5.1) | 0 | 247 | 14,514 | 2,903 | 0 | 9.5 | 3.4 | 16.2 | 17.7 |
| Seyda Neen 5 | 887/863/145/52/93 | 10,039 | 8,642 | 8,921 (1.03) | 30,909 (3.6) | 1,397 | 345 | 20,701 | 5,118 | 0 | 13.3 | 6.6 | 23.4 | 25.3 |

What the table shows:

- Brush models dominate the view: 67-82 % of `R_RenderView` time in Balmora, 39-59 %
  in Seyda Neen. The world (terrain) itself costs under 1 ms.
- Almost every visible brush model takes the clipped path (Balmora: 39-76 of 43-80 in
  view). Clipped faces split into few fragments (1.03-1.59 per face), but each face
  walks far down the world BSP before it reaches a leaf: 27-52 node visits per face in
  Balmora (up to 234,000 visits per frame at Balmora 1), 3-5 in Seyda Neen. Every visit
  transforms the node plane into model space and tests every edge of the face. The
  cost is the depth of the descent, not the number of fragments
  ([RENDER-BMODEL-FRAGMENTS-32](../bugs/RENDER-BMODEL-FRAGMENTS-32.md)).
- The surface cache is rebuilt every frame at Seyda Neen 1 and 3: 914 and 625 blocks
  (0.76 and 0.55 million texels) drawn and allocated each frame at a fixed camera, so
  the cache is smaller than what those views need and evicts its own blocks. Balmora
  needs no surface cache work once the view has settled.
- The edge cache is used in Balmora (190-350 edges reused per frame) and not in
  Seyda Neen (0).
