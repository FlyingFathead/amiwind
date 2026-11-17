# WEDGE-TRAP-24: wedge1: the player is trapped at -225,348,131

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 30 September 2026, in v0.0.24-rc1 |
| Where | Seyda Neen: wedge1 at -225,348,131 |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.24-rc1 (last seen) |
| Severity | medium: the player is trapped |
| Family | Object placement and in-game geometry (`placement-geometry`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-09-30: reported in v0.0.24-rc1
- 2026-09-30: RC1 remaining acceptance items: The coordinate-by-coordinate record is in INVESTIGATION-v0.0.24-rc1.md (docs/history/investigations/INVESTIGATION-v0.0.24-rc1.md).

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66 (16 November 2026)._

## Status: 16 November 2026

Open. Kept open at the v0.0.24-rc1 acceptance (30 September 2026): the exact trapped state was not reproduced; nearby native retreat works only after lateral placement recovery (docs/history/investigations/INVESTIGATION-v0.0.24-rc1.md). Recorded as an entry from the bug journal on 16 November 2026.

## Symptom

Trapped at wedge1.

## Where

Seyda Neen: wedge1 at -225,348,131.

## How it happened

As recorded in the bug journal: see the dated history in the timeline below.

## Why it was not caught

Not recorded.

## Reproduction

As in the symptom; reproduction: unknown.

## Repair

None recorded.

## Verification

See the status and the timeline below.

## Prevention

Not recorded.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- BALMORA-FLAMES-IN-SKY-51 (no report page): Four fire sprites in Balmora with no fire under them: two float in the air, two stand on the ground
- CENSUS-BACK-TABLE-NOT-DRAWN-58 (no report page): The back-room table of the Census and Excise Office is not drawn
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): A Dwemer ruin at Azura's Coast is drawn in the wrong shape
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- COURTYARD-ARRIVAL-STUCK-66 (no report page): Arriving in the census courtyard from the back room, the player was once stuck in solid: twenty "player is stuck" lines and two moves out
- CREATURE-FLOATING-62 (no report page): A scrib in the wilderness floats above the terrain
- [DOOR-ARRIVAL-INSIDE-ACTOR-66](DOOR-ARRIVAL-INSIDE-ACTOR-66.md): Coming back out of the census office onto the Seyda Neen street after a kill, the player arrives inside the guard who has walked to the door and stays stuck
- [PORT-ROCK-ROTATION-23](PORT-ROCK-ROTATION-23.md): A rock by the Seyda Neen port was converted with the wrong rotation
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- ROOM-GROUND-STEEP-ICE-66 (no report page): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

<!-- END GENERATED CATEGORY -->
