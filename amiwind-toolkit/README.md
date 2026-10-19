# AmiWind Toolkit

_Last updated with AmiWind v0.0.39 (14 October 2026)._

The AmiWind Toolkit is a set of web pages for looking at AmiWind's world: where the conversion stands on the
island map, any converted map in 3D, and its polygon and memory figures. Everything runs in your own browser.
The views are made from your own Morrowind files and your own build output; nothing is uploaded, and no game data
ships with the Toolkit.

Full guide: [docs/AMIWIND_TOOLKIT.md](../docs/AMIWIND_TOOLKIT.md).

Final v0.0.39 updates historical-image labels and verified RC1 inclusion data.
The Toolkit metadata is version 0.1.3 and its header names AmiWind v0.0.39;
the inspection controls below retain their v0.0.38 behavior.

## v0.0.38 inspection controls

The public Toolkit includes the same inspection controls used with local build
output. Supply your own converted maps, CHIM world data and optional palette;
there is no separate reduced-feature public viewer. Raw Morrowind assets first
go through the conversion tools; the inspector does not directly load an ESM
or BSA as a 3D scene.

- **World: Names on/off** sits beside **Grid on/off**. Names default to on;
  an explicit choice is remembered in this browser. Hiding names keeps the
  location markers. Other metric/ring numbers have their own layer controls.
- **Direct cell links** such as `index.html?served=1&cell=3,-3` open World,
  center the cell and select it after its data loads. **Layers > Highlight cell**
  defaults to on and pulses a yellow outline for both linked and clicked cells.
  Untick it to hide the outline without clearing the selection. Reduced-motion
  browser preferences use a steady outline. Without served mode, import your
  data first; the pending cell link is then applied.
- **3D Inspector: Copy JSON** appears on the terrain-preview, selected-object
  and scene-summary panels. Each copies evidence for that panel, including
  source identity, camera and display settings. The selection export includes
  object/reference identity, bounds and original/current counts when available.
  Successful copying shows a green **Copied** confirmation for four seconds;
  clipboard denial offers selectable JSON instead. Preview-only counts do not
  imply the compiled map changed.
- **Inspector layout and face budget:** the sidebar can be hidden while
  From above, Fly view and Orbit stay in the toolbar. The budget display counts
  loaded placed polygon faces, including hidden objects, rather than native
  memory. Yellow starts at 80%, orange at 90%, red above the chosen budget.
- **Textures and heatmap** can be shown together. Load an owned palette for
  original indexed colors; the built-in grayscale preview is labelled. These
  are unlit base textures, not a native lighting comparison.
- **Direct scene links** open the Inspector tab and forward `map`, `maps`,
  `world`, `worldzip` and `frame`. For example, with a CHIM archive served
  locally at the same origin:
  `index.html?worldzip=world.zip&frame=frames%2Fx%2B10%2Fy%2B01`.
  `worldzip` accepts HTTP(S) URLs without credentials and rejects archives over
  128 MiB. Another local origin must permit browser access (CORS). File-picker
  loading remains available without a server.

Inspection JSON references source files; it does not embed mesh, texture or
palette pixels. Keep generated game data, exports and captures with your owned
installation. This update adds viewer code and documentation, not game assets.

## Start it

From the repository root, with your data preloaded (recommended; Python standard library only, bound to this
machine):

```bash
python3 tools/toolkit_serve.py --data DIR --maps MAPS_DIR --open
```

- `DIR`: the folder with `world-progress.json` (every image build writes it) and the optional local layers.
- `MAPS_DIR`: a build's `id1/maps` folder, so the Local view and the 3D Inspector open maps directly.
- Optional: `--metrics FILE` (map metrics layer), `--progress DIR` (CHIM progress tracker).
- Without `--open`, browse to the address it prints (default `http://127.0.0.1:8031/`).

Or open `index.html` straight from disk in a desktop browser and pick your files with the buttons on the page
(a page opened from disk cannot read other files by itself, so each one has to be chosen).

## The pages

The screenshots below show the historical v0.0.36 interface and its data.
Current controls are described above; screenshot totals are not current
conversion, native or packaged coverage.

![World: the whole island with the CHIM progress tracker, each cell coloured by its conversion status](../docs/images/amiwind-v0.0.36-toolkit-world-chim-tracker.png)

| Page | What it shows |
| --- | --- |
| `index.html` | The start page: the World, Local, 3D Inspector and Monitor tabs |
| **World** (`world-map.html`) | The whole island: conversion status per cell, the CHIM progress tracker, the map metrics heatmap |
| **Local** | One area's maps around a cell, ready to open in 3D |
| **3D Inspector** (`map-inspector.html`) | Fly through a map's real polygons: Quake `.bsp` maps, CHIM maps (`.chim`) and whole CHIM worlds, with polygon counts, textures and the CHIM memory overlay |
| **Monitor** (`monitor.html`) | A build as it runs, read-only: its live log, stage progress, ETA, cores in use, a live stage timeline and recent builds and gates |

![3D Inspector on a CHIM map (.chim): its entities as markers and the CHIM frame that holds its geometry](../docs/images/amiwind-v0.0.36-toolkit-inspector-chim-map.png)

![3D Inspector on a CHIM world: a frame of Balmora from above with the memory overlay (the active ring's bytes at every player position against the CHIM zone) and the worst position's ring](../docs/images/amiwind-v0.0.36-toolkit-inspector-chim-world-memory.png)

**Open CHIM world** (in the 3D Inspector) takes a build's `chim-world` folder, or a zip of it: a frame's ground and
objects, the bytes of each chunk and model, and the memory overlay from the build's `chim-heap.json`
([details](../docs/POLYCOUNT_INSPECTOR.md#chim-maps-and-chim-worlds)).

## Monitor

![Monitor: a running build's progress, its stages, the live log of the running stage and the live stage timeline under it](../docs/images/amiwind-v0.0.36-toolkit-monitor.png)

The Monitor follows a build of your own while it runs: start the server with your builds folder, then open the
**Monitor** tab (or `monitor.html`). It is read-only: the page and the server only read the run's files.

```bash
python3 tools/toolkit_serve.py --builds BUILDS_DIR --open
```

`BUILDS_DIR` is the folder holding your build runs (`tools/build.py` run folders). For a Docker build
(`tools/run_docker.py`), read its volume instead:

```bash
python3 tools/toolkit_serve.py --monitor-docker amiwind-docker-builds --open
```

The Monitor listens on this machine only; `--bind ADDRESS` opens it to a phone on your network (only on a network
you trust). Walkthrough: [Watch a build in the Monitor](../docs/DOCKER_BUILD.md#watch-a-build-in-the-monitor);
details and the read-only rules: [Monitor](../docs/AMIWIND_TOOLKIT.md#monitor).

`.bsp` is a regular Quake map; `.chim` is a CHIM map, AmiWind's own map format, which is no longer directly
compatible with Quake's `.bsp` ([CHIM file format](../docs/CHIM_FILE_FORMAT.md)).

## Your data

The island picture and the layers are made from your own `Morrowind.esm` with the tools in `tools/`
(for example `tools/world_progress_background.py`); the guide lists every one. Keep what they make with your own
files: it is derived from the game and is not for sharing.

### Included in build

The World map has an **Included in build** selector, independent of release plans and conversion colours. Green means a region frame and its chunks were verified against final HDF readback; amber means selected for an unfinished build; grey means coverage is not established by this dataset. Select Conversion / plan view to return to the normal layers. Cell details identify verified versions; they do not invent a first version when earlier history has not been reconciled.

`chim-inclusion.json` contains only version labels, cell coordinates, frame identifiers, scope and receipt digests. The initial v0.0.36 record covers 325 region cells. Town-frame cell boundaries and earlier versions still need reconciliation. Package inclusion does not certify actors, lighting or traversal.
