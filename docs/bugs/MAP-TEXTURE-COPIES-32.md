# MAP-TEXTURE-COPIES-32: Every map carries its own copy of every texture it uses

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Map converters and BSP texture lump |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Textures stored in hundreds of maps, about 1.4 GB island-wide. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

Quake maps embed their textures, so the same texture is stored in hundreds of maps:
about 1.4 GB island-wide against a few MB if each were stored once. Per-map names
(`surfaceN`) hide identical textures; only a pixel hash finds them.

## Where

The converters and the BSP texture lump.

## How it happened

Quake's map format embeds textures.

## Why it was not caught

Per-map size checks only.

## Reproduction

Hash texture pixels across all maps.

## Repair

Not yet: a shared texture store loaded once (part of the world streamer).

## Verification

Pending.

## Prevention

The builder reports texture bytes stored more than once.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

Related bugs in other categories:

- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)

<!-- END GENERATED CATEGORY -->
