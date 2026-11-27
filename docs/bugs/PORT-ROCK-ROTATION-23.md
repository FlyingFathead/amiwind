# PORT-ROCK-ROTATION-23: A rock by the Seyda Neen port was converted with the wrong rotation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 September 2026, in v0.0.23-dev2 |
| Where | Seyda Neen: the port rock |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.23-dev3 |
| Severity | low: a misplaced scenery object |
| Family | Object placement and in-game geometry (`placement-geometry`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-09-29: reported in v0.0.23-dev2
- 2026-09-29: dev3 feedback follow-up: The reported Vodunius-house visibility holes and the misrotated port rock are addressed; see terrain findings and workflow (docs/WHAT_ARE_ROCKS.md).
- 2026-09-29: dev3 regression retest / dev4: The maintainer confirms the port rock is fixed.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66 (16 November 2026)._

## Status: 16 November 2026

Fixed in v0.0.23-dev3. Fixed in v0.0.23-dev3: the corrected transforms and low-poly rock conversion; the maintainer confirmed it fixed in dev3. Recorded as an entry from the bug journal on 16 November 2026.

## Symptom

The maintainer reported a misrotated rock at the port on v0.0.23-dev2.

## Where

Seyda Neen: the port rock.

## How it happened

As recorded in the bug journal: see the dated history in the timeline below.

## Why it was not caught

Not recorded.

## Reproduction

As in the symptom; reproduction: always.

## Repair

The rock's transforms were corrected in v0.0.23-dev3.

## Verification

See the status and the timeline below.

## Prevention

Not recorded.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- [AW-20260928-03](AW-20260928-03.md): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- [AW-20260928-06](AW-20260928-06.md): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- [AW-20260928-20](AW-20260928-20.md): Census clipped outside room near captain wing
- [BALMORA-FLAMES-IN-SKY-51](BALMORA-FLAMES-IN-SKY-51.md): Four fire sprites in Balmora with no fire under them: two float in the air, two stand on the ground
- [BC-TREE-74609-FLOATING-67](BC-TREE-74609-FLOATING-67.md): A Bitter Coast tree near cell -2,-8 is drawn above the ground while its collision reaches the ground
- [CENSUS-BACK-TABLE-NOT-DRAWN-58](CENSUS-BACK-TABLE-NOT-DRAWN-58.md): The back-room table of the Census and Excise Office is not drawn
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): A Dwemer ruin at Azura's Coast is drawn in the wrong shape
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- [COURTYARD-ARRIVAL-STUCK-66](COURTYARD-ARRIVAL-STUCK-66.md): Arriving in the census courtyard from the back room, the player was once stuck in solid: twenty "player is stuck" lines and two moves out
- [CREATURE-FLOATING-62](CREATURE-FLOATING-62.md): A scrib in the wilderness floats above the terrain
- [DOOR-ARRIVAL-INSIDE-ACTOR-66](DOOR-ARRIVAL-INSIDE-ACTOR-66.md): Coming back out of the census office onto the Seyda Neen street after a kill, the player arrives inside the guard who has walked to the door and stays stuck
- [PRISON-SHIP-FLOOR-STUCK-67](PRISON-SHIP-FLOOR-STUCK-67.md): On the prison ship the player gets stuck on a floor tile that stands out of the hold floor
- [ROCK-FLORA-SURFACE-29](ROCK-FLORA-SURFACE-29.md): Angular rock-like surfaces newly appearing in Bitter Coast
- [ROOM-EMPTY-PERSON-STANDS-HIGH-67](ROOM-EMPTY-PERSON-STANDS-HIGH-67.md): A person in a room without scenery stays at his placed height, about 80 units above the floor
- [ROOM-GROUND-STEEP-ICE-66](ROOM-GROUND-STEEP-ICE-66.md): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [SOL-SEA-INVISIBLE-BLOCKER-68](SOL-SEA-INVISIBLE-BLOCKER-68.md): An object in Solstheim's eastern waters is not drawn but still stops a player walking on the water
- [VIVEC-CITY-FRAME-EDGE-WALLS-69](VIVEC-CITY-FRAME-EDGE-WALLS-69.md): The Vivec city map is closed by invisible walls at its edge, so a player who arrives in Vivec or Ebonheart by travel cannot leave the city on foot, swimming or levitating
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WEDGE-TRAP-24](WEDGE-TRAP-24.md): wedge1: the player is trapped at -225,348,131
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

<!-- END GENERATED CATEGORY -->
