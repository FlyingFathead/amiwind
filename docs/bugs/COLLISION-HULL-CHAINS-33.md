# COLLISION-HULL-CHAINS-33: 183 brush models across the island collide through long standing-hull chains

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Standing hulls of large placed models in legacy maps (prepare_mesh_bsp collider) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every trace near such a model walks its chain: thousands of plane tests per trace on a 68040 (prison ship, census office); offline gates take tens of minutes. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Measured: hull depth 512 or more, v0.0.33-dev1 full build](#measured-hull-depth-512-or-more-v0033-dev1-full-build)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Open; measured. Repair in source on v0.0.33-chim-format (the legacy converter's routed standing
hulls, `--model-hull auto`), not yet built. The before/after table follows the first build with it.

## Symptom

A converted model's standing hull is a chain of its convex pieces, and a chain's depth is its
length: every movement trace near the model walks it piece by piece. On the v0.0.33-dev1 full build
(2,673 maps), 183 brush models of 63 meshes have a standing hull 512 or more clipnodes deep. The
worst are the opening prison ship (31,659), the census office (23,127), the Vivec canton bodies
(10,270-11,211, 23 placements in the Arena maps), a mould cave of Addamasartus (10,157) and the
lighthouse interior (8,974).

## Where

Standing hulls of large placed models in legacy maps: `prepare_mesh_bsp` collider. qbsp's compiled
union (`collision_bsp.compile_standing`) covers models with exact pieces only, and it fails on some
large meshes ("CheckFace: non-convex face"); the chain is the fallback, and models without exact
pieces always got it.

## How it happened

The converter has always written the standing hull as one chain per model. It is exact (the same
solid set as the pieces) and was cheap for small models. Nothing measured how deep the hulls of the
large ones became.

## Why it was not caught

No gate reads hull depth. The stair gate and the engine both walk the chains without complaint;
they only get slow. CHIM-HULL-CHAIN-COST-33 (the Arena canton bodies on CHIM) and the Arena Pit
interior (one chain of 36,545 clipnodes, reported by the Arena interiors job, its own record follows
with that job's branch) showed the cost first.

## Reproduction

`python3 tools/hull_chain_audit.py <image>/id1/maps --min-depth 512 --jobs N` on a build of v0.0.33-dev1
or earlier: it lists every brush model's hull clipnodes and longest root-to-contents path, worst
first.

## Repair

In source on v0.0.33-chim-format, not shipped: `tools/routed_hull.py`, shared by the legacy converter
and the CHIM builder, writes a large model's standing hull as short chains behind axial clipnodes in
x, y and z (the same solid set). The first version (`balanced`: parts of at most 8, 32 or 128 pieces,
xy cuts) copied plates that span two axes (decks, walls, a bowl's tiers) into almost every part and
ran out of clipnodes on the Arena Pit (reported by the Arena interiors job). The default (`nested`)
picks each cut by expected cost and chains the pieces that straddle it at that cut once a copy
allowance (1x, then 0.25x the chain's clipnodes) is used up; without copies every piece is written
once, so it fits wherever the chain fits. `model_hull` / `--model-hull auto|chain|routed|balanced`
(`auto` by default: nested above 16 pieces) keeps the chain and the first routing selectable.

## Verification

Measured on 9 October 2026, standalone (each mesh prepared from its map's own scenery index with its
converter's profile, routed alone against the full clipnode budget): the default nested routing
routes all of the sweep's 20 worst meshes and the Arena Pit, with the same contents as the chain at
1,500 random points each. Mean clipnodes visited per point test fall 3 to 22 times (the Pit 7,304 to
328, the prison ship 3,439 to 298, the census office 3,218 to 355). The first routing (`balanced`)
runs out of clipnodes on the Pit and the census office. Visits are the engine's cost per hull test;
depth is the worst single test.

In a real map (9 October 2026): Seyda Neen's scene map rebuilt with `--model-hull auto`. The first try
overflowed the map's shared clipnode budget (BUILD-HULL-ROUTE-BUDGET-33); legacy maps now route without
copies. Result: 57,181 to 57,637 clipnodes, 20 models routed, no chain fallbacks, and the worst chains
1.3 to 3.2 times shallower (the lighthouse 3,172 to 1,170, the thatch tower 1,888 to 593). Still
pending: the island-wide audit and the stair gate's time on a full build with `--model-hull auto`.

| Mesh | Map | Pieces | Chain clipnodes | Chain visits | Balanced (before): depth / visits | Nested (default): depth / visits / clipnodes |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `i/in_v_arena_01.nif` | `vai000` | 1,597 | 36,545 | 7,304 | chain (budget) | 4,477 / 328 / 46,559 |
| `i/in_prison_ship.nif` | `prison` | 1,205 | 28,599 | 3,439 | 2,768 / 351 | 5,084 / 298 / 57,825 |
| `i/in_common_tower_thatch.nif` | `warehouse` | 928 | 23,127 | 3,218 | chain (budget) | 3,463 / 355 / 46,785 |
| `x/ex_vivec_c_04.nif` | `va010` | 238 | 3,045 | 663 | 417 / 89 | 717 / 85 / 6,272 |
| `x/ex_vivec_c_02.nif` | `va012` | 414 | 5,130 | 1,113 | 431 / 95 | 768 / 89 / 10,669 |
| `i/in_moldcave_08.nif` | `addamasartus` | 394 | 10,157 | 1,573 | 838 / 150 | 1,925 / 225 / 20,671 |
| `i/in_common_lighthouse.nif` | `lighthouse` | 451 | 8,974 | 1,256 | 2,087 / 328 | 1,409 / 134 / 18,284 |
| `i/in_velothismall_room_02.nif` | `bmtemple` | 264 | 5,835 | 496 | 1,682 / 166 | 1,444 / 36 / 8,491 |
| `i/in_moldcave_21_1.nif` | `addamasartus` | 206 | 5,118 | 728 | 2,909 / 392 | 1,477 / 48 / 10,276 |
| `i/in_moldcave_15.nif` | `addamasartus` | 426 | 4,686 | 972 | 359 / 80 | 849 / 115 / 9,825 |
| `i/in_velothismall_r8_ramp.nif` | `bmtemple` | 191 | 4,178 | 698 | 676 / 114 | 738 / 58 / 8,489 |
| `x/ex_hlaalu_b_11.nif` | `bm001` | 51 | 600 | 115 | 331 / 60 | 320 / 37 / 1,191 |
| `x/ex_velothi_temple_02.nif` | `bm035` | 23 | 358 | 100 | 153 / 29 | 159 / 16 / 674 |
| `x/ex_hlaalu_b_21.nif` | `bm001` | 43 | 519 | 114 | 268 / 40 | 261 / 28 / 1,063 |
| `i/in_velothismall_r8_dome.nif` | `bmtemple` | 149 | 3,845 | 603 | 805 / 143 | 864 / 108 / 7,808 |
| `i/in_moldcave_10.nif` | `addamasartus` | 290 | 3,190 | 570 | 1,201 / 222 | 811 / 103 / 6,591 |
| `x/ex_hlaalu_b_23.nif` | `bm018` | 46 | 542 | 119 | 305 / 39 | 385 / 46 / 994 |
| `x/ex_common_lighthouse.nif` | `seyda` | 191 | 3,134 | 546 | 1,834 / 337 | 766 / 56 / 6,454 |
| `i/in_hlaalu_loaddoor_01.nif` | `bmastius` | 143 | 3,121 | 432 | 2,626 / 365 | 2,732 / 112 / 5,779 |
| `i/in_moldcave_25.nif` | `addamasartus` | 272 | 2,992 | 581 | 356 / 76 | 793 / 110 / 6,220 |
| `x/ex_hlaalu_b_18.nif` | `bm029` | 43 | 504 | 105 | 261 / 41 | 370 / 33 / 1,013 |


## Prevention

`tools/hull_chain_audit.py` reports hull depth for any map. Tests (`tests/test_routed_hull.py`): the
routed hull classifies every point like the chain, the legacy converter writes the same routed hull
as the CHIM writer, coarser parts are undone cleanly when the budget runs out.

## Measured: hull depth 512 or more, v0.0.33-dev1 full build

One row per mesh: the longest chain of its placements, its faces, how many placements (one per map
they appear in) and where.

| Mesh | Longest chain (clipnodes) | Faces | Placements | Refs | Maps |
| --- | ---: | ---: | ---: | --- | --- |
| `i/in_prison_ship.nif` | 31,659 | 7,997 | 1 | 391417 | `prison` |
| `i/in_common_tower_thatch.nif` | 23,127 | 1,697 | 1 | 321953 | `warehouse` |
| `x/ex_vivec_c_04.nif` | 11,211 | 5,134 | 21 | 117156, 466153, 466157, 466160 and 1 more | `va000`, `va001`, `va002`, `va003` and 10 more |
| `x/ex_vivec_c_02.nif` | 10,270 | 1,193 | 2 | 82613 | `va012`, `va013` |
| `i/in_moldcave_08.nif` | 10,157 | 925 | 1 | 365499 | `addamasartus` |
| `i/in_common_lighthouse.nif` | 8,974 | 1,324 | 1 | 129152 | `lighthouse` |
| `i/in_velothismall_room_02.nif` | 5,835 | 277 | 1 | 243270 | `bmtemple` |
| `i/in_moldcave_21_1.nif` | 5,118 | 508 | 1 | 376813 | `addamasartus` |
| `i/in_moldcave_15.nif` | 4,686 | 1,036 | 1 | 365507 | `addamasartus` |
| `i/in_velothismall_r8_ramp.nif` | 4,178 | 947 | 1 | 243245 | `bmtemple` |
| `x/ex_hlaalu_b_11.nif` | 4,017 | 603 | 4 | 19034 | `balmora`, `bm001`, `bm019`, `bm027` |
| `x/ex_velothi_temple_02.nif` | 4,005 | 689 | 2 | 5970 | `bm035`, `bm043` |
| `x/ex_hlaalu_b_21.nif` | 3,961 | 497 | 1 | 6883 | `bm001` |
| `i/in_velothismall_r8_dome.nif` | 3,845 | 556 | 1 | 243244 | `bmtemple` |
| `i/in_moldcave_10.nif` | 3,190 | 579 | 1 | 365491 | `addamasartus` |
| `x/ex_hlaalu_b_23.nif` | 3,177 | 460 | 2 | 34120 | `bm018`, `bm026` |
| `x/ex_common_lighthouse.nif` | 3,134 | 1,475 | 1 | 114026 | `seyda` |
| `i/in_hlaalu_loaddoor_01.nif` | 3,121 | 212 | 49 | 33868, 33926, 41652, 41721 and 45 more | `bmastius`, `bmbalyn`, `bmbooks`, `bmcaius` and 29 more |
| `i/in_moldcave_25.nif` | 2,992 | 788 | 1 | 89758 | `addamasartus` |
| `x/ex_hlaalu_b_18.nif` | 2,903 | 386 | 2 | 32620 | `bm029`, `bm030` |
| `i/in_velothilarge_con_01.nif` | 2,669 | 812 | 2 | 243230, 322855 | `bmtemple`, `tharystomb` |
| `i/in_velothilarge_cap_01.nif` | 2,553 | 792 | 3 | 243237, 243238, 322858 | `bmtemple`, `tharystomb` |
| `i/in_moldcave_03.nif` | 2,508 | 1,029 | 1 | 365508 | `addamasartus` |
| `i/in_moldcave_07.nif` | 2,486 | 840 | 1 | 89899 | `addamasartus` |
| `i/in_moldcave_09.nif` | 2,486 | 978 | 1 | 89756 | `addamasartus` |
| `i/in_velothilarge_4way_01.nif` | 2,471 | 664 | 1 | 243231 | `bmtemple` |
| `i/in_moldcave_exit00.nif` | 2,441 | 413 | 1 | 89877 | `addamasartus` |
| `i/in_v_l_int_stairs_03.nif` | 2,277 | 529 | 1 | 322857 | `tharystomb` |
| `i/in_velothilarge_3way_01.nif` | 2,118 | 584 | 3 | 243234, 243235, 243236 | `bmtemple` |
| `i/in_moldcave2_s_05.nif` | 2,111 | 608 | 1 | 365509 | `addamasartus` |
| `i/in_velothilarge_corner_01.nif` | 1,900 | 561 | 2 | 243232, 243233 | `bmtemple` |
| `x/ex_common_tower_thatch.nif` | 1,888 | 741 | 1 | 113827 | `seyda` |
| `i/in_velothismall_room_07.nif` | 1,587 | 1,102 | 1 | 243243 | `bmtemple` |
| `i/in_velothismall_dj_01.nif` | 1,500 | 84 | 10 | 243378, 243380, 243382, 243383 and 6 more | `bmtemple`, `tharystomb` |
| `x/ex_nord_house_02.nif` | 1,240 | 933 | 1 | 113863 | `seyda` |
| `i/in_velothismall_room_05.nif` | 1,214 | 637 | 1 | 243213 | `bmtemple` |
| `i/in_moldcave2_s_02.nif` | 1,056 | 416 | 1 | 365514 | `addamasartus` |
| `i/in_moldcave2_s_04.nif` | 1,056 | 409 | 1 | 365511 | `addamasartus` |
| `x/ex_bc_cave_entrance.nif` | 991 | 932 | 1 | 208137 | `seyda` |
| `i/in_velothismall_hall_01.nif` | 966 | 376 | 4 | 243220, 243221, 243225, 243229 | `bmtemple` |
| `x/ex_de_ship.nif` | 936 | 4,046 | 1 | 172850 | `seyda` |
| `x/ex_common_house_tall_02.nif` | 933 | 546 | 1 | 113828 | `seyda` |
| `o/contain_corpse10.nif` | 928 | 3,646 | 1 | 481164 | `addamasartus` |
| `x/ex_de_shack_02.nif` | 908 | 1,113 | 1 | 321235 | `seyda` |
| `i/in_velothismall_room_08.nif` | 794 | 455 | 1 | 243214 | `bmtemple` |
| `f/flora_emp_parasol_01.nif` | 765 | 409 | 1 | 384149 | `bmtyravel` |
| `x/ex_common_house_tall_01.nif` | 756 | 578 | 1 | 113824 | `seyda` |
| `x/ex_common_house_addon.nif` | 746 | 589 | 1 | 113895 | `seyda` |
| `x/ex_velothi_entrance_02.nif` | 741 | 427 | 2 | 315558 | `bm009`, `bm010` |
| `f/terrain_rock_wg_06.nif` | 720 | 75 | 1 | 43177 | `bm046` |
| `i/in_velothismall_room_04.nif` | 716 | 545 | 1 | 243212 | `bmtemple` |
| `x/ex_de_shack_03.nif` | 689 | 863 | 1 | 321236 | `seyda` |
| `x/ex_de_rowboat.nif` | 665 | 663 | 1 | 326704 | `addamasartus` |
| `x/ex_nord_house_01.nif` | 638 | 545 | 1 | 113886 | `seyda` |
| `i/in_velothismall_column_01.nif` | 611 | 216 | 10 | 243246, 243247, 243248, 243249 and 6 more | `bmtemple`, `tharystomb` |
| `i/in_nord_house_02.nif` | 592 | 443 | 1 | 119666 | `eldafire` |
| `x/ex_hlaalu_striderport_01.nif` | 576 | 432 | 5 | 41510 | `balmora`, `bm011`, `bm012`, `bm019` and 1 more |
| `f/furn_de_firepit.nif` | 571 | 811 | 2 | 119852, 119925 | `erene`, `foryn` |
| `f/terrain_rock_wg_13.nif` | 543 | 87 | 2 | 342053 | `bm008`, `bm009` |
| `f/terrain_rock_wg_11.nif` | 538 | 84 | 1 | 192436 | `bm007` |
| `x/ex_nord_win_02.nif` | 537 | 1 | 9 | 113843, 113861, 113868, 113874 and 5 more | `seyda` |
| `x/ex_common_balcony_01.nif` | 535 | 667 | 1 | 113897 | `seyda` |
| `r/siltstrider.nif` | 517 | 3,266 | 4 | 41523, 227023 | `balmora`, `bm011`, `bm019`, `seyda` |

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water

Related bugs in other categories:

- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"

<!-- END GENERATED CATEGORY -->
