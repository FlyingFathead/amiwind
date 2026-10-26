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

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- BALMORA-FLAMES-IN-SKY-51 (no report page): Four fire sprites in Balmora with no fire under them: two float in the air, two stand on the ground
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast

<!-- END GENERATED CATEGORY -->
