# INTERIOR-HULLS-HEAVY-32: Interior collision hulls are bigger than the interior geometry they belong to

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | interior collision hulls (tools/mesh_geometry.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Interior collision is about 1.6 times the drawn bytes and the largest kind of world data. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py).

## Symptom

Interior architecture pieces carry about 1.6 times their drawn bytes in collision (hollow shells
with exact bevels). Interior hulls are the largest single kind of world data in the streamer
estimate: about 479 MB with the recommended policy, 512 MB with today's rules.

## Where

`tools/mesh_geometry.py` collision parts for interior meshes.

## How it happened

Exact hollow-shell collision per piece.

## Why it was not caught

Collision bytes were never compared with drawn bytes.

## Reproduction

Run the census disk breakdown.

## Repair

Not yet: simpler collision for interior pieces (merged or convex parts within a tolerance),
measured against getting stuck.

## Verification

Pending.

## Prevention

The census reports hull bytes per class.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

<!-- END GENERATED CATEGORY -->
