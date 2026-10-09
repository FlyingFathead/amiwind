# VF-VIS-LUMP-32: Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Open-world terrain maps, visibility lump |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: About 21 percent of open-world map bytes (0.77 GB) are visibility data that culls little. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py). Estimated from a 1-in-10 sample.

## Symptom

About 21 % of the open-world (`vf`) map bytes, roughly 0.77 GB, are visibility lumps, although
visibility culls little outdoors (TOWN-VIS-OCCLUSION-31).

## Where

Open-world terrain map builds (vis pass).

## How it happened

Every map runs vis.

## Why it was not caught

Bytes per lump were not reviewed.

## Reproduction

Sum lump sizes over the vf maps.

## Repair

Superseded by the world streamer (heightfield terrain without vis); until then,
measure whether a minimal visibility lump changes anything.

## Verification

Pending.

## Prevention

Lump byte report per map family.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

Related bugs in other categories:

- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
