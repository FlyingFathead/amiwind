# The first Solstheim CHIM frame, measured

_Last updated with AmiWind v0.0.64-dev3 (10 November 2026)._

<!-- contents start -->
## Contents

- [What was built and how](#what-was-built-and-how)
- [The frame against the limits](#the-frame-against-the-limits)
- [Where the faces go: the trees](#where-the-faces-go-the-trees)
- [The trees as star prisms (built, 10 November 2026)](#the-trees-as-star-prisms-built-10-november-2026)
- [The trees as crossed panels (computed, the first study)](#the-trees-as-crossed-panels-computed-the-first-study)
- [What stopped the first runs](#what-stopped-the-first-runs)
- [What the numbers point to](#what-the-numbers-point-to)
- [In the emulator (FS-UAE, 32 MB Fast)](#in-the-emulator-fs-uae-32-mb-fast)
- [In the forest: original trees (A) against star trees (D)](#in-the-forest-original-trees-a-against-star-trees-d)
- [Not measured yet](#not-measured-yet)

<!-- contents end -->

Solstheim (Bloodmoon) is planned as an optional layer of the world, with its own CHIM store. The census
([EXPANSIONS-CENSUS-v0.0.64.md](EXPANSIONS-CENSUS-v0.0.64.md)) counted its placements; this page builds its densest
forest cell as a real CHIM frame and measures it against the engine's limits at 32 MB Fast RAM. Every number below is
MEASURED on the built frame unless the row says it is computed.

## What was built and how

| Item | Value |
| --- | --- |
| Frame | exterior cell -23,20 (frame `rcm23_p20`): the Solstheim cell with the most trees (96 trees in 127 placements, census of Bloodmoon.esm) |
| Why this cell | the densest cell overall (-20,23, 579 placements) holds 13 trees; -23,20 is the densest forest, the case the tree plan has to answer |
| Builder source | v0.0.64-dev1 (commit 25fc5de0) plus `tools/chim_layer_data.py` (this branch) |
| Game data | the maintainer's GOTY data: Morrowind.esm `5c3c8c2c...`, Bloodmoon.esm `bd27090d...`, Morrowind.bsa `3dcd5e6b...`, Bloodmoon.bsa `7c209567...` |
| Layered test data | `python3 tools/chim_layer_data.py --data-files <Data Files> --layer Bloodmoon --out <dir>`: the base master with Bloodmoon's 10,473 records appended (18 exterior cells the base already has and 284 object ids it already defines left out; land textures numbered after the base's 107), one archive of 12,609 files (Bloodmoon's file wins) |
| Frame build | the CHIM stage's own command as the v0.0.63 release build runs it (`tools/chim_build.py --terrain-hull compiled --terrain-refs on --terrain-pack generate --uv-scroll turbulent --lighting-type hybrid --validate --stats`), with `--chim-regions-cells=-23,20:l`, `--jobs 12`, a private unit cache, and for this test `AMIWIND_COLLISION_HULL_POINTS=all` and `--stair-collision-method 0` (see [What stopped the first runs](#what-stopped-the-first-runs)) |
| Build time | 17 s for the frame, validation and every gate (12 jobs) |
| Compared with | the v0.0.63 release world, `2026_11_09_v0.0.63_full-v0.0.63-release_84bc6f5` (its `chim-stats.json` and `chim-heap.json`: 1,351 frames of Vvardenfell) |

The builder option `--chim-sol-test CELLS` (test builds only) runs the same two steps as stages `chim-sol-data` and
`chim-sol` into `run/chim-sol`; both are keyed by Bloodmoon's files, no base stage is, and the image does not take them.

## The frame against the limits

| Limit | The Solstheim frame | Vvardenfell (v0.0.63 release, whole island) |
| --- | --- | --- |
| CHIM zone at 32 MB Fast (6,864 KiB = 7,028,736 bytes; ring budget 6,242,304 bytes) | active ring peak 3,838,368 bytes (61 % of the budget), load ring peak 4,474,144 (72 %), largest block 432,944; 0 of 3,600 positions over | every frame passes; the largest resident ring of the stats 5,921,132 bytes |
| Frames that need the 32 MB mark (within 64 KiB of the 16 MB budget) | 0 | (as shipped) |
| Zone walk (engine allocator, lawnmower, 2,376 steps) | passed: locked peak 4,869,808 bytes, 0 failed loads, 0 holes, 139 model loads | passed |
| Models | 126 stored model variants, 40 in the peak ring | 32,564 over the island, 198 in the largest ring |
| Faces stored | 50,387 model faces + 2,000 terrain | 10,997,817 |
| Placed faces in the frame | 238,504 (431 placements, the apron's copies included) | 73,526,062 over 467,005 placements |
| Faces drawn per view (placed models, all chunks of the view) | median 45,964, maximum 61,175 | median 7,562, maximum 59,137 |
| Placements sent per view | median 81, maximum 107 | median 54, maximum 451 |
| Placements over 16 BSP leaves | 49 (8 to 21 per view) | 84,539 (11 to 167 per view) |
| Textures (the store's table, not BSP texinfo) | 71, 46 in the peak ring | 1,126 |
| Edicts | placements are chunk records, not edicts (no edict use); the cell's live actors are 2 NPCs and 8 levelled creatures, not part of this test frame | MAX_EDICTS 600 |
| Efrag links | ring peak 74 placements of 61,440 links | passes |
| Frame size on disk | 6,512,604 bytes (25 sector files 6,493,276, index 12,664, frame 6,664) | 1,351 frames |

The memory side fits with room to spare: the forest frame uses 61 % of the ring budget at 32 MB Fast and needs no
32 MB mark. The drawing side does not: the median view of this frame draws six times the faces of the median
Vvardenfell view, and its worst view is 3 % above the worst view anywhere on Vvardenfell.

## Where the faces go: the trees

| | Value |
| --- | --- |
| Tree placements in the frame (with the apron) | 327 of 431 |
| Faces of those placements | 207,072 of 238,504 (87 %) |
| Faces per tree after the CHIM reduction | 472 to 724 (mean 633) |
| Most placed faces | flora_tree_bm_02 at scale 2 (40 placements, 28,200 faces), flora_tree_bm_07 (41, 21,238), flora_tree_bm_01 (27, 19,305) |

The 14 Bloodmoon tree models are kept whole by today's reduction (the reduction keeps every closed edge); one colony
tower (3,085 faces) is the largest single model of the frame.

## The trees as star prisms (built, 10 November 2026)

Tree type 2, route D of [WORLD_TREE_SPRITES.md](../WORLD_TREE_SPRITES.md): every Solstheim tree model drawn as a
closed, opaque star prism: seen from above a four-pointed star; three stacked tiers that taper upward, starting where
the model's needles start (its lowest vertex on a see-through needle material), so the bare trunk shows below; a
hexagonal trunk of six bark faces without caps, its width from the bark's own vertices (wider at the foot, narrower
under the crown). The star's needle faces take an opaque needle texture baked from the model's side view (the
see-through texels filled from their neighbours), so no black gaps. The frame was built twice from the same source
(v0.0.64-dev2 line, branch v0.0.64-soltrees, base commit 8d979c39), the same stage command and data, 8 jobs: A with
the original models, D with `tools/chim_tree_star.py` (the chim-sol stage's `--chim-sol-tree-copies star`, settings in
`config/tree-copies.json`: 3 tiers, point depth 0.45, no undersides, 6 trunk sides, baked needles). Every number is
MEASURED on the built frames (chim-stats.json, chim-heap.json).

| Frame -23,20 | A: original trees | D: star prisms | D / A |
| --- | --- | --- | --- |
| Faces per tree | 472 to 724 | 30 (24 crown, 6 trunk) | |
| Tree faces placed (321 tree placements) | 204,640 | 9,630 | 0.05 |
| Placed faces in the frame | 238,504 | 43,494 | 0.18 |
| Faces drawn per view, median | 45,964 | 6,096 | 0.13 |
| Faces drawn per view, maximum | 61,175 | 16,942 | 0.28 |
| Model faces stored (126 variants) | 50,387 | 30,885 | 0.61 |
| Textures in the store | 71 | 77 (the baked needle textures) | |
| Model bytes of the peak ring (49 models) | 3,084,564 | 1,769,176 | 0.57 |
| Placements sent per view, median / maximum | 81 / 107 | 83 / 109 | |
| Frame build time | 64 s | 44 s | |

Faces per view, median: before 45,964 / removed 39,868 / total 6,096, against the Vvardenfell median of 7,562. The
remaining faces are the frame's other models (the colony tower alone has 3,085). Collision is unchanged (each
tree keeps its own). The zone walk passes in both. The baked copies (billboard and four 45-degree views per model,
`tools/chim_tree_copies.py`) are 194,295 pixel bytes for the 14 billboards and 777,180 for the four views of all 14
models; they are the far copy and the texture source of the next step, not in the frame yet.

Not measured yet: the frame time and the renderer's posted surfaces and edges (the engine posts at most 800 surfaces
and 2,400 edges a frame and drops the rest) need the frame in the image.

## The trees as crossed panels (computed, the first study)

Not built: the tree type 2 of docs/WORLD_TREE_SPRITES.md (crossed panels, an eight-spoked star) is a study item and
has no builder path yet. Computed from the measured placement rows above, replacing every tree placement's faces by
the panel count and keeping every other placement:

| Tree drawn as | Faces per tree | Frame placed faces (computed) | Of today |
| --- | --- | --- | --- |
| the original model (today, measured) | 633 (mean) | 238,504 | 1.00 |
| eight crossed half-panels (the star) | 8 | 34,048 | 0.14 |
| two crossed panels | 4 | 32,740 | 0.14 |
| one camera-facing billboard | 2 | 32,086 | 0.13 |

At the same share per view, the median view would fall from 45,964 to about 6,600 faces with the star (computed), in
line with the Vvardenfell median. The panels' cost is fill (overdraw of the transparent pixels), which a face count
does not show; that needs the frame time on the emulator.

## What stopped the first runs

Both are registered and both apply to every Solstheim frame, not only this one:

- The collision surface check refused 25 Bloodmoon meshes (rocks, snow banks, the ice exits, the garden plot, a
  colony tower: walkable collision 9 to 64 units under their convex pieces) that the measured table
  config/collision-hull-surface.json does not list (CHIM-SOLSTHEIM-HULL-SURFACE-64). The test frame took the surface
  rule on every mesh (the measurement mode); the layer needs table rows.
- The geometric stair check (stair collision method 1) failed on three Bloodmoon meshes, act_bm_garden_plot_01,
  ex_colony_house02 and ex_colony_wall_02 (CHIM-SOLSTHEIM-STAIR-CHECK-64). The test frame used method 0. No stair
  walk was run.

The frame's face count is CHIM-SOLSTHEIM-TREE-FACES-64.

Both are settled since (v0.0.64-dev2): the 25 meshes are rows of config/collision-hull-surface.json and the three
stair meshes are on config/stair-check-known.json (they keep method 0's collision until method 1 makes them pass),
each named under the table's `layers` block (bloodmoon). The frame now builds with the shipped defaults (the
surface rule from the table, stair collision method 1): collision surface check 73 meshes, 0 over a step; stair
check "known" (5 meshes with 6 flights, 1 ships a stairway collision mesh); 22 s at 8 jobs. A stage that does not
read Bloodmoon's files keys these tables without the layer's rows, byte for byte as they were before them
(tools/build_cache.py `LAYER_ROW_TABLES`, tests/test_game_input_keys.py), so the base CHIM world keeps its key.

## What the numbers point to

- Memory is not the limit of a dense Solstheim forest on CHIM: 61 % of the ring budget at 32 MB Fast.
- Drawing is: the trees are 87 % of the faces and push the median view to six times Vvardenfell's. The Solstheim
  trees should not ship as the original models: the crossed-panel tree (tree type 2) with the mesh only close up, or
  billboards where that is too heavy, is the route, and its frame time on the emulator and the Pi decides between
  them.
- The layered path builds Solstheim with the base converters unchanged; what it still needs is table rows for the
  Bloodmoon meshes and three stair fixes, then the store (chimsol) in the image.

## In the emulator (FS-UAE, 32 MB Fast)

A MiniWind test image (recipe config/recipes/miniwind-solstheim.json, `--chim-sol-test`, build
`2026_11_10_v0.0.64-dev2_miniwind-solstheim-solstheim-frame5_5c1b646`, source commit 5c1b6466) carries the frame as the
test store chimsol. The console's `map solm23p20` loads it after the Balmora frame (the engine changes store between the
two maps). FS-UAE, 68040 JIT preset, 32 MB Fast, `dbg rcount 1`, a turn in six steps at the frame centre:

| | The Solstheim frame -23,20 | Balmora, same session and preset |
| --- | --- | --- |
| Frames per second (fps10 / 10) | 65.5 to 70.7 | 39.4 to 60.7 |
| R_RenderView per frame | 7.9 to 12.0 ms (looking at the trees), 4.5 to 5.8 ms (open ground) | 13.8 to 22.3 ms |
| Slowest frame of a second (pk) | 94 ms (the first second after the load), then 28 to 56 ms | 34 to 126 ms |
| Brush model faces tested / front | 2,033 to 3,849 / 1,003 to 1,919 | 4,748 to 5,263 / 2,245 to 2,505 |
| Placements in view (chim pl) | 33 resident, 14 to 17 drawn | |
| CHIM ring after the load | models 33 (1,775 KiB), textures 18, chunks 29; zone 2,881 KiB used of 13,007; 0 failed loads | |
| Load | 120 models, 98 textures, 61 chunks: 1,598 KiB in 815 reads, 77 opens | |
| Fast RAM after the load | 2,507 KiB free, largest block 2,424 KiB | |

The emulator's host frame stays near 14 ms either way, so the JIT preset caps the frame rate; the renderer time is the
comparable figure. This first measurement leaves out the tree crowns: the pictures show the trunks of the trees near the
start and no crowns at all, so the needles (the frame's largest share of faces) were not in view and these renderer
times are not the cost of the forest (CHIM-SOLSTHEIM-CROWNS-NOT-DRAWN-64; the reason and the forest numbers are in
[the next section](#in-the-forest-original-trees-a-against-star-trees-d)). The frame time on the Pi 4B is not
measured yet. The HUD names the place "Vvardenfell / Region unavailable": the region table has no
Solstheim rows (WORLD-REGION-NAMES-VF-ONLY-64).

## In the forest: original trees (A) against star trees (D)

Why the first pictures showed no crowns: the frame centre, where the map starts the player, has no tree within the
far test's reach (299 units in these runs; the nearest trees of the 327 stand 360 to 450 units away), so the views
held two rocks and open ground. Flying into the forest (noclip, the same script for both images: a turn, then
forward in 2-second steps, 8 stills, counters every second) shows the crowns in both images.

Both images are MiniWind test builds of commit e7bfa707 (A, `--chim-sol-test`) and 74b4da6e (D, the same plus
`--chim-sol-tree-copies star`), v0.0.64-dev3 engine; FS-UAE 68040 JIT preset, 32 MB Fast. The two flights do not
end on exactly the same headings (the turn is timed), so the views are close, not identical.

| In the forest of frame -23,20 | A: original tree models | D: star trees |
| --- | --- | --- |
| Renderer time per frame (R_RenderView) | 6.7 to 27.2 ms, most 10 to 17 ms | 2.1 to 5.5 ms |
| Brush model time per frame | 2.0 to 15.0 ms | 0.26 to 0.61 ms |
| Brush faces tested / front | 2,033 to 10,276 / 1,002 to 5,142 | 240 to 500 / 99 to 232 |
| Frames per second (capped near 71 by the preset) | 32.0 to 69.6 | 62.6 to 71.8 |
| Slowest frame of a second | 40 to 108 ms | 28 to 134 ms (four one-off hitches of 98 to 134 ms) |
| CHIM ring at the end | 44 models, 2,542 KiB; zone 3,875 KiB used | 37 models, 760 KiB; zone 2,095 KiB used |
| Fast RAM free at the end | 2,478 KiB | 2,446 KiB |

The star trees cut the renderer time in the forest to about a third and the drawn faces to about a twentieth, with
1.8 MB less in the CHIM zone. D's one-off hitches of about 120 ms are not explained yet (load of the next chunk
models while moving is the first suspect).

## Not measured yet

- The frame time on the Pi.
- The densest cell overall (-20,23, 579 placements, 13 trees).
- Fill cost of crossed panels.
