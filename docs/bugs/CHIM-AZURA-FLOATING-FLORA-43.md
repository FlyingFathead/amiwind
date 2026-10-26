# CHIM-AZURA-FLOATING-FLORA-43: plant or tree pieces hang in the air at Azura's Coast

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 7 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 18:10 +0300: maintainer: second spot, cell 16,9 (global 136878 75700 373, frame map vf2303): leaf cards and twig lines in a tree-crown pattern, no trunk drawn
- Reported with v0.0.43-dev2 at 2026-10-18 18:12 +0300: maintainer pinned it: CHIM placement 379487, mesh f/flora_tree_ac_01@s1.85 (model 12410), source ref 137320, cell 16,9; a repeating pattern
- Reported with v0.0.43-dev2 at 2026-10-18 18:14 +0300: maintainer: third spot, cell 18,5, leaf cards under a giant mushroom (pick: f/flora_emp_parasol_02@s1.84, ref 133286); the leaves themselves are not pickable
- Reported with v0.0.43-dev2 at 2026-10-18 18:15 +0300: maintainer: fourth spot, cell 19,4 under a parasol (f/flora_emp_parasol_02@s1.58); 'it's the same plant, repeating', not the mushroom
- Reported with v0.0.43-dev2 at 2026-10-18 18:22 +0300: maintainer found a WORKING copy of the same tree: cell 18,5, f/flora_tree_ac_01@s1.54 (model 12430), ref 133288; compare with the broken @s1.85 (model 12410)
- Reported with v0.0.43-dev2 at 2026-10-18 19:46 +0300: maintainer: a broken rock on CHIM, Bitter Coast cell -4,-6: f/terrain_rocks_ai_02@s1 (model 1750, ref 476548), a rock that takes the flora reducer profile
- Reported with v0.0.43-dev2 at 2026-10-18 20:25 +0300: correction: terrain_rocks_ai_02 (Bitter Coast -4,-6) is not on the flora path and not reduced (393 of 396 faces); its open edges match the one-sided NIF: OpenMW A/B needed

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Azura's Coast, cell 16,7 (global 133593 61273 267, local -393 -41 66, looking up) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | low: a visual break in the open world; no effect on play |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 7 times; something has to be done](#persisting-reported-7-times-something-has-to-be-done)
- [Status: 18 October 2026](#status-18-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Cause found; fixed in source on the v0.0.43 line (branch v0.0.43-azuraflora, gate 2970 passed), not yet in a build;
in-game check to do. Reported by the maintainer during the v0.0.43-dev2 playtest at four spots: cells 16,7, 16,9,
18,5 and 19,4.

## Symptom

Looking up at Azura's Coast, leafy plant or tree pieces joined by thin branch lines hang in the air with nothing
below them. The inspect tool finds no target within 2048 units there.

## Where

Azura's Coast region, cell 16,7 (global position 133593 61273 267, local -393 -41 66), on CHIM since v0.0.42.

## How it happened

The pieces do not float and are not duplicated: they are the crowns of Azura's Coast trees (`flora_tree_ac_01`
and `flora_tree_ac_02`) whose trunks were reduced away. The builder's flora profile gives every `flora_` mesh a
target of about 120 triangles. For `flora_tree_ac_01` (1,672 triangles) that is 7 % of the mesh. The reducer works
on each connected part separately, and the 192-triangle trunk tube collapsed: the bark kept 12 % of its area and
nothing below the bottom few units of the mesh, while the leaf caps kept about 60 %. `flora_tree_ac_02` kept 8 %
of its bark. Seen in game, the crown hangs above a missing trunk.

Measured on the v0.0.43-dev2 world:

- every placement of these trees matches its original record (position, scale, rotation, no tilt), and no
  reference appears twice or shifted;
- every scale copy of the tree has the same faces, so the scale is not the cause;
- the lowest drawn part of the two trees is above the ground at 299 of their 311 placements in the checked frames
  (more than 200 units at 154 of them). The tree that looked right at cell 18,5 is the same broken model; the trunk
  seen there belongs to a neighbouring `flora_tree_ac_04`, which keeps its bark.

Island-wide 250 meshes go through the reducer; 51 of them lose more than 65 % of a material's area or 30 % of
their height or width. The worst are `flora_tree_ac_01` and `_02`, the `tree_gl_` trees, `tree_wg_06`, the
`bc_fern_01` and `_02` ferns and hackle-lo. The Azura's Coast trees alone are 1,114 placements in about 70 frames.

## Why it was not caught

The reducer's own checks look at face counts and validity, not at whether a part keeps its shape; no audit compared
the height or area of each reduced part with the original mesh.

## Reproduction

In v0.0.43-dev2, travel to cell 16,7 and look up near local -393 -41.

## Repair

In source (`tools/static_lod.py`, flora profile in `tools/town_regions.py`; gate 2970): a shape guard in the reducer. A part of at least 96 source triangles that the reducer
shrinks below 0.9 of its height is reduced again with the reducer that keeps its outline, or kept as in the source.
It is on for the flora profile; `lod_shape_guard 0` keeps the old method. `flora_tree_ac_01` goes from 153 to 161
triangles with 92 % of its bark and its full height. Over the 250 reduced meshes, 31 change, with 5.3 % more
triangles per model and 6.4 % more for what is placed. Thin twigs of 36 to 60 triangles stay thinned.
Guarding every axis of every part would cost 80 % and 66 % more and was not chosen.

The 51 reduced meshes that lose part of their shape, measured 18 October 2026 on the maintainer's data (v0.0.43-dev2
world; before = v0.0.43-dev2, after = the guard; "lowest height kept" is the lowest over the mesh's materials):

| Mesh | Placements | Triangles: source, before, after | Weakest material (source triangles) | Area kept | Extent kept | Lowest height kept | Result |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `o/flora_wickwheat_04` | 7794 | 176, 122, 122 | Tx_wickwheat_03 (14) | 0.73 -> 0.73 | 0.53 -> 0.53 | 0.53 -> 0.53 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_wickwheat_03` | 4326 | 176, 122, 122 | Tx_wickwheat_03 (14) | 0.70 -> 0.70 | 0.53 -> 0.53 | 0.53 -> 0.53 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `x/flora_ashtree_07` | 3543 | 1079, 234, 320 | Tx_ashtree_bark_01 (572) | 0.38 -> 0.38 | 0.61 -> 0.61 | 0.94 -> 0.94 | trunk/stem height kept; smaller parts stay thin |
| `o/flora_wickwheat_01` | 3129 | 204, 100, 100 | Tx_wickwheat_01 (14) | 0.34 -> 0.34 | 0.35 -> 0.35 | 0.35 -> 0.35 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_kreshweed_03` | 2001 | 308, 108, 108 | Tx_kreshweed_03 (308) | 0.23 -> 0.23 | 0.73 -> 0.73 | 0.83 -> 0.83 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_kreshweed_02` | 1679 | 550, 100, 100 | Tx_kreshweed_04 (60) | 0.01 -> 0.01 | 0.60 -> 0.60 | 0.46 -> 0.46 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_rm_scathecraw_01` | 1656 | 170, 110, 110 | Tx_RM_scathecraw_01 (170) | 0.60 -> 0.60 | 0.67 -> 0.67 | 0.87 -> 0.87 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `x/flora_ashtree_01` | 1499 | 584, 149, 276 | Tx_ashtree_bark_03 (169) | 0.58 -> 0.58 | 0.55 -> 0.55 | 0.55 -> 0.55 | partly: stems under 96 triangles stay short |
| `o/flora_stoneflower_01` | 1408 | 525, 109, 109 | Tx_bittergreen_01 (69) | 0.45 -> 0.45 | 0.34 -> 0.34 | 0.69 -> 0.69 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_saltrice_01` | 1390 | 250, 174, 174 | Tx_saltrice_03 (60) | 0.75 -> 0.75 | 0.45 -> 0.45 | 0.59 -> 0.59 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_wickwheat_02` | 1292 | 170, 118, 118 | Tx_wickwheat_01 (14) | 0.64 -> 0.64 | 0.53 -> 0.53 | 0.53 -> 0.53 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_fern_03` | 1203 | 220, 114, 114 | Tx_BC_fern_01 (18) | 0.30 -> 0.30 | 0.39 -> 0.39 | 0.39 -> 0.39 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_stoneflower_02` | 850 | 248, 112, 112 | Tx_bittergreen_01 (48) | 0.77 -> 0.77 | 0.70 -> 0.70 | 0.84 -> 0.84 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_emp_parasol_02` | 838 | 611, 163, 163 | Tx_emperor_parasol_03 (18) | 0.91 -> 0.91 | 0.56 -> 0.56 | 0.56 -> 0.56 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_hackle-lo_01` | 800 | 638, 432, 568 | Tx_Hackle-lo_02 (168) | 0.13 -> 1.00 | 0.20 -> 1.00 | 0.20 -> 1.00 | trunk/stem height kept; smaller parts stay thin |
| `f/flora_bc_fern_02` | 760 | 310, 96, 96 | Tx_BC_fern_02 (18) | 0.09 -> 0.09 | 0.17 -> 0.17 | 0.17 -> 0.17 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_wg_04` | 744 | 805, 120, 120 | Tx_bark_05 (805) | 0.76 -> 0.76 | 0.47 -> 0.47 | 0.93 -> 0.93 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_ac_04` | 672 | 872, 163, 163 | Tx_mushroom_05 (133) | 0.12 -> 0.12 | 0.83 -> 0.83 | 0.95 -> 0.95 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_ac_02` | 622 | 1018, 115, 123 | Tx_bark_01 (408) | 0.08 -> 1.09 | 0.44 -> 0.87 | 0.44 -> 0.97 | fixed |
| `f/flora_emp_parasol_01` | 621 | 428, 160, 160 | Tx_emperor_parasol_03 (16) | 0.59 -> 0.59 | 0.25 -> 0.25 | 0.25 -> 0.25 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_ac_01` | 492 | 1672, 153, 161 | Tx_bark_01 (624) | 0.12 -> 0.92 | 0.47 -> 0.84 | 0.47 -> 0.97 | fixed |
| `o/flora_hackle-lo_02` | 490 | 638, 432, 568 | Tx_Hackle-lo_02 (168) | 0.13 -> 1.00 | 0.25 -> 1.00 | 0.25 -> 0.99 | fixed |
| `f/flora_tree_wg_05` | 430 | 932, 356, 356 | Tx_bark_05 (660) | 0.77 -> 0.77 | 0.47 -> 0.47 | 0.93 -> 0.93 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_03` | 426 | 376, 134, 134 | Tx_leaves_02 (20) | 0.21 -> 0.21 | 0.60 -> 0.60 | 0.72 -> 0.72 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_ai_06` | 422 | 596, 119, 119 | Tx_leaves_02 (20) | 0.21 -> 0.21 | 0.51 -> 0.51 | 0.47 -> 0.47 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_tree_02` | 417 | 1688, 486, 716 | Tx_BC_bark_02 (532) | 0.63 -> 0.93 | 0.36 -> 0.71 | 0.72 -> 0.93 | fixed |
| `f/flora_bc_tree_01` | 399 | 1743, 488, 730 | Tx_BC_bark_02 (390) | 0.43 -> 0.90 | 0.33 -> 0.71 | 0.74 -> 0.91 | fixed |
| `o/flora_fire_fern_01` | 386 | 597, 287, 287 | Tx_bittergreen_01 (69) | 0.26 -> 0.26 | 0.31 -> 0.31 | 0.87 -> 0.87 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_wg_06` | 383 | 632, 111, 111 | Tx_branches_01 (14) | 0.06 -> 0.06 | 0.09 -> 0.09 | 0.14 -> 0.14 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_tree_04` | 378 | 1376, 167, 381 | Tx_BC_bark_02 (496) | 0.34 -> 0.93 | 0.58 -> 0.79 | 0.74 -> 0.91 | fixed |
| `f/flora_tree_wg_08` | 373 | 591, 119, 119 | Tx_bark_05 (591) | 0.85 -> 0.85 | 0.66 -> 0.66 | 0.94 -> 0.94 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_fern_01` | 347 | 528, 164, 164 | Tx_BC_fern_02 (18) | 0.03 -> 0.03 | 0.19 -> 0.19 | 0.10 -> 0.10 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_fern_04` | 339 | 220, 122, 122 | Tx_BC_fern_01 (18) | 0.52 -> 0.52 | 0.53 -> 0.53 | 0.53 -> 0.53 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_willow_flower_01` | 325 | 457, 117, 117 | Tx_willow_flower_02 (18) | 0.20 -> 0.20 | 0.25 -> 0.25 | 0.37 -> 0.37 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_04` | 320 | 396, 114, 114 | Tx_leaves_02 (20) | 0.21 -> 0.21 | 0.74 -> 0.74 | 0.56 -> 0.56 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_black_anther_01` | 305 | 541, 134, 134 | Tx_black_anther_03 (48) | 0.19 -> 0.19 | 0.93 -> 0.93 | 0.61 -> 0.61 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_tree_05` | 285 | 1461, 352, 549 | Tx_BC_bark_02 (633) | 0.65 -> 0.89 | 0.42 -> 0.78 | 0.75 -> 0.96 | fixed |
| `o/flora_fire_fern_02` | 284 | 392, 188, 188 | Tx_bittergreen_01 (48) | 0.55 -> 0.55 | 0.36 -> 0.36 | 0.83 -> 0.83 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_willow_flower_02` | 247 | 201, 104, 104 | Tx_willow_flower_02 (18) | 0.38 -> 0.38 | 0.49 -> 0.49 | 0.78 -> 0.78 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `o/flora_bittergreen_pod_01` | 180 | 1023, 94, 370 | Tx_bittergreen_01 (63) | 0.35 -> 0.35 | 0.23 -> 0.23 | 0.23 -> 0.23 | partly: stems under 96 triangles stay short |
| `o/flora_bittergreen_03` | 163 | 228, 116, 116 | Tx_bittergreen_02 (16) | 0.50 -> 0.50 | 0.59 -> 0.59 | 0.71 -> 0.71 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_gl_02` | 137 | 1198, 196, 196 | Tx_leaves_07 (14) | 0.06 -> 0.06 | 0.08 -> 0.08 | 0.10 -> 0.10 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_gl_05` | 113 | 2102, 328, 418 | Tx_leaves_07 (14) | 0.06 -> 0.06 | 0.07 -> 0.07 | 0.10 -> 0.10 | partly: stems under 96 triangles stay short |
| `f/flora_bc_podplant_03` | 101 | 481, 118, 118 | Tx_BC_podplant_03 (16) | 0.34 -> 0.34 | 0.39 -> 0.39 | 0.39 -> 0.39 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_tree_gl_01` | 96 | 1366, 188, 282 | Tx_leaves_07 (14) | 0.06 -> 0.06 | 0.08 -> 0.08 | 0.10 -> 0.10 | partly: stems under 96 triangles stay short |
| `f/flora_tree_gl_06` | 81 | 2332, 402, 563 | Tx_leaves_07 (14) | 0.06 -> 0.06 | 0.08 -> 0.08 | 0.09 -> 0.09 | partly: stems under 96 triangles stay short |
| `f/flora_tree_gl_07` | 62 | 2345, 340, 559 | Tx_leaves_07 (14) | 0.06 -> 0.06 | 0.08 -> 0.08 | 0.09 -> 0.09 | partly: stems under 96 triangles stay short |
| `o/flora_ash_yam_01` | 44 | 397, 112, 112 | Tx_ash_yam_03 (112) | 0.30 -> 0.30 | 0.57 -> 0.57 | 0.57 -> 0.57 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `r/siltstrider` | 15 | 5600, 2926, 2926 | TX_Siltstrider_skin_13 (36) | 0.98 -> 0.98 | 0.00 -> 0.00 | 0.00 -> 0.00 | not changed: only parts under 96 triangles (cards, blades, twigs) thinned |
| `f/flora_bc_tree_06` | 12 | 1339, 153, 201 | Tx_BC_bark_02 (504) | 0.27 -> 0.27 | 0.63 -> 0.63 | 0.94 -> 0.94 | trunk/stem height kept; smaller parts stay thin |
| `f/flora_bc_tree_07` | 10 | 1453, 311, 509 | Tx_BC_bark_02 (585) | 0.82 -> 0.93 | 0.51 -> 0.74 | 0.87 -> 0.96 | fixed |

Fixed: 8 (among them `flora_tree_ac_01` and `_02`). Trunk or stem height kept, smaller parts still thin: 3. Partly
(stems under 96 triangles stay short): 6. Not changed, only parts under 96 triangles thinned (leaf cards, grass
blades, twigs): 34.

## Verification

`tests/test_static_lod.py`: `ShapeGuardTests` (a trunk the reducer collapses is reduced again and keeps its height;
the guard off gives the previous output exactly; small parts and other axes are not guarded; the flora profile sets
the guard) and `AzuraTreeTrunkTests` (with the tester's own data, `AMIWIND_TEST_MORROWIND`: the trunk of
`flora_tree_ac_01` keeps over 0.9 of its height, and the profile without the guard equals the previous reducer).
Gate 2970 passed. In game, to do: the same pose in the next build, headlamp off and on, against OpenMW.

## Prevention

A shape audit of every reduced mesh against its original (height, width and area kept per material), next to the
seam audit (to do); the regression tests above keep the tree trunk's height.

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
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): A Dwemer ruin at Azura's Coast is drawn in the wrong shape
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid

<!-- END GENERATED CATEGORY -->
