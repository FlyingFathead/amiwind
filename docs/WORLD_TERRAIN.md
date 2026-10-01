# Playable Vvardenfell terrain — v0.0.25-dev1

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
(stride 4 of the original heights), original LAND materials and standing humanoid
collision hull. The matching Balmora material corrections are applied to this
terrain pass too. Local coordinates stay below the signed network-coordinate
limit, including near Red Mountain. The outdoor draw distance remains 540.

At town boundaries the existing town loader retains its detailed sub-cells,
architecture, NPCs, doors and interiors. Only one scene is resident at a time;
crossings still load a scene and can pause. The current method 1 remains the
default. This is not a new background streaming method.

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

The initial terrain output was 2,220,222,432 bytes. Lossless sharing reduces it to
1,837,389,212 bytes: lightmaps shrink from 386,165,499 to 12,009,315 bytes and
visibility rows from 602,289,401 to 593,613,901 bytes. Total saving is 382,833,220
bytes (17.24%). Each face retains identical light samples; each leaf retains its
identical encoded visibility row. Geometry, materials and collision are unchanged.
The existing BSP29 runtime reads the shared offsets without new decompression.

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
