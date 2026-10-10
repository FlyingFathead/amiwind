# CHIMport: the whole island on CHIM, cell by cell

CHIMport (`tools/chimport.py`) converts every exterior cell of your own
Morrowind data to CHIM, one cell at a time, starting at the sea around the
island and working inwards ring by ring. Every cell goes through every
mechanism audit the CHIM builder has, and its figures and results are kept, so
the CHIM Progress Tracker in the AmiWind Toolkit shows how far the island is
and which mechanisms still fail. A failing cell never stops the run: it is
recorded with the reason, and the run moves on.

<!-- contents start -->
## Contents

- [Island results (9 October 2026)](#island-results-9-october-2026)
  - [Cells with hull policy pending](#cells-with-hull-policy-pending)
  - [Failure classes](#failure-classes)
  - [Stored once, island-wide](#stored-once-island-wide)
  - [Whole-island world](#whole-island-world)
- [What is in a converted cell](#what-is-in-a-converted-cell)
- [Hull policy pending](#hull-policy-pending)
- [What a cell is](#what-a-cell-is)
- [Order: from the sea inwards](#order-from-the-sea-inwards)
- [Audits per cell](#audits-per-cell)
- [Cell results](#cell-results)
- [The growing world](#the-growing-world)
- [Figures per cell](#figures-per-cell)
- [Store once across the run](#store-once-across-the-run)
- [The shared storage pool](#the-shared-storage-pool)
- [Running CHIMport yourself](#running-chimport-yourself)
- [Feeding the CHIM Progress Tracker](#feeding-the-chim-progress-tracker)

<!-- contents end -->

On CHIM today: the towns (Seyda Neen's square, docks and census office courtyard, and Balmora); the open
land outside them is still built the legacy way until CHIMport replaces it, coast first
([IMAGE_SIZE.md](../IMAGE_SIZE.md#what-is-on-chim-today)).

## Island results (9 October 2026)

The first island-wide run converted all 1,292 exterior cells of Vvardenfell (the base master), from the
open sea at the edge of the map inwards over 13 rings, at low priority beside the release builds (4 to 8
cells at once).

**Done: 716 of 1,292 (55 %).** Done counts the cells with content that pass every audit and the empty sea
cells, as the CHIM Progress Tracker counts them (its completion levels, including cells awaiting
lighting, plus passed and empty sea); each kind keeps its own line. Every done cell is also eligible as a
release candidate for v0.0.34, empty sea included:

| Result | Cells | Meaning |
| --- | --- | --- |
| Passed | 613 | Content converted, every audit passed |
| Empty sea | 103 | Nothing placed: the frame ships as terrain and water |
| Hull policy pending | 546 | Everything else passed; only the collision-chain policy is open (below) |
| Failed | 26 | A real failure class (below) |
| Not converted | 4 | The cell world could not be built (below) |

Records: 143,147 placed records in the exterior cells, 133,793 converted (statics, containers,
activators, doors, lights, items), 8,282 deferred with the converter's reason (levelled creatures and
creatures 5,415, NPCs 566, light emitters without a mesh and other invisible markers 2,301) and 1,072
skipped (1,049 of them in the four cells that were not converted); see
[What is in a converted cell](#what-is-in-a-converted-cell).

### Cells with hull policy pending

These cells fail only the hull-chain check; see [Hull policy pending](#hull-policy-pending) below for what
that means. Until the shared rule lands they are counted apart, not as failures.

### Failure classes

Each class is one mechanism, to be fixed once at the shared layer and then run again for every cell of
the class (`--retry-failed`), never cell by cell:

| Class | Cells | Mechanism |
| --- | --- | --- |
| Memory fit | 13 | A town frame's ring of chunks does not fit the CHIM zone (the large-model cut and the zone budget) |
| Stair walk | 10 | Steps the standing box cannot walk (2 of these cells also miss a door) |
| Doors | 3 | A door placement is not in the frame |
| Not converted | 4 | A window whose façade is placed in the next cell ([CHIM-WINDOW-MOUNT-CROSS-CELL-33](../bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md)) |

One more cell ran out of memory early in the run, when the run shared the host with a release build; it
converted when run again.

### Stored once, island-wide

The island has 1,436 distinct meshes. With the CHIM builder's units keyed by content
([CHIM-UNIT-FP-SOURCE-LAYOUT-33](../bugs/CHIM-UNIT-FP-SOURCE-LAYOUT-33.md)), each is converted about once
for the whole island: after the change, 319 cells wrote 1,156 mesh units for 977 distinct meshes (1.18 per
mesh, the rest being flora and collision-only variants), where before every cell converted its meshes
again (9,526 units for 1,081 meshes, 8.8 per mesh).

### Whole-island world

One CHIM world of every converted cell (a frame per cell, every unit from the shared cache), validated and
run through the per-frame heap audit.

| Figure | Value |
| --- | --- |
| Frames | measuring |
| Size on disk | measuring |
| Files | measuring |
| Validation | measuring |
| Heap audit (per frame) | measuring |

## What is in a converted cell

Every placed reference of the base master in an exterior cell is accounted for, per record type:
converted, deferred (with the converter's reason) or skipped (with a reason). From the island-wide run:

- **Converted as models**: terrain (and water), statics, flora (statics and containers named `flora_`),
  containers, activators, doors, lights that have a mesh, and items.
- **Recorded but deferred, with the reason**: NPCs ("resident conversion") and creatures and levelled
  creatures ("creature simulation pending"), 5,981 island-wide, waiting for the open-world actor pipeline;
  2,284 lights without a mesh (1,936 plain lights, 332 glowing plants, 12 darkeners, 4 fires), waiting for
  the CHIM light design ([CHIM-MESHLESS-LIGHTS-33](../bugs/CHIM-MESHLESS-LIGHTS-33.md)); and 17 invisible
  source markers ("nonvisual source marker").
- **Skipped**: 1,049 references in the four cells that were not converted, and 23 in converted cells whose
  converted bounds lie outside their own cell ("not in the frame").
- **Doors**: 1,041 of 1,119 converted; 72 are in the four unconverted cells and 6 are markers.
- **Not yet in a cell**: the far-terrain layer (distant ground drawn beyond the ring) and the hidden-face
  audit (faces under the terrain), both still "not measured".

| Record type | Placed | Converted | Deferred | Skipped |
| --- | --- | --- | --- | --- |
| Statics (STAT) | 107,675 | 106,791 | 11 | 873 |
| Containers (CONT) | 22,225 | 22,193 | 0 | 32 |
| Levelled creatures (LEVC) | 5,082 | 0 | 5,082 | 0 |
| Lights (LIGH) | 2,974 | 643 | 2,284 | 47 |
| Activators (ACTI) | 2,806 | 2,761 | 0 | 45 |
| Doors (DOOR) | 1,119 | 1,041 | 6 | 72 |
| NPCs (NPC_) | 566 | 0 | 566 | 0 |
| Creatures (CREA) | 333 | 0 | 333 | 0 |
| Items (MISC, INGR, WEAP, BOOK, ARMO, ALCH, CLOT, REPA, APPA, LOCK, PROB) | 367 | 364 | 0 | 3 |
| **All** | **143,147** | **133,793** | **8,282** | **1,072** |

No reference failed to convert inside a converted cell. The same figures per cell are in each cell's
`result.json` (`records.by_type`) and in the export.

## Hull policy pending

**How Quake collides with a model.** Every placed model carries a clip hull: a tree of clipnodes, each a
plane with a "front" and a "back" child. When the player moves, the engine traces the movement through
that tree from its head node, one clipnode after another, until it reaches empty space or solid. The cost
of a trace near a model is the number of clipnodes it visits.

**Two hull forms.** The CHIM builder writes a model's standing hull (Quake hull 1) in one of two forms:

- **chain**: the model's convex collision pieces one after another. A trace tests every piece in turn,
  so its cost grows with the number of pieces; a house of a few hundred pieces is a chain a few hundred
  clipnodes deep.
- **routed**: the pieces sorted into a nested tree of axis-aligned cuts, so a trace visits only the few
  nodes on its way down to the pieces near it.

v0.0.33 ships the chain for house-size models by default: routed hulls had two problems (the extra
clipnodes ate into the memory reserved for flora, and a node-order fault), both fixed since. Every form
stays selectable with the builder's `--model-hull` option (`auto`, `chain`, `routed`, `balanced`).

**What it costs.** Measured on the slow emulator preset (emulator-relative figures): about 1.36
microseconds per clipnode visited; Balmora's houses cost 12 to 33 ms per trace as chains and 2.8 to 3.6 ms
routed (COLLISION-TRACE-COST-33).

**The shared rule.** One limit is read by the router and by the audit: `CHAIN_DEPTH_LIMIT`, 256 clipnodes of
chain depth (`tools/routed_hull.py`; a measurement can override it with `AMIWIND_CHIM_CHAIN_DEPTH`). For each
model the audit follows the standing hull from its head node and takes two figures
(`hull_chain_audit.hull_depth`): its depth (the deepest path, in clipnodes) and its reach (the clipnodes
reachable from the head). A hull is reported (`hull_chain_audit.over_limit`) only when it is a chain deeper
than the limit: depth above 256, and reach not above depth. A hull that reaches more clipnodes than its
depth is routed (or compiled) and is never reported, even where a routed house keeps straddling pieces in a
chain of 1,600 to 2,100.

**Kept as chain for memory.** With `--model-hull auto` the CHIM builder routes every chain over the limit,
with a memory fallback: while a frame's ring does not fit the CHIM zone, the routed mesh with the fewest
clipnodes in the peak ring keeps its chain, and the world is built again. The builder lists those meshes in
`chim-receipt.json` (`hull_fallback`) and the routed ones in `routed_hulls`. CHIMport reports the meshes the
fallback kept as their own outcome: the hull audit passes with the outcome `kept_as_chain`, and the meshes
are listed (`kept_as_chain_for_memory` in the hull audit's numbers and in the cell's collision figures).

**What it costs in memory.** CHIM Balmora's tightest ring, against a budget of 6,242,304 bytes:

| Hulls | Fits? |
| --- | --- |
| Chains only (v0.0.33) | Yes, 2,528 bytes to spare |
| Limit 256, no fallback | No, 1,920 bytes over |
| Limit 1,024, no fallback | No, 576 bytes over |
| Limit 256 with the fallback | Yes, 240 bytes to spare, four meshes kept as chains (two West Gash rocks, the silt strider, one Hlaalu house) |

The stair gate passes in every case.

**Hull policy pending.** A cell is hull policy pending when it converted and every other audit passes
(format, memory, stairs, doors and the rest) and only the hull check fails. The first island run was made
before the shared rule reached the builder line, with the audit's own stricter check (a standing hull 256
clipnodes deep or more, routed or not), so its 546 pending cells are audited again with the shared rule
once the builder line carries it; most should become passed.

**Defaults.** v0.0.33 ships house-size models as chains; after it, `--model-hull auto` (the shared rule
with the fallback) becomes the default again for legacy and CHIM. Every form stays selectable.

## What a cell is

Each exterior cell becomes its own CHIM frame: one cell is 2048 x 2048 map
units, cut into 8 x 8 chunks of 256 units and stored in sectors of 4 x 4
chunks (sectors must divide the frame; Balmora's 3 x 3 cell frame uses 3 x 3
chunk sectors). The frame is built by the CHIM builder itself
(`tools/chim/build.py`, the same code as `tools/chim_build.py`), with the
converter settings of a town frame made for that one cell, so there is no
second converter.

Everything placed in the cell is taken: terrain, statics, flora, lights,
doors, containers, activators and items become placed models. NPCs,
creatures, levelled creatures and invisible source markers are counted and
recorded as deferred with the converter's reason (the actor pipeline places
them). Every placed record of the base master is accounted for per record
type: converted, deferred (with reason), failed (with the conversion error) or
skipped (with reason).

A cell without a LAND record gets flat ground at the default height
(-2048 Morrowind units, the value OpenMW uses for cells without land) instead
of stopping the converter. This is an opt-in of the shared terrain audit
(`src/mwad/audit.py`, `missing_land='flat'`); town frames keep refusing a
square with missing land.

## Order: from the sea inwards

`chimport.py plan` reads the base master once and writes the order:

- **ring 0**: sea cells without land that hold any record (none in the base
  master: every cell that holds something has a LAND record there);
- **ring 1**: the outer edge of the cells with land (open sea with its seabed,
  rocks and wrecks);
- **ring 2, 3, ...**: each next layer inwards (an onion peel over the cell
  grid, 8 neighbours), up to the centre of the island.

Inside a ring the walk always steps to the nearest unvisited cell, clockwise
on ties, starting next to where the previous ring ended, so the converted area
grows as one piece. This is the same rule as the CHIM Progress Tracker's
spiral.

## Audits per cell

| Audit | What CHIMport runs | Failure means |
| --- | --- | --- |
| World format validation | `chim.validate.validate` on the cell's world | The world does not read back as written |
| Sky-bank texels | The validator's sky-bank check | A texture keeps texels the image repaints as sky |
| Seam tears | The validator's terrain/hull seam check | Terrain and its hull disagree at a seam |
| Far-terrain coverage | The validator's terrain coverage check | A chunk's ground leaves a hole |
| Stair walk | `chim.collision.require_stairs` | A flight of steps cannot be walked |
| Memory fit | `chim.heap.require_heap` (active ring 636, load ring 892) | A ring does not fit the CHIM zone |
| Hull chains | Standing-hull clipnodes and chain depth per model (`tools/hull_chain_audit.py` on the model images) | A model's hull 1 chain is 256 clipnodes deep or more |
| Doors | Doors converted against doors placed | A door of the cell is missing |
| Visibility | The validator's visibility measurement | (figures only) |

Hidden faces, sprite shape and actor grounding are recorded as "not measured"
until the CHIM builder has an audit for them (flora is converted as meshes in
a CHIMport cell; actors are deferred). An audit that cannot run is "not
measured", never "passed".

Errors are recorded with the stage they happened in and a mechanism class
(for example `missing-terrain`, `scenery-conversion`, `stair-walk`,
`heap-ring`, `measure-empty-world`, `timeout`). The run's summary counts cells
per class, so a class is fixed once in the shared builder and every cell of
that class is run again (`--retry-failed`), never patched one by one.

## Cell results

Each cell ends as one of:

- **passed**: converted, records placed, no error, no failed audit;
- **empty**: converted, but nothing is placed in the cell (open sea: terrain and water only), no error
  and no failed audit. Empty cells are counted apart so they do not inflate "passed"; a world without
  models is not stream-measured
  ([CHIM-MEASURE-EMPTY-FRAME-33](../bugs/CHIM-MEASURE-EMPTY-FRAME-33.md));
- **hull policy pending**: converted, and only the hull-chain check fails
  ([Hull policy pending](#hull-policy-pending)); counted apart from failures;
- **failed**: an error or a failed audit (the classes are in the summary);
- **not converted**: the cell world was not built.

## The growing world

When the last cell of a ring has finished, the run builds one CHIM world of every converted cell so far
(`RUN/world/ring-K/`: a frame per cell, every unit from the run's shared cache, so nothing is converted
twice) and audits it whole: format validation, the streaming walk and visibility measurement, the heap
rings (per frame and its neighbours, in parallel, with a cache;
[CHIM-WORLD-AUDIT-SCALING-33](../bugs/CHIM-WORLD-AUDIT-SCALING-33.md); `world --no-heap` leaves it out) and the stats; `world.json` records what it holds, its disk figures and what the audits found.
`chimport.py world --out RUN [--through-ring K]` builds it on request; `--world-every N` builds it every N rings
(and after the last), `--no-world` turns it off. It runs alone: no cell is converted beside it.

## Figures per cell

`cells/<cell>/result.json` (format `aw-chimport-cell-1`) holds, per cell:
record counts by type and category, unique meshes (new to the run and reused
from the unit cache), source triangles and CHIM faces (stored, placed,
terrain), textures and their bytes, chunks and bytes on disk, collision
(clipnodes, deepest standing-hull chain), memory (active and load ring peaks,
headroom, largest block, zone), visibility figures, conversion time (wall and
CPU seconds, per stage), every audit with its numbers, and every error.

`chimport.py export --out RUN --csv FILE --json FILE` writes one row per cell;
`chimport.py status --out RUN` prints totals per ring and the failure classes.

## Store once across the run

All cells share one unit cache (`RUN/units/`): a mesh, model variant or
texture is converted once and reused by every later cell, so the run's
"new meshes per ring" is the store-once reuse curve. The game inputs are
hashed once per run (`RUN/inputs.lock`, the build's input lock), not once per
cell.

## The shared storage pool

`--storage-pool on` puts CHIMport on the builder's shared, content-addressed
storage pool (`tools/storage_pool.py`, `docs/BUILD_CACHE.md`) instead of
keeping its own store. Share one pool between builds and the CHIMporter by
naming the same folder: `--storage-pool-dir DIR` (or `AMIWIND_STORAGE_POOL`,
or `--workspace W` for `W/cache/asset-pool-v1`).

- **Units** (meshes, model variants, textures, terrain chunks, visibility
  rows): each is keyed by its fingerprint (its inputs, the code that makes it
  and the switches that change it), stored once in the pool and hard-linked
  into `RUN/units/`. A unit whose key is in the pool, from any earlier run or
  workspace, is linked, not converted again.
- **Whole cells:** a cell's outputs (`chim/`, `far/`, its reports) are stored
  once and a manifest is kept under a cell key: the hash of the cell and its
  frame settings, the game inputs (the run's input lock), the palette, the
  qbsp binary, the engine sizes, every file of the converter (`tools/`, `src/`,
  `config/`), the `AMIWIND_*` switches and the Python and numpy versions. The
  same cell with the same key in any later run is linked whole, not converted.
  The key is deliberately broad; the fine-grained reuse after a code change
  is the units'. A cell's source stage (`work/`), `result.json` and `cell.log`
  are never shared.
- **`--reuse-mode`** `copy` (default) copies what the pool already holds into
  the run; `pool` (or `hardlink`) links it read-only.
- **Default `off`:** the run keeps its own `units/` cache as before. `auto` is
  on when a pool folder is named.
- When the pool and the run cannot be hard-linked (another file system or
  mount, or running as root), one warning is printed and recorded and the
  run copies instead; it never fails because of the pool.

Every run prints and records (`summary.json` and `state.json`, key `pool`;
`result.json` and `progress.jsonl` per cell) the bytes stored and linked, and
the cells and units reused, computed and failed.

CHIM workers convert region by region, each with its own run folder and all
on one pool, so nothing is converted twice:

```sh
python3 tools/chimport.py run --data-files DATA --palette PALETTE.lmp --out RUN-BITTER-COAST \
    --region "Bitter Coast" --storage-pool on --reuse-mode pool --storage-pool-dir POOL --workers 4
```

One `run` writes a run folder's `state.json` at a time: a second `run` on the
same folder refuses (`RUN/run.lock`). Use `--workers` for more cells at once,
or one run folder per worker sharing the pool.

## Running CHIMport yourself

```sh
python3 tools/chimport.py plan --data-files DATA --out RUN
python3 tools/chimport.py run --data-files DATA --palette PALETTE.lmp --out RUN \
    --qbsp QBSP --sdk SDK --workers 8 --jobs 1 --rings 2
python3 tools/chimport.py status --out RUN
```

- `--workers N` cells at once (default 8), `--jobs N` worker processes inside
  each cell (default 2);
- `--rings N` only rings 0 to N-1; `--cells "x,y x,y"` only these cells;
  `--region NAME` only the cells of a region as named in `plan.json`
  (repeatable; "Bitter Coast" finds "Bitter Coast Region");
- `--storage-pool on --reuse-mode pool --storage-pool-dir DIR` the shared
  storage pool (above);
- `--retry-failed` runs failed cells again; `--timeout S` stops a cell after S
  seconds (default 3600);
- `--dry-run` prints what would run;
- create `RUN/STOP` to stop starting new cells (running cells finish);
- a restart continues from `RUN/state.json`;
- `--sdk` lets the heap gate probe the engine's target sizes once per run;
- `--world-every N` builds the growing world every N rings (and after the last), `--no-world` never;
- `--tracker DIR --tracker-tool cell_progress.py` feeds the CHIM Progress Tracker as it goes.

The run folder:

| Path | What it holds |
| --- | --- |
| `plan.json` | The census and the ring order of every exterior cell |
| `state.json` | Each cell's state (pending, running, done, failed) and attempts: a restart continues from it |
| `STOP` | Create it to stop starting new cells; remove it and run again to go on |
| `run.lock` | Held by the one `run` that writes `state.json`; a second `run` on the folder refuses |
| `units/` | The shared unit cache: every mesh, model variant and texture converted once |
| `inputs.lock` | The game inputs hashed once per run |
| `cells/xNN_yNN/` | One cell: its CHIM world (`chim/`), the builder's reports and `result.json` |
| `world/ring-K/` | The growing world through ring K, with `world.json` |
| `summary.json`, `progress.jsonl` | Totals per ring and failure classes; one line per finished cell |
| `tracker/` | The result files fed to the tracker |

PALETTE is the game palette of a build (`id1/gfx/palette.lmp`). Run it in the
builder container, as every other build step. Everything in the run folder is
derived from your own game files and stays private.

## Feeding the CHIM Progress Tracker

The tracker system end to end is described in `docs/chim/PROGRESS_TRACKER.md`, and the result file format
CHIMport writes for it (`aw-cell-result-1`) in `docs/chim/CELL_RESULT_FORMAT.md`. Each fed cell carries
its status (passed, empty, hull_pending, failed, not_converted), whether it is eligible, its audits with
their numbers and outcomes, its errors and its figures.

With `--tracker DIR --tracker-tool cell_progress.py [--tracker-ingest ARGS]` the run feeds the tracker
automatically: every `--feed-every` seconds (default 180) and when a ring ends, the finished cells go to
the tracker's own ingester (`result --file`, then `ingest`), with no manual step.
`chimport.py feed --out RUN` writes the cells finished since the last feed as
a tracker result file (`RUN/tracker/result-NNNN.json`, format
`aw-cell-result-1`). The tracker's own ingester stores it
(`cell_progress.py result --file`) and remains the only writer of the
progress data; the Toolkit page then shows the cells' colours, the "CHIM
cells: passed / total" headline and the per-cell figures.

`RUN/progress.jsonl` has one line per finished cell (time, CPU, result) for
the build and perf ledger.
