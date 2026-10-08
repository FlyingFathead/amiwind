# BUILD-SEYDA-HULL2-32: From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt). Release blocker for the public builder (MANDATORY from-scratch rule).

## Symptom

The builder's `bsp` stage stops: qbsp reports "Clipnode count exceeds bsp 29 max (68655 >
65520)" for hull 2 of the Seyda Neen full-town standing collision map. The builder never uses
hull 2, but qbsp aborts on it. v0.0.26 and v0.0.27 pass; v0.0.28 to today fail identically.

## Where

`tools/prepare_quake.py` (`town_ground_triangles`, `required_edge_samples` added in v0.0.28:
69 more terrain brushes) and the qbsp call for that map.

## How it happened

v0.0.28 added edge samples to the town ground; hull 2 crossed the limit.

## Why it was not caught

No from-scratch build was run between releases; release images were patched up from older images.

## Reproduction

Run `tools/build.py` from scratch with your own data.

Cost signals from the fix: the v0.0.28 edge samples grow the full-town standing hull 1 from
19,156 to 35,292 nodes (+84 %), and the full-town map's hull 0 is at 31,162 of 32,767 nodes (95 %).

## Repair

Fixed in source (v0.0.32-dev, a97861b): the engine uses hulls 0 and 1 only (hull 2 is never
traced: world.c selection rule, every QuakeC and engine trace box fits hull 1). The standing-hull
intermediate is compiled as BSP2 (32-bit indices, no overflow) and only its hull 1 is grafted;
`rebuild_world_hull` is the one standing-hull path for every map (the region converter's inline
copy now calls it). The graft uses the engine's real limit (65,520) with unsigned 16-bit
children, as the engine reads them. A new gate, `check_engine_hulls`, fails a map only when
hull 0 or 1 breaks an engine limit. The v0.0.28 edge samples are kept; maps that already fit
are byte-identical. Residual risk: each map's own base compile is still BSP29 with all hulls.

## Verification

From-scratch build (25 min 38 s) passes `bsp`: the full-town Seyda Neen map has 55,632
clipnodes and 31,162 nodes, within the engine limits. Tests: `tests/test_engine_hulls.py`
(engine contract, synthetic grafts, BSP2/BSP29 intermediates graft to identical bytes).

## Prevention

A periodic from-scratch build (mandatory project rule) and a builder test for hull limits.
