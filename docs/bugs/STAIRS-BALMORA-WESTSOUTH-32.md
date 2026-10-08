# STAIRS-BALMORA-WESTSOUTH-32: A Hlaalu hall staircase in a Balmora interior has no clear foot

| | |
| --- | --- |
| Reported by | stair walkability gate (development branch) |
| First noticed | 8 October 2026, v0.0.32-dev2 maps |
| Where | Balmora interior bmwestsouth, in_hlaalu_hall_stairsl |
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

bmwestsouth, `in_hlaalu_hall_stairsl` (ref 384371), riser at local 1048 1024 3809.3, rise 8.0; the solid at the foot belongs to ref 384326.

## How it happened

The standing hull at the visible foot of the flight is inside the collision of a neighbouring piece (384326). The stair's own authored collision is a 45-degree ramp (walkable at the 0.69 limit). The same model in bmeastguard passes after the gate's box-clearance check.

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
