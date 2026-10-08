# STAIRS-BALMORA-B01-32: A Balmora Hlaalu house staircase cannot be approached from below

| | |
| --- | --- |
| Reported by | stair walkability gate (development branch) |
| First noticed | 8 October 2026, v0.0.32-dev2 maps |
| Where | Balmora bm020, ex_hlaalu_b_01 (ref 41499) |
| Reproduction | always (gate) |
| Duplicate of | none (family: COLLISION-STAIR-SLOPE-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | medium (a staircase cannot be used) |

## Status: 8 October 2026

Open. Fails the gate (start in solid). Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

bm020, `ex_hlaalu_b_01` (ref 41499), riser at local 705.6 -926.0 75.1 (heading east), rise 8.0.

## How it happened

The standing hull is solid above the stair foot from about 8 units before the riser (standing origin blocked up to z 135) where the visible approach is open (floor at 67.1, nothing above). The model is on Balmora's hand-made surface list (authored plates, exact bevels); its point collision is the authored 45-degree ramp. Cause of the solid band not yet known.

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
