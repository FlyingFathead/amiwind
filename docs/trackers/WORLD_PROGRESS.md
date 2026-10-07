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
