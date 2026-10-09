# NPC-TARGET-REDUNDANT-31: NPC targeting runs 2-4 times per frame and checks every NPC

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | engine NPC target search (AW_SceneDraw, AW_NPCTarget) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | medium: Per-frame cost: several searches testing every NPC each frame, measured in Balmora. |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; fixed in source (FPU fixes branch, not yet released). Measured with the new
per-frame counters (`dbg fpucount`).

## Symptom

The scene draw calls the NPC target search 2-4 times per frame; each call traces twice and
computes direction vectors for every NPC on the server, visible or not.

## Where

`engine/aga/src` AW_SceneDraw and AW_NPCTarget.

## How it happened

Each caller (target name, travel target, hints, speaker) asks for the target separately.

## Why it was not caught

No per-frame call counters.

## Reproduction

Count AW_NPCTarget calls per frame in Balmora.

## Repair

The scene's target lookup is computed once per host frame (stamped with
`host_framecount`, the way Quake stamps `visframe`) and reused while the player,
view angles and edict table are unchanged. Inside the search, an NPC farther from
the eye than the ray length plus the sum of its largest bound extents is skipped
before its direction vectors are computed.

## Verification

v0.0.31 image, same pose and route, emulator with JIT, per frame (median of the
one-second averages):

| Pose | Before: target searches / NPCs tested | After |
| --- | --- | --- |
| Balmora (-20088 -14638) | 5 / 70 | 1 / 0 |
| Seyda Neen spawn | 5 / 40 | 1 / 1 |

Direction-vector calls per frame fell from 93 to 19 (Balmora) and 168 to 85
(Seyda Neen). Host tests: `aga_npc_contact_test.c` (precheck skips a far NPC
without direction vectors), `aga_scene_test.c` (each call a new frame).

## Prevention

`dbg fpucount` prints the per-frame counts (`npct`, `npcscan`, `npctest`).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

Related bugs in other categories:

- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)

<!-- END GENERATED CATEGORY -->
