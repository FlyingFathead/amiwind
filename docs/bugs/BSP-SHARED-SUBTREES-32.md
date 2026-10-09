# BSP-SHARED-SUBTREES-32: Converted maps share node subtrees between submodels; naive tree walks explode

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Converter output (submodel node trees) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Shared node subtrees make naive tree walks explode; a tooling hazard, not a game fault. |
| Family | World storage and duplication (`world-storage`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

The converter's submodel node trees share subtrees. A tool that walks them without tracking
visited nodes repeats work exponentially (a measurement script was killed for running out of
memory).

## Where

Converter output (submodel node trees); any tool walking them.

## How it happened

Subtree sharing saves space.

## Why it was not caught

Not documented.

## Reproduction

Walk every submodel tree of a converted map without a visited set.

## Repair

Document it; tools that walk node trees track visited nodes.

## Verification

Pending.

## Prevention

A test map with shared subtrees for tree-walking tools.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

Related bugs in other categories:

- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)

<!-- END GENERATED CATEGORY -->
