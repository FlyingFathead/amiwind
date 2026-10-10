# Lava

How AmiWind finds Morrowind's lava in your own game data and turns it into Quake liquid: the census, the map layer,
the converter, and the engine side (damage, view tint, glow, embers). Tracked as
[LAVA-NOT-IMPLEMENTED-33](bugs/LAVA-NOT-IMPLEMENTED-33.md).

<!-- contents start -->
## Contents

- [What Morrowind calls lava](#what-morrowind-calls-lava)
- [What existed before](#what-existed-before)
- [The census](#the-census)
- [The map layer and the tracker audit](#the-map-layer-and-the-tracker-audit)
- [Conversion: one implementation for every builder](#conversion-one-implementation-for-every-builder)
- [Engine settings](#engine-settings)
- [Visibility and memory](#visibility-and-memory)

<!-- contents end -->

## What Morrowind calls lava

Morrowind has no lava "water type". Its molten lava is ordinary art plus a script:

- **Lava pools** are six activator meshes (`in_lava_1024`, `in_lava_1024_01`, `in_lava_512`, `in_lava_256`,
  `in_lava_256a`, `in_lava_oval`). Each is a flat stack of two or three planes: a self-lit molten layer
  (`tx_lava_molten`, emissive), a second molten layer with alpha, and a crust layer on top (`tx_lava_crust`, with
  holes), all scrolling slowly. Each carries an `AvoidNode`, so actors path around it.
- **The lava contract** is the activator's script: while the player is in the cell it loops the "lava layer"
  sound at the pool and hurts any actor standing on the pool by 20 health points a second. Nothing else makes lava
  hurt. Tribunal's hot oil uses the same contract (20 a second, its own sound) on other meshes.
- **Lava-named rock is not lava.** Molag Amur's rocks and ground (`tx_ma_lava*` textures on `terrain_rock_ma_*`
  meshes and in the land texture table) and the lava caverns' walls (`tx_cavern_lavawall00`) are grey or brown
  basalt, not self-lit and without a script. They stay ordinary rock.

The census therefore decides "molten" from the game's own records (an object whose script hurts a standing actor),
never from texture colour or names alone.

## What existed before

- **The engine kept Quake's lava all along.** A texture whose name starts with `*` is a liquid: the BSP loader marks
  its faces turbulent (`SURF_DRAWTURB`, `model.c`), they are drawn by the warp span drawer (`Turbulent8`,
  `d_scan.c`) straight from the texture, without the surface cache and without lightmaps, so they are fully bright.
  The BSP compiler gives a brush whose texture starts with `*lava` the contents `CONTENTS_LAVA` (`bspfile.h`), and
  the view takes the lava colour shift when the eye is inside it (`cshift_lava` in `view.c`, `V_SetContentsColor`).
  This is the "existing preset": id's own convention of a `*lava1` texture on a liquid brush gives the warp, full
  brightness, lava contents and the lava colour shift with no new code.
- **What the fork did not keep:** the lava damage of id's game code (`WaterMove` in `client.qc`) is not in
  AmiWind's game code, and the C version (`PF_WaterMove`) is compiled only under `QUAKE2`. The lava splash effect
  (`R_LavaSplash`, `r_part.c`) exists but is too heavy to run continuously (it spawns over a thousand particles).
- **Plans that never became work:** the v0.0.29 plan's "weather, storms and lava study"
  ([PLAN-v0.0.29.md](PLAN-v0.0.29.md#weather-storms-and-lava-study)), the lighting source study
  ([LANTERNS_AND_TORCH_LIGHTING.md](LANTERNS_AND_TORCH_LIGHTING.md#source-study-light-attachments-and-lava-are-separate-contracts)),
  the world map study ([WORLD_MAP_AND_JOURNAL.md](WORLD_MAP_AND_JOURNAL.md#v0029-lava-and-weather-map-study)) and
  the roadmap's "fires and lava" entry ([ROADMAP.md](ROADMAP.md#near-future-fires-and-lava-across-the-world)).
  Self-lit materials (v0.0.30, `dbg emissive`) made lava textures glow but left them solid models. No bug or tracker
  row recorded the gap.

## The census

`tools/lava_census.py` reads your own masters and archives (nothing derived from them is part of this repository):

```sh
python3 tools/lava_census.py --data-files "<Morrowind>/Data Files" --out lava-census.json \
    --cells-out lava-cells.json [--jobs N]
```

It scans every placed mesh whose file mentions lava with the converter's own NIF reader, measures the lava faces
(area, the upward-facing part, the plan footprint), reads the script of every placement and the land texture
grid of every exterior cell. Output `aw-lava-census-1`: per mesh, per texture and per cell (exterior `x,y` or the
interior's name) every placement with object, mesh, position, rotation, scale, kind (`molten` or `rock`), damage
per second, sound and footprint, plus the land squares painted with a lava-rock ground texture. `--cells-out`
writes the small per-cell stat (`aw-lava-cells-1`) the trackers read.

Measured on the GOG Game of the Year masters (9 October 2026):

| What | Count |
| --- | --- |
| Molten lava pools (placements of the six pool activators) | 687 |
| outdoors | 349 in 27 cells: Molag Amur (310 in 24 cells), Sheogorad (38 in 2 cells), Red Mountain (1) |
| indoors | 338 in 59 cells, e.g. Akulakhan's Chamber 23, the Dagoth Ur facility 14, Ularradallaku 23, Rissun 14 |
| Molten surface (plan footprint) | about 515 million square Morrowind units, half outdoors (259 million) and half indoors (256 million) |
| Lava-named rock, cave and vent placements (not molten) | 9,979 on 101 meshes |
| Exterior cells with lava-rock ground textures (not molten) | 207 |

Red Mountain's lava is almost all indoors (the Dagoth Ur facility, Akulakhan's Chamber); the open lava fields are
in Molag Amur.

## The map layer and the tracker audit

The CHIM Progress Tracker counts the molten pools of every cell in its census of your files (`lava` per exterior
and interior cell) and audits each cell with `tools/cell_lava.py`: converted, partial, mapped but not converted,
static (built with `--lava static`) or not measured, from the build's lava record (the CHIM receipt's `lava`: mode
and pools by source cell). The Toolkit World Map shows it as the "Lava (mapped / converted)" colouring with a Lava
preset; details in [PROGRESS_TRACKER.md](chim/PROGRESS_TRACKER.md#the-lava-audit-and-the-lava-layer). The census
tool's `--cells-out` file carries the same counts with the footprint area for other tools.

## Conversion: one implementation for every builder

Each part reuses a Quake mechanism:

| Part | Quake mechanism | Morrowind source |
| --- | --- | --- |
| Liquid surface | a convex liquid brush with a `*lava` texture over the pool's footprint, compiled into the world (contents `CONTENTS_LAVA`, warp faces) | the pool's molten faces, placement position, rotation and scale |
| Warp texture | the `*` texture convention (64 x 64, drawn by `Turbulent8`, no surface cache) | made by the builder from your own `tx_lava_molten` with `tx_lava_crust` laid over it by its alpha; never committed |
| Full brightness | warp faces have no lightmap; the texture is drawn as is | the molten material's emissive colour |
| Standing in lava | a shallow liquid brush (8 Quake units) over a solid bed, so the player stands with the feet in lava (`waterlevel` 1) and cannot swim | Morrowind actors walk on the pool and burn |
| Damage | engine game logic on `watertype` / `waterlevel` (as id's `WaterMove`), the combat code's player damage | 20 health a second, the pool script's value |
| View tint | the contents colour shift (`cshift_lava`), blood red, rising with time in lava | the original's red damage flash |
| Glow on the walls around | rooms and region maps: baked light entities over the pool (light compiler, a lava colour); CHIM frames (no lightmaps): one row per 512-unit square of pools in the night lamp table (`lamps.awl` class 8), lit at night like the lamps, the nearest few at a time (285 rows for the 349 outdoor pools; at most 101 glow rows in any 3 x 3 cells, within the engine's 256-lamp cache together with the lamps) | the molten layer's emissive colour |
| Embers | the static-flame emitter's ember stream (`r_part.c` particles), a few per pool | none in the original (an AmiWind addition, labelled so) |
| Sound | `aw_loop` ambient loops (`ambientsound`, as the prison ship's hull), at most 4 per map spread over the pools (largest first, then farthest); the file converted once from the user's own sound to 11,025 Hz 8-bit mono (`env/lava_layer.wav`, 54 KB) | the "lava layer" loop of the pool script and its sound record's volume |
| Actors | an actor's step into lava fails (`AW_ActorStep`, the feet point `SV_CheckWater` tests), so the navigation ladder takes another way; an actor already in lava may step out | the `AvoidNode` on every pool |

The previous behaviour stays selectable: builder option `--lava static` (config key `lava`, exported to the
converters as `AMIWIND_LAVA`): interior rooms leave the pool activator out, as they always did ("unsupported
activator"), and exterior frames place the pool mesh as a solid model. The default is `--lava quake`.

Where it is implemented, once for every builder:

- `tools/lava.py`: the contract, the footprint, the brushes, the entity, the glow and the warp texture;
- interior rooms (`tools/prepare_area.py`, every room of the legacy and the CHIM builder): the liquid and bed
  brushes join the room's map before the BSP compiler, the glow lights join the room's light bake;
- exterior frames (`tools/import_town.py`): the pools leave the scenery (`lava-pools.json` in the source stage) and
  become brushes and `aw_lava` entities of the region map that holds their centre;
- CHIM chunks (`tools/chim/terrain.py`): the same prisms are carved into each chunk's world BSP (a `CONTENTS_LAVA`
  leaf with the two-sided warp face on its top plane), and the bed joins the chunk's standing hull; a chunk without
  lava is built byte for byte as before, so its cached unit is reused.

## Engine settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `aw_lava` | 1 | lava damage and the in-lava tint (0: off) |
| `aw_lava_dps` | 20 | health lost per second while standing in lava (Morrowind's pool script) |
| `aw_lava_tint` | `128 4 4` | colour of the in-lava view tint: a deep blood red |
| `aw_lava_tint_min` | 110 | tint strength (0-255) on stepping in |
| `aw_lava_tint_max` | 230 | tint strength after `aw_lava_tint_ramp` seconds in lava |
| `aw_lava_tint_ramp` | 3 | seconds from the first to the full tint ("red, then more red") |

The blood red is darker and more saturated than the damage flash (190, 20, 20) and far from the planned blight
weather tint (a dusty brown red at low strength, [ROADMAP.md](ROADMAP.md#weather-ash-storms-and-blight-winds)), so
the three read as different things.

## Visibility and memory

Measured offline (9 October 2026) on the real pools of four lava cells, carved into CHIM chunks of 256 Quake units
over flat ground (the census positions; `chim.terrain.chunk_terrain`, the builder's own code):

| Cell | Pools | Chunks with lava | Extra nodes | Extra warp faces | Extra chunk bytes |
| --- | --- | --- | --- | --- | --- |
| 9,-1 Molag Amur | 24 | 39 of 64 | 604 | 434 | 85,436 |
| 8,0 Molag Amur | 31 | 26 of 64 | 585 | 436 | 83,258 |
| 10,2 Molag Amur | 22 | 29 of 64 | 504 | 370 | 71,032 |
| 6,21 Sheogorad | 29 | 10 of 64 | 251 | 142 | 36,810 |

About 2 KB more per chunk that holds lava (the beds add about 14 standing-hull clipnodes a chunk). Pools that touch
or overlap are merged region by region on their side lines, as the BSP compiler merges brushes; a first version
that carved every pool inside the others' outside grew one cell by 17,820 nodes and overflowed the node format,
which a regression test now guards against.

Liquid brushes do not block visibility (the compiler's liquid rule), so a lava pool never hides what is behind it,
and its faces live in the world model like Quake's own water: they are drawn only when their leaf is visible. A
warp face costs no surface cache and no lightmap; its texture is one 64 x 64 miptex per map (5,440 bytes). The
per-pixel cost of the warp drawer on the 68040 is measured in the lava sandbox before the conversion becomes a
default.
