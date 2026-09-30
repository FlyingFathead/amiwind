# Recurring stair failure: authored ramps below the walkable-floor cutoff

Found during v0.0.24-rc1 Balmora validation, 30 September 2026.

## What failed

A staircase can have intact visible steps and an open arch, yet stop an ordinary
walking player partway up. Its authored collision surface may be a continuous
ramp. One inspected Balmora ramp has upward unit-normal component
`normal.z = 0.6976600289`, below the engine's former `0.7` walkable-floor cutoff.
It was classified as too steep to stand on, so the movement/support rules could
not consistently climb and remain grounded on it.

The owner report is `stairs1`: XYZ `-410 -586 137`, yaw `4`, pitch `-6`.
The blocking ramp resolves to source reference `19034`, `ex_hlaalu_b_11`, in
the `bm027` exterior sub-cell. The overlap also includes a balcony and a
separate stair object, so the nearest visible stair object alone does not
identify the blocking collision reference.

## Why this recurs

The normal's Z component is the cosine of the surface angle from horizontal.
The old cutoff admitted slopes below approximately 45.573 degrees; this
authored ramp is approximately 45.760 degrees. This is a real classification
mismatch, not evidence that the player is too tall or that the mesh should be
flattened. It is also larger than a rounding-only discrepancy.

Shared architectural meshes repeat the same collision surfaces across many
placements. Similar failures can occur in other towns and interiors. A ramp
may look like discrete steps, and a stair assembled from several references
may inherit its blocking surface from the surrounding building.

Different floor tests must agree. Correcting the main slide/step test while
leaving ground support or arrival placement on the old cutoff can still cause
sliding, sticking, failed placement or inconsistent ascent/descent.

## Correction

The RC1 candidate centralizes the threshold as `AW_WALKABLE_Z = 0.69f` in
`engine/aga/src/quakedef.h`, allowing the inspected ramp with a modest margin
(approximately 46.370 degrees). This is a measured AmiWind movement policy,
not a claim about the original executable's exact maximum slope.

The shared threshold is used by:

- `sv_phys.c`: floor classification and the step-up/step-down decisions.
- `aw_walk.c`: ground support, uphill tangent following and downward support.
- `aw_spawn.c` and `aw_scene.c`: exterior and interior floor placement.

The player hull, race/sex eye heights, FOV, 8.5-unit step height and camera bob
are unchanged. Arch clearance and incorrect convex collision remain separate
diagnoses; accepting a ramp as a floor cannot remove a solid arch obstruction.

## Evidence and limits

| Check | Result |
| --- | --- |
| Before cutoff correction, rebuilt geometry | Normal walking stopped near XYZ `-361 -584 151` |
| After shared cutoff correction | Normal walking reached XYZ `-250 -581 226`, then descended to `-529 -588 142` |
| Movement mode | `3` (ordinary walking) throughout the measured ascent/descent |
| Native run | 241 frames; clean exit; zero surface/edge overflow frames |
| Host movement regression | Inspected slope holds idle, climbs and descends; a steeper unsupported slope still falls |
| Existing host native checks | 43 tests passed after the correction |

Diagnostic positioning was used to stage the starting point. The route itself
used ordinary movement and collision, without jumping or noclip. These results
accept this targeted route only; other reported stairs, arches, doors and new
regions retain their own acceptance gates. Raw coordinates and private build
evidence belong with the specific tested candidate, not an assumed future
binary.

## Future diagnosis and regression procedure

1. Record XYZ, yaw/pitch, race, movement mode and the loaded sub-cell. Reproduce
   from a supported starting point with ordinary walking.
2. Check both ascent and descent, an idle stop on the ramp, and adjacent arch
   clearance. Separate unsupported floor from head/side obstruction.
3. Trace the actual standing hull and identify the blocking reference. Inspect
   its collision mesh as well as the visible stairs. Use `aw_blockers` and
   `aw_dimensions`; retain trace normals at full precision in an offline audit
   or diagnostic log. The percentage normals printed by `aw_blockers` are too
   coarse to distinguish `0.69766` from nearby cutoffs reliably.
4. Compare the upward normal with `AW_WALKABLE_Z`. Inspect every floor/support
   test for a leftover literal cutoff. Do not change player size, FOV or mesh
   shape merely because the symptom occurs beneath an arch.
5. If another authored ramp falls below the shared threshold, measure its
   slope and inspect intended traversal before changing policy. Do not keep
   lowering the cutoff to accommodate walls, malformed hulls or steep roofs.
6. Recheck existing accepted stairs and unsupported slopes after any change.
   Keep the host tests for idle stability, uphill/downhill movement, cliffs,
   jumping and swimming. Complete native route tests for affected placements.

`tests/aga_walk_test.c` includes the measured ramp slope and a steeper rejection
case. `tools/audit_walkability.py` uses the matching `player_hull.WALKABLE_Z`;
`tests/test_walkability_audit.py` checks classification and agreement with the
native constant. The offline result does not substitute for native movement.

See [player movement](PLAYER_MOVEMENT.md),
[RC1 investigation](INVESTIGATION-v0.0.24-rc1.md) and
[conversion recipes](CONVERSION_RECIPES.md).
