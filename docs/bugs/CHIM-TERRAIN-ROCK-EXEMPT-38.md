# CHIM-TERRAIN-ROCK-EXEMPT-38: Terrain-named placed rocks bypass experimental buried-surface clipping

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38 |
| Where | Experimental CHIM terrain clipping |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | medium: Buried render geometry remains and expected memory savings are absent. |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | unknown |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Observed in an unshipped experimental build and mutable inspector; no single release commit identifies both. |
| Platform or emulator | not in game (Observed in inspector and experimental compiler output.) |

<!-- END GENERATED FACTS -->

## Symptom

Buried placed geometry remains visible from beneath the terrain despite enabling the clipping workflow.

## Where

Experimental CHIM terrain clipping; exterior cell (10,1).

## How it happened

The experimental compiler excluded every placed mesh with a terrain_ filename prefix, conflating rock props with authoritative LAND.

## Why it was not caught

Earlier coverage did not combine collision-only sprite diagnostics and terrain-named placed rocks with this scene.

## Reproduction

Load a converted scene with these cases, enable terrain preview and compare buried object counts. Compile the same cell with experimental clipping enabled.

## Repair

Apply terrain clipping to placed props, retain the separate LAND receiver and unchanged collision; include terrain and placement context in cache fingerprints. Shared removals require burial at every placement.

## Verification

Isolated cell (10,1) compile passed; 59 collision models match baseline. Active peak saves 34,112 bytes and load peak saves 32,864 bytes. Native terrain-contact and matched original comparison remain pending.

The converter now has an opt-in `clip_to_terrain` frame setting. It uses the
authoritative ground triangles, preserves the original collision pieces and
occluder inputs, and includes terrain and every placement pose in the variant
cache key. It rejects simultaneous model cutting. Default builds remain
unchanged pending wider validation. Synthetic regression coverage checks a
terrain-named prop, shared exposed placement retention, empty-placement
rejection and collision classification before and after clipping.

## Prevention

Use explicit geometry roles, preserve shared asset identity, and record compiled face counts, collision equality and resident-byte changes independently.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): A Dwemer ruin at Azura's Coast is drawn in the wrong shape
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

<!-- END GENERATED CATEGORY -->
