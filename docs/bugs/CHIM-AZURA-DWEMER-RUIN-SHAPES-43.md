# CHIM-AZURA-DWEMER-RUIN-SHAPES-43: a Dwemer ruin at Azura's Coast is drawn in the wrong shape

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Azura's Coast, cell 19,4 (global 163684 35725 1154, local 985 -284 288, looking up) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | medium: a landmark looks broken; the ruins are what players head for along that coast |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer playtest) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-18: reported in v0.0.43-dev2
- 2026-10-18: CHIM-AZURA-FLOATING-FLORA-43 cause found and CHIM-AZURA-DWEMER-RUIN-SHAPES-43 measured: CHIM-AZURA-DWEMER-RUIN-SHAPES-43: Daedric ruin pillars at cell 19,4 looked like twisted shapes in the air.
- 2026-10-18: CHIM-AZURA-DWEMER-RUIN-SHAPES-43: The maintainer's v0.0.43-dev2 playtest: a Dwemer ruin on Azura's Coast (cell 19,4) is drawn as twisted shapes that do not match the original.
- 2026-10-18 18:18 +0300: seen again in v0.0.43-dev2: maintainer pinned it: Daedric pillar x/ex_dae_pillar_01@s1 (model 102), placement 394489, ref 77482, placement local 849 -376 552, yaw -43; floating in the air

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 18 October 2026

Open. Reported by the maintainer during the v0.0.43-dev2 playtest; cause not measured.

## Symptom

A Dwemer ruin on Azura's Coast is drawn as twisted dark shapes that do not match the original ruin. The inspect
tool finds no target within 2048 units there.

## Where

Azura's Coast region, cell 19,4 (global position 163684 35725 1154, local 985 -284 288), looking up at the ruin.

## How it happened

The maintainer's pin shows a Daedric ruin, not a Dwemer one: the pillar `ex_dae_pillar_01` (source reference
77482). Daedric ruins are spiky by design. Measured on the v0.0.43-dev2 world, the pillar is placed exactly as in
the original record (height 2,208) and stands on the ruin base `ex_dae_ruin_01` (source reference 67494, base at
1,536, top at 2,310); both converted models match their original meshes. It is not the reducer problem of
[CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md). If the pillar seems to float in game, the likely
cause is that the ruin base is not drawn there; that needs an in-game check.

The details, measured on the same world: the CHIM placement of the pillar is 394489 and that of the base 394429 (it
reaches more than 16 leaves). The pillar stands 472 units from the base's centre (the base's radius is 561), so its
foot (height 1,952) is inside the top of the base. The other pillars, claws, walls and buttresses around it are also
placed exactly as in their records. Per 256-unit height band, the surface area of the converted base and pillar
equals the original meshes; the bounds of the pillars, claws, walls and buttresses are exact. No collision union
fell back, and the base's compiled hull is patched by 200 nodes as recorded. These architecture meshes are not
reduced.

## Why it was not caught

The placement and geometry audits compare positions and face validity, not the overall shape of a converted model
against the original.

## Reproduction

In v0.0.43-dev2, travel to cell 19,4 on Azura's Coast and look at the Dwemer ruin near local 985 -284.

## Repair

None yet. The models at the spot are identified and match the original; next is the in-game check whether the base
(placement 394429) is drawn and sent (`dbg rcount`), in a MiniWind sandbox of cell 19,4.

## Verification

The same pose in the next build, headlamp off and on, against OpenMW.

## Prevention

An island-wide audit of every model on the faulty converter path once the mechanism is named.

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
- [ROOM-GROUND-STEEP-ICE-66](ROOM-GROUND-STEEP-ICE-66.md): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WEDGE-TRAP-24](WEDGE-TRAP-24.md): wedge1: the player is trapped at -225,348,131
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast

<!-- END GENERATED CATEGORY -->
