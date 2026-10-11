# AmiWind Toolkit

The AmiWind Toolkit is a set of web pages for looking at AmiWind's world: where the conversion stands on the
island map, any converted map in 3D, and its polygon and memory figures. Everything runs in your own browser.
The views are made from your own Morrowind files and your own build output; nothing is uploaded, and no game data
ships with the Toolkit.

Full guide: [docs/AMIWIND_TOOLKIT.md](../docs/AMIWIND_TOOLKIT.md).

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
