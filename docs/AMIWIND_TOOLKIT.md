# AmiWind Toolkit

![AmiWind Toolkit, last updated with AmiWind v0.0.31](images/amiwind-v0.0.31-toolkit-header.png)

<!-- contents start -->
## Contents

- [Starting it](#starting-it)
- [Your data](#your-data)
- [The three tabs](#the-three-tabs)
  - [World](#world)
  - [Local](#local)
  - [3D Inspector](#3d-inspector)
- [Map metrics layer](#map-metrics-layer)
  - [Making the layer](#making-the-layer)
  - [Reading it](#reading-it)
- [CHIM Progress Tracker](#chim-progress-tracker)
  - [Making the data](#making-the-data)
  - [Showing it](#showing-it)
- [Using it for development](#using-it-for-development)
- [Other parts](#other-parts)

<!-- contents end -->

The AmiWind Toolkit is the browser workbench for anyone developing AmiWind: it
shows how much of Morrowind's world has been converted to the Amiga, what is
missing and where, and lets you open any built map in 3D to see its actual
polygons. It runs entirely on your machine; nothing is uploaded.

Nothing in the public repository shows the game world. Every view of it is
made on your machine from your own Morrowind files and your own AmiWind build
output, and stays there.

The header line "Last updated with AmiWind v..." names the AmiWind version the
Toolkit was last updated and tested with. It is changed by hand when the
Toolkit itself is next worked on, not with every release.

## Starting it

Either way opens [`amiwind-toolkit/index.html`](../amiwind-toolkit/index.html).

**With your data preloaded (recommended).** A tiny read-only server, bound to
this machine only, serves the Toolkit and your files so everything loads at
once and the Local view opens maps without picking a folder:

```bash
python3 tools/toolkit_serve.py --data DIR --maps MAPS_DIR --open
```

`DIR` holds `world-progress.json` and the local layers listed below; `MAPS_DIR`
is a build's `id1/maps` folder. Add `--metrics FILE` for the
[Map metrics layer](#map-metrics-layer) and `--progress DIR` for the
[CHIM Progress Tracker](#chim-progress-tracker). Without `--open`, browse to the address it
prints (default `http://127.0.0.1:8031/`). Python standard library only.

**Straight from disk.** Open `amiwind-toolkit/index.html` in a desktop browser
and pick the files with the **Status**, **Island (local)** and **Maps folder
(local)** buttons. Browsers do not let a page opened from disk read other files
by itself, so each one has to be chosen.

## Your data

1. **Status.** Every image build writes `world-progress.json` (counts and status
   only, no names) next to `entity-tracker.json`.
2. **Island (local)**, optional, made from your own `Morrowind.esm`:

   ```bash
   python3 tools/world_progress_background.py --esm /path/to/Morrowind.esm --out island.png
   python3 tools/world_progress_background.py --esm /path/to/Morrowind.esm --out island-world.png --style world
   python3 tools/world_progress_background.py --esm /path/to/Morrowind.esm --out island-cells.json --style cells
   ```

   `island.png` is the topographic view, `island-world.png` the look of the
   game's own World map, and `island-cells.json` the Local level: each cell's
   terrain, its original placements, and the place and region names.
3. **Maps folder (local).** A build's `id1/maps`, for the 3D Inspector.

## The three tabs

### World

![World view: the whole island on the topomap, with Balmora and Seyda Neen outlined as full town maps and named places and interior entrances shown](images/amiwind-v0.0.31-toolkit-world.png)

Vvardenfell's exterior cells, one square per cell, north up.

- **Bottom layer** (‹ dropdown ›): the topomap (terrain converted for the whole
  island; the basis every other layer sits on) or the game's own World map look.
- **Layers**: topomap, heatmap of original entities, share of entities placed,
  full town/area maps (white border, black outline), content missing, interiors,
  named places, points of interest (interior entrances: green converted, white
  not converted), owner-checked cells, cell grid. More switches behind the
  cog (Options).
- **Map metrics** (only when a metrics layer is loaded): the estimated heap and
  BSP limits of every exterior cell; see [Map metrics layer](#map-metrics-layer).
- **Grid: on | off** at the map's top left switches the cell grid, in step with
  the Cell grid layer.
- **Zoom**: − / reset / + at the top right, the mouse wheel, or drag to pan.
- **Keys**: while the map is active (clicked, or under the mouse), the arrow
  keys or WASD pan it: up/W north, down/S south, left/A west, right/D east.
- **Hover**: the tooltip gives the cell's place and region, its map, entities
  placed against the original, interiors converted and named places. Over an
  interior-entrance marker the marker turns gold and the tooltip starts with
  "Highlighted: <name>".
- **Click** a cell: the Selected-area bar names it ("Selected area: Balmora
  (West Gash Region) · cell -3, -2 ...") and **Local view** opens it.
- **Copy state (JSON)**: the Toolkit version, the loaded data, the layers and
  the selection, ready to paste into a bug report or a message.

### Local

One cell up close: its terrain, its named places and every original placement
(filled = placed, red ring = not placed), counted by kind (statics, doors,
lights, containers, NPCs and more), and the list of places in the cell with
whether each interior is converted. **Map** lists the built maps that cover the
cell; **Show in 3D** opens the chosen one in the 3D Inspector tab.

### 3D Inspector

The compiled geometry of a built map: from above, fly view or orbit, with
wireframe or solid display, optional textures with your own palette, polygon
heatmap, collision preview, a compass and orientation gizmo, face selection and
markup for planning, and session export. Until a map is loaded it says so under
the crosshair. Open a map with **Show in 3D** in Local, or with **Open BSP /
JSON** in the inspector itself. The inspector also works on its own:
[`amiwind-toolkit/map-inspector.html`](../amiwind-toolkit/map-inspector.html),
[details](POLYCOUNT_INSPECTOR.md).

#### Sub-cell cuts and the divider

The **Sub-cell cuts** panel shows where a map is, or would be, divided: region
borders and section cuts are drawn as translucent coloured rectangles standing
through the map, in the perspective and the From above views, with a label on
each. Hover one for its name and position. **Show cuts and region borders**
turns them all off; **Show coverage** turns off the dashed coverage outlines.

- **Load cut overlay JSON** draws an overlay written by
  `tools/region_cuts.py` (or exported by the divider). For a town region map:

  ```bash
  python3 tools/region_cuts.py town --config config/balmora.json --map bm019 --out bm019-cuts.json
  python3 tools/region_cuts.py town --config config/seyda-bounded-regions.json --map sn012 --out sn012-cuts.json
  python3 tools/region_cuts.py plan --plan section-plan.json --out room-cuts.json
  ```

  A town overlay holds the map's own core (solid) and coverage (dashed) plus
  the cores of every region that reaches into it, so the borders you see are
  the sub-cell cuts that pass through that map. A section plan overlay holds
  each section's coverage box and each portal as a plane at its split.
- **The divider** adds cuts by hand: **Add X cut** (a plane of constant X) or
  **Add Y cut**. Move a cut with the position box or slider, or drag it in
  **From above**; drag its end squares to shorten it. Undo and Redo cover every
  cut change. The panel lists, for every section between the cuts, its faces,
  the placements inside it and straddling it, lightmap bytes and an estimated
  heap share against the 11,534,336-byte map budget (an estimate, with its
  method printed under the numbers).
- **Export cut overlay JSON** saves the cuts and sections as an overlay;
  **Export section plan JSON** writes them in the format of
  `tools/prepare_interior_sections.py` (2 to 8 sections, one portal per shared
  cut), with the fields only a build can supply marked `PENDING`. **Import
  cuts** reads either file back. Nothing is installed or changed in any map.

Interiors are divided at doorways and corridors first
([interior sections](INTERIOR_SECTIONS.md)); the divider is where you try those
cuts against the actual polygons before writing the plan. Format and method:
[sub-cell cuts](POLYCOUNT_INSPECTOR.md#build-020-sub-cell-cuts-and-divider).

## Map metrics layer

The Map metrics layer shows, for every exterior cell, how close the maps
covering it come to the engine's limits: the estimated map heap against the
11,534,336-byte budget, and faces, texinfo, nodes, clipnodes, marksurfaces,
vertexes, edicts, inline brush models, static flames and lights against
theirs. It is an estimate made from your own game data, before anything is
converted, so you can see where the world will not fit and plan the sub-cell
cuts there.

### Making the layer

1. Run the builder's world estimate on your own Morrowind data files. It writes
   `metrics.json` and `metrics.csv`, one row per proposed map: every exterior
   sub-cell region (its core cells, set and counts) and every interior cell,
   each with `cur_*` columns (what the converters convert today) and `evr_*`
   columns (every placed object converted, actors as edicts).
2. Serve it with the Toolkit. The server converts the table when it starts:

   ```bash
   python3 tools/toolkit_serve.py --data DIR --maps MAPS_DIR --metrics metrics.json --open
   ```

   Or convert it once into the smaller layer file and serve that:

   ```bash
   python3 tools/world_metrics.py metrics.json --out world-metrics.json
   python3 tools/toolkit_serve.py --data DIR --metrics world-metrics.json
   ```

   Opened from disk, pick `world-metrics.json` with **Metrics (local)**.

The layer file (format `aw-world-metrics-1`) holds, per exterior cell, the
worst value of each metric among the regions whose core lies in the cell, its
ratio to the limit and the region it comes from, plus the cell's region list;
every region's values; every interior's values; and summary counts. Optional
columns missing from the table are left empty. It holds names and numbers from
your game data: keep it with your own files. Without `--metrics` the server
serves no layer and the World Map shows no Map metrics bar.

### Reading it

- **Map metrics** switches the layer; it widens the map to Solstheim.
- **Metric**: heap, faces, texinfo, nodes, clipnodes, marksurfaces, vertexes,
  edicts, inline models, static flames or lights.
- **Current content | Everything**: today's converters, or every placed object.
- **Texinfo limit**: 32,767 today or 65,535 planned.
- **Colours** (value / limit, as on the world heat map chart): the palest blue
  is up to 50 %, then one darker blue per 10 % up to 100 %; red is over the
  limit. Bloodmoon (Solstheim) cells have a dark outline. Town labels come
  from your local `island-cells.json`.
- The bar and the side panel count the cells that hold at least one region
  over the limit, and the cells with objects.
- **Hover** a cell: its coordinates and name, the worst value, its share of
  the limit and the region it comes from.
- **Click** a cell: the panel under the map lists every sub-cell region with
  its core in the cell, with all its numbers; the region that sets the cell's
  value is outlined for each metric. **3D** opens a region in the 3D Inspector
  when a map of that name is in your maps folder; the built maps covering the
  cell are listed with their own **3D** buttons.
- **Interiors table**: every interior (the Tribunal set is interiors only),
  filtered by set, by name and by "over any engine limit" (lights excluded) or
  "over the selected metric's limit", sorted by any column.
- **Copy state (JSON)** includes the layer, metric, content, counts and the
  clicked cell.

The limits are the engine's own: `AMIWIND_HEAP_MB` (the map heap budget),
`MAX_MAP_FACES`, `MAX_MAP_NODES`, `MAX_MAP_VERTS`, `MAX_MAP_MARKSURFACES`, the
clipnode count check (65,520), `MAX_EDICTS` (600), the inline model budget
(220), `STATIC_FLAME_MAX` (128) and `MAX_DLIGHTS` (32, as if every light were
a dynamic light). `tests/test_world_metrics.py` checks them against the
sources.

## CHIM Progress Tracker

The CHIM Progress Tracker drives and shows the whole-island conversion to CHIM, cell by cell: one record per
exterior cell, the interiors reached from it, what is converted, what each audit found, what the legacy converters had
mapped there before, and the order to convert the rest in. It is built on the data the Toolkit already has (the
World progress table for the legacy mapping quality, the Map metrics layer for risk and cost) and adds the CHIM side.

A headline sits at the top of the Toolkit page, on every tab: **CHIM cells: passed / land cells (percent)**. A cell
counts as passed only when it is converted **and every audit that was measured passed**. Audits that were not measured are
counted apart ("unmeasured audits on N converted cells") and are never counted as passed. Under the headline are the
breakdown (owner-approved, playtested, audits passed, converted with failing audits, converted with nothing measured,
not started) and a history line (passed cells per day). Click a number to highlight those cells on the map.

### Making the data

The data is derived from your own Morrowind files and your own build output, so it lives in a private folder, never in
the repository. `tools/cell_progress.py` is the only writer of that folder:

```bash
python3 tools/cell_progress.py ingest --out DIR \
    --progress world-progress.json --metrics world-metrics.json --cells island-cells.json \
    --bugs docs/bugs/bugs.json --ledger build-ledger.jsonl --areas config/cell-progress-areas.json \
    --chim-run balmora=BUILD_FOLDER --chim-run seyda=OTHER_BUILD_FOLDER \
    --data-files "Morrowind/Data Files" --png
```

- `--chim-run NAME=PATH`: a folder written by `chim_build --validate --stats` (its `chim-receipt.json`,
  `chim-validate.json`, `chim-stairs.json`, `chim-heap.json`, `chim-zone-walk.json`, `chim-stats.json`; every report is
  optional). Which cells a build converted comes from the chunks the frame owns placements in. The digest of each run is
  kept in `DIR/runs`, so later ingests need no access to the build folders. `--run-label` and `--run-commit` record a
  label and the source commit.
- `--data-files` parses your game files once into `DIR/mesh-census.json`: per exterior cell the references by type, the
  unique meshes, the doors and where they lead; per interior cell its counts and doors. Without it the tracker still
  works, without contents, mesh numbers and interiors.
- The command remembers its inputs (`DIR/sources.json`). Run it again after every build; it is idempotent: the same
  inputs give the same files. Anything it cannot measure is `not_measured`, never a guess.

Other commands, all of them go through the same ingester:

```bash
python3 tools/cell_progress.py result --out DIR --file RESULT.json    # per-cell stats, audits, errors from the conversion job
python3 tools/cell_progress.py record --out DIR --mechanism seam_tears --build NAME --status passed --cells "-3,-2 -3,-1"
python3 tools/cell_progress.py owner  --out DIR --status playtested --cells "-3,-2"    # or approved
python3 tools/cell_progress.py export --out DIR --csv cells.csv --json cells.json
python3 tools/cell_progress.py status --out DIR
python3 tools/cell_progress.py render-md --out DIR    # writes docs/chim/CELL_TRACKER.md (generated, compact, public)
python3 tools/cell_progress.py check-md               # header, private content and policy section of the committed page
```

`render-md` writes the public page [docs/chim/CELL_TRACKER.md](chim/CELL_TRACKER.md): the headline ("Done: N of 1,292"),
totals, a table per ring, failures by mechanism class, objects by type and an import policy generated from the code's own
constants. Re-run it after every ingest; the page is never edited by hand. `check-md` (and the test suite) fails when the
committed page lacks its generated header, mentions a private path, or has an import policy that no longer matches the code.

Completion levels (map fill, headline and totals): **Terrain complete** = all audits pass and every placed object except
actors is converted (bright green); **Cell complete** = terrain complete and every actor converted too (the same bright
green plus a solid white border around a run of such cells; the legacy full town/area map border is dashed amber).

A cell the conversion job found to hold nothing but terrain and water is sent with `"status": "empty"`: it gets its own
status and chip, **empty sea**, and is never counted as passed or converted. A converted cell whose only problem is hull-chain depth is sent with
`"policy_pending": true`: status **hull policy pending**, counted neither as passed nor as failing.

A result file (`aw-cell-result-1`) carries per cell: `converted`, `errors`, `audits` (mechanism, status, detail) and a
`stats` block (records, meshes new/reused, faces before/after, textures, bytes, chunks, hull, memory, vis, time). Every
field is optional. The audit mechanisms are the ones listed in `MECHANISMS` in the tool: format validation, stair walk,
memory fit (zone ring and heap), seam tears, hull bevels and chain length, sky-bank texels, hidden faces, far-terrain
coverage, sprite shape, actor grounding and doors/interior links. An audit result measured on another build than the
cell's current one is shown as stale and counts as not measured.

### Showing it

```bash
python3 tools/toolkit_serve.py --data DIR --maps MAPS_DIR --metrics world-metrics.json --progress DIR --open
```

`--progress` takes the folder the ingester writes (or its `cell-progress.json`). The file is read again on every
request: run `cell_progress.py` after a build and reload the page (or press **Reload progress**, or return to the window);
the server does not need a restart. Without `--progress`, or when you open the pages from disk, use **Import progress**
and pick `cell-progress.json`.

The **CHIM Progress Tracker** layer has its own bar and is exclusive with Map metrics (both colour cells); every older
layer stays selectable.

- **Colour by**: CHIM status; spiral ring; scout risk (the estimator's share of the tightest engine limit); legacy mapping
  quality (grade A full town/area map with 80 % or more of the entities placed, B full map, C terrain with some entities
  placed, D terrain only, E no terrain); open bugs linked to the cell; last build time; or any single audit.
- **Show**: all cells, any failing audit, any audit not measured, or one mechanism failing or not measured; the other
  cells fade.
- **Sweep order**: the **spiral** goes from the coast inwards, ring by ring (ring 1 touches the sea; sea-only cells that
  hold something are ring 0 and come first; Solstheim is its own island), always stepping to the nearest unvisited cell
  of the ring so the converted area stays contiguous. The **risk** list (scout list) goes riskiest first. Ring numbers are
  drawn in the cells when zoomed in, the next 25 cells of the chosen order are outlined, and the 25 riskiest cells are
  marked with a diamond. Both lists, 300 cells each, are also written to `next.json`.
- **Find a cell or interior**: one search box finds a cell or interior by in-game name, region, coordinates, cell ID,
  our map name or door reference number, and jumps to it on the map.
- **Hover** a cell for its status, ring and rank, risk, legacy grade and failing audits. **Click** it for the record:
  contents; the stats (records by type, unique meshes new and reused, faces before and after, textures, bytes CHIM against
  legacy, chunks, clipnodes and hull depth, zone ring and frame heap, vis, conversion time, errors; fields nobody has
  measured say "not measured"); the legacy mapping quality; every audit with its detail and build; the build provenance
  (build, source commit, CHIM version, world format); the linked bugs; and **the interiors reached from the cell**.
- **Interiors reached from a cell** are found from the door destinations in your game files: the interior cells whose
  doors stand in the exterior cell, with a door inside an interior leading deeper shown indented under it (loops are
  not followed twice, depth is capped at 8). Each row gives the in-game name, the cell ID, our map name where one
  exists, the door's reference number, object and position, the status ("not started" for CHIM, legacy converted or not),
  the contents counts and the linked bug IDs. Click a row for the interior's own page.
- **Overview** (nothing selected): the next ten cells of the chosen order, the audits over all converted cells, totals
  per island and ring, the CHIM builds read, and the **mesh-first view**: the store-once reuse curve (cumulative unique
  meshes against cells converted, in the spiral and risk orders, compared with every cell converting its own meshes) and the
  numbers behind it.
- **Export CSV** and **Export JSON** write the cells shown (after the filter): status, audits and every numeric stat.

`tests/test_cell_progress.py` checks the schema, the orders, the audit and "not measured" handling, idempotence, results,
the interiors tree and the serving, on synthetic data only.

## Using it for development

- **Find what is missing.** In World, turn on *Content missing* or the
  *Heatmap*; zoom in on the hot spots; hover for placed-against-original counts;
  open the cell in Local to see exactly which placements are not placed.
- **Check a converter change.** Rebuild, load the new `world-progress.json`
  (and maps folder), compare the cell counts and look at the map in 3D. The
  entity tracker gives the reason for every placement that is not placed
  ([trackers](trackers/README.md)).
- **Report a bug precisely.** Select the cell, press *Copy state (JSON)* and
  paste it into the report together with the in-game position.
- **Find what will not fit.** Load the Map metrics layer, pick a metric and
  *Everything*; click a red cell to see which sub-cell region is over and by
  how much, then plan its cuts in the 3D Inspector's divider.
- **Plan optimisation.** Open a heavy map in the 3D Inspector, use the polygon
  heatmap and face markup to find what to simplify; see the
  [Map Optimization Toolkit](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md).
- **Plan lighting.** [Light sources](LIGHT_SOURCES.md) counts every original
  lamp, candle, torch and fire per cell (`tools/light_sources.py census`).

## Other parts

| Part | What it is | Where |
| --- | --- | --- |
| Trackers | Entity tracker (original against placed, with reasons) and world progress table, written by every image build; POI checklist. | [trackers](trackers/README.md), [world progress](trackers/WORLD_PROGRESS.md) |
| Map optimisation | Map inspection, conversion and verification tools for reducing compiled-world costs. | [Map Optimization Toolkit](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md) |
| Console commands | Every `dbg` command in the game's own catalogue. | [console commands](AMIWIND_CONSOLE_COMMANDS.md) |
