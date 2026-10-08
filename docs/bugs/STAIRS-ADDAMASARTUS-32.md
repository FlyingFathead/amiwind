# STAIRS-ADDAMASARTUS-32: A low step in the Addamasartus cave is blocked

| | |
| --- | --- |
| Reported by | stair walkability gate (development branch) |
| First noticed | 8 October 2026, v0.0.32-dev2 maps |
| Where | Addamasartus cave, in_moldcave_09 (ref 89756) |
| Reproduction | always (gate); in-game effect not yet checked |
| Duplicate of | none (family: COLLISION-STAIR-SLOPE-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | low (a 1-unit step) |

## Status: 8 October 2026

Open. Fails the gate (blocked). Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

addamasartus, `in_moldcave_09` (ref 89756), riser at local 247.8 421.1 35.9, rise 1.0.

## How it happened

The walk is blocked by the cave collision just past a 1-unit step (surface 6.6 degrees). May be the cave proxy over a lip rather than a staircase; needs an in-game look.

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
