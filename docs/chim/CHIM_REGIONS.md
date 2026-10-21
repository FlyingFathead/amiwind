# CHIM regions: exterior cells on CHIM inside the legacy open world

_Last updated with AmiWind v0.0.47-dev2 (21 October 2026)._

Status: the default of a full CHIM build since v0.0.47 (`--chim-regions`, BUILD-CHIM-CELLS-PRIVATE-LIST-47): with no
`--chim-regions`, `tools/build.py --builder chim` takes the cell list in the source tree, `config/chim-cells.json`
(every exterior cell of Vvardenfell, 1,409 cells: the release cells since v0.0.43), checked against
`docs/chim/cell-progress-reference.json` (the default of `--chim-regions-status`). `--chim-regions none` builds
with no CHIM region cells (the earlier default, kept selectable). Until v0.0.47-dev2 this was an experimental
option, off by default, and the releases named a cell list kept outside the source tree.

Update, 19 October 2026: this page describes how a cell joins a build, as designed in v0.0.36. Since v0.0.43 every
exterior cell of Vvardenfell is a CHIM frame (one cell per region frame, 1,348 of them, besides the three town
frames; [release notes](../RELEASE-v0.0.43.md)), so "the legacy open world stays the default" below describes
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
  `notes`), or the Toolkit World Map state export (`selected_cells[].cell`).

`FILE` is a CHIM progress tracker file (`cell-progress.json`) or the public reference
`docs/chim/cell-progress-reference.json`. The selection is resolved before any stage; the chim stage gets
the resolved cells on its command line (`--chim-regions-cells "x,y:k ..."`), so its fingerprint covers
exactly the cells and not the tracker file. `tools/chim/regions.py SET... --status FILE` runs the same
preflight on its own.

## Preflight (seconds, before any stage)

A build is refused, with every cell and its reason, when a selected cell:

- is not finished in CHIMport (taken: cell / terrain complete with or without lighting, owner states,
  audits passed, empty sea);
- is open sea without LAND (no legacy map to replace, and the engine does not read the shared ocean chunk
  yet: [WORLD_FORMAT.md](WORLD_FORMAT.md));
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

- Open-sea cells (no LAND) on the shared ocean chunk: when the engine reads it.
- Harvest catalogues of replaced maps, night-lamp entries of their cells, and the entity tracker's view of
  the replaced maps (it is taken before the replacement).
- Prefetch across the hand-over. (The border audit measures region frames: `tools/chim/stitch.py audit
  --regions all`.)
- Frames larger than one cell (fewer margins): they need a frame that owns several directory rows;
  with terrain references the margins between neighbouring frames are already stored once.
