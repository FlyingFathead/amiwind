# World map manifest (design)

Status: default build policy, updated 13 October 2026. The historical measurements below describe earlier builds; current builds use the manifest and final-payload gates described here.

<!-- contents start -->
## Contents

- [The rule](#the-rule)
- [What happens today (v0.0.36-dev3, measured)](#what-happens-today-v0036-dev3-measured)
- [What still reads a legacy map of a CHIM cell](#what-still-reads-a-legacy-map-of-a-chim-cell)
- [The manifest](#the-manifest)
- [Checks](#checks)
- [Step 2: region cells without their legacy map](#step-2-region-cells-without-their-legacy-map)
- [Step 2b: divided cells (CHIM-REGION-DIVIDED-CELLS-36)](#step-2b-divided-cells-chim-region-divided-cells-36)
- [Step 3: Seyda Neen CHIM-native (done, v0.0.36-dev5)](#step-3-seyda-neen-chim-native-done-v0036-dev5)
- [Collision check (before any stage)](#collision-check-before-any-stage)
- [Order of work](#order-of-work)

<!-- contents end -->

CHIM replaces the selected exterior BSP maps by default: no additional cleanup flag is needed. Terrain, scenery and flora stages skip those legacy maps. The image step rejects duplicate legacy maps before partition packing, and records removed files and payload counts in `chim-removed-legacy.json` and `legacy-maps-of-chim-cells.json`. Required BSP interiors and other routed BSP cells remain. Historical build caches are separate from the playable HDF payload.

## The rule

A cell that is on CHIM (a CHIM area such as a town, or a CHIM region cell) has no legacy map in the build: no stage
converts, compiles, passes over, stages or ships its legacy region map, unless a recorded engine need keeps one
("kept because ..."). The builder decides this once, before the first stage, from the CHIM coverage, and every stage
reads that decision instead of deriving its own map list (BUILD-LEGACY-TOWN-MAPS-SHIPPED-36).

## What happens today (v0.0.36-dev3, measured)

- The coverage is known before the first stage: `tools/build.py` resolves the CHIM areas and the `--chim-regions`
  cells (`resolve_chim_regions`) before any stage runs.
- The world terrain, world scenery and world flora stages still build every open-world map (2,532), including the
  270 maps of CHIM region cells; the image step requires a complete world overlay.
- The image step converts Seyda Neen into 65 legacy region maps, runs every per-map pass (sky, hidden-surface cull,
  hand stamps, optimizer, harvest, actor grounding, entity tracker) over those and the 270 region maps, and then
  removes them: 435,379,983 bytes listed in `chim-removed-legacy.json`. None of them ships.
- The 42 `bm*` maps in the image are Balmora interiors (they stay Quake maps), not legacy region maps.

## What still reads a legacy map of a CHIM cell

| Reader | What it takes | Replacement |
| --- | --- | --- |
| CHIM region frame map (`chim.frame_map.build_region`) | worldspawn, player start, point entities (flora sprites, sounds); check that every static is a CHIM placement; activated objects | entity rows from the game data per cell, as CHIM-native towns do (`tools/chim_town.py`) |
| Seyda Neen frame map and its two special maps (`intro_docks`, `sncourt`) | entities incl. grounded actors, origin check, walk check against the legacy docks map | Done (v0.0.36-dev5, step 3 below): Seyda Neen is CHIM-native; no Seyda Neen legacy map is read or made |
| Night lighting tables | lamps of the final maps | lamps from the CHIM world's placements for CHIM cells |
| Harvest catalogues, entity tracker | per-map rows | rows from the CHIM world (as CHIM-native towns already do) |

## The manifest

`world-manifest.json`, written into the run folder before the first stage, its SHA-256 in the recipe and the
receipt. One row per exterior cell map and interior map:

- `map`, `kind`: `chim-area` (frame map of a CHIM area), `chim-region-cell`, `legacy-region`, `interior`,
  `special` (a sub-cell section such as the intro docks);
- `cells`: the game cells it covers; `inputs`: its source inputs with their SHA-256;
- `stages`: the stages that work on it;
- `kept_because`: only for a legacy map of a CHIM-covered cell, with the engine need that keeps it.

Stages take the manifest (its relevant rows are part of their key) and skip every map whose kind says CHIM. Per-map
work of all stages becomes units of the shared worker pool, keyed by the SHA-256 of their inputs and scheduled
largest first.

## Checks

- The image step's replace-in-place step becomes a check: it must find 0 legacy maps of CHIM cells. The image
  summary prints `legacy maps of CHIM cells: 0`, the bytes saved and the payload by kind.
- A test builds the manifest from the dev3 inputs (its CHIM areas and 270 region cells) and finds no legacy map of a
  CHIM cell in any stage's work list.

## Step 2: region cells without their legacy map

Measured on the v0.0.36-dev3 run: every one of the 270 CHIM region frame maps holds exactly two entities, the
worldspawn and the player start; none carried a static, a flora sprite or a sound from its legacy map (all 270 cells
are coast and seabed). What the legacy map still gives the frame map:

| From the legacy map | Where it really comes from | Without the legacy map |
| --- | --- | --- |
| worldspawn (`message`, `aw_hull`, the shared-sky keys, the hand timing and eye height) | the world terrain converter's worldspawn, then the exterior sky and hand metadata passes | one shared function writes the open-world worldspawn with those keys; the passes call it too |
| player start `0 0 z`, angle 90 | the terrain height at the cell centre + 24 (the world terrain converter) | the same height from the terrain survey, no map compiled |
| statics, flora, sounds, activated objects | none in the 270 cells | refused as today if a cell has any: such a cell needs its rows from the game data first |
| the check that every static is a CHIM placement | the legacy map's statics | the CHIM stage's own placement check (the cell's references in the game data) |

With that, the stages read the manifest: world terrain keeps every directory row (the engine resolves the map by
name) but compiles no map for a CHIM region cell; world scenery and world flora leave those cells out and their
overlay checks accept exactly the manifest's cells as missing; the image writes the region frame maps from the game
data before any pass. The method that copies from the legacy map stays selectable (labelled, for an A/B check of
the two: on dev3's inputs both must give the same worldspawn keys and start).

Done (image side): `--chim-region-rows game-data` (default; `legacy` keeps the earlier method). A/B on the v0.0.36-dev3
run's own files, all 270 region frame maps made both ways: 117 are byte-identical; 150 differ only by the world terrain
converter's `wad` key (a compiler input the engine never reads), one by that key and its start, and two by their start
alone: a static stands at the cell centre there, and the legacy start was inside it (the new start stands on it).

Done (stages): world terrain, world scenery and world flora take the CHIM region cells (`--chim-regions-cells`, given by
the builder only with `--chim-region-rows game-data`) and make no map for them; world terrain keeps their directory rows
(origin from the terrain, as for a compiled map). Their receipts mark those rows, the image's install steps and payload
preflight accept exactly them and refuse a staged legacy map of such a cell, and the entity tracker counts the cell's CHIM
placements in place of its map.

## Step 2b: divided cells (CHIM-REGION-DIVIDED-CELLS-36)

Status: done in source (v0.0.36-chimport-x), 11 October 2026.

**What the legacy layout really is (measured on the v0.0.36-dev4 run's own world terrain receipt).** The open world
has 2,532 maps over 1,404 cells: 1,076 cells are one map, 316 are 2 x 2 maps and 12 are 4 x 4 maps (the survey splits a
cell whose geometry is over its triangle ceiling; 8 maps come from the recorded refinements). Every map's core lies
inside ONE cell: the cores of a divided cell tile exactly that cell, and no map's core crosses a cell border. What
reaches across the border is only a map's apron (its coverage, the core + 896 units on every side), which draws the
neighbouring ground and objects up to the fog.

**Why the preflight refused far too many cells.** It counted the tracker's `legacy.maps` list. That list is not the
cell's own maps: it adds every map whose apron holds an object of the cell (the entity tracker's `map_cells`), so a
one-map land cell is listed with 3 to 90 maps. Of the 621 finished land cells, 473 are one map (the preflight refused
about 305 of them for nothing) and 148 are truly divided.

**The rule.** A divided CHIM region cell is ONE CHIM frame (the frame is always one cell, as before). Its legacy maps:

- none of them is made (world terrain, scenery and flora take every map of the cell as a CHIM map, `chim_region`);
- the world terrain stage widens the directory row of the cell's first map (lowest index) to the whole cell: origin the
  cell centre, core the cell, coverage the core + 896 (`merge_chim_rows`); every other map of the cell keeps its row
  (the runtime needs sequential names `vf0000` ...) with the same origin, core and coverage, marked as an alias of
  the first (`chim_region_alias`). It refuses rows that do not tile the cell exactly;
- the engine takes the FIRST directory row whose core holds a point (`aw_world.c` `AW_WorldDestination`,
  `AW_WorldMapTarget`), so every point of the cell resolves to the first map's name and no alias is ever a
  destination: no engine change. The image installs one frame map under that name (`frame_map.region_owned`), sets
  the origin z of the row and its aliases together, records the aliases in the frame map's record and removes any
  legacy map or harvest catalogue a stage still made under an alias name (recorded). The entity tracker counts the
  cell once (`region_map_names(..., primary_only=True)`);
- the earlier method (`--chim-region-rows legacy`, which copies ONE legacy map's rows) cannot take a divided cell:
  its preflight keeps the old one-map check and the image refuses a divided cell in that mode.

**Legacy maps of the neighbours.** A neighbouring legacy map keeps only its own cell as its core: it owns nothing of
the CHIM cell. Its apron still shows the CHIM cell's ground and objects from the legacy side up to the fog, exactly
as beside a one-map CHIM cell (dev3, dev4): that is what the player sees across the border before the handover, and
cutting it would open the gap the far band and the hand-over pop-in findings describe (CHIM-FAR-BAND-GAP-36,
CHIM-HANDOFF-POPIN-36). The edge stitcher's parts are per frame and unchanged for a divided cell: the frame's
terrain-only margin (896, the handoff core = the cell) and the shoreline refinement. The border audit now measures
region frames too (`tools/chim/stitch.py audit --regions all|X,Y`).

**Tests** (`tests/test_chim_regions.py` `DividedCells`): no legacy map of the cell is made and no made map's core
reaches into it; one row owns the cell and the engine's lookup finds it at every sampled point while the neighbours
keep their own; rows that do not tile the cell are refused; the image writes one frame map for a 2 x 2 cell, owns
all four names and counts the cell once; rows that were not widened, and the earlier method, are refused.

## Step 3: Seyda Neen CHIM-native (done, v0.0.36-dev5)

The legacy chain cut the scene stage's complete converted town (`maps/seyda.bsp`, made from the game data by the scene,
bsp, npcs, hands and intro stages) into 64 region maps and the two special scenes (the intro docks, the Census
courtyard), compiled each of them (in the actor-contact stage and again in the image step), installed the town flora
into them, and then took the frame maps' entities from them before removing them.

The `chim-town-seyda` stage (`tools/chim_town.py`, `prepare_seyda`) now takes the same entities from the complete town
directly, by the same rules and the same code (nothing compiled):

- the region and special cuts: `prepare_seyda_regions.select_entities` per region coverage, and
  `prepare_intro_docks.keep_entity` then `select_entities` with the route polygon for the specials;
- the town flora sprites: the flora overlay's own selection (`prepare_world_flora.overlay_selection`, `sprite_rows`) and
  legacy sprite replacement (`install_town_flora.derive_bindings_fields`, `bound_legacy_sprite`); the flora meshes and
  the solid sprites' collision are CHIM world placements (`chim.seyda`) as before;
- the frame rows: `chim.frame_map.frame_entities` over the cut entities; the residents fitted on the CHIM frame's own
  collision (`ground_actors`, as Balmora and the Vivec Arena); the objects the engine activates (the courtyard barrel)
  with their brush model box from the complete town;
- the statics check both ways against the CHIM frame's placements (the image's flora and harvest changes from the CHIM
  world's parity record).

Its output holds the town frame rows, the two special frames' rows, the activated objects and the region table
(`seyda-regions.txt`: harvest catalogues and saves follow it). The image step writes the three frame maps from it,
runs the arrival, walk, actor, stair, heap and engine-limit checks on them, and stages no Seyda Neen legacy map (the
scene's complete town is removed from the staged payload at once). The actor-contact stage makes no Seyda Neen region
maps (`--seyda-chim-native`).

Parity on the v0.0.36-dev3 run's own files (its legacy-chain frame maps): the town frame's 243 entities, the intro
docks' 56 and the courtyard's 14 are identical (three residents' fitted height differs by 0.00001 unit: the frame
collision instead of the region map's), the activated barrel's box is identical, and 360 statics match the CHIM
placements both ways. The stage takes about 40 s; the chain it replaces compiled 66 maps twice.

Still built: the complete town map itself (the bsp stage), because the scene chain's later stages write the residents,
hands and intro entities into it; it is the stage's source of entities and never staged or shipped. Moving that carrier
off a compiled map is a follow-up.

## Collision check (before any stage)

The builder writes the manifest and checks it before the first stage (`world_manifest.collisions`): every cell has one
owner. It refuses the plan, listing the cells, when a cell is claimed twice, when an open-world stage's work list would
make the legacy map of a CHIM region cell (it does not take exactly the manifest's cells), or when a legacy map of a CHIM
cell is made with no recorded "kept because". Recorded reasons today: the earlier region method
(`--chim-region-rows legacy`) and an A/B regression build with a retired flag (`--legacy-area TOWN`, `--seyda-recorded`,
`--chim-native-towns off`; refused in developer mode without `--override`). The Seyda Neen town chain is no longer a
reason (v0.0.36-dev5): a CHIM area's legacy chain without a retired flag is refused.

## Order of work

1. The manifest from the coverage, with the image check and summary (reports what the stages still build).
2. Region cell entity rows from the game data; world terrain, scenery and flora skip CHIM region cells; divided cells
   are one frame each (step 2b).
3. Done (v0.0.36-dev5): Seyda Neen CHIM-native; its legacy chain leaves the build (the old method stays selectable as
   a labelled regression build: `--legacy-area seyda --override legacy-area`). See "Step 3" below.
4. Per-map units of every stage in one pool.
