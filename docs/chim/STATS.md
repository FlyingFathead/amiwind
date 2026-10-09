# CHIM build statistics (`chim-stats.json`)

Every CHIM build writes `chim-stats.json` next to `chim/`. It holds the polycounts,
disk, memory, streaming and build figures of the world that is actually on disk: the
numbers come from the world files as the validator reads them
(`tools/chim/validate.py`), the validator's measurements and the builder receipt. Counts
are the main currency. Times are either the builder's own seconds or estimates from the
read cost model (`tools/chim/readcost.py`); none of them is a hardware measurement.

To write the file for an existing world:

```
python3 tools/chim/stats.py OUT [--legacy-maps DIR --legacy-regions FILE] [--camera NAME X Y]... [--json FILE]
```

`OUT` is the builder output folder. With no `--camera`, the area's benchmark cameras
are used: the `dbg tp` positions in
[HARDWARE-BENCHMARK.md](../HARDWARE-BENCHMARK.md#frame-time-in-the-game). The tool
refuses a world that fails validation.

## Schema `chim-stats 1`

The schema is stable. Fields may be added. A field is never renamed, never removed and
never changes meaning without a new schema name. A test (`tests/test_chim_stats.py`)
fixes the field set. A field that does not apply is `null` and is never left out:
the legacy fields without `--legacy-maps`, and `camera_faces` without cameras.

"Distribution" below means `{count, total, min, p50, p95, max, mean}`. The percentiles
are nearest-rank, the same rule the validator uses. Faces are BSP faces (`dface_t`
records); bytes are file bytes.

| Field | Content |
| --- | --- |
| `schema`, `builder`, `chim_version`, `world_format`, `areas` | `"chim-stats 1"`, `"chim"`, versions from the receipt, the areas (town ids) this world holds |
| `counts` | models, textures, chunks, placements, reach copies, frames, PAKs (sector files) |
| `faces` | `models_stored` (each model once), `terrain`, `stored`, `placed` (every placement's model faces plus terrain), `placed_over_stored`; with legacy maps also `legacy_stored` (all faces of today's region maps of the area) and `legacy_over_chim_placed` |
| `models` | `faces` distribution per model; `top_by_faces` and `top_by_placed_faces` (top 20: id, name, faces, placements, placed faces, render bytes); `per_model` (every model: id, name, faces, render and collision bytes, placements, placed faces, file) |
| `placements` | `faces` and `leaves` distributions per placement, `over_16_leaves` (placements the engine sends with every view of their chunks); `rows` with `columns` `pid, model, faces, leaves, chunk_x, chunk_y` |
| `chunks` | distributions of `faces` (terrain plus the placements the chunk owns), `faces_with_reach` (plus reach copies) and `terrain_faces`; `top_by_faces` (top 20) and `per_chunk` (frame, cell, terrain faces, owned, reach, placed faces, faces, faces with reach, bytes) |
| `views` | `cameras`: per camera its frame (null, and no counts, when no frame of the world holds it), the chunk, potentially visible chunks, ring, chunk-row and placement-list placements and faces, terrain faces of the visible chunks, and `faces` (terrain plus placement list); `camera_faces` (p50, max); `all_chunks` (the validator's visibility report over every chunk) |
| `disk` | files, bytes, bytes by kind, `index_bytes` (`world.cwi`, shared by every area), PAKs, `pak_bytes` distribution, `largest_paks` (top 20: path, bytes, records, models, textures), `stored_once` (model bytes stored, model bytes if every placement stored its own copy, `model_sharing_factor`), `areas` (per area: CHIM bytes and files, every file for a one-area world and the area's frame and sector files for several areas; for one area with legacy maps also legacy bytes and files and `duplication_factor` = legacy bytes / CHIM bytes) |
| `memory` | `ring_chunks`; `resident_ring_bytes` distribution over every chunk as the player's chunk (the ring's chunk records plus its distinct models and textures); `resident_ring_peak` (that chunk and its parts); `model_zone_bytes` distribution and `model_zone_peak_bytes`; `walk_resident_max` (the walk with no extra cache); `basis` |
| `streaming` | route stops, chunks visited, `cache` (per extra cache size in bytes: crossings, bytes read, bytes and runs per crossing, estimated ms, resident bytes), `legacy` (today's region reads on the same walk), `cost_model` |
| `build` | wall and CPU seconds, jobs, `sections` (seconds and CPU seconds per builder section), `units` (built and reused per unit kind) |
| `legacy` | with legacy maps: regions, files, bytes, faces stored, `faces_per_region` and `bytes_per_region` distributions |
| `pain_points` | models whose placed faces are in the top 5 %, chunks whose faces are in the top 5 %, and placements over 16 leaves. Each list holds at most 20 entries; each entry has `kind`, an identity, `value` and the `rule` that put it there |

## Reading the numbers

- View faces are the faces of everything a view sends to the renderer. They are counted
  before the distance, frustum and backface tests. The engine's `dbg rcount` counts
  what is left after those tests
  ([RENDERER-COUNTERS.md](../performance/RENDERER-COUNTERS.md)). Compare entities
  sent with the engine's brush model passes. Compare faces only with faces.
- Memory figures are file bytes. The engine expands BSP lumps into its own structures
  and reports its zone use itself.
- Legacy face counts include the faces that the map compiler split across BSP nodes.
  The duplication factor compares bytes on disk for the same area.
