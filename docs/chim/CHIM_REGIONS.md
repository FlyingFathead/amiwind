# CHIM regions: exterior cells on CHIM inside the legacy open world

_Last updated with AmiWind v0.0.68 (24 November 2026)._

<!-- contents start -->
## Contents

- [How a cell joins](#how-a-cell-joins)
- [The frame and its margin](#the-frame-and-its-margin)
- [Selecting cells](#selecting-cells)
- [The recordless open sea](#the-recordless-open-sea)
- [Preflight (seconds, before any stage)](#preflight-seconds-before-any-stage)
- [The ownership table](#the-ownership-table)
- [Not yet](#not-yet)

<!-- contents end -->

Status: the default of a full CHIM build since v0.0.47 (`--chim-regions`, BUILD-CHIM-CELLS-PRIVATE-LIST-47): with no
`--chim-regions`, `tools/build.py --builder chim` takes the cell list in the source tree, `config/chim-cells.json`
(every exterior cell of Vvardenfell, 1,409 cells: the release cells since v0.0.43), checked against
`docs/chim/cell-progress-reference.json` (the default of `--chim-regions-status`). `--chim-regions none` builds
with no CHIM region cells (the earlier default, kept selectable). Until v0.0.47-dev2 this was an experimental
option, off by default, and the releases named a cell list kept outside the source tree.

Update, 19 October 2026: this page describes how a cell joins a build, as designed in v0.0.36. Since v0.0.43 every
exterior cell of Vvardenfell is a CHIM frame (one cell per region frame, 1,348 of them, besides the three town
frames; [release notes](../releases/notes/RELEASE-v0.0.43.md)), so "the legacy open world stays the default" below describes
v0.0.36, not the releases.

CHIMport ([CHIMPORT.md](CHIMPORT.md)) converts the island cell by cell and grades every cell
([cell tracker](CELL_TRACKER.md)). `--chim-regions` puts finished cells on CHIM in a normal build, inside
the legacy open world: the player walks from legacy land onto CHIM cells and back. Nothing else changes:
the towns, the interiors and every other open-world map stay as they are, and the legacy open world stays
the default.

## How a cell joins

The legacy open world is one map per cell (`vfNNNN`, the open-world directory `world/regions.awr`); denser
cells are split into 2 x 2 or 4 x 4 maps (316 and 12 of 1,404 cells), whose cores tile exactly that cell. A CHIM
region frame is **one cell**, and its frame map **takes the place of that cell's open-world map under the same
name**: `maps/vfNNNN.bsp` gives way to
`maps/vfNNNN.chim`, an empty world whose worldspawn names its CHIM frame (`_chim_frame`), and the engine
draws, collides and streams the cell from the CHIM world as it does for a CHIM town ([ENGINE.md](ENGINE.md)).
The map name stays `vfNNNN`; only the file extension says it is a frame map (`vf1637.chim` beside
`vf1638.bsp`). The engine and every tool find a map through one resolver: `maps/<name>.chim` when the image
has a CHIM world and that file exists, else `maps/<name>.bsp`
([WORLD_FORMAT.md](WORLD_FORMAT.md#frame-maps-are-chim-files)). With `--chim-frame-ext bsp` the frame map
replaces `maps/vfNNNN.bsp` under its own file name, as before.

Because the map keeps its name and its directory row:

- the engine's hand-over between open-world maps (`aw_world.c` `AW_WorldDestination`) is unchanged: the
  player enters the cell at its edge and leaves 64 units past it, exactly as between two legacy maps; from
  one CHIM cell to the next is one map load, as before;
- saves, the world map, teleports, fog, the location HUD and every open-world tool keep working by name;
- walking the island loads no more maps than the legacy open world does.

The directory row keeps its core (the cell) and its cover; only its origin height becomes 0 (a CHIM
frame's heights are the game's x 0.25; a legacy map's are shifted to fit its own range).

A divided cell is one frame too (CHIM-REGION-DIVIDED-CELLS-36): none of its legacy maps is made, the world
terrain stage widens the row of its first map (lowest index) to the whole cell, and the other maps' rows become
aliases of it with the same origin, core and cover. The engine takes the first row whose core holds a point, so
the whole cell resolves to the first map's name, where the frame map is installed; no alias is ever a
destination. The earlier method (`--chim-region-rows legacy`, which copies one legacy map) takes one-map cells
only. Design: [BUILD_MANIFEST.md](../BUILD_MANIFEST.md) step 2b.

What the frame map carries over from the legacy map (`chim.frame_map.build_region`): its worldspawn (sky and
fog keys), its player start and its point entities inside the cell (flora sprites, sounds, as the legacy
chain made them), moved to the frame's origin. Every static of the legacy map must be a CHIM placement of
the frame (counted, refused otherwise), and an object the engine activates keeps its edict. Harvestable
plants: the CHIM world leaves them out, and the image step's harvest plan writes a catalogue for each region
frame map under the cell's map name, in the frame's coordinates (`tools/harvest_build.py plan_rows`); the
engine loads it with the frame map. That catalogue stays; any other catalogue of the replaced map leaves the
image (recorded). A coverage check stops the build when a plant the CHIM world left out is in no catalogue,
or a region cell's plant is not in its own frame map's catalogue (HARVEST-CHIM-REGION-LOSS-41).

## The frame and its margin

Each frame owns its cell (2048 map units) and carries a terrain-only margin of 896 units on every side
(no placements of its own there), so that from every hand-over point there is ground up to the fog plane
where the far terrain layer starts ([STITCH_AUDIT.md](STITCH_AUDIT.md), CHIM-FAR-BAND-GAP-36: at least
draw distance + 32). 896 units is also the legacy map's own coverage, and it makes the frame 15 x 15
chunks of 256 units, which the world's sector size (3) divides. Neighbouring frames may share margin
terrain (each stores its own copy); they never share their owned box (`chim.world.frame_order` compares
owned boxes). The margin multiplies a cell's terrain storage by about 3.5
([CHIM-REGION-MARGIN-STORAGE-36](../bugs/CHIM-REGION-MARGIN-STORAGE-36.md)).

Two build settings take that back (both the default since v0.0.36; `--chim-terrain-hull auto` and
`--chim-terrain-refs off` select the earlier per-chunk terrain):

- `--chim-terrain-hull compiled` (default): the chunks' standing hull compiled by qbsp from the same pieces instead of
  routed chains: about half the bytes. Each compiled hull is checked against the exact union of its pieces;
  pieces the compiler lost are patched in (model hulls too, `--chim-model-hull-patch`, on by default), and a
  chunk whose hull still fails keeps the routed hull
  ([CHIM-COMPILED-HULL-SHORT-36](../bugs/CHIM-COMPILED-HULL-SHORT-36.md)).
- `--chim-terrain-refs on` (default): terrain references (world format 0.7, [WORLD_FORMAT.md](WORLD_FORMAT.md)
  "Terrain references"): every chunk's terrain stored once per content and placed at an offset, so
  neighbouring frames share their margins and repeated sea floor is stored once.

Together, measured on two scratch worlds of 7 and 6 cells, the CHIM frames take 0.91 and 0.93 times the
bytes of the open-world maps they replace (copies with the routed hull: 4.3 and 3.6 times).

## Selecting cells

    tools/build.py ... --builder chim [--chim-regions SET ...] [--chim-regions-status FILE]

`SET` is one of (none given: `@config/chim-cells.json`):

- `none`: no CHIM region cells (the earlier default);
- `seabed`: the empty sea cells (a LAND record, nothing placed);
- `coast`: the finished land cells of ring 1 (the cells that touch the sea);
- `sea-ring`: both;
- `coast2`: the whole coastline of v0.0.36 (project decision 11 October 2026): every cell of rings 1 and 2 from
  the sea. A cell that cannot go on CHIM (not finished in CHIMport, open sea, inside a town's frame) is left
  out and listed with its reason under `dropped` in the ownership table; nothing in it is refused;
- a region name (`"Bitter Coast"` finds "Bitter Coast Region"): its finished cells;
- `@FILE`: a CSV with `x` and `y` columns (the tracker's Export CSV as it is), a JSON cell list
  (`aw-chim-cells-1`, schema `config/schemas/aw-chim-cells-1.json`: `cells`, `regions`, `reason`,
  `notes`, `recordless`), or the Toolkit World Map state export (`selected_cells[].cell`).

With no `--chim-regions`, the default is `config/chim-cells.json` and `config/chim-sea-grid.json` (the recordless
open sea inside the base game's box, below).

## The recordless open sea

The world map ends at the box of every exterior cell record of the selected game files: OpenMW draws its world map
over exactly that box (`apps/openmw/mwrender/globalmap.cpp`, lines 291-308). With Morrowind.esm, Tribunal.esm and
Bloodmoon.esm that box is cells x -29 to 23, y -19 to 28 (2,544 cells); with the base game alone it is x -18 to 23,
y -19 to 27. Inside the box the original game has open sea wherever no cell is defined: a cell that no game file has
a record for is made the first time it is needed, as an empty exterior cell with water
(`apps/openmw/mwworld/worldmodel.cpp`, lines 55-62, the `HasWater` flag), the water at the sea level
(`apps/openmw/mwworld/cell.cpp`, lines 98-102) over the flat default height of -2048 units
(`components/esm3/loadland.hpp`, line 77; `components/esmterrain/storage.cpp`, lines 571-577). So the player can swim,
walk on water or jump between Vvardenfell and Solstheim, and around both, as far as the map reaches.

AmiWind builds every cell of that box. A cell with a record is built as before. The cells without any record (982 of
them) are the open-sea frame of the shared ocean chunk ([WORLD_FORMAT.md](WORLD_FORMAT.md), "Shared ocean chunk"),
listed in two cell files marked `"recordless": true` and written from the game data by `tools/chim/sea_grid.py write`:

- `config/chim-sea-grid.json`: the 542 recordless cells inside the base game's own box, part of the base world, so a
  build without Bloodmoon has its own whole map;
- `config/solstheim-sea-grid.json`: the 440 recordless cells of the area Bloodmoon adds to the box, a world of their
  own in the Bloodmoon module (the stage `bloodmoon-solstheim-sea`, the store `chimsea`). They are not in Solstheim's
  world, so Solstheim's store index does not grow: its densest forest frame has little room left at 32 MB.

The rule for these cells, in the preflight: a cell of a recordless list is open sea even when the tracker file has no
finished status for it (every such cell is the same shared ocean chunk, measured once); the preflight checks with the
game files, in seconds, that no file has a CELL or LAND record for any of them, and refuses the build otherwise. Their
frames come after every other cell of their world, so the frames, the frame map names (`vfNNNN`, `slNNNN`) and the
placement order of the cells built before stay as they were; the base world's routing rows for them follow its
earlier ones. The progress tracker counts them as sea in the game once a build that holds them is ingested.

The edge of the world (the sea current of [WORLD_BOUNDS.md](../WORLD_BOUNDS.md)) is then only at the edge of the box.
Where two worlds meet (Vvardenfell's and Solstheim's, Solstheim's and its open sea's, the open sea's and Vvardenfell's),
the engine hands the player over by the open-world directory, which holds every world's rows; that crossing is a
change of level, as the engine streams one store at a time.

The image step checks every frame of every store, every room and every crossing between two worlds against 32 MB of
Fast RAM in its first seconds (`tools/chim/traversal_heap.py`, the report `image/traversal-memory.json`): each frame
with its own store's index, each room by the rooms stage's early report, each edge between two stores and each door
between a room and a frame by the larger of its two ends (the area left behind is freed on a change of level). A
frame, room, edge or door over 32 MB stops the image step there, named.

`FILE` is a CHIM progress tracker file (`cell-progress.json`) or the public reference
`docs/chim/cell-progress-reference.json`. The selection is resolved before any stage; the chim stage gets
the resolved cells on its command line (`--chim-regions-cells "x,y:k ..."`), so its fingerprint covers
exactly the cells and not the tracker file. `tools/chim/regions.py SET... --status FILE` runs the same
preflight on its own.

## Preflight (seconds, before any stage)

A build is refused, with every cell and its reason, when a selected cell:

- is not finished in CHIMport (taken: cell / terrain complete with or without lighting, owner states,
  audits passed, empty sea);
- is open sea without LAND and not listed by name (open sea is taken only from an explicit cell list; the recordless
  open sea of the map's box is listed, above: [WORLD_FORMAT.md](WORLD_FORMAT.md), [WORLD_BOUNDS.md](../WORLD_BOUNDS.md));
- lies in a town's frame (named on purpose; cells of `seabed`, `coast` and region names that do are left
  out and listed instead: towns keep their own frame);
- or leaves a pocket: up to 8 unselected cells enclosed by selected cells (4-connected, so a pocket open
  only at a corner is enclosed). A larger enclosed area, such as the island inside a sea ring, is legacy
  territory.

The CHIM world's gates then run on every frame (validation, stair walk, CHIM heap and zone walk), and the
image runs the frame-map heap gate on every replaced map.

## The ownership table

The chim stage writes `chim-world/chim-regions.json` (`aw-chim-ownership-1`): every cell with its frame
id (`rcm7_p2` for cell -7,2) and kind (seabed or land), every frame (cell, origin, owned core, ground with
the margin), the cells left out with their reasons and the selection. The image step reads it to replace
the maps; `chim-removed-legacy.json` records every replaced file with its hash, and the optimizer receipt
lists the replaced maps under `chim_rebind.replaced_by_region_frames`.

## Not yet

- Open sea outside the map's box stays outside the playable world (the original game's sea goes on; AmiWind's ends at
  the edge of the map). Inside the box every cell is built, with or without a record (above).
- Harvest catalogues of replaced maps, night-lamp entries of their cells, and the entity tracker's view of
  the replaced maps (it is taken before the replacement).
- Prefetch across the hand-over. (The border audit measures region frames: `tools/chim/stitch.py audit
  --regions all`.)
- Frames larger than one cell (fewer margins): they need a frame that owns several directory rows;
  with terrain references the margins between neighbouring frames are already stored once.
