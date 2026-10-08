# STAIRS-SEYDA-WAREHOUSE-32: A spiral stair in the Seyda Neen warehouse tower is blocked

| | |
| --- | --- |
| Reported by | stair walkability gate (development branch) |
| First noticed | 8 October 2026, v0.0.32-dev2 maps |
| Where | Seyda Neen warehouse tower, in_common_tower_thatch (ref 321953) |
| Reproduction | always (gate) |
| Duplicate of | none (family: COLLISION-STAIR-SLOPE-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | medium (a staircase cannot be used) |

## Status: 8 October 2026

Open. Fails the gate (start in solid) after the rule. Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

warehouse, `in_common_tower_thatch` (ref 321953), riser at local 127.0 -7.6 8.2, rise 6.7.

## How it happened

The tower's authored plates had approximate standing bevels; 9 of its flight steps failed. With the stair rule (exact bevels on plate meshes with stairs) 8 pass; one riser still starts in solid.

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

Not yet.

## Verification

Pending: gate result and an in-game check.

## Prevention

The stair walkability gate in the image step.
