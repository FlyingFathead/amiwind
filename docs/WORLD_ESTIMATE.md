# World estimate

How big would every map of a whole-world import be, and which engine limits
would each one hit? The world estimate answers that from your own Morrowind
files in about ten minutes (seconds on a rerun), without converting the world: one row per
interior cell and per exterior town-converter region, with BSP sizes, the
target heap, entity counts and every limit ratio, plus charts.

<!-- contents start -->
## Contents

- [How Quake does it, and what is computed](#how-quake-does-it-and-what-is-computed)
- [Limits](#limits)
- [Accuracy and bias](#accuracy-and-bias)
- [Development cells (IMPORT-TEST-CELLS-31)](#development-cells-import-test-cells-31)
- [Check it on your machine: --sample-convert](#check-it-on-your-machine---sample-convert)
- [Recalibrate from your own conversions](#recalibrate-from-your-own-conversions)
- [Output](#output)
- [Loading the results into the Toolkit](#loading-the-results-into-the-toolkit)

<!-- contents end -->

It is a builder command:

```sh
python3 tools/build_aga.py estimate --data-files "/path/to/Morrowind" --out ~/amiwind-estimate
# or, through the guided builder:
./build.sh --data-files "/path/to/Morrowind" --estimate-world ~/amiwind-estimate
```

Options (`build_aga.py estimate --help`):

| Option | Meaning |
| --- | --- |
| `--scenario cur\|evr\|both` | `cur`: what the converters take today. `evr`: every placed object with a mesh as geometry, NPCs and creatures as edicts. Default `both`. |
| `--texinfo-limit 32767\|65535` | Texinfo gate: 32,767 (the loader's signed index today) or 65,535 (planned unsigned index). |
| `--jobs N` | Worker processes (default: all CPUs). |
| `--work DIR` | Mesh-scan cache (default `OUT/work`); a rerun only rescans changed meshes. |
| `--exclude default\|listed\|none` | Development cell exclusion, below. |
| `--frame-anchor CX CY` | Centre cell of one exterior frame; frames are every third cell from it (default: the Balmora source cell). |
| `--model FILE` | Coefficient file (default `config/world-estimate-model.json`). |
| `--sample-convert N` | Also convert N maps and report the estimator's error, below. |
| `--sdk`, `--quake-tools`, `--palette` | Tools for `--sample-convert`. |

Everything runs on your machine and reads only your files. Nothing derived
from them is part of this repository: the code is generic and the shipped
coefficients are plain numbers.

## How Quake does it, and what is computed

A map's cost is Quake's own lump sizes: faces, texinfo, nodes, clipnodes,
vertexes, lightmap bytes, and the hunk that `Mod_LoadBrushModel` allocates for
them, which `tools/check_world_map_heap.py` models from the target ABI. The
converter turns each placed mesh into a brush submodel of the map
(`tools/prepare_mesh_bsp.py`); its counts follow from the mesh, so the
estimate runs the converter's own functions on every mesh instead of
converting maps:

- **Computed from your data** (exact or nearly so): the census of cells,
  references, NPCs, creatures, lights, light styles, night lamps per 3x3
  cells, static flames, edicts, inline models and room coordinates; and per
  mesh, with the converter's NIF reader and its `surface_polygons`,
  `split_surface`, `collision_parts`/`shell_collision_parts` and
  `standing_planes`, under the interior and the exterior profile: faces,
  texture mappings, lightmap samples, point-hull nodes, standing-box
  clipnodes, the largest surface extent (with the 68040's outward rounding of
  grid-exact ends, MESH-EXTENT-GRID-31) and the ground height of every region
  core.
- **Estimated**: map lumps, as non-negative linear fits of those per-mesh
  counts summed over the map's converter variants (once per variant; once per
  instance in interiors, where light is baked per instance) plus terrain terms;
  the heap, as a linear fit of the lumps to `check_world_map_heap` (it
  reproduces that model to 0.02 % for interiors and 0.19 % for exteriors on
  measured lumps); final (optimized) BSP bytes and compile seconds.

`metrics.json` lists the estimated columns under `estimated_columns`.

Maps: one per interior cell; exteriors are the town converter's regions
(`tools/town_regions.py` with the Balmora sub-cell settings: 3x3-cell frames
of 6,144 units, 8x8 cores of 768, overlap 896) on a regular frame grid. Regions
with no references (sea) are listed with `buildable` = no and left out of the
counts. Tribunal and Bloodmoon are separate sets with only their new cells.

## Limits

Read from this repository at run time: `MAX_MAP_FACES`, `MAX_MAP_NODES`,
`MAX_MAP_VERTS`, `MAX_MAP_MARKSURFACES` (`bspfile.h`), `MAX_EDICTS`,
`MAX_LIGHTSTYLES` (`quakedef.h`), `MAX_DLIGHTS`, `MAX_STATIC_ENTITIES`
(`client.h`), `STATIC_FLAME_MAX` (`aw_guard_torch.c`), `LAMP_CACHE`
(`aw_lamps.c`), the inline-model budget (`model_budget` of the town config),
the heap (`AMIWIND_HEAP_MB` in `sys_amiga.c`, with the checker's baseline
reserve and safety headroom) and the town frame ceiling (`import_town.py`).
Fixed by the format: clipnodes 65,520 (`model.c` loader), surface extent 256
(`CalcSurfaceExtents`), coordinates +-4,096 (`MSG_WriteCoord` shorts).

Ratios are value / limit; `*_fails` lists the limits over 1.0, `*_pass` is
yes when there are none, `*_sections_est` is how many maps the binding size
limit would need.

## Accuracy and bias

Measured on one owner's data (Morrowind, Tribunal, Bloodmoon); your numbers
come from `--sample-convert` and `estimate-calibrate`.

Per mesh, against the submodels of 1,102 converted maps (interiors): faces
equal on 100 % of meshes, point nodes 99.6 %, clipnodes 94.8 %, texture
mappings 84 % (median error 0 %).

Per map, median / 90th-percentile absolute error:

| Metric | Interiors, CV | Exteriors, CV | Interiors, 13 new maps | Exteriors, 13 new maps |
| --- | ---: | ---: | ---: | ---: |
| Heap (gate value) | 0.3 / 1.3 % | 1.8 / 4.6 % | 0.7 / 2.2 % (max 4.1) | 0.8 / 3.9 % (max 5.4) |
| Faces | 0.1 / 0.2 % | 5.0 / 16.5 % | 0.1 / 0.2 % | 5.2 / 21 % |
| Texinfo | 3.0 / 4.7 % | 5.6 / 22 % | 3.5 / 3.8 % | 7.3 / 28 % |
| Clipnodes | 0.6 / 1.1 % | 15 / 42 % | 0.6 / 0.8 % | 19 / 34 % |
| Hull-0 nodes | 0.0 / 0.0 % | 21 / 57 % | 0.0 / 0.0 % | 10 / 35 % |

CV = grouped 5-fold cross-validation on the 1,102 calibration maps (256
interiors, 846 exterior regions). New maps = a 30-map `--sample-convert` with
the predictions frozen first: 26 converted, and pass/fail agreed on 155 of 156
measured gates (one interior at 98.7 % of the heap budget measured 1 % over).
The four that stopped were all flagged: two over 65,520 clipnodes (predicted
89,000 and 140,000), one region whose ground rises above the frame ceiling (the
map leaks), and one region predicted at 94 % of the texinfo limit that went
over it.

**Bias: maps near a limit are under-predicted. Treat 90 % of a limit as
failing.** `summary.json` counts maps `within_10pct_of_a_limit` separately for
this reason. Exterior node and clipnode estimates are loose: a region's
collision is not carried by its mesh submodels, so these two rest on the
region fit alone and their gates are indicative only.

## Development cells (IMPORT-TEST-CELLS-31)

The data contains developer test cells that are not part of the game world.
The default rule leaves out every interior cell a player cannot reach: no
chain of load doors leads to it from an exterior cell or from a cell that a
script or dialogue result names (scripts move the player with `PositionCell`).
Each one is listed with its reason under `excluded_interiors` in
`summary.json`. `config/world-estimate.json` is yours
to edit: `include_cells` keeps a cell the rule would drop, `exclude_cells`
drops any cell. On the owner's data the rule left out 15 interiors: every
known test cell and a few unused cells that nothing in the game leads to. `--exclude listed`
applies only `exclude_cells`; `--exclude none` keeps everything. The rule uses
no cell names, so the repository carries none.

## Check it on your machine: --sample-convert

```sh
python3 tools/build_aga.py estimate --data-files "/path/to/Morrowind" --out ~/amiwind-estimate \
    --sample-convert 30 --quake-tools /path/to/ericw-tools/bin --sdk /path/to/amiga-sdk
```

Picks N maps of Morrowind.esm (half interiors, half exterior regions, by
quantile bins of the predicted heap), freezes their predictions in
`validation/sample.json`, then converts them with this repository's
converters (`prepare_area.build_room`; the town converter steps of
`import_town.py` on the region's frame), measures the BSPs, runs
`check_world_map_heap` on the raw and the optimized map (needs the SDK) and
writes `validation/compare.json`/`.csv`: per-metric errors, pass/fail
agreement per gate, and `charts/estimator-accuracy.svg`. A map whose
conversion stops on a limit is reported with the converter's error.

## Recalibrate from your own conversions

```sh
python3 tools/build_aga.py estimate-calibrate --data-files "/path/to/Morrowind" \
    --from ~/amiwind-estimate [more estimate output dirs...] --model-out my-model.json
python3 tools/build_aga.py estimate --data-files ... --out ... --model my-model.json
```

Refits every coefficient from the maps that `--sample-convert` runs measured
(at least 3 interiors and 3 exterior regions; more maps, better fit), with a
grouped 5-fold cross-validation in the model's `calibration` block when there
are 15 or more. The shipped coefficients came from the same fit on 1,102
converted maps (256 interiors, 846 exterior regions).

## Output

| File | Content |
| --- | --- |
| `metrics.csv` | One row per map (format below). |
| `metrics.json` | `format` `aw-world-estimate-1`, `limits`, `gates`, `headline_gates`, `scenarios`, `estimated_columns`, `at_risk_ratio`, `model`, and the same `rows`. |
| `summary.json` | Limits used, excluded cells, census and mesh-scan summary, per set (vvardenfell, tribunal, bloodmoon) and scenario: failures per gate (interior/exterior), maps within 10 %, median heap, total size, time and disk projection; the 30 worst maps. |
| `charts/` | `heap-vs-budget.svg`, `faces-vs-limits.svg`, `entities-vs-max-edicts.svg`, `limits-failing.svg`, `world-heat-map.svg` (town labels from your data), `estimator-accuracy.svg` with `--sample-convert`. |
| `work/meshes.json` | Mesh-scan cache (your data; keep it private). |

### metrics.csv / metrics.json rows

Identity: `map` (`i0001`.. interiors; `w+CX+CY` frame plus region `000`..`063`
for exteriors; `ti`/`bi` and `b` for Tribunal/Bloodmoon), `set`, `space`,
`name` (cell name, or `exterior CX,CY rNN`), `mw_region`, `frame`,
`core_cells`, `cov_area_q2`, `land_frac_core`, `refs_total`, `buildable`.

Census: `refs_STAT` .. `refs_LEVI`, `refs_items`, `load_doors`, `npc`,
`creatures`, `lights`, `lights_animated`, `styles`, `lamps_3x3`, `coord_max`;
for exteriors also `core_refs_total`, `core_npc`, `core_creatures`,
`core_lights`, `core_items` (references whose origin is in the region core, so
sums over regions count each reference once) and `terrain_max_q`.

Per scenario (`cur_` and `evr_` prefixes): `refs_geometry`, `variants`,
`textures`, `faces`, `texinfo`, `nodes`, `clipnodes`, `marksurfaces`,
`vertexes`, `edges`, `planes`, `lighting_bytes`, `texture_bytes`,
`entity_bytes`, `bsp_bytes`, `final_bytes`, `seconds`, `inline_models`,
`heap_raw` (before the optimizer), `heap` (after; what the game loads),
`flames`, `edicts`, `known_extent`, `fallback_variants` (meshes whose cost
pass failed), then `ratio_<gate>` for every gate, `worst_ratio`, `fails`,
`pass`, `sections_est`. Gates: heap, faces, texinfo,
texinfo_planned_65535, nodes, clipnodes, marksurfaces, vertexes, edicts,
inline_models, static_flames, lightstyles, lights_if_dynamic_dlights,
night_lamp_cache_3x3, coord_4096, surface_extent_256, terrain_ceiling. All but
texinfo_planned_65535 and lights_if_dynamic_dlights count towards `fails`.
`evr` is never below `cur` in any column (a test enforces it).

## Loading the results into the Toolkit

The Toolkit's world map (`amiwind-toolkit/world-map.html`, see
[AMIWIND_TOOLKIT.md](AMIWIND_TOOLKIT.md)) shows per-map metrics as a layer.
Its converter reads `metrics.csv` or `metrics.json` from this command
unchanged; open the converted layer file in the world map's data panel.
