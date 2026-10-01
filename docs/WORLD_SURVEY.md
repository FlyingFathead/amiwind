# Vvardenfell terrain and cell-density survey

The first complete base-master survey places Seyda Neen and Balmora in a shared
world coordinate system. It is a conversion plan and inspection dataset. The
native **M** screen uses its island overview. The v0.0.25-dev1
[playable terrain pass](WORLD_TERRAIN.md) now consumes these subdivision candidates
while retaining both detailed towns and their interiors.

## Measured baseline, 1 October 2026

| Measurement | Result |
| --- | ---: |
| Exterior CELL records | 1,404 |
| LAND height grids | 1,292 |
| Unique scenery/item meshes measured | 1,405 |
| Placed scenery/item references measured | 134,865 |
| Placed source triangles | 34,924,945 |
| Unresolved scenery meshes/placements | 0 / 0 |
| Mismatched adjacent height edges | 0 |
| Existing regions mapped into world space | 64 Balmora + 25 Seyda Neen |

Actors and leveled lists are counted separately, not included in scenery polygon
cost. Deleted references and nonvisual markers are excluded. Source texture
records 68 and 86 cannot be resolved from the supplied files, but neither is
used by any surveyed LAND material assignment. They remain visible in the report.
The source master and archive hashes are recorded in the private receipts.

Original exterior cells are 8,192 source units square. Each LAND has 65 by 65
height samples at 128-unit spacing, including shared border samples. Negative
coordinates use mathematical floor: X = -1 is in cell -1, not cell 0. The
conversion preserves source axes; world Y increases northward. Images are
north-up and therefore reverse row order once when exported.

For the two current exterior areas, `world_xy = local_xy / scale + centre` and
`world_z = local_z / scale`. Both use scale 0.25. The transforms are read from
the actual area configurations, and their core/overlap rectangles are generated
by the same region planners used for conversion. Interior local coordinates do
not imply an exterior position.

## Sub-cells where measurements warrant them

The first screen uses a source-geometry ceiling of **140,801 triangles**, the
highest measured complete-object residency among the current 89 reference
regions (Seyda Neen `sn012`). Its existing BSP is 5,509,644 bytes, but that is
not a universal conversion ratio or a memory guarantee. Coverage adds 3,584
source units of overlap on each side, equivalent to 896 current runtime units.

| First passing candidate | Source cells |
| --- | ---: |
| Whole original cell | 1,078 |
| 2 by 2 regions | 314 |
| 4 by 4 regions | 12 |

These are **screening candidates**, not approved runtime splits. The 4 by 4
candidates include Gnaar Mok and its neighbours, Sadrith Mora, Zainab Camp and
parts of the Molag Mar/Bitter Coast regions. Large repeated natural meshes also
matter; town names alone are a poor proxy for loading cost. Vivec's bridges
remain useful logical-boundary candidates, subject to visibility and converted
cost. No existing town split is replaced by this survey.

The density layer assigns every placed source triangle once using its centroid.
The loading estimate instead includes each complete transformed object whose
bounds intersect a candidate's coverage. This distinction catches distant-origin
objects and measures overlap duplication. Failed source geometry marks the
screen incomplete; its unknown extent must not be treated as zero cost.

Before accepting a split, convert representative regions and measure BSP faces,
collision nodes, textures, actors, peak heap, renderer overflow, ordinary walking
and bidirectional transitions. Include the terrain cost. Reuse canonical actor
ownership and ground-contact auditing; never resolve a resident against an
incomplete distant overlap copy. Keep method 1 as the default until a measured
replacement earns that position.

## Reproducible private outputs

```bash
python3 tools/survey_vvardenfell.py --data-files "/path/to/Data Files" \
    --out /private/world-survey --cache /private/world-mesh-cache \
    --maps /private/converted/id1/maps
python3 tools/export_world_terrain.py --survey /private/world-survey \
    --out /private/world-terrain --stride 4
python3 tools/prepare_world_ui.py --data-files "/path/to/Data Files" \
    --survey /private/world-survey --scene /private/converted
```

The mesh workers use the bounded CPU/memory planner. A finished survey directory
is immutable; choose a new output directory for a rerun and reuse its validated
mesh cache. All extracted geometry, rasters, text catalogues and atlases stay
private. The public repository contains conversion tools and synthetic tests.

- `Vvardenfell-atlas.html`: self-contained browser atlas with terrain, density,
  subdivision candidates, source grid, current core/overlap regions, cell
  inspection and local-to-world coordinate lookup. No external service is used.
- `terrain-source.npz`: every original height/material sample, water values,
  cell identity and spacing; this is the baseline for later conversions.
- `terrain-samples.npz` and `terrain.png`: reduced preview, averaged original
  texture colours and relief. They are not full original UV terrain textures.
- `Vvardenfell-terrain.ply`: terrain-only mesh. At stride 4 it contains 373,388
  vertices and 661,504 triangles across all 1,292 LAND grids. It retains separate
  shared border samples and includes the seafloor. It has no water surface,
  scenery, actors, collision or playable BSPs.
- JSON receipts retain source hashes, geometry, counts, calibration and limits.

Ocean fills the atlas and map outside supplied terrain. This presentation does
not implement endless playable ocean or whole-island 3D traversal. Those require
bounded runtime coordinates, terrain conversion, water/collision behaviour,
scene ownership and measured transition budgets.
