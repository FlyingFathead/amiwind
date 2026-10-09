# CONVERT-VARIANTS-32: Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Scenery converters (one model per mesh, scale and tilt) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: 4 to 7 times more models than meshes; storage and load cost. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

The converter makes a separate model for every (mesh, scale, tilt) combination: 9,586
exterior variants of 1,402 meshes and 9,315 interior variants of 2,957 meshes.

## Where

The scenery converters (variant keys).

## How it happened

Quake collision hulls cannot scale or tilt, so each combination was baked.

## Why it was not caught

Counted per map, never across the island.

## Reproduction

Count distinct variant keys in the whole-world estimate.

Review note (8 October 2026): Morrowind placements have continuous scale (0.5-2.0), so baked
scale defeats sharing for rocks and flora; histogram the scales per mesh first, then quantize
or scale at run time (collision planes stored unexpanded and expanded per scale at load).

Census (8 October 2026, whole island): tilt, not scale, causes the explosion. Vvardenfell
exteriors have 33,076 variants (the 9,586 above was extrapolated from Balmora). Scale is
already in 0.01 steps (151 values) and quantizing it gains at most 1.17x; tilt at run time
gives 3.9x, scale and tilt at run time 23.5x (1,405 meshes). About 811 placements tilted by
less than one degree still count as tilted variants.

CHIM Balmora build (8 October 2026): 531 variants of 226 meshes (2.35 per mesh), 87 % of CHIM bytes.
Also: model bytes depend on the first placement's yaw for untilted variants (yaw float noise), so
otherwise identical variants do not deduplicate; the legacy builder behaves the same.

## Repair

Not yet: scale and tilt at run time for drawing (one geometry per mesh); keep baked hulls only where
collision needs them.

## Verification

Pending.

## Prevention

The builder reports variants per mesh.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

<!-- END GENERATED CATEGORY -->
