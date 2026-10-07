# SEYDA-BLOCK-31: invisible obstacle blocks the path on a Seyda Neen slope

## Status: 7 October 2026

Open. Owner report from the v0.0.31-dev3 playtest; cause unknown.

## Symptom

Walking forward toward an NPC between a rock and a building, the player is
stopped by something that cannot be seen ("a terrain thing ... can't move
through there forward towards that figure").

## Where

Seyda Neen, global XYZ -11548 -71200 278 (local -71 119 69), facing south-west
(244), the figure ahead in a gap between a rock face and a wall.

## How it happened

Unknown. Candidates: a collision hull of a nearby rock or wall wider than its
visible shape, a terrain collision step, or an invisible object.

## Why it was not caught

Unknown until the cause is found.

## Reproduction

v0.0.31-dev3: `dbg tp -11548 -71200`, face 244, walk forward.

## Repair

Not started: measure with `dbg blockers` / `dbg probe` at the spot and compare
with OpenMW.

## Verification

Pending.

## Prevention

Pending the cause.
