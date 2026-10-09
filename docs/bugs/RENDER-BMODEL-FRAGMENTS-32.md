# RENDER-BMODEL-FRAGMENTS-32: Brush models spanning many terrain leaves are clipped face by face down the terrain BSP

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | engine r_bsp.c brush models clipped down the terrain BSP |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: Deep BSP walks take 67-82 percent of Balmora render time. |
| Family | Rendering cost and visibility (`render-performance`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan. Hypothesis from the source; fragment counts not yet measured.

## Symptom

A brush model whose box crosses several world leaves takes the clipped path: each face is
clipped recursively down the terrain BSP and drawn as fragments per leaf. Converted buildings
mostly touch many leaves (362 of 590 in Balmora touch more than 16), so their faces may
fragment several times over; one-leaf models take the cheap path.

## Where

`engine/aga/src/r_bsp.c` (`R_RecursiveClipBPoly`, `R_DrawSolidClippedSubmodelPolygons`), `r_main.c` brush model loop.

## How it happened

Quake's brush models were small and sat in few leaves.

## Why it was not caught

Fragments per face are not counted.

## Reproduction

Count faces submitted against fragments emitted at fixed Balmora cameras.

Measured with renderer counters (8 October 2026, ten cameras): the fragments-per-face part is
wrong (1.03-1.59 fragments per clipped face). The cost is the depth of the walk: each clipped face
visits 27-52 world-BSP nodes in Balmora (up to 233,867 node visits per frame), transforming each
node's plane every time. That path is 67-82 % of render time in Balmora and 39-59 % in Seyda
Neen. The one-leaf path is almost unused in Balmora (0-8 models in view).

## Repair

Measure first; the world streamer's simple grid world puts each model in one or two leaves.

## Verification

Pending.

## Prevention

Fragment counters in the performance overlay.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
