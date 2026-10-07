# Polygon density, cells and town subcells

`tools/generate_polygon_heatmap.py` takes **user-provided converted BSP29 assets**
and creates a self-contained private HTML viewer plus optional numeric JSON.
Convert your own legally obtained game data with AmiWind first. This tool does
not directly read TES3/NIF, download assets, or package original game material.
The public source and tests work with synthetic data only. To compare a whole
set of sub-cell maps, see [sub-cell redundancy](SUBCELL_REDUNDANCY.md).

```sh
python tools/generate_polygon_heatmap.py --config /private/heatmap-input.json \
  --output /private/AmiWind-polygon-heatmap.html --stats /private/polygon-stats.json
```

Keep real configurations, BSPs and generated outputs outside the source checkout
and source handoffs. No original map artwork, pixels, textures, mesh vertices,
entity records or polygon coordinates are exported. Only aggregate counts in
equal-size world-coordinate bins, rectangular selector outlines, transform
metadata and a BSP SHA-256 are exported. The viewer works offline.

Input example (BSP paths resolve relative to the configuration):

```json
{
  "title": "AmiWind synthetic polygon survey",
  "scope": "Local converted assets; investigation only; target playtest pending",
  "bin_size": 512,
  "views": [{
    "name": "Town baseline",
    "bsp": "town.bsp",
    "centre": [-11264, -71680],
    "scale": 0.25,
    "note": "One complete town BSP; independent of subcell BSP views",
    "regions": [{
      "name": "sn012",
      "core": [[-768, -768], [1024, 474]],
      "coverage": [[-1664, -1664], [1920, 1370]],
      "peak_bytes": 8286944,
      "clearance_bytes": -1995488
    }]
  }]
}
```

`centre` is in original game units. BSP positions and input core/coverage bounds
are runtime-local units. The viewer applies `world = runtime / scale + centre`.
Original cells have side 8192 source-game units, including correct negative-cell
flooring. Supply authoritative current coverage bounds; the tool does not infer
coverage from a core or claim that a selector outline establishes content.

Density counts each referenced **placed compiled BSP polygon** by the arithmetic
mean of its vertices, after the inline entity's origin and Euler rotation. Model
zero contributes once. Each repeated inline placement contributes separately.
Disk face-record count is shown separately; aliased face ranges can make placed
counts differ. `edges - 2` is a fan triangle equivalent, **not original source
NIF triangles**, rendered triangles, physical collision complexity or memory.
Actors represented by external models are not included in brush-face density.

Use the view selector for independent BSPs, the metric selector for polygon or
triangle-equivalent density, and checkboxes for original cells, subcell cores and
loading coverage. Drag, zoom and click for world/bin/core bounds and counts.
Coverage counts use half-open **centroid inclusion**, not complete polygon/model
intersection. A face spanning a boundary still has one centroid bin. Overlapping
coverage counts and independent BSP views **must not be added**: these are neither
a deduplicated complete-town inventory nor proof of concurrent loading.
Use a complete full-town BSP for a baseline; clearly label partial fallback maps.

The optional heap overlay uses reported per-map `clearance_bytes` supplied by
the caller, independently of polygon density. Red exceeds the ceiling, amber is
near it, green has larger margin. Warning-margin and exploratory payload-growth
sliders help visualize sensitivity; they do not change the build policy:
11 MiB Hunk minus 3 MiB engine reserve minus 2 MiB safety leaves a 6 MiB map peak.
Static estimates, source geometry and prototype outlines do not certify installed
HDFs, seams, collision, gameplay, target RAM or target acceptance.

Optional `audit_scope` accepts `baseline_maps`, `baseline_failures`, `trial_maps`,
`trial_failures`, and `trial_values` to show separate audit cohorts without
conflating them. Supply numeric trial rows only; never place asset payloads there.

For a whole exterior, a view can use `sources` instead of `bsp`. Each source
provides `name`, `bsp`, `centre`, `scale`, runtime-local `core` and `coverage`, and
optional `peak_bytes`, `clearance_bytes` and `expected_sha256`. Sources must have
disjoint world-coordinate cores; overlapping owners cause an error. Only each
map's half-open **own-core centroid** contributes to the merged density bins,
discarding repeated apron geometry. This is an owner inventory of compiled
polygon pieces, not deduplication of original source meshes or whole-map loading
counts. Compiler splits can change face counts between maps. A source's disk
record total still includes its apron, so summed disk records are not a unique
world inventory. Missing BSPs are listed and highlighted magenta, never zero.
Town and world inventories should use separate views to avoid overlapping owners.
Interiors have local coordinates and must not be plotted in the exterior mosaic.

`read_world_directory(raw, scale=0.25)` decodes current AWR2 region metadata for
callers preparing a private configuration. Directory origins are global runtime
units: the source-world `centre` is `origin.xy / scale`, not the raw origin.
Use the directory accompanying the exact staged map set. `--jobs` controls
parallel mosaic reading and defaults to the host's logical CPU count. Every BSP
can be checked against a caller-supplied expected SHA-256 before aggregation.
