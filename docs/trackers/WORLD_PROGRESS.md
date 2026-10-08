# World progress tracker

**Status: first version in the image build (v0.0.31 development).**

One view of the whole conversion: Vvardenfell's exterior cell grid with
switchable layers: the World Map of the [AmiWind Toolkit](../AMIWIND_TOOLKIT.md)
([`amiwind-toolkit/`](../../amiwind-toolkit/index.html); open it in a browser,
nothing to install).

## The basis: the topomap

The open-world terrain is converted for the whole island. The table takes
each cell's terrain coverage from the image's own region table
(`id1/world/regions.awr`); every other layer sits on top of it.

## Layers

Tick any combination in the layer bar:

- **Island (local image):** your island, rendered on your machine (below).
- **Topomap (terrain):** cells with converted open-world terrain.
- **Heatmap: original entities:** how much the original game places in each
  cell, to see where the dense areas are.
- **Entities placed (share):** placed vs original placements
  ([entity tracker](ENTITIES.md)).
- **Full town/area maps:** cells with a fully converted town or area map.
- **Content missing:** outline where original placements are not placed.
- **Interiors:** interior entrances in the cell and how many are converted.
- **Named places:** cells with a named place ([POI checklist](POI.md)).
- **Owner checked:** cells walked and accepted in a playtest
  ([`checked.json`](checked.json), edited by hand).
- **Cell grid.**

Hover a cell for its numbers; click it to pin them under the map.

## In the build

Each image build writes `world-progress.json` (cell coordinates, counts and
status only; place names are never written) next to `entity-tracker.json`,
and records its hash in `build.json`. Load it with "Status".

## Your island image

With your own Morrowind installation, render the island from its terrain data
and load both files with "Island (local)":

```bash
python3 tools/world_progress_background.py --esm /path/to/Morrowind.esm --out island.png
```

The image is made from your game data: keep it on your machine.

Clicking a cell lists the maps covering it; with your maps folder chosen, a
button opens each one in the toolkit's 3D Map Inspector. Planned: a
polygon-count heatmap layer.

## Map limits: whole-world estimate (8 October 2026)

A first estimate of every map the whole island would need, with every object
placed, against AmiWind's limits (heap budget, faces, texture mappings,
collision nodes, brush models per map, entities, flames, lamps, coordinate
range). It was made from the owner's own data with an estimator calibrated on
1,102 converted maps and checked on 30 new conversions (heap error about 1 %
median; pass or fail agreed on all 28 maps it could check). A public builder
command to make the same estimate from your own Morrowind files is in
progress, with a Toolkit layer to show it on this map.

| Vvardenfell, every object placed | Maps |
| --- | ---: |
| Maps in total (interiors one each, exterior regions) | 9,698 |
| Under 90 % of every limit | 8,561 |
| Within 10 % of a limit | 490 |
| Over at least one limit | 647 (374 interiors, 273 exterior regions) |

| Limit | Maps over |
| --- | ---: |
| Brush models per interior (220) | 402 |
| Heap budget | 307 |
| Collision nodes (65,520) | 118 |
| Texture mappings (32,767 today; 65,535 planned clears all) | 76 |
| Night lamps per 3x3 cells (96) | 36 |
| Surface extent (256 texels) | 17 |
| Static flames (128) | 12 |
| Faces (65,535) | 8 |
| Coordinate range (4,096) | 8 |
| Entities (600) | 4 |

Treat 90 % of a limit as failing when planning: maps close to a limit are
under-estimated. Estimated conversion time for the whole island is about two
hours on 24 cores. Each limit hit is a bug in the register:
[INTERIOR-INLINE-LIMIT-31](../bugs/INTERIOR-INLINE-LIMIT-31.md),
[VIVEC-TEXINFO-31](../bugs/VIVEC-TEXINFO-31.md),
[LAMPS-CACHE-31](../bugs/LAMPS-CACHE-31.md),
[MESH-EXTENT-GRID-31](../bugs/MESH-EXTENT-GRID-31.md),
[FLAMES-CAP-31](../bugs/FLAMES-CAP-31.md),
[INTERIOR-COORDS-31](../bugs/INTERIOR-COORDS-31.md),
[LIGHTMAP-TAIL-31](../bugs/LIGHTMAP-TAIL-31.md),
[BUILD-EXPANSIONS-31](../bugs/BUILD-EXPANSIONS-31.md) (Tribunal and Bloodmoon:
1,112 more maps, not yet convertible) and
[IMPORT-TEST-CELLS-31](../bugs/IMPORT-TEST-CELLS-31.md).
