# CHIM-TERRAIN-HULL-BEVELS-33: A standing box rests above the ground at convex CHIM terrain edges

## Status: 8 October 2026

Open: fixed in source on the CHIM branch (v0.0.33-chim-format, 057a37c), not merged, not shipped.
Found by the CHIM engine native test on a world format 0.4 world.

## Symptom

A standing box dropped near a convex terrain edge (a ridge between terrain tiles of different
slope) comes to rest above the highest ground under it. The engine native test measured 216
border samples: 0 below the ground (the format 0.4 seam works), 72 above it, by at most 8.07 local
units, on slopes of 90/128.

## Where

CHIM terrain collision pieces (`tools/chim/`): the standing-hull expansion of the terrain prisms.

## How it happened

The terrain prisms are expanded for the standing box with `standing_planes(exact=False)`, which
adds no edge bevels. Without bevels the expanded hull bulges out at convex edges, so the box is
held up before it touches the ground. Quake's `qbsp` (`ExpandBrush`) adds edge bevels when it
expands brushes, so legacy maps do not float.

## Why it was not caught

The validator's seam check only tests that the space one box height above the ground is empty,
which passes even when the box rests well above the ground.

## Reproduction

The CHIM engine native test: drop a standing box at the border samples of a format 0.4 world and
compare its resting height with the highest ground under it.

## Repair

On the CHIM branch (057a37c): each terrain piece is the exact Minkowski sum with the standing box
(`standing_planes` exact, as `ExpandBrush` bevels brushes), and the validator's seam check tests
0.25 units either side of the stand height, so a hull that holds the box above the ground fails.
Contents only: the binary layout and hull contract are unchanged, so the format stays 0.4.
Balmora: 5.1 KB of routed clipnodes per chunk (was 4.1), 19.9 clipnode visits per point test
(95th percentile 30), 0 validator failures. The engine test's bound goes from 12 to 0.25 units.

## Verification

`tests/test_chim_hull.py` `test_without_edge_bevels_the_box_rests_above_ridges` (the bevel-less
hull fails the tightened check). Pending: merge, and the engine native test within 0.25 units at
every border sample.

## Prevention

The tightened validator seam check and the 0.25-unit bound in the engine test.
