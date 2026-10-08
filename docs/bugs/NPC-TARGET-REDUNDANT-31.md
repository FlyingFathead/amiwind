# NPC-TARGET-REDUNDANT-31: NPC targeting runs 2-4 times per frame and checks every NPC

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
