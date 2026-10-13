# The CHIM progress map: what CHIMport is and what every colour means

The CHIM progress map shows, cell by cell, how far AmiWind's open world has moved from Quake's old way of storing a
map onto CHIM. It appears in the README, in the release notes and in the Toolkit (the World Map's CHIM Progress
Tracker layer). This page explains the work behind it in plain words, then goes through every colour: what it
means, the problems that usually sit behind it, a few examples, what fixes it and who decides. The tracker itself,
its statuses and its commands are described in [CHIM Progress Tracker](PROGRESS_TRACKER.md); the live figures are on
the generated [CHIM cell tracker](CELL_TRACKER.md).

<!-- contents start -->
## Contents

- [What CHIMport is](#what-chimport-is)
- [Why: what Quake's map format cannot do for an open world](#why-what-quakes-map-format-cannot-do-for-an-open-world)
- [What CHIM does instead](#what-chim-does-instead)
- [Reading the map](#reading-the-map)
- [Green: done](#green-done)
  - [Cell complete and terrain complete](#cell-complete-and-terrain-complete)
  - [Awaiting lighting (green with cyan stripes)](#awaiting-lighting-green-with-cyan-stripes)
  - [Passed, something still deferred (plain green)](#passed-something-still-deferred-plain-green)
- [Violet: hull policy pending](#violet-hull-policy-pending)
- [Red: failing a check](#red-failing-a-check)
- [Magenta: not converted](#magenta-not-converted)
- [Dark grey: not started](#dark-grey-not-started)
- [Blue: empty sea](#blue-empty-sea)
- [Silver: open ocean](#silver-open-ocean)
- [Gold: planned for a release](#gold-planned-for-a-release)
- [Owner marks: approved, playtested, accepted](#owner-marks-approved-playtested-accepted)
- [Problems that are not a colour](#problems-that-are-not-a-colour)
- [Who decides what](#who-decides-what)
- [Package inclusion](#package-inclusion)

<!-- contents end -->

## What CHIMport is

Morrowind's world is one big outdoor space made of square cells (Vvardenfell has 1,292 land cells, Solstheim 144).
AmiWind started by cutting that space into many small Quake maps, one per region, and loading them one at a time.
**CHIMport** is the work of moving the whole island from those legacy Quake region maps onto CHIM, the project's
own way of storing and streaming a world ([CHIM](README.md)). It goes cell by cell, **starting at the coast and
spiralling inward**, because the coast is where the land meets the sea and the neighbouring cells can be checked
edge by edge. [CHIMport](CHIMPORT.md) describes the conversion tool and its audits; the progress tracker keeps the
score, and the map is the picture of that score.

## Why: what Quake's map format cannot do for an open world

AmiWind runs on a Quake engine (AmiQuake). Quake maps (the BSP29 format) were made for corridors and rooms, not for an
island. The documented problems for an open world are:

- **A map is one self-contained file with fixed limits.** Its tables use 16-bit indices, an entity can touch at most
  16 leaves of the map before it counts as visible everywhere, and there are fixed limits on surface lists and texture
  info ([the .chim map format](CHIM_MAP_FORMAT.md)). A whole area cannot be one map.
- **Coordinates are small.** The engine's positions were designed for a range of about +-4,096 units, so a large
  area has to be re-centred as the player moves ([engine notes](ENGINE.md)). Version 0.0.36 widens the range so
  that a whole city fits one map ([release notes](../RELEASE-v0.0.36.md)).
- **Every map is a separate file, and objects are copied.** The old exterior regions each carry a core of 768 units
  plus an overlap on every side, so each placed object is stored about ten times, and every
  map holds its own copy of every texture it uses ([world streamer](../WORLD_STREAMER.md)).
- **Quake's visibility does not help outdoors.** Quake hides what cannot be seen through walls; in the open air
  almost everything can be seen, so the visibility data culls little ([town visibility](../performance/TOWN-VISIBILITY.md)).
- **Every region crossing reads a whole map** from a slow disk ([Seyda Neen performance](../SEYDA_NEEN_PERFORMANCE.md)).
- **The Amiga is small.** Memory is tight; disk partitions must stay below 2 GiB and drive images below
  4 GiB ([image size](../IMAGE_SIZE.md)). Storing the island ten times over does not fit, and loading it
  whole into memory is out of the question.

## What CHIM does instead

- **Store once, place by reference.** Every mesh, collision shape and texture is stored a single time; a placement
  is a small record that names its model ([world streamer](../WORLD_STREAMER.md)).
- **Small pieces, streamed.** The land is cut into frames of 3 x 3 cells, chunks of 256 units and small sector
  files that a classic Amiga disk reads whole; the engine streams them around the player ([CHIM](README.md),
  [world format](WORLD_FORMAT.md)).
- **Shared terrain.** Terrain is stored once as compiled pieces, and the open sea around the island is a single
  shared ocean piece.
- **Its own map file.** A CHIM map is a `.chim` file, no longer a Quake `.bsp`, and the plan is to leave BSP29's
  limits behind step by step; interiors stay ordinary Quake `.bsp` maps until they move too
  ([the .chim map format](CHIM_MAP_FORMAT.md)).
- **Wide coordinates**, so one frame can cover a whole city.

## Reading the map

Each square is one map cell, north up. The colours are the statuses of the tracker, drawn by the Toolkit and by
`tools/cell_progress_map.py` for the README. The table is a snapshot of the tracker data of 11 October 2026 (the
v0.0.36 development line); the live numbers are on the [CHIM cell tracker](CELL_TRACKER.md).

| Colour | Status | Cells | Counted as done |
| --- | --- | ---: | --- |
| Green | Terrain complete, awaiting lighting | 367 | yes |
| Green | Cell complete, awaiting lighting | 96 | yes |
| Green | Passed, something still deferred | 456 | yes |
| Blue | Empty sea | 103 | yes |
| Violet | Hull policy pending | 218 | no |
| Red | Converted, failing a check | 23 | no |
| Magenta | Not converted | 29 | no |
| Dark grey | Not started (Solstheim and 8 cells outside both island maps) | 152 | no |
| Silver | Open ocean | 867 | no |
| | **TOTALS** | **2,311** | **1,022 done** |

The Done figure is 1,022 of 1,292 Vvardenfell land and empty-sea cells (79.1 %); the open ocean is counted on its
own line and is not part of it (see [Silver](#silver-open-ocean)). The 2,311 cells above are 2,158 map cells of
Vvardenfell, with its 866 open-ocean cells, 145 of Solstheim and 8 that belong to neither island's map. Gold is not a status of its own: it is a
second layer, the release plan, drawn over the statuses ([Gold](#gold-planned-for-a-release)).

## Green: done

A green cell is converted to CHIM and every audit that has been measured has passed. Green has three shades of
meaning, from most to least finished.

### Cell complete and terrain complete

**What it means.** The terrain and every placed object of the cell are converted, all audits passed and the cell is
lit like the original. *Terrain complete* is the same except that characters (NPCs and creatures) may still be
deferred. Today the map has no cell in either state: the lighting audit has not passed anywhere yet (see below).

**What fixes it.** Lighting that matches the original, and converting the characters. Both are code work, not
decisions; the owner decides when the lighting is "like the original".

### Awaiting lighting (green with cyan stripes)

**What it means.** Everything a complete cell needs except the lighting audit, which counts the cell as done anyway.
Today 463 cells are here (96 cell-complete-but-unlit, 367 terrain-complete-but-unlit).

**What it usually is.** The lighting audit looks at whether light reaches the frame and whether the surfaces carry
real light data. Of the 463 cells, 420 are *unlit* (no light source reaches the frame and no surface carries real
light data: the terrain has a constant light and models have no lightmaps) and 43 are *partial* (some lights only
as night lamps, others not represented, some without a mesh). Of the 1,436 land cells, 276 have no lighting
measurement yet, and no cell is lit yet.

| Lighting state of the awaiting-lighting cells | Cells |
| --- | ---: |
| Unlit | 420 |
| Partial | 43 |
| **TOTALS** | **463** |

**What fixes it.** The lighting work ([lighting](LIGHTING.md), [lighting roadmap](LIGHTING_ROADMAP.md)): baking the
lights of a cell into its CHIM pieces so that terrain and models are lit the way the original game lights them. The
decision about what "lit like the original" means is the owner's; the baking is code.

### Passed, something still deferred (plain green)

**What it means.** Converted, and every audit that was measured passed, but something placed in the cell was
deferred or skipped on purpose: the converter lists each one with its reason ([what is in a converted cell](CHIMPORT.md#what-is-in-a-converted-cell)).
Today: 456 cells.

**What it usually is.** The deferred things are the same kinds everywhere: light emitters (the cell counts
"lights converted" below the total), creatures, NPCs and, rarely, statics. Cells can appear in several rows:

| What is still deferred in a passed cell | Cells |
| --- | ---: |
| Lights not all converted | 453 |
| Creatures not all converted | 423 |
| NPCs not all converted | 43 |
| Statics not all converted | 4 |
| **Passed cells (each counted once)** | **456** |

**What fixes it.** Characters are placed by the character pipeline (their behaviour is never invented: it follows the
local reference sources and OpenMW); light emitters without a mesh need the lighting work above. These are code
fixes made once at the shared layer and then applied to every cell.

## Violet: hull policy pending

**What it means.** The cell converted, and every audit passes (format, memory, stairs, doors and the rest) except
one: the *hull chain* check. It is neither passed nor failed: it waits for one shared rule. Today: 218 cells.

**What a hull chain is.** Every model that something can bump into has a collision shape, a tree of tests the engine
walks when a player or character moves near it. Written as a **chain**, the model's convex collision pieces are tested
one after another, so a house made of a few hundred pieces is a chain a few hundred tests deep; every step of a
character near it pays for all of them. Written as **routed**, the pieces are sorted into a nested tree and a step
visits only a few. The rule is `CHAIN_DEPTH_LIMIT`: a chain deeper than **256** is reported. Details and the
measured costs are in [hull policy pending](CHIMPORT.md#hull-policy-pending).

**Why the router cannot just split every chain.** Two reasons. A chain of overlapping pieces (the blades of a plant) cannot
be cut into a tree of non-overlapping cuts. And routing costs memory. The extra nodes eat into the memory the
engine reserves for a frame's models and flora, and a frame whose ring of chunks already uses its whole budget has
none to spare. So the builder routes every chain over the limit and, where the frame would no longer fit, keeps the
fewest-node mesh as a chain and builds again; that is "kept as chain for memory". On Balmora's tightest ring, a
limit of 256 without that fallback was 1,920 bytes over the budget; with it, 240 bytes to spare. A model that is both
deep and unroutable in the available memory stays pending.

**What actually blocks the 218 cells.** Measured on the tracker data of 11 October 2026: every violet cell is blocked by
**plants**, not by buildings. A plant's collision is one chain of overlapping blades (many thin pieces, one after
another), which the router cannot split into a tree because the pieces overlap each other; each is over the 256 limit
of the audit. The depth is the longest path of the chain in clipnodes.

| Plant (type) | Cells blocked | Chain depth |
| --- | ---: | ---: |
| Kelp (two variants) | 65 | about 305 |
| Kreshweed | 80 | 280 |
| Grass | 37 | 348 |
| Gold kanet | 29 | 267 |
| Willow flower | 25 | 362 |
| Fire fern (variant 2) | 16 | 317 |
| Tree, Grazelands (variant 8) | 12 | 285 |
| Fire fern (variant 1) | 6 | 496 |
| Black anther | 1 | 484 |
| Emperor parasol | 1 | 486 |
| **Violet cells (each counted once)** | **218** | |

A cell can contain several of these plants, so the rows add up to more than 218. Counted once: **65 cells are blocked by
kelp alone**, and the other **153 by the nine other plants**: 116 by one plant, 20 by two and 17 by three.

The kelp case has a decision already: the owner accepted the kelp chain on 11 October 2026 (12:01), and those 65 cells
clear on their next run. For the nine other plants, the choice below is open.

**What fixes it, and who decides.** Two things, one of each kind. A **code fix**: split or simplify the collision of
the thin plants so that it is no longer a chain (for example fewer, fatter collision pieces), or a router that can
cut an overlapping chain. A **policy choice** by the owner: whether a thin plant may be **kept as a chain** and
counted as passed (the audit records the outcome as `kept_as_chain`), or whether the cells keep waiting until
the collision is rebuilt. The mechanism does not decide that: a chain costs every collision trace near the plant (the measured cost per
clipnode is in [hull policy pending](CHIMPORT.md#hull-policy-pending)), and the owner weighs that against the memory and
the work spent on the model. Until the choice is made the cells
are counted apart, not as failures.

## Red: failing a check

**What it means.** The cell converted, but at least one audit failed or the conversion reported an error. Today: 23
cells. These are real problems, each one mechanism fixed once and then re-run for every cell of its class.

| Audit that failed | What it means | Cells |
| --- | --- | ---: |
| Memory fit | The ring of chunks around a point does not fit the CHIM zone; the frame ran out of heap | 12 |
| Hull bevels (hull chain, old strict check) | Models over the chain-depth limit, judged by the stricter check of an earlier run | 12 |
| Stair walk | Steps that the standing box of a character cannot walk (a stair a character could not climb) | 11 |
| **Failing cells (each counted once)** | A cell can fail more than one audit | **23** |

**What usually causes each.**

- *Memory fit* means a frame's ring of chunks does not fit the CHIM zone (the large-model cut and the zone budget).
  It is fixed at the shared layer, not cell by cell.
- *Stair walk* is a geometry problem in the converted steps. The audit walks every flight and reports the steps the
  standing box cannot walk; the cause is traced and fixed at the shared layer, never one flight at a time.
- *Hull bevels* failing in a red cell is the same chain-depth question as violet, judged here as a failure.

**Who decides.** Almost always a code fix. The exception is a failure the owner accepts for a development build
(a cell marked *accepted*, see below).

## Magenta: not converted

**What it means.** The conversion was tried and could not finish the cell. A failure state, never counted as done.
Today: 29 cells.

| Reason the conversion stopped | Cells |
| --- | ---: |
| A stale source stage predates the lava conversion and its town has lava pools | 25 |
| A window has no supporting façade within mounting range | 4 |
| **TOTALS** | **29** |

- **Lava, stale source (25 cells).** The cells were violet before. A re-run used an older source stage that was
  built before lava pools were converted, and the builder refuses to mix them: "use a new work folder (or
  `--lava static`)". It is a tooling problem, not a problem of the cells
  ([CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](../bugs/CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md)). Fix: start the re-run in a
  new work folder; it is the first item of the v0.0.37 plan.
- **Window mounted across a cell border (4 cells).** A window whose façade is placed in the next cell cannot find
  its wall inside its own cell. Four exterior cells are affected, in four different towns of the island
  ([CHIM-WINDOW-MOUNT-CROSS-CELL-33](../bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md)). Fix: a code change in the window
  mounting so that it may look into the neighbouring cell.

**Who decides.** Code fixes. The re-run is mechanical once the fix is in.

## Dark grey: not started

**What it means.** The conversion has not reached the cell. Today: 152 cells, 144 of them on Solstheim and 8 outside both island maps; the whole of
Vvardenfell has been reached. Nothing is wrong with them; they simply wait for their turn in the order (coast first,
inward).

## Blue: empty sea

**What it means.** A land-record cell with nothing placed in it: just terrain and the water. It passes as it is and
counts as done, because the open world needs the water around the coast. Today: 103 cells (the seabed cells next to
the coast).

## Silver: open ocean

**What it means.** A map cell with **no land record at all**: open sea. All of them refer to one shared ocean
piece, stored once ([open sea](CHIMPORT.md#open-sea-one-shared-ocean-chunk)). Today: 867 cells (866 around
Vvardenfell, 1 at Solstheim).

**Why it is not done.** The piece is made and checked, but the engine does not place it yet; it will once the
open-world frames read it. Counting these cells as done would have shown progress the game does not have, so they
have their own colour, their own line in the figures and their own totals row, and are left out of Done
([TRACKER-OCEAN-COUNTED-DONE-36](../bugs/TRACKER-OCEAN-COUNTED-DONE-36.md)).

**What changes it.** Engine work: reading the ocean piece in the open-world frames. When that lands, the ocean moves
into the done figure in one place (`DONE_SEA` in the tracker's ingester).

## Gold: planned for a release

**What it means.** Gold is not a state of the conversion. It is the **release plan**: the cells the project intends
to ship in a release, a layer drawn over the status colours (it never changes them). The next release is gold; later
planned releases are a paler gold; a shipped release goes back to its status colours. The plan is data, so the next
release becomes gold by itself when the current one is published
([the release plan](PROGRESS_TRACKER.md#the-release-plan-gold-for-the-next-release)).

| Plan | Cells | Scope |
| --- | ---: | --- |
| v0.0.36 (gold) | 368 | the coast (outer ring and seabed), Seyda Neen, Balmora, all of Vivec |
| v0.0.37 (pale gold) | 670 | all green zones on CHIM |
| **TOTALS** | **1,038** | |

A gold cell can be any status. A gold cell that is violet or red is a gap between what is planned and what is
finished, which is exactly what the layer is for. **Who decides:** the owner makes the plan; nothing in the code
changes it.

## Owner marks: approved, playtested, accepted

Three marks are set by the owner and never by a tool.

- **Approved** and **playtested** (gold-yellow and teal in the Toolkit): the owner looked at a converted cell that
  passes and approved it or played it. Today: none.
- **Accepted:** an audit failure the owner accepted for a development build, labelled as such. A failure is never
  accepted silently. Today: none.

## Problems that are not a colour

Some problems keep a cell from being converted or from switching to CHIM without having a colour of their own.

- **Divided cells.** The legacy builder sometimes split one cell over several map files, and a CHIM region frame
  replaces exactly one. Such a cell converts fine but cannot switch to CHIM inside the open world until the frame is
  allowed to own the whole cell. Repaired in source, build verification pending (the image step's handling of the alias map rows of a divided cell is
  being fixed on the same branch)
  ([CHIM-REGION-DIVIDED-CELLS-36](../bugs/CHIM-REGION-DIVIDED-CELLS-36.md)).
- **Lava.** 27 cells hold 349 lava pools; none is converted yet, so lava stays "mapped, not converted". It is a
  separate layer in the Toolkit ([lava](../LAVA.md)).
- **Audits never measured.** Several audits have no result for any cell yet (character grounding, hidden faces,
  sprite shape); they show as "not measured" and are never counted as passed.
- **Lighting not measured.** 276 land cells have no lighting measurement yet.

## Who decides what

| Kind of problem | Decided by | Example |
| --- | --- | --- |
| A mechanism that is wrong or missing in the converter or the builder | Code fix, once at the shared layer, then every affected cell is re-run | Stair walk, memory fit, window mounting, the lava re-run folder |
| A rule that trades memory for speed or cells against each other | Owner policy | The hull chain limit and whether a cell may keep a chain for memory |
| What counts as done | Owner policy, written into the tracker's definitions | Open ocean is not done until the engine places it |
| What ships in which release | Owner (the release plan, gold) | The v0.0.36 and v0.0.37 plans |
| Playtested, approved, accepted | Owner only | An accepted audit failure in a development build |
| The engine does not use the output yet | Engine work | Placing the ocean piece |

## Package inclusion

Use **Included in build** in the Toolkit to view verified package coverage independently of plans. Green marks region frames whose files match final HDF readback. Amber marks selected cells of an unfinished build. Grey means coverage is not established in the displayed dataset, not necessarily absent from the game. The initial verified record covers 325 region cells in v0.0.36; town-frame boundaries and earlier releases remain to be reconciled. Conversion, actors, lighting and traversal are separate checks.
