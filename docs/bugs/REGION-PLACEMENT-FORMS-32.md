# REGION-PLACEMENT-FORMS-32: The same placement is stored in different forms from region to region

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | region converters (overlap handling) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: One placement is stored in different forms across region maps, so regions disagree on the same object. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

One object can appear as render-only in one region map, as collision only (no faces) in
another, or with its collision clipped to the core plus margin in a third.

## Where

The region converters (overlap handling).

## How it happened

Each region decides its own overlap treatment.

## Why it was not caught

Regions are checked one at a time.

## Reproduction

Compare one placement across the 64 Balmora maps.

## Repair

Superseded by the world streamer (each placement stored once); document for the transition.

## Verification

Pending.

## Prevention

A placement consistency check across regions.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

<!-- END GENERATED CATEGORY -->
