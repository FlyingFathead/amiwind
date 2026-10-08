# COLLISION-SEYDA-PREVIEW-BYPASS-32: The legacy Seyda Neen preview builds its own convex collision

| | |
| --- | --- |
| Reported by | collision census (development branch) |
| First noticed | 8 October 2026 |
| Where | tools/prepare_bsp.py (legacy Seyda Neen preview) |
| Reproduction | always (static check) |
| Duplicate of | none |
| Persists in | v0.0.32 (shipped images use the recorded Seyda stage) |
| Severity | low (no shipped map built by it) |

## Status: 8 October 2026

Open. Found while checking that every converter uses the shared collision function (COLLISION-STAIR-SLOPE-32), 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

The stair rule cannot reach the collision of the legacy Seyda Neen preview map.

## Where

`tools/prepare_bsp.py` (the `bsp` stage).

## How it happened

It writes one 14-direction convex brush per model into `seyda.map`, outside `mesh_geometry.collision_pieces`, so the stair rule does not apply there. Shipped images use the recorded Seyda Neen stage instead; the static test lists this file as the only exception.

## Why it was not caught

No test looked at it.

## Reproduction

Read the file named in Where.

## Repair

Not yet.

## Verification

Pending.

## Prevention

Tests over the builder sources.
