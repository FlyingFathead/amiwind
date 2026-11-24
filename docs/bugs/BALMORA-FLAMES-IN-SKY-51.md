# BALMORA-FLAMES-IN-SKY-51: Four fire sprites in Balmora with no fire under them: two float in the air, two stand on the ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 25 October 2026, in v0.0.51 |
| Where | Balmora CHIM frame, cell -3,-2, near global -19669 -15819 (exterior static flames) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.51 (last seen) |
| Severity | medium: Stray animated fire in the air over the main town |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_25_v0.0.51_final_d74cc652 |
| From commit | source 3c0c6c8, engine 3c0c6c8, CHIM world 3c0c6c8 |
| CHIM engine version | CHIM 0.2.2, engine 3c0c6c8, world format 0.12 |
| Platform or emulator | FS-UAE, JIT, A1200 profile, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- [AW-20260928-03](AW-20260928-03.md): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- [AW-20260928-06](AW-20260928-06.md): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- [AW-20260928-20](AW-20260928-20.md): Census clipped outside room near captain wing
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
- [PORT-ROCK-ROTATION-23](PORT-ROCK-ROTATION-23.md): A rock by the Seyda Neen port was converted with the wrong rotation
- [PRISON-SHIP-FLOOR-STUCK-67](PRISON-SHIP-FLOOR-STUCK-67.md): On the prison ship the player gets stuck on a floor tile that stands out of the hold floor
- [ROCK-FLORA-SURFACE-29](ROCK-FLORA-SURFACE-29.md): Angular rock-like surfaces newly appearing in Bitter Coast
- [ROOM-EMPTY-PERSON-STANDS-HIGH-67](ROOM-EMPTY-PERSON-STANDS-HIGH-67.md): A person in a room without scenery stays at his placed height, about 80 units above the floor
- [ROOM-GROUND-STEEP-ICE-66](ROOM-GROUND-STEEP-ICE-66.md): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [SOL-SEA-INVISIBLE-BLOCKER-68](SOL-SEA-INVISIBLE-BLOCKER-68.md): An object in Solstheim's eastern waters is not drawn but still stops a player walking on the water
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WEDGE-TRAP-24](WEDGE-TRAP-24.md): wedge1: the player is trapped at -225,348,131
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-EXTERIOR-FLAMES-MISSING-48](CHIM-EXTERIOR-FLAMES-MISSING-48.md): CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation

<!-- END GENERATED CATEGORY -->
