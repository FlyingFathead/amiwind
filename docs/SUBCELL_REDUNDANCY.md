# Sub-cell redundancy and cell map

`tools/analyze_subcell_redundancy.py` measures how much geometry a set of
sub-cell maps (for example the Seyda Neen `sn` or Balmora `bm` subdivisions)
duplicates between neighbours, and draws a density map of the whole area with
the configured ownership cores on top. It complements the
[polygon heatmap](POLYGON_HEATMAP.md) and the
[polycount inspector](POLYCOUNT_INSPECTOR.md): those show what one map
contains; this shows how the maps of one area relate.

It reads **user-provided converted BSP29 maps** only. Convert your own legally
obtained game data with AmiWind first. The public source and tests use
synthetic maps only. Keep real maps and generated outputs outside the source
checkout and source handoffs.

```sh
python tools/analyze_subcell_redundancy.py --maps /private/build/id1/maps \
  --prefix sn --regions config/seyda-bounded-regions.json \
  --json /private/seyda-redundancy.json --image /private/seyda-cells.png
```

## What it reports

Every placed face (world model and brush entities, moved by their origin and
yaw) gets a world-space key rounded to half a unit, so a face that several maps
carry is counted once.

- `distinct_faces_union`: faces in the whole area, each counted once.
- `faces_summed_over_maps`: faces as stored on disk, summed over all maps.
- `redundancy_factor`: the ratio of the two. 1.0 means no face is stored twice.
- `median_copies_per_face`: over all distinct faces, how many maps store each.
- Per map: bytes, faces, faces by entity class, the share of its faces that
  other maps also store, and the median copy count of its own faces.

The optional image bins face centroids into 32-unit cells (log scale; dark red
sparse, yellow and white dense) and outlines each region core from the region
JSON. Only aggregate counts and core rectangles are drawn; no vertices,
textures or entity records are exported.

## Why it matters

Each automatic region crossing loads the destination map in full. Earlier
measurements put a crossing at about 1.1 seconds, mostly file reading (see the
[cell-transition investigation](performance/CELL-TRANSITION-INVESTIGATION-v0.0.29-dev4.md)).
The bytes loaded per crossing and the number of crossings along a route
therefore set how often and how long movement pauses.

First measurement, v0.0.29 maps, 7 October 2026:

| Area | Maps | Median map | Distinct faces | Redundancy |
| --- | ---: | ---: | ---: | ---: |
| Seyda Neen (`sn`) | 64 | 4.74 MB | 74,556 | 24.1x |
| Balmora (`bm`) | 64 | 1.97 MB | 256,956 | 7.3x |

Seyda Neen's cores are about 448 by 310 units with an 896-unit overlap against
a 540-unit draw distance, so each sub-cell stores about 28,000 of the town's
~75,000 faces, and the dense town centre is cut into about thirty small cores.
This is a measured diagnosis, not an accepted fix. See
[cell changing](CELL_CHANGING.md) for the residency and overlap rules any new
layout must keep.
