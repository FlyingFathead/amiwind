# Asset census: what the world streamer has to store

The [world streamer](WORLD_STREAMER.md) stores every mesh, hull and texture
once and places it by reference. The asset census measures what that means
for the whole game from your own Morrowind files: how many unique meshes and
textures are placed, how large they are in AmiWind form, how many converter
variants scale and tilt create, how much a chunk ring holds, how much light
each placement carries, what the terrain costs, and whether the whole game
fits on one drive image.

<!-- contents start -->
## Contents

- [Running it](#running-it)
- [How Quake does it, and what is computed](#how-quake-does-it-and-what-is-computed)
- [Results on the owner's data](#results-on-the-owners-data)
- [Recommendations](#recommendations)

<!-- contents end -->

Status: measurement, 8 October 2026. No converter or engine change.

## Running it

```sh
python3 tools/build_aga.py census --data-files "/path/to/Morrowind" --out ~/amiwind-census \
    [--route-cell "Town Name" ...] [--grains 256 512 1024] [--jobs N]
python3 tools/asset_census.py bakes --data-files ... --maps DIR_OF_CONVERTED_MAPS \
    --census-meshes ~/amiwind-census/work/census-meshes.json --out bakes.json
python3 tools/asset_census.py terrain --maps DIR_OF_OPEN_WORLD_MAPS [--listing SIZES.txt] --out terrain.json
python3 tools/asset_census.py disk --census ~/amiwind-census/census.json --bakes bakes.json \
    [--extra payload.json] --out disk.json
```

`--jobs N` runs exactly N mesh readers (absent or 0: automatic, from the CPU
count and memory); see [Parallel host builds](PARALLEL_BUILD.md).

Everything runs on your machine and reads only your files; the output is
yours and stays private. `--route-cell` names an exterior cell; the walk goes
through every load door of the cells with that name (a nearest-neighbour
tour), which is a street route through the town.

## How Quake does it, and what is computed

The census reuses the world estimate's readers
([WORLD_ESTIMATE.md](WORLD_ESTIMATE.md)) and the converter's own functions:

- **Measured from your files:** every placed object with a mesh (the
  estimate's `evr` policy: actors and editor markers left out; development
  interiors excluded as in the estimate); per mesh, under the interior and the
  exterior converter profile: faces after `split_surface`, unique vertexes
  and edges, surfedges, texture mappings, planes, lightmap samples
  (`CalcSurfaceExtents` rule, 16 texels per sample), point-hull nodes,
  standing-box clipnodes and collision planes (`collision_parts` /
  `shell_collision_parts`, `standing_planes`), and the textures the emitted
  faces use (source, converter size, tint, glow: the converter's texture
  identity). Bytes are BSP29 lump bytes (`dface_t` 20, `dedge_t` 4, ...);
  textures are Quake miptex (8-bit, four mip levels) at the converter's size.
- **Measured from converted maps:** lightmap bytes per placement (`aw_ref` of
  each `func_wall`), before and after the lightmap sharing in the stored
  lump; terrain (world model) bytes of the open-world maps.
- **Estimated:** bytes of scaled variants (unit-scale counts reused),
  lightmaps of scaled placements (`luxels(s) = luxels(1) + a(s-1) + b(s^2-1)`
  with the per-face terms), the route walks, and every disk total.

Quake mechanisms behind the numbers: brush models (`Mod_LoadBrushModel`),
lightmaps per face (`R_BuildLightMap`), hulls pre-expanded by the player box
(`SV_HullForEntity`, which is why a hull cannot be scaled or tilted at run
time), `R_RotateBmodel` (drawing already applies all three angles to a brush
entity; scale is the missing part), miptex.

## Results on the owner's data

Morrowind, Tribunal and Bloodmoon, 8 October 2026. Expansions count only the
cells they add. Interiors: 1,127 + 92 + 93 cells.

### 1. Unique assets

| | Vvardenfell ext. | Vvardenfell int. | Tribunal int. | Solstheim ext. | Solstheim int. |
| --- | ---: | ---: | ---: | ---: | ---: |
| placements | 134,865 | 162,089 | 13,868 | 12,532 | 11,693 |
| unique meshes | 1,405 | 2,921 | 1,253 | 419 | 848 |
| geometry, once per mesh (MB) | 48.4 | 115.8 | 54.3 | 21.7 | 35.1 |
| hulls, once per mesh (MB) | 15.5 | 143.1 | 43.0 | 3.5 | 44.2 |
| textures (converter identity) | 945 | 1,833 | 1,131 | 324 | 701 |
| texture bytes (MB) | 1.44 | 8.77 | 5.25 | 0.47 | 3.34 |

All textures of the game, each stored once: 18.9 MB (Vvardenfell 9.9 MB
both spaces). Exterior textures are mostly 32 x 32, interior ones 64 x 64.
The original BSAs hold 494 MB, the masters 94 MB.

Interior hulls are larger than interior render geometry: hollow kit pieces
use exact standing-box bevels, and architecture pieces carry 1.6 times their
render bytes in collision.

### 2. Scale and tilt

- Scale is already quantized by the data: 151 distinct values (0.50 to 2.00
  in steps of 0.01). Exterior: 43 % of placements at exactly 1.0, 30 % at
  2.0 (rocks 49 % at 2.0). Interior: 88 % at 1.0.
- Tilt: 22 % of exterior placements are tilted (most between 5 and 45
  degrees: rocks, flora, buildings on slopes); 12 % of interior placements
  (most at 45 degrees or more: props on their side).
- A tilted placement keeps its yaw in the variant key (tilt and yaw do not
  commute), so **tilt, not scale, multiplies the variants**:

Vvardenfell exteriors, variants (dedup factor against today's 33,076):

| scale policy | tilt exact | tilt 5/15 degree steps | tilt at run time |
| --- | ---: | ---: | ---: |
| exact (0.01 steps) | 33,076 (1.0) | 27,982 (1.2) | 8,426 (3.9) |
| 16 steps per octave (max error 2.1 %) | 30,703 (1.08) | 25,493 | 5,109 (6.5) |
| 8 steps per octave (max error 4.3 %) | 29,814 (1.11) | 24,542 | 3,954 (8.4) |
| 4 steps per octave (max error 8.8 %) | 29,085 (1.14) | 23,653 | 3,065 (10.8) |
| per mesh, 8 levels over its own range | 29,306 (1.13) | 23,873 | 3,347 (9.9) |
| run time | 27,424 (1.21) | 20,920 | 1,405 (23.5) |

Vvardenfell interiors: 19,872 today; tilt at run time 8,168 (2.4); both at
run time 2,921 (6.8). Solstheim exteriors 3,348 to 419 (8.0); Tribunal
interiors 3,963 to 1,253 (3.2).

Geometry stored once per variant (today's rule) would be 1.41 GB for the
game; once per mesh 0.28 GB.

### 3. Chunk rings

Per chunk: everything within draw distance + hysteresis (540 + 96 units) of
any point of the chunk (bounds rule: a placement marks every chunk its bounds
touch). Resident = render geometry of the ring plus hulls of the chunks within
the 224-unit collision margin, one model per mesh. Vvardenfell, chunks with
land or placements; MB p50 / p95 / max:

| grain | chunks | resident | geometry | hulls (margin) | one model per variant (geometry + hull) | textures | models in ring |
| ---: | ---: | --- | --- | --- | --- | --- | --- |
| 256 | 82,688 | 0.45 / 1.62 / 4.87 | 0.39 / 1.43 / 4.56 | 0.05 / 0.21 / 2.00 | 1.08 / 2.76 / 7.17 | 0.03 / 0.08 / 0.33 | 23 / 55 / 135 |
| 512 | 20,672 | 0.72 / 2.46 / 6.54 | 0.59 / 1.98 / 4.87 | 0.11 / 0.42 / 3.52 | 1.83 / 4.23 / 8.78 | 0.04 / 0.11 / 0.36 | 33 / 76 / 156 |
| 1024 | 5,168 | 1.11 / 3.49 / 8.33 | 0.83 / 2.67 / 5.52 | 0.27 / 0.92 / 4.77 | 2.85 / 6.05 / 10.39 | 0.06 / 0.14 / 0.37 | 44 / 98 / 194 |

Solstheim at 256: 0.85 / 2.73 / 5.87 MB. The hottest rings are in the
largest towns and cantons. Placement records (24 bytes) are at most 10-25 KB
per ring.

Street walks (one model per mesh; read = bytes loaded after the first ring;
extra = cache kept beyond the ring):

| grain | town A: crossings, hit rate (extra 0 / 1 MB / 2 MB) | read MB (0 / 2 MB) | largest crossing MB (0 / 2 MB) | town B: hit rate (0 / 1 MB) | largest crossing MB |
| ---: | --- | --- | --- | --- | --- |
| 256 | 73, 0.919 / 0.948 / 0.963 | 25.0 / 11.5 | 1.36 / 0.84 | 0.921 / 0.956 | 1.55 |
| 512 | 36, 0.877 / 0.924 / 0.953 | 23.5 / 9.0 | 2.39 / 1.76 | 0.929 / 0.985 | 0.54 |
| 1024 | 19, 0.846 / 0.896 / 0.908 | 19.9 / 10.1 | 3.96 / 2.06 | 0.913 / 0.968 | 0.61 |

Town A is a large town (69 doors, 14,500 units walked), town B a village (20
doors). With one model per variant the hit rate drops by 1-13 points and up
to 3.6 times as many bytes are read.

### 4. Light per placement

Measured in 58 converted interiors (4,345 placements) and 64 exterior region
maps:

- The census predicts the baked samples of a placement to within 4 % for
  architecture, furniture, rocks and clutter (flora 19 %): the per-placement
  light budget can be set from the census alone.
- Lightmap sharing in the stored lump keeps 31-36 % of the samples
  (identical blocks share bytes; interior rocks keep almost nothing).
- Stored bytes per placement, p50 / p95: architecture 436 / 2,862,
  furniture 222 / 3,207, clutter 621 / 3,015, flora 287 / 2,896.
- Exteriors: none of 15,371 placements in the region maps has a lightmap;
  only terrain is lit.
- Today's interiors store a full copy of every placement: 20.9 KB per
  placement measured, about 3.9 GB for every interior of the game.

Tier 2 (per-placement lightmaps for architecture, furniture, rocks) for the
whole game: 99 MB at 16-unit samples, 25 MB at 32-unit samples. Tier 3
(flora and clutter: one light level per placement): under 0.1 MB.

### 5. Terrain

| | per cell | Vvardenfell (1,292 LAND cells) | Solstheim (144) |
| --- | ---: | ---: | ---: |
| compiled today (open-world maps, world model incl. visibility, overlaps) | 1.42 MB per LAND cell | about 1.84 GB | no open-world maps |
| heightfield 65 x 65 shorts + 16 x 16 materials | 8.7 KB | 11.3 MB | 1.3 MB |
| + 8-bit lightmap, 32-unit samples | 12.9 KB | 16.7 MB | 1.9 MB |
| + 8-bit lightmap, 16-unit samples | 25.3 KB | 32.7 MB | 3.6 MB |

Compiled terrain: a 1-in-10 sample of the open-world maps (207 maps, 300 MB);
the world model is 51 % of those files, and its visibility lump is 42 % of
that. The compiled terrain lightmaps are almost all shared (about 5 KB stored
per map against 130,000 samples).

### 6. Disk

Whole game, estimated from the numbers above, with today's non-world payload
(sound, music, intro video, gallery, alias models, executables, tables) as
shipped in v0.0.31 (694 MB). One drive image holds two partitions of about
1.66 GB of game files each (3.32 GB).

| scenario | geometry | hulls | interior light | terrain | world data | total | fits |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| today's rules | per variant | per variant | 16-unit | 16-unit | 2.30 GB | 3.00 GB | one image, 90 % full |
| recommended | per mesh (run-time scale and tilt) | 8 steps per octave, tilt 5/15 degrees | 16-unit | 32-unit | 1.06 GB | 1.75 GB | one image, 53 % |
| lean | per mesh | unexpanded per scale, tilt 5/15 degrees | 32-unit | 32-unit | 0.91 GB | 1.61 GB | one partition |
| interior architecture compiled into each map | per placement | as recommended | 16-unit | 32-unit | 2.50 GB | 3.20 GB | one image, 96 % full |

Recommended, by kind: interior hulls 479 MB, interior geometry 205 MB,
exterior hulls 161 MB, interior lightmaps 99 MB, exterior geometry 70 MB,
textures 19 MB, terrain 19 MB, placement records 8 MB.

The original game: Morrowind.bsa 310 MB + Morrowind.esm 80 MB; with both
expansions 588 MB. The recommended world data is 1.8 times that.

Classic FFS rules for the layout: no pack above about 1 GiB (the largest kind
is 0.48 GB; packs sharded by area), file names of at most 30 characters, and
few files per directory (72 hash chains): chunk packs one per 3 x 3 cell
frame, spread over subdirectories.

## Recommendations

- **Chunk size: 256 units** for residency (worst resident ring 4.9 MB against
  8.3 MB at 1024; largest crossing on the town walk 0.84-1.36 MB against
  2.1-4.0 MB), with reads grouped by frame on disk. 1024-unit chunks read
  slightly fewer bytes in total but in larger steps.
- **Scale and tilt:** draw with run-time scale and tilt (one geometry per
  mesh: 1.41 GB to 0.28 GB, 23.5 times fewer exterior models); quantizing
  scale alone is not worth it (at most 1.17 times). Hulls: store them
  unexpanded per mesh and expand per placement at load for the collision
  margin (hulls 0.25 GB), or keep baked hulls with scale in 8 steps per
  octave and tilt in 5/15-degree steps (0.64 GB).
- **Lighting tiers:** tier 1 terrain lightmaps; tier 2 per-placement
  lightmaps for architecture, furniture and rocks (99 MB at 16-unit, 25 MB at
  32-unit samples; keep the lightmap sharing); tier 3 one light level for
  flora and clutter. Exteriors keep no per-placement lightmaps.
- **Terrain:** a quantized heightfield (12.9 KB per cell with a 32-unit
  lightmap) instead of compiled terrain, about 110 times smaller; generation
  time per chunk on the 68040 is not measured yet.
- **Interiors:** shared kit pieces (catalogue placements with per-placement
  lightmaps), not one copy per placement: compiling architecture into each
  interior map costs 1.4 GB more geometry, before its collision.
