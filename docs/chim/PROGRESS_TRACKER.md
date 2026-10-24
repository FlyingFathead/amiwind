# CHIM Progress Tracker

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Current state, 19 October 2026](#current-state-19-october-2026)
- [Why it exists](#why-it-exists)
- [Data flow](#data-flow)
- [Statuses](#statuses)
- [The legend groups: in the game, not in the game yet, settled](#the-legend-groups-in-the-game-not-in-the-game-yet-settled)
- [Audits](#audits)
- [The lighting audit](#the-lighting-audit)
- [The lava audit and the Lava layer](#the-lava-audit-and-the-lava-layer)
- [Eligible for a release](#eligible-for-a-release)
- [The release field and the version tracker](#the-release-field-and-the-version-tracker)
- [The release plan: gold for the next release](#the-release-plan-gold-for-the-next-release)
- [Legend checkboxes and presets](#legend-checkboxes-and-presets)
- [The map view](#the-map-view)
- [Interiors: every room on the tracker](#interiors-every-room-on-the-tracker)
- [Included in build: what each packaged build holds](#included-in-build-what-each-packaged-build-holds)
- [Track your own build and compare with the project](#track-your-own-build-and-compare-with-the-project)
- [Command reference](#command-reference)
- [History: v0.0.41 preparation notes, 15 October 2026](#history-v0041-preparation-notes-15-october-2026)
  - [v0.0.41 candidate - visibility aprons, 15 October 2026](#v0041-candidate---visibility-aprons-15-october-2026)
  - [v0.0.41 candidate - window support, 15 October 2026](#v0041-candidate---window-support-15-october-2026)
  - [v0.0.41 candidate - lava coverage, 15 October 2026](#v0041-candidate---lava-coverage-15-october-2026)
  - [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
  - [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
  - [Owner apron follow-up, 15 October 2026](#owner-apron-follow-up-15-october-2026)
  - [Current mapping evidence, 15 October 2026](#current-mapping-evidence-15-october-2026)

<!-- contents end -->

Where the conversion of the open world to CHIM stands, and how the tracker that measures it works.

## Current state, 19 October 2026

The open world is converted to CHIM release by release, lightest cells first. Exterior cells of Vvardenfell on CHIM
in each packaged build, as counted at the time, out of 1,395: the 1,390 cells with a LAND record (1,292 land cells
and 98 sea-floor cells) and the 5 open-sea cells then selected. 14 more open-sea cells joined in v0.0.43, so the
whole outdoors is 1,409 cells. Every count and what it means: [what we count](CELL_TRACKER.md#what-we-count). The cell
tracker's "Included in builds" table counts from the packaged images instead (cells with a LAND record only), so its
figures differ by a few cells.

| Build | Cells on CHIM | Notes |
| --- | --- | --- |
| v0.0.42 (released 17 October) | 1,168 of 1,395 (84 %) | |
| v0.0.43-dev1 (pre-release) | 1,310 (94 %) | Seabed cells without height data admitted; medium cells |
| v0.0.43-dev2 | 1,348 (97 %) | 38 more cells; the cells that waited for a hull policy pass |
| v0.0.43 (released 19 October) | every exterior cell: 1,409 (1,348 in one-cell region frames + 61 in the three town frames) | The stair-walk cells (Ald-ruhn, Maar Gan, Suran), Balmora's border cells and 14 open-sea cells joined |
| v0.0.44-dev1 | as v0.0.43 | Bitter Coast trees fit in memory again ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](../bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md)) |
| v0.0.44 (released 19 October) | as v0.0.43 | The patch release: the Bitter Coast trees fit in memory again; the same cells as v0.0.43 ([release notes](../RELEASE-v0.0.44.md)) |

The [cell tracker](CELL_TRACKER.md) holds the per-cell results: 1,193 of Vvardenfell's 1,292 land cells have passed
every measured audit; the other 99 land cells and the 98 sea-floor cells are empty sea (nothing placed, done as they
are). None is waiting for a hull policy and none fails an audit. Solstheim's 144 land cells are not started.

Since v0.0.43 no exterior cell of Vvardenfell is classic: no classic region maps are left outdoors. Interiors
stay Quake maps, and some interiors of the base game are not in the build yet; bringing them in, with the
cell-to-cell crossing pauses first among the fixes, is the next work ([roadmap](../ROADMAP.md)). Solstheim is
not converted yet. The per-cell numbers above and on the [cell tracker](CELL_TRACKER.md) come from the tracker
ingest after each packaged build.

History, as written after v0.0.43-dev2 (all three items were fixed in v0.0.43). What still kept exterior cells
classic then:

- **39 cells held by the stair walk**
  ([CHIM-STAIR-STEPS-SOLID-43](../bugs/CHIM-STAIR-STEPS-SOLID-43.md)): Ald-ruhn, Maar Gan, Suran and one rope bridge
  cell fail it, and the town cells around them wait for them. The fix is in the shared converter (collision checked
  over every visible flight), on its way into v0.0.43-dev3.
- **8 Balmora border cells** were built as narrow classic strips around the town frame, and **14 open-sea cells**
  off the west coast were never selected
  ([CHIM-BALMORA-INSET-SLIVERS-43](../bugs/CHIM-BALMORA-INSET-SLIVERS-43.md),
  [CHIM-OCEAN-CELL-RECORD-CLASSIC-43](../bugs/CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md)); both are fixed for
  v0.0.43-dev3.

No cell outside these was over the memory budget or failing an audit.

## Why it exists

The open world of Vvardenfell is 1,409 exterior cells: 1,292 land cells, 98 sea-floor cells and 19 open-sea cells
([what we count](CELL_TRACKER.md#what-we-count)); Solstheim adds 144 land cells. Converting them one at a time and judging each by eye does not scale, and "it looks fine" does not catch a stair that cannot be walked or a frame that does not fit in memory. The tracker turns the conversion into numbers: one record per cell, one result per audit, one status per cell, and the same definitions everywhere (the Toolkit map, the generated page, the release notes). Anything that is not measured says "not measured": the tracker never guesses and never counts an unmeasured audit as passed.

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
| Maintainer-approved, Playtested | gold, teal | Set by the maintainer for a converted cell that passes |
| Passed | green | Converted and every measured audit passed, but something placed is still deferred or skipped |
| Empty sea | blue | Terrain and water only, nothing placed; counts as done |
| Open ocean | silver | No LAND record; explicit ocean-frame conversion is tracked separately from native placement and packaging. Never counted as land. The legend shows it as sea in the game, settled or open sea not in the newest build (see the groups below) |
| Hull policy pending | purple | The only open problem is a standing-hull chain deeper than the limit, waiting for one shared rule; neither passed nor failed |
| Converted, failing audits | red | At least one audit failed or the conversion reported an error |
| Not converted | magenta | The conversion was tried and could not finish the cell; a failure-type state, never counted as done |
| Converted, nothing measured | light blue | Converted, no audit measured |
| Not started | grey-blue | The conversion has not reached the cell |

Precedence: cell complete, terrain complete, the two awaiting-lighting levels, maintainer-approved, playtested, passed, hull policy pending, failed, not converted, not started. Nonvisual markers (door, travel, north and editor markers) are not drawn and not required, so they never block a level; light emitters without a mesh do cast light, so they stay under Lights and the lighting audit judges them.

**Done** = cell complete + terrain complete + the two awaiting-lighting levels + passed + empty sea, each on its own line. The open ocean is **not** done: it is drawn silver, has its own legend row and its own totals row, and is counted apart (`ocean`, `map_cells`) until the tracker policy and exact runtime evidence establish otherwise. An island's figures count its land and empty-sea cells and keep the land-only figures beside them (land cells, land done, land percent); the headline's percent stays passed of land cells. The generated page repeats the exact definitions in its import policy section, built from the code's own constants.

## The legend groups: in the game, not in the game yet, settled

The status says how far a cell's conversion got; the legend group says where the cell stands today. Every square of the grid
is in exactly one group, worked out by the tracker against the newest ingested build (`cell_progress.py ingest` writes
`chim.group` and `chim.state` per cell and `groups`, `states`, `in_game_build` in the headline):

| Group | Legend states | Which cells |
| --- | --- | --- |
| In the game | the land states above (cell and terrain complete, awaiting lighting, approved, playtested, passed, nothing measured) and **sea, in the game** (sea blue with green stripes) | The newest build holds the cell. Every sea cell it holds is "sea, in the game", whatever an older run called it: seabed cells and the empty cell records in open water such as -15,-8 |
| Not in the game yet | **Solstheim (Bloodmoon)**, not started, converted but not in the newest build, empty sea and open sea not in the newest build, failing, not converted, hull policy pending | The work left. A problem state stays a problem even when the build holds the cell. Every other Solstheim cell the build does not hold counts as Solstheim, its sea cells included |
| Beyond the world's edge: settled | **settled** (faint grey) | No cell record in the original game data (the mesh census has none) and not in the newest build. The edge current ([WORLD_BOUNDS.md](../WORLD_BOUNDS.md)) turns the player back before them: there is nothing to build |

**Accounted for** = in the game + settled. Settled squares count toward it, never toward the cells in the game. In the
Toolkit each group header shows its count; a state with no cells waits in the **More states** fold-out and comes back to its
group by itself once it has cells. The generated [cell tracker](CELL_TRACKER.md) and `cell_progress.py status` print the same
three figures. Older tracker data without the fields still draws, with the flat legend; the generated page then derives the
groups from the cells.

## Audits

Eleven mechanisms are measured per cell: world format validation, stair walk, memory fit, seam tears, hull bevels / chain length, sky-bank texels, hidden faces, far-terrain coverage, sprite shape, actor grounding and doors / interior links. Each one's pass rule and limit is in the [import policy](CELL_TRACKER.md#import-policy) of the generated page; it is not repeated here so the two cannot disagree. An audit result measured on another build than the cell's current one is shown as stale and counts as not measured.

## The lighting audit

A cell is only complete when it is lit like Morrowind. `tools/cell_lighting.py` counts the original light placements of the cell (by class, with and without a mesh) from your own master files, looks at how the CHIM build brought them to the frame (baked into lightmaps, the engine's night lamp table, or not at all) and how much of the terrain and the models carries real light data. The result is **lit** (every active light baked, every surface lit), **partial** (some light or some lit surfaces) or **unlit**; **not measured** when the cell is not converted. Lit is required for both completion levels; until then a cell that otherwise qualifies is shown as awaiting lighting. The Toolkit has a colouring by lighting status.

## The lava audit and the Lava layer

`tools/cell_lava.py` judges whether a cell's molten lava became Quake liquid ([LAVA.md](../LAVA.md)). The census counts the molten lava pools the original places in each exterior and interior cell (objects whose script hurts an actor standing on them, from your own master files; Molag Amur's lava-coloured rock is not molten and is not counted). The build's lava record (the CHIM receipt's `lava`: mode and pools by source cell) says how many became liquid. The result is **converted** (every pool a Quake liquid), **partial**, **mapped, not converted** (the cell is not built, or its build is from before the lava record), **static** (built with `--lava static`) or **not measured** (a census without lava counts); cells without lava have no row. The Toolkit's "Lava (mapped / converted)" colouring and the Lava preset show it on the map; the cell panel has a Lava line, and the overview line counts lava cells, pools and converted pools. The lava audit does not change a cell's completion level.

## Eligible for a release

"Eligible for vX" is the set of cells usable now for the next release, lighting done or not: every passed status (the completion levels, awaiting lighting included, owner states and passed) plus empty sea and sea in the game. vX is the upcoming release of the release plan, or the version in development (the repository's `VERSION`) when the plan is older than it; no version is written in the code. Eligibility is a planning filter; explicit ocean routing, frame validation and runtime/package checks still apply. The generated page prints the figure; the Toolkit has a "Show: eligible" filter and a legend preset.

## The release field and the version tracker

Which cells are approved for which release is a project decision, kept separate from the measured data:

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

## The release plan: gold for the next release

Besides the maintainer's approval (above), every cell can be **planned** for an upcoming release. The plan is a layer of its own: it is stored in `plan.json` next to the tracker data (format `aw-cell-plan-1`, schema 1), written only by `cell_progress.py plan` and `cell_progress.py ship`, and it never changes a cell's conversion or audit status. Conversion results and ingest do not touch it, and a re-ingest keeps it.

Each planned cell carries one open record in the tracker data (`cell.plan`):

```json
{"release": "v0.0.36", "state": "planned", "since": "2026-10-11T09:07:18+03:00", "source": "who or what set it", "tier": "next"}
```

- `state` is `planned`, `in_build` or `shipped`. `tier` is computed: `next` for the upcoming release, `later` for a planned release after it, `shipped` once it is published.
- The record is open. Any other key (for example `--set scope=coast`) is kept, shown in the cell panel and exported; a key written by a newer tool survives a re-plan. A `plan.json` with a newer schema than the tool knows is never overwritten.
- **The upcoming release is data, not code.** It is the lowest-numbered plan release that has not shipped. Several releases may be planned at once; the next one is gold, later ones are drawn in a paler gold.
- When a release is published, one command flips all its plan cells to `shipped`; the next planned release takes the gold with no code change.

```bash
python3 tools/cell_progress.py plan --out DIR --release v0.0.36 --cells @LISTFILE --set scope=coast --source "run X"
python3 tools/cell_progress.py plan --out DIR --release v0.0.36 --cells "area:NAME build:RUN 4,-11" --state in_build
python3 tools/cell_progress.py plan --out DIR --release v0.0.36 --cells "0,0" --clear      # take a cell back out
python3 tools/cell_progress.py ship --out DIR --release v0.0.36                              # published: planned -> shipped
```

Selectors: a cell ID `x,y`, `@FILE` (cell IDs separated by whitespace), `build:RUN`, `plan:VERSION`, `state:STATE`, `unplanned`, `ring:N`, `status:BUCKET`, `eligible` and `all`. The CSV export carries `plan_release`, `plan_state`, `plan_since` and `plan_source`. The tracker data carries `schema` 2, `plan_next` (the upcoming release, or none) and `plans` (one row per plan release: planned cells and how they stand, from which the Toolkit prints the per-release table with a TOTALS row).

In the Toolkit, nothing about the plan shows while no plan exists. With a plan: the **Release plan** colouring fills the planned cells gold (the gold of the Toolkit header) and keeps every other cell in its status colour; in every other colouring the next release's cells get a gold outline; the legend has a row "Planned for vX (next release)" generated from the data, the **Preset** pull-down gets "Planned for vX (gold)", the version pull-down can filter by plan release, the cell panel and tooltip print the plan record, and a table under the legend lists each plan release with its planned cells, how many are complete, awaiting lighting, failing, hull-pending or not started, and a TOTALS row. Shipped cells keep their status colours.

## Legend checkboxes and presets

Every row of the map legend has a checkbox. Unticking a row **dims** the cells of that row (the same dimming as the status chips and the Show filter), so the island stays readable around what you picked; the box beside a gradient scale is disabled because a scale has no rows to untick. **all** and **none** tick or untick every row. The **Preset** pull-down sets the ticks in one go: Everything, In the game, Not in the game yet (work left), Eligible for the next release, Awaiting lighting, Problems only (failed, not converted, hull pending), Not started (Solstheim included), Lighting (switches to the lighting colouring), Lava (switches to the lava colouring) and Release content (only cells assigned to a release). Ticking a row by hand switches the pull-down to Custom. Your ticks, preset and version choice are remembered in the browser (local storage; the page works without it).

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

## Interiors: every room on the tracker

Parity with the original game: every interior cell of the game is a room on the tracker, keyed by its cell ID, and
none is left out. With the door graph and the batch plan ([DOOR_GRAPH.md](DOOR_GRAPH.md)), the ingest adds
`interior_rooms` to the tracker data (`--door-graph`, `--batch-plan`, and `--chim-rooms` with a CHIM rooms receipt or
a build's `chim-interiors.json`). Each room gets its master, its island (the island its entrance is on; `none` for a
room with no entrance area), its entrance cell, its state, its batch and its reasons. The states fall into the three
groups of the legend:

- **In the game:** on CHIM rooms (a build's `chim-interiors.json` installed it), or as today's room map.
- **Not in the game yet:** converted (a CHIM room record exists), or not started.
- **Set aside, with a reason:** test cell, teleport only, no entrance and no script (the rooms no door reaches,
  converted in the final parity batch or in their expansion's later batch), or another hard case (water, lava, size,
  Levitate-only).

On the World map, the **Interior tracker** block sits under the map: closed by default and remembered like the other
blocks, its title line always shows the rooms in the game, not in the game yet and set aside. Opened, it lists the
rooms by island, then by entrance (the town or place and its exterior cell; Mournhold's rooms are reached by script),
each group folding out to its rooms with their state (a chip in the legend colour), batch, reasons and master. The
search box filters by name, cell ID, town, state, batch or reason, and opens the groups that match. Clicking a room
selects and centres its entrance cell on the map. The rooms with no entrance area are their own group at the end.
The side panel's overview keeps a short table: rooms per island in the three groups. The **Interiors** layer marks
every exterior cell that holds an entrance, coloured by its rooms' state (the most common one; a tie goes to the
state further from the game); an unticked legend row hides that state.

The generated page [CELL_TRACKER.md](CELL_TRACKER.md#interiors) has the counts per island and state (aggregate counts
only). Tracker data without interiors still loads: the block stays hidden and the Interiors layer keeps its older
colouring (the converted share of the rooms behind a cell's doors).

## Included in build: what each packaged build holds

The plan says what a release should hold; the **Included in build** pull-down on the map says what a build really
holds. With a build selected, its cells are drawn green (included in a packaged or released build, checked against the
package's disk readback), amber (included in a build that is not packaged yet, or listed but not included) or grey
(not in that build); the line under it counts them.

- The data is the inclusion ledger, `amiwind-toolkit/chim-inclusion.json` (format `aw-chim-inclusion-1`; the page
  loads the same content from `chim-inclusion.js`). One entry per build, newest first: version, state (built,
  packaged or released), the build run, source commit, the SHA-256 of the package and of its disk readback, and the
  cells with their frames. The cells are stored compactly: `region_cells` lists the cells each in the region frame named
  after it (`rcm19_p14` for -19,14) and `frame_cells` the rest by frame (the town frames), one entry per line; the page
  still reads the earlier per-cell form.
- Every entry is written from the build's own records, never by hand: `tools/chim_inclusion.py` reads the run's
  `chim-world/chim-source.json` (every frame: region frames by cell, town frames by their ownership core, so the
  cells of Vivec, Seyda Neen and Balmora count with their town frame) and the cell list the build was given.
- **Built:** every build with a CHIM world writes its own entry when it ends, into the run's own copy,
  `BUILD/toolkit/chim-inclusion.json` and `.js`: the repository ledger with this build on top. The build's World map
  (the live tracker page, `toolkit_serve.py --build BUILD`) shows the build it belongs to, and
  `toolkit_serve.py --builds DIR` adds the newest runs' entries. It takes well under a second, runs beside the size
  ledger after the stages, keys no stage, and is reused when its inputs (the code, version, run, commit, CHIM world
  source and cell list) are unchanged. It needs no package yet and never fails a build.
- **Packaged:** packaging adds the package's and the readback's SHA-256 to the run's entry (both required):

```bash
python3 tools/chim_inclusion.py package --run BUILD --archive PACKAGE.zip --readback READBACK.json \
    --evidence "boot smoke PASS, readback OK" [--shipped]
```

- **Released:** only the release step changes the repository ledger, and it holds packaged and released builds only
  (a built entry stays in its run). The release run's packaged entry goes in as released, replacing any earlier entry
  of that version; commit the ledger before the source package is cut. `tools/release.py` refuses to cut the public
  source of a release candidate or final whose version the ledger lacks (`chim_inclusion.py check-release` runs the
  same check on its own).

```bash
python3 tools/chim_inclusion.py release --run BUILD
python3 tools/chim_inclusion.py check-release [--version v0.0.48]
```

The earlier one-step form still writes a packaged or released entry straight into the repository ledger
(`--version V --state packaged --source-commit C --chim-source RUN/chim-world/chim-source.json --cells CELLS.json
--archive PACKAGE.zip --readback READBACK.json --evidence TEXT`).

The cell list a build is given comes from the tracker too: `tools/chim_cell_list.py` takes the rings from the tracker
data, keeps every cell already on CHIM, and leaves cells out only by name with a reason (`--leave-out X,Y=REASON`);
`--open-pockets` also leaves out the neighbours that would enclose a classic cell in CHIM cells.

**After every packaged build:** re-ingest the tracker (the build's run as `--chim-run`), package the run's entry with
`chim_inclusion.py package`, and check that the map's pull-down lists it with the right count.

## Track your own build and compare with the project

A CHIM build writes the tracker data of its own world into `BUILD/toolkit` by default, and the Toolkit can show it live while the build runs. The commands, the live build tracker (file mode and server mode) and the compare layer are in [Track your own build](../AMIWIND_TOOLKIT.md#track-your-own-build).

## Command reference

All commands take `--out DIR`, the tracker folder, and are run with `python3 tools/cell_progress.py`.

| Command | What it does |
| --- | --- |
| `ingest --out DIR [inputs...]` | Fill the records from everything that exists now: legacy progress table, metrics, census (`--data-files`), CHIM runs (`--chim-run NAME=PATH`), bugs, build ledger, area names, interiors (`--door-graph`, `--batch-plan`, `--chim-rooms`, see [Interiors](#interiors-every-room-on-the-tracker)). Idempotent |
| `result --out DIR --file RESULT.json` | Validate and store a per-cell result file ([format](CELL_RESULT_FORMAT.md)), then ingest again |
| `record --out DIR --mechanism ID --build NAME (--results FILE or --status S --cells "x,y ...")` | Record one audit's results from another tool |
| `owner --out DIR --status playtested/approved --cells "x,y ..." [--note T]` | The maintainer's verdict on cells |
| `release --out DIR --version V --cells SELECTORS [--clear] [--shipped] [--who W]` | The maintainer's release assignment, see above |
| `export --out DIR [--csv F] [--json F]` | The cells as CSV (status, audits, every numeric stat) and JSON |
| `status --out DIR` | One line with the headline counts |
| `render-md --out DIR [--md FILE]` | Write the generated page `docs/chim/CELL_TRACKER.md` |
| `check-md [--md FILE]` | Fail when the committed page lacks its generated header, shows private content or has a stale import policy |
| `publish --out DIR [--file FILE]` | Write the project reference file `docs/chim/cell-progress-reference.json` |
| `check-reference [--file FILE]` | Fail when the reference file has a key outside its allow-list or looks private |

`tools/cell_progress_build.py --out DIR --chim-world WORLD [--data-files DIR]` is the build-side ingest the CHIM builder runs for you.

## History: v0.0.41 preparation notes, 15 October 2026

These notes record the state during the v0.0.41 preparation and are kept as written. The current state is at the
[top of this page](#current-state-19-october-2026).

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](../RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](../bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](../bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](../bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

### v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](../bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.

### v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](../bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.

15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

### v0.0.41 candidate - lava coverage, 15 October 2026

[CHIM-LAVA-DUPLICATE-VERTEX-40](../bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md) - The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

### Compiled apron selection, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The full combined conversion found a conservative
source box overlapping an apron although the compiled rock footprint ends
0.83 game units outside it. The selection now records and excludes only external
references whose compiled pieces all miss that apron. Owned originals, reaching
pieces and missing-piece failures remain protected. The original reference and
compiled boxes remain in the source receipt. All 68 focused checks pass.
The preceding source passed 4,218 tests: 4,212 passed, three Windows checks
skipped and three tracked Census cases were expected failures. The later source
requires its own full suite and combined validation. Native, package and shipment
acceptance remain pending; no converted or accepted coverage count is promoted.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

### Paired boundary validation, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

The CHIM Progress Tracker is how AmiWind keeps count of the open world on CHIM: for every exterior cell of the island, whether it is converted, what each audit found, how it is lit, what it still lacks and which release it is approved for. This page is the hand-written guide. The live figures are on the generated [CHIM cell tracker](CELL_TRACKER.md), the conversion itself is described in [CHIMport](CHIMPORT.md) (how the conversion works), and the file format the conversion hands to the tracker is the [cell result format](CELL_RESULT_FORMAT.md). What each colour of the map means, and the problems usually behind it, is on [the CHIM progress map](CHIM_PROGRESS_MAP.md).

### Owner apron follow-up, 15 October 2026

The source owner check found twelve additional references in the sampled
regional apron: four placements of the fourth kelp mesh, four objects already
deferred by Seyda, and four nonsolid grasses represented by existing sprites.
The successor retains all four original kelp models. Regional aprons now honor
the included town's exact declared deferrals; nonsolid grasses retain the same
hash-verified sprite bytes and original transforms instead of duplicate meshes.
Unrecorded missing owners, changed original identities and corrupt sprite assets
still fail. The existing ownership validator is unchanged. Forty-seven focused
checks pass, including serialized ownership and sprite corruption controls.

The earlier authored-collision source passed 4,213 tests: 4,207 passed, three
Windows-only checks skipped, and three tracked Census expected failures. This
does not certify the later source. Combined conversion, native seams, gameplay,
fresh packaging and delivery remain pending; no coverage acceptance is promoted.

[Canonical report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

### Current mapping evidence, 15 October 2026

The public reference records historical conversion and audit results. The release
plan records the current candidate separately: 435 original cells in 369 frames,
including all five ring-0, 171 ring-1 and 160 ring-2 cells. A town frame can own
several original cells, so frames, cells and boundary segments are different counts.

| Evidence layer | Current result | Remaining gate |
| --- | --- | --- |
| Earlier combined conversion | All 369 frames passed conversion, structure, heap, zone walking and stairs on that source | Later repairs need their own compiled and combined results |
| Corrected sampled boundary | Zero full-static support-status disagreements in 2,816 samples and 5,632 queries; terrain and water controls agree | Other 541 original segments remain unmeasured |
| Corrected Seyda frame | Compilation, zero structural failures, heap and zone-walk checks pass | Complete stair gate unfinished after memory exhaustion |
| Later combined attempt | Ownership validation failed before packing: original kelp omitted | Compile and validate the next kelp source correction |
| Native verification | No complete candidate traversal count established | Matched views, normal collision crossing, actors and gameplay |
| Package and delivery | No new candidate coverage promoted | Fresh image, exact package readback and delivery |

The regional scenery apron first reduced the southern Seyda comparison from
477 to 69 support-status disagreements. Original reference 463188 had identical
63 rendered faces but 40 collision hit-presence disagreements in 588 rays:
the regional path retained the authored RootCollisionNode while the legacy
Seyda carrier omitted it. A CHIM-only supplement verifies the original NIF and
visual hashes, preserves carrier bytes and appends the original authored hulls.

The corrected Seyda frame now compiles with zero structural failures and passes
heap and zone-walk checks. Compared with the repaired regional frame, the same
boundary has zero full-static support-status disagreements across 2,816 samples
(5,632 queries); terrain and water controls also agree. Its complete stair gate
is unfinished: the parallel run exceeded its memory limit and was stopped by
out-of-memory termination. A passing boundary sample is not a complete stair,
combined-world, native or package pass.

The combined attempt then stopped at ownership validation before packing:
original kelp references, including 463098, were omitted from the Seyda frame.
These references are present in the original source carrier and absent from the
existing flora sprite receipt; a legacy dressing filter removed them. The next
source correction retains only the three known original kelp meshes 01/02/03,
binds additions to the original scenery index and leaves unrelated deferred
dressing unchanged. All 43 focused Seyda, town and ownership checks pass.
Compiled verification of this later correction, native checks and packaging
remain pending. The earlier source's running full suite does not certify it.
See [the static seam report](../bugs/CHIM-FRAME-STATIC-SEAM-40.md).

Keep the candidate source/build identity, world index and validation hashes,
measured/failed/unmeasured seam segments, native evidence and package evidence
as separate plan fields. Earlier packaged receipts stay attached to their own
builds. A newer planned candidate never inherits their acceptance.

A boundary object may appear in multiple frames so it remains visible and
collidable during handover. Its original master, reference number, type and
transform select one logical owner; other copies are dependencies. Terrain or
scenery aprons, horizon samples and external dependencies do not add owned cells.
Per-type records must retain converted, failed, deferred and excluded references,
including NPCs, creatures and meshless lights. Geometry audits do not establish
dialogue, combat, quests or other gameplay.

Ring3 feasibility is future work after v0.0.40 delivery; it does not alter the
current plan or package layer. See [the roadmap](../ROADMAP.md#v0041-dev1-ring3-feasibility-after-v0040-delivery).
