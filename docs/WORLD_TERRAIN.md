# Playable Vvardenfell terrain

## Current scope — published v0.0.27

The 2,526-region terrain foundation now carries 37,960 exterior rocks and 816
giant mushrooms. Detailed Seyda Neen and Balmora use the later bounded town
layouts; other settlements, vegetation and actors remain incomplete. Current
private builds span two simultaneously mounted HDFs. Use their generated
configuration and full drive list. See [v0.0.27 scope](RELEASE-v0.0.27.md),
[current cell handoffs](CELL_CHANGING.md) and [storage](STORAGE.md).

The following preserves the v0.0.25-rc1 terrain baseline, including its original
town-boundary and single-HDF measurements. Later town coverage, subdivision and
storage changes supersede those historical settings; the original evidence is
retained without claiming additional target acceptance.

## Historical v0.0.25-rc1 terrain baseline

The first native terrain pass uses the original polygon survey and its proposed
sub-cell divisions. It preserves the detailed Seyda Neen and Balmora conversions;
it does not replace either town with terrain-only geometry.

| Survey subdivision | Source cells | Terrain regions |
| --- | ---: | ---: |
| Whole cell | 1,078 | 1,078 |
| 2 by 2 | 314 | 1,256 |
| 4 by 4 | 12 | 192 |
| Total | 1,404 | 2,526 |

Terrain and water are converted across that footprint. Other settlements,
objects, interiors and actors outside the two detailed towns are not part of
this pass. Natural steep slopes and water retain their collision behavior;
conversion coverage is not a claim that every slope can be climbed on foot.

## Coordinates and transitions

Each region has a stable `vf0000` through `vf2525` identity and an explicit XYZ
origin. The source transform is `source = (local + origin) * 4`. Crossing rebases
the position, preserving world location, velocity, camera direction and movement
mode. Saves include the region identity and the exact terrain-content fingerprint.
Older saves with different converted-content hashes are rejected as before.

Core size follows the measured survey; coverage extends 896 runtime units past
each edge. Every region uses the same source-aligned 128-unit sampling grid
(stride 4), refined at original 32-unit samples where necessary to preserve
shoreline land/water classification, original LAND materials and standing humanoid
collision hull. The matching Balmora material corrections are applied to this
terrain pass too. Local coordinates stay below the signed network-coordinate
limit, including near Red Mountain. The outdoor draw distance remains 540.

At town boundaries the existing town loader retains its detailed sub-cells,
architecture, NPCs, doors and interiors. Only one scene is resident at a time;
crossings still load a scene and can pause. The current method 1 remains the
default. This is not a new background streaming method.

The Seyda Neen handoff now comes from its actual ground bounds, not its larger
sea/enclosure bounds. Its core is local `[-1184,-1696]..[1568,1440]`; the 32-unit
exit margin leaves at least 64 units of converted ground before any edge.
Balmora retains its `[-2976,-2976]..[2976,2976]` core. Both towns keep their
existing geometry, actors, interiors and detailed region conversions.

## Shoreline correction

The source survey's exterior water datum is zero. Auditing all dev1 water faces
after adding each region's Z origin found no different global datum. However,
stride-four triangulation put **10,282 original dry samples below sea level**.
Lowering the whole ocean would mask this conversion error and move correct coasts.

rc1 inserts original-height edge/interior points where coarse triangles change
wet/dry classification. Shared edges make the same decision from the same source
samples; overlaps and unlike region subdivisions therefore agree. The full source
LAND audit covers 330,752 coarse tiles: 12,871 require refinement, and all 321,775
sample checks in those tiles preserve the original classification. This is not
full-resolution reconstruction of every slope between the samples.

Ocean-only enclosures now extend above water even when all local terrain is below
it. A compiler-only air seed lets QBSP fill those enclosures; it is removed from
the final entities. Terrain-only maps retain point and standing-player collision;
unused stock large-actor hulls are removed before grafting the standing hull.
Future non-humanoid actors will need their own supported hull policy. Detailed
town collision is unchanged.

The previously flat material-zero ground and water swatches now use the original
default-land and water textures, quantized into the existing palette. The 92
affected town BSPs receive only those texture pixels; every other lump is unchanged.
There is no source evidence for adding curvature or a town-specific sea datum.
The owner's old `9,484,102` report lacked a terrain region ID, so that exact camera
cannot be identified uniquely. New GLOBAL/LOCAL rows and `aw_pos` solve that
reporting ambiguity.

## Disk layout

One self-contained RDB HDF holds exactly two FFS partitions: `AMIWIND` for boot,
saves, existing content and the first terrain files; `AW_WORLD0` for the remaining
terrain. The packer balances their payloads. Both partitions stay below 2 GiB and
the complete device stays below 4 GiB, following the [storage plan](STORAGE.md).
The older 1 GiB boot cap was a build setting, not a filesystem limit.

This measured capacity split is distinct from the owner's preferred future
layout: main Morrowind on partition 1 where it fits, with future expansions,
videos and selected infrequent assets on partition 2. No expansion conversions
are included here. See [placement and loading costs](STORAGE.md#preferred-future-content-placement).

For the historical dev1 build, terrain output was 2,220,222,432 bytes. Lossless sharing reduced it to
1,837,389,212 bytes: lightmaps shrink from 386,165,499 to 12,009,315 bytes and
visibility rows from 602,289,401 to 593,613,901 bytes. Total saving is 382,833,220
bytes (17.24%). Each face retains identical light samples; each leaf retains its
identical encoded visibility row. Geometry, materials and collision are unchanged.
The existing BSP29 runtime reads the shared offsets without new decompression.

For rc1, the refined terrain occupies **1,948,944,656 bytes**, 111,555,444 bytes
more than dev1. Identical lighting/visibility sharing removes 397,700,784 bytes
from the new output. The largest BSP is `vf2251`: 3,249,072 bytes, 9,790 faces
and 26,286 clipnodes, below the existing limits. The extra shoreline geometry
fits the same runtime profile; no polygon or heap cap was raised.

This does not eliminate overlap between adjacent regions. Each still carries its
own bounded render/collision working set. Further cross-region sharing would need
an asset-format/loading change; it is not claimed as completed optimization.

`world/volumes.awv` lists the required terrain-volume count. All partitions mount
from the same HDF; no extra disk files or manual emulator mounts are needed.
Additional loose-file search paths leave saves and configuration on the boot
partition. Packing verifies every terrain file again from the final combined
image, in addition to validating each partition's legacy root metadata.

## Rebuilding

The normal AGA pipeline now runs `world-survey`, then `world-terrain`, before
image assembly. Shared scene writes remain ordered. The survey computes the
same 140,801-source-triangle screening reference from both existing town plans.
For the restored frozen survey, run:

```bash
python3 tools/prepare_world_regions.py \
    --survey /private/world-survey --data-files "/owned/Data Files" \
    --scene /private/converted --out /private/native-world \
    --bindir /tools/ericw/bin --jobs 8
```

A finished conversion directory is immutable. Interrupted region work can resume
only where the map/WAD/profile input hash and resulting BSP hash match. Diagnostic
`--only vf0000` subsets never install a complete world directory. The build fails
on unresolved survey cells, mismatched original input hashes, invalid local
coordinates or BSP limits; it does not silently omit failed regions.

The ordinary production image gate still stops on the existing 23 contact
findings. The development package retains that failed audit and its limited
native validation. Read the release notes before treating it as broad traversal
acceptance; full-route, Windows/WSL and physical-Amiga testing remain separate.

### Retained conversion diagnostics

Keep the complete compiler logs and warning index with conversion evidence.
Across render and standing-hull compilations, rc1 reports 5,052 missing-deathmatch
spawn notices (the game is single-player), 764 leaf-self-visibility notices,
14 clipped-portal notices, 230 no-empty-seed notices and one collision-fill
occupant notice. Dev1 had respectively 5,052, 689, 10, 7,517 and one. The final
render compilations have no missing-air-seed or occupant-fill notices; those
remaining notices occur in the separately scaled collision compilation.

The original collision helper scales brush coordinates but not entity-origin
strings, which can leave the diagnostic seed outside the scaled air region.
The explicit enclosing brushes and grafted standing hull remain present. Keep
seed transformation and near-coplanar portal cleanup as follow-up work. These
diagnostics are not a warning-free conversion claim: rc1 acceptance is bounded
by BSP-budget checks, original-sample checks and the documented native walking
routes, not exhaustive validation of every visibility portal and collision path.
