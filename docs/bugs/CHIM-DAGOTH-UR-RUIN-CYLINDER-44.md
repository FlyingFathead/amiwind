# CHIM-DAGOTH-UR-RUIN-CYLINDER-44: the Dagoth Ur blight cloud whirlwind is drawn solid and still

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.44-dev1 at 2026-10-19 15:17 +0300: third screenshot, global 20178 71745 17371: curved swept sheets around the crater; maintainer suspects animated graphics layers
- Reported with v0.0.44-dev1 at 2026-10-19 15:18 +0300: the inspect pick cannot select the sheets: no collision, which fits an effect layer rather than a ruin piece
- Reported with v0.0.44-dev1 at 2026-10-19 15:20 +0300: maintainer, from modding and playing the original through: a graphics layer meant to be something else, like a whirlwind (animated ash swirl)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | Dagoth Ur, cell 2,8: CHIM placement 174155, x/ex_dwrv_ruin20 tilted copy, ref 210906 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | medium: a large wrong shape at a key place of the main quest |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

## Status: 19 October 2026

Reported by the maintainer; cause not found yet.

## Symptom

At Dagoth Ur, a black-brown cylinder wall surrounds an area that is open in the original game.

## Where

Red Mountain region, Dagoth Ur, cell 2,8 (global 20610 70041 15553). The inspect pin names CHIM placement 174155,
mesh `x/ex_dwrv_ruin20`, a tilted copy (the model name carries a tilt), CHIM model 15864, source reference 210906.

## How it happened

Found 19 October 2026: the sheets are the activator "blight cloud" (`f/active_blight_large.nif`) that the original
places in cell 2,8: about a dozen nested cylinders textured `Tx_Dagoth_cloud02`, each with a material alpha of 0.0
to 0.4, together about 6,400 by 5,600 by 6,700 units around Dagoth Ur, with no collision. In the original they are
transparent and animated, a whirlwind; the converter draws them solid and still. The pinned ruin piece only sat
behind them. Earlier guess, kept for the record: The piece is a tilted copy: CHIM stores a copy of a mesh for each tilt it is placed with. The West Gash
rock the player gets stuck on ([TERRAIN-TRAP-29](TERRAIN-TRAP-29.md)) is also a tilted copy, and the rocks that do
not close up ([CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md)) may share a cause: a wrong rotation or
scale for some tilted copies would turn a ruin piece into a large wrong shape.

## Why it was not caught

No check compares the orientation and bounds of every tilted copy with its source placement.

## Reproduction

Always: noclip to the reported position.

## Repair

To do: compare this copy's rotation and bounds with the source placement and with OpenMW at the same pose; if the
tilt is wrong, fix it in the shared converter, then audit every tilted copy on the island.

## Verification

To do: OpenMW and AmiWind stills at the same pose, and the island-wide audit with no tilted copy off.

## Prevention

To do: the tilted-copy audit kept as a check in the CHIM stage.

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
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures

<!-- END GENERATED CATEGORY -->
