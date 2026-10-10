# CHIM Progress Tracker

The CHIM Progress Tracker is how AmiWind keeps count of the open world on CHIM: for every exterior cell of the island, whether it is converted, what each audit found, how it is lit, what it still lacks and which release it is approved for. This page is the hand-written guide. The live figures are on the generated [CHIM cell tracker](CELL_TRACKER.md), the conversion itself is described in [CHIMport](CHIMPORT.md) (how the conversion works), and the file format the conversion hands to the tracker is the [cell result format](CELL_RESULT_FORMAT.md).

## Why it exists

The open world is 1,292 exterior cells on Vvardenfell (and 144 on Solstheim). Converting them one at a time and judging each by eye does not scale, and "it looks fine" does not catch a stair that cannot be walked or a frame that does not fit in memory. The tracker turns the conversion into numbers: one record per cell, one result per audit, one status per cell, and the same definitions everywhere (the Toolkit map, the generated page, the release notes). Anything that is not measured says "not measured": the tracker never guesses and never counts an unmeasured audit as passed.

## Data flow

1. **CHIMport converts cells.** Each cell is built into a CHIM frame and run through every audit the CHIM builder has.
2. **Per-cell result files.** CHIMport writes `aw-cell-result-1` files: per cell its status, audit results, errors and figures ([cell result format](CELL_RESULT_FORMAT.md)).
3. **`cell_progress.py ingest`.** The one writer of the tracker folder. It stores the result files, adds what it can measure itself (the census of your own game data, the estimator's risk, the lighting audit, linked bugs, build history) and writes `cell-progress.json`.
4. **`cell-progress.json`** is what everything else reads.
5. **Shown in two places:** the Toolkit's World Map (colours, legend, cell panel, live mode) and the generated page [CELL_TRACKER.md](CELL_TRACKER.md) (`cell_progress.py render-md`).

The tracker data is derived from your own game files, so the folder it writes is yours and stays private. The one thing a release publishes is a reference file with cell IDs, statuses and audit results only (see "Compare with the project" below).

## Statuses

A cell has exactly one status. Strongest first:

| Status | Map | Meaning |
| --- | --- | --- |
| Cell complete | bright green, solid white border around a run of such cells | Terrain and every placed object converted, actors included, every measured audit passed, and the cell is lit like the original |
| Terrain complete | bright green | The same, except that actors (NPCs, creatures) may still be deferred |
| Cell complete, awaiting lighting | bright green with cyan stripes, white border | Everything cell complete needs except the lighting audit; counts as done |
| Terrain complete, awaiting lighting | bright green with cyan stripes | Everything terrain complete needs except the lighting audit; counts as done |
| Owner-approved, Playtested | gold, teal | Set by the owner for a converted cell that passes |
| Passed | green | Converted and every measured audit passed, but something placed is still deferred or skipped |
| Empty sea | blue | Terrain and water only, nothing placed; counts as done |
| Hull policy pending | purple | The only open problem is a standing-hull chain deeper than the limit, waiting for one shared rule; neither passed nor failed |
| Converted, failing audits | red | At least one audit failed or the conversion reported an error |
| Not converted | magenta | The conversion was tried and could not finish the cell; a failure-type state, never counted as done |
| Converted, nothing measured | light blue | Converted, no audit measured |
| Not started | grey-blue | The conversion has not reached the cell |

Precedence: cell complete, terrain complete, the two awaiting-lighting levels, owner-approved, playtested, passed, hull policy pending, failed, not converted, not started. Nonvisual markers (door, travel, north and editor markers) are not drawn and not required, so they never block a level; light emitters without a mesh do cast light, so they stay under Lights and the lighting audit judges them.

**Done** = cell complete + terrain complete + the two awaiting-lighting levels + passed + empty sea, each on its own line. The generated page repeats the exact definitions in its import policy section, built from the code's own constants.

## Audits

Eleven mechanisms are measured per cell: world format validation, stair walk, memory fit, seam tears, hull bevels / chain length, sky-bank texels, hidden faces, far-terrain coverage, sprite shape, actor grounding and doors / interior links. Each one's pass rule and limit is in the [import policy](CELL_TRACKER.md#import-policy) of the generated page; it is not repeated here so the two cannot disagree. An audit result measured on another build than the cell's current one is shown as stale and counts as not measured.

## The lighting audit

A cell is only complete when it is lit like Morrowind. `tools/cell_lighting.py` counts the original light placements of the cell (by class, with and without a mesh) from your own master files, looks at how the CHIM build brought them to the frame (baked into lightmaps, the engine's night lamp table, or not at all) and how much of the terrain and the models carries real light data. The result is **lit** (every active light baked, every surface lit), **partial** (some light or some lit surfaces) or **unlit**; **not measured** when the cell is not converted. Lit is required for both completion levels; until then a cell that otherwise qualifies is shown as awaiting lighting. The Toolkit has a colouring by lighting status.

## The lava audit and the Lava layer

`tools/cell_lava.py` judges whether a cell's molten lava became Quake liquid ([LAVA.md](../LAVA.md)). The census counts the molten lava pools the original places in each exterior and interior cell (objects whose script hurts an actor standing on them, from your own master files; Molag Amur's lava-coloured rock is not molten and is not counted). The build's lava record (the CHIM receipt's `lava`: mode and pools by source cell) says how many became liquid. The result is **converted** (every pool a Quake liquid), **partial**, **mapped, not converted** (the cell is not built, or its build is from before the lava record), **static** (built with `--lava static`) or **not measured** (a census without lava counts); cells without lava have no row. The Toolkit's "Lava (mapped / converted)" colouring and the Lava preset show it on the map; the cell panel has a Lava line, and the overview line counts lava cells, pools and converted pools. The lava audit does not change a cell's completion level.

## Eligible for a release

"Eligible for vX" is the set of cells usable now for the next release, lighting done or not: every passed status (the completion levels, awaiting lighting included, owner states and passed) plus empty sea. The generated page prints the figure; the Toolkit has a "Show: eligible" filter and a legend preset.

## The release field and the version tracker

Which cells are approved for which release is an owner decision, kept separate from the measured data:

- The field is `release` (for example `v0.0.33`, `v0.0.34`) per cell, stored in `releases.json` next to the tracker data. Only `cell_progress.py release` writes it; conversion results and ingest never change it, and a re-ingest keeps it.
- Every change is also one line in `history.jsonl` with the host-clock date and who made it.
- `v0.0.33` is seeded with the cells of the shipped CHIM towns (Balmora and Seyda Neen) and marked shipped; `v0.0.34` starts empty and is filled by approving cells.

```bash
python3 tools/cell_progress.py release --out DIR --version v0.0.33 --cells shipped-towns --shipped
python3 tools/cell_progress.py release --out DIR --version v0.0.34 --cells eligible        # approve every eligible cell
python3 tools/cell_progress.py release --out DIR --version v0.0.34 --cells "ring:1 -3,-2"   # a ring and one cell
python3 tools/cell_progress.py release --out DIR --version v0.0.34 --cells "0,0" --clear    # take a cell back out
```

Selectors: a cell ID `x,y`, `ring:N`, `status:BUCKET`, `eligible`, `unassigned`, `release:VERSION`, `shipped-towns` and `all`. The map has a version pull-down (all versions, each release, unassigned, assigned to any) with a one-line summary per version (approved cells, how many are complete or awaiting lighting, how many are lit, how many still fail), the cell panel shows the cell's release, and the generated page has a per-release table.

## Legend checkboxes and presets

Every row of the map legend has a checkbox. Unticking a row **dims** the cells of that row (the same dimming as the status chips and the Show filter), so the island stays readable around what you picked; the box beside a gradient scale is disabled because a scale has no rows to untick. **all** and **none** tick or untick every row. The **Preset** pull-down sets the ticks in one go: Everything, Eligible for the next release, Awaiting lighting, Problems only (failed, not converted, hull pending), Not started, Lighting (switches to the lighting colouring), Lava (switches to the lava colouring) and Release content (only cells assigned to a release). Ticking a row by hand switches the pull-down to Custom. Your ticks, preset and version choice are remembered in the browser (local storage; the page works without it).

## The map view

The World Map shows the tracker on the island, one square per cell. The whole island fits the window (the **fit** button, and
the first view you get); you can zoom out to a fifth of that and in sixteen times, and small labels hide when a cell is under
16 pixels on the screen. The **Controls** button folds the rows of file, layer and CHIM controls away so the map gets the
window; it is closed by default in a short window and the choice is remembered, like your last zoom and position. The
A status strip in the bar above the map says where the data comes from and how fresh it is: a state dot (green live, amber
stale, grey off or final, red load error), the source, the data's own last-update time with a ticking "N s ago", and the
auto-update switch with its interval. The
overview below the map has a chart that answers what storing every mesh once saves: its title states the saving in words,
panel (a) shows meshes converted as cells are converted (store-once against every cell converting its own, log scale) and
panel (b) compares the spiral order with the risk order. Every Toolkit page carries the same header; see the
[Toolkit guide](../AMIWIND_TOOLKIT.md#chim-progress-tracker).

## Track your own build and compare with the project

A CHIM build writes the tracker data of its own world into `BUILD/toolkit` by default, and the Toolkit can show it live while the build runs. The commands, the live build tracker (file mode and server mode) and the compare layer are in [Track your own build](../AMIWIND_TOOLKIT.md#track-your-own-build).

## Command reference

All commands take `--out DIR`, the tracker folder, and are run with `python3 tools/cell_progress.py`.

| Command | What it does |
| --- | --- |
| `ingest --out DIR [inputs...]` | Fill the records from everything that exists now: legacy progress table, metrics, census (`--data-files`), CHIM runs (`--chim-run NAME=PATH`), bugs, build ledger, area names. Idempotent |
| `result --out DIR --file RESULT.json` | Validate and store a per-cell result file ([format](CELL_RESULT_FORMAT.md)), then ingest again |
| `record --out DIR --mechanism ID --build NAME (--results FILE or --status S --cells "x,y ...")` | Record one audit's results from another tool |
| `owner --out DIR --status playtested/approved --cells "x,y ..." [--note T]` | The owner's verdict on cells |
| `release --out DIR --version V --cells SELECTORS [--clear] [--shipped] [--who W]` | The owner's release assignment, see above |
| `export --out DIR [--csv F] [--json F]` | The cells as CSV (status, audits, every numeric stat) and JSON |
| `status --out DIR` | One line with the headline counts |
| `render-md --out DIR [--md FILE]` | Write the generated page `docs/chim/CELL_TRACKER.md` |
| `check-md [--md FILE]` | Fail when the committed page lacks its generated header, shows private content or has a stale import policy |
| `publish --out DIR [--file FILE]` | Write the project reference file `docs/chim/cell-progress-reference.json` |
| `check-reference [--file FILE]` | Fail when the reference file has a key outside its allow-list or looks private |

`tools/cell_progress_build.py --out DIR --chim-world WORLD [--data-files DIR]` is the build-side ingest the CHIM builder runs for you.
