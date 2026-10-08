# STAIRS-SEYDA-LIGHTHOUSE-32: Seyda Neen lighthouse stairs are blocked (outside and inside)

| | |
| --- | --- |
| Reported by | stair walkability gate (development branch) |
| First noticed | 8 October 2026, v0.0.32-dev2 maps |
| Where | Seyda Neen lighthouse, outside (sn012) and inside |
| Reproduction | always (gate) |
| Duplicate of | none (family: COLLISION-STAIR-SLOPE-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | medium (stairs cannot be used) |

## Status: 8 October 2026

Open. Exterior fixed by the rule once Seyda Neen is regenerated (CHIM); interior step fails the gate. Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

Exterior sn012, `ex_common_lighthouse` (ref 114026): 5 steps at local about -244..-313 -585..-607 224..261, rises 3.8-6.7, blocked by vertical collision. Interior lighthouse, `in_common_lighthouse` (ref 129152): riser at local 45.7 16.5 -131.3, rise 4.1.

## How it happened

Exterior: the lighthouse collides with its visual mesh through convex proxies; a vertical railing or wall arc closes the spiral treads. The stair rule changes this model (authored plates), but v0.0.32 ships the recorded Seyda Neen stage (BUILD-SEYDA-REGEN-30), so the shipped maps keep the old collision; the gate reports them without failing. Interior: two steps failed; with the rule one still starts in solid.

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
