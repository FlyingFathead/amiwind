# CHIM-BC-TREE-PYRAMID-BOX-47: Bitter Coast trees look like a pyramid trunk with a flat box floating above it

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 21 October 2026, in v0.0.47-dev1 |
| Where | Bitter Coast: f/flora_bc_tree_01, _04 (and the family), cells -6,-7, -7,-6, -6,-5 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.47-dev1 (last seen) |
| Severity | medium: a whole tree family (up to about 3,000 placements across scale variants) is drawn broken across the Bitter Coast, a main look of the first region |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9 |
| From commit | source 4a2d42b, engine 4a2d42b, CHIM world 4a2d42b |
| CHIM engine version | CHIM 0.2.1, engine 4a2d42b, world format 0.7 |
| Platform or emulator | maintainer's playtest, emulator |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56 (30 October 2026)._

## Status: 21 October 2026

Open. Cause unknown. Fix direction decided for the project, 21 October 2026: crossed vertical planes through the
trunk, each textured with the tree's own outline (below). Nothing is built yet; it is tested against the current
look and the original game at the same poses before it becomes a default.

## Symptom

The Bitter Coast trees of the `flora_bc_tree` family are drawn as broken flat slabs. The maintainer, playing
v0.0.47-dev1, described the family as tree types that look like a pyramid with a floating rectangular box on
top, called the trees a bit wonky (an earlier remark of his too), said one tree's figure is more or less broken, and
found all of them poor-looking because their polygon count is very low. He also thinks they would probably work
better as a sprite. Screenshots from the maintainer's playtest (private) show all
three spots below.

## Where

Three pinned spots, all in the Bitter Coast Region, build 2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9 (commit
4a2d42b9, CHIM 0.2.1, world format 0.7):

| # | Mesh (CHIM model) | Source ref | Cell | CHIM placement | Placement local x y z, yaw | Player GLOBAL, time |
| --- | --- | ---: | --- | ---: | --- | --- |
| 1 | `f/flora_bc_tree_01@s2` (372) | 267841 | -6,-7 | 2908 | 141.3 829.7 220.8, -77.4 | -43908 -49736 187, 12:02 |
| 2 | `f/flora_bc_tree_04@s2` (196) | 256979 | -7,-6 | 4134 | 39.8 89.7 154.5, -83.1 | -53018 -44443 113, 12:52 |
| 3 | `f/flora_bc_tree_04@s2` (196) | 255166 | -6,-5 (Hla Oad) | 7593 | 276.3 -481.9 193.9, -256.9 | not recorded |

## How it happened

Unknown. What is measured so far: the CHIM stats of the v0.0.47-dev1 run give these triangle counts per stored
model of the family, against the original meshes' counts from
[CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md):

| Mesh | Original triangles | In the v0.0.47-dev1 run | Placements (all scale variants) |
| --- | ---: | ---: | ---: |
| `flora_bc_tree_01` | 1,743 | 542 | 399 |
| `flora_bc_tree_02` | 1,688 | 553 | 417 |
| `flora_bc_tree_03` | 1,316 | 180 to 252 | 591 |
| `flora_bc_tree_04` | 1,376 | 222 | 378 |
| `flora_bc_tree_05` | 1,461 | 352 to 434 | 285 |
| `flora_bc_tree_06` | 1,339 | 169 | 12 |
| `flora_bc_tree_07` | 1,453 | 365 | 10 |
| `flora_bc_tree_08` to `_13` | not listed here | 118 to 166 | 940 |

So `flora_bc_tree_04` keeps 16 % of its triangles and `_01` keeps 31 %. The flora visual profile reduces these
meshes and guards the height of the trunk; whether the reduced leaf crown (a flat box in the pictures) comes from
that reduction, from the shape guard, or from the original mesh's own card layout is not established. Bounding
boxes and a per-mesh look have not been read yet.

## Why it was not caught

The reduction checks measure triangle counts, trunk height and heap use, not how the reduced tree looks from the
side and from above. The earlier fix of [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md) restored
trunk heights of 31 of 250 reduced flora meshes and was judged by height ratios, not by pictures of each tree.

## Reproduction

Always at the three spots above (the model is the same everywhere it is placed).

## Repair

None yet. Proposed direction (maintainer's idea, decided as the direction to evaluate): looking at a 3D tree from
above, cut it into slices, as some PlayStation rally games did, and do that for many trees, existing sprite trees
included.

- Crossed vertical planes through the trunk (two planes, four slices), each textured with the tree's own outline
  rendered from the original mesh, transparent pixels kept (the sprite shape rule: the outline survives).
- Quake's oriented sprites (a sprite drawn as a fixed plane in the world, transparent pixels skipped) draw this
  without new drawing code. The recipe side exists: `tools/visual_recipes.py`, `prepare_sprite_replacements`.
- Apply it to the `flora_bc_tree` family first, then evaluate it for the existing sprite trees.
- Alternative: angle impostors, each tree pre-rendered from the original mesh from 8 directions with the alpha
  outline kept, the engine picking the frame by the view angle relative to the placement's yaw; Quake sprite
  drawing does the rest, only the angle pick is new engine code. The project tried eight-view scenery impostors
  in A500 v0.0.7, which were parked as too slow on an A500 (see the optimisation history), and the distant-terrain
  notes mention angle impostors for vegetation.
- Before either becomes a default: A/B against the current mesh and the original game in headless OpenMW at the
  same poses (headlamp off, plus a clip), and a like-for-like cost comparison (what each variant loads and draws).

Island-wide check to do first (rule: think in scale): list every `flora_bc_tree_*` mesh and mark which come out as
a pyramid with a box; the table above gives the triangle counts, the models' bounding boxes are still to be read.

## Verification

None yet. Done means: the island-wide list, the three pinned spots checked in game with a headlamp-off still and a
clip each, an OpenMW reference at the same poses, and the frame cost measured against the current mesh.

## Prevention

A look check for every reduced flora mesh: render the reduced model from the side and from above beside the
original, and fail on a crown that collapses to a flat slab.

## Related

TREE-PILLAR-28 and TREE-VIEW-FLOAT-38 (sprite trees), HORIZON-FLORA-SPRITES-32 (the sprite shape rule),
[CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md),
[CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md).

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
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions

<!-- END GENERATED CATEGORY -->
