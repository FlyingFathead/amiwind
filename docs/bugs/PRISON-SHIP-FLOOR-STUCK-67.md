# PRISON-SHIP-FLOOR-STUCK-67: On the prison ship the player gets stuck on a floor tile that stands out of the hold floor

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 November 2026, in v0.0.66 |
| Where | The opening: the prison ship hold floor, a tile near the local position 8 132 48 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.66, v0.0.67-dev1, v0.0.67-dev2 (last seen) |
| Severity | high: the player can get stuck in the opening, before any save can be made |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| Playtest version | 2026_11_17_v0.0.66_full-v0.0.66-release-try2_ad5e9a0 |
| From commit | source ad5e9a0, engine ad5e9a0, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine ad5e9a0, world format unknown |
| Unknown because | the world commit and CHIM version of the release image were not read for this entry |
| Build note | the v0.0.66 release image, played by the maintainer |
| Platform or emulator | the v0.0.66 release image (playtest) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a commit on the dev line | v0.0.67-dev3 line (fac3d8f7) | 2026-11-18 | tests/test_room_map_shapes.py and the drawn-collision check on the v0.0.67-dev2 hold | the masts and the other shapes with collision drawn whole; no collision piece taller than a step without drawn faces is left; the collision is unchanged |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-17: reported in v0.0.66
- 2026-11-17: v0.0.67-dev1: Cause found on the v0.0.67-dev1 image: the mast of the hold shell has its collision column but no drawn faces in the converted hold (the visual reduction kept the structural shapes but not the mast); the drawn tile at its base is all that ...
- 2026-11-18: seen again in v0.0.67-dev2: Seen again on the v0.0.67-dev2 image: something stands out of the upper deck floor near the local position 4 133 43 and stops the player; the pick names the hold shell (source ref 391417).
- 2026-11-18: v0.0.67-dev3: Fix in source: the masts and the other shell shapes whose collision stays are drawn whole (exact names, the room map's own preparation); a check that every collision piece the original draws keeps drawn faces at its place runs in the ...
- 2026-11-18: fixed in source: a commit on the dev line, v0.0.67-dev3 line (fac3d8f7); tests/test_room_map_shapes.py and the drawn-collision check on the v0.0.67-dev2 hold: the masts and the other shapes with collision drawn whole; no collision piece taller than a step without drawn faces is left; the collision is unchanged

<!-- END GENERATED TIMELINE -->

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
- [PORT-ROCK-ROTATION-23](PORT-ROCK-ROTATION-23.md): A rock by the Seyda Neen port was converted with the wrong rotation
- [ROCK-FLORA-SURFACE-29](ROCK-FLORA-SURFACE-29.md): Angular rock-like surfaces newly appearing in Bitter Coast
- [ROOM-EMPTY-PERSON-STANDS-HIGH-67](ROOM-EMPTY-PERSON-STANDS-HIGH-67.md): A person in a room without scenery stays at his placed height, about 80 units above the floor
- [ROOM-GROUND-STEEP-ICE-66](ROOM-GROUND-STEEP-ICE-66.md): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [SOL-SEA-INVISIBLE-BLOCKER-68](SOL-SEA-INVISIBLE-BLOCKER-68.md): An object in Solstheim's eastern waters is not drawn but still stops a player walking on the water
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WEDGE-TRAP-24](WEDGE-TRAP-24.md): wedge1: the player is trapped at -225,348,131
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [PRISON-SHIP-SHELL-ONE-MODEL-66](PRISON-SHIP-SHELL-ONE-MODEL-66.md): The prison ship hold's shell is one brush model whose box is the whole room: all its 7,997 faces are tested at every heading, though at most headings a few hundred are on screen

<!-- END GENERATED CATEGORY -->
