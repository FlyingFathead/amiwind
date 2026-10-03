# rc3 full-runtime map memory profile

The complete staged runtime map set contains **2,678 BSPs**: 2,526 `vfNNNN` world cells and 152 named maps. The target-ABI audit estimates one map at a time, including ordered decoded allocations and temporary input peaks. It uses an 11 MiB target Hunk, reserves 3 MiB for non-BSP engine state, and keeps a separate 2 MiB safety margin. **2,650 maps pass the estimate and 28 need reduction**; none of those failures are world-cell `vfNNNN` maps. A storage partition does not increase runtime heap. This is the rc3 baseline profile from before the latest member-relative stream-reader change; use it to prioritize map work, not as clearance evidence for a newly built engine. The image gate now compares the engine receipt with current hashes for `Makefile`, `model.c`/`model.h`, `zone.c`/`zone.h`, `common.c` and `sys_amiga.c`, and records those hashes with each new map audit.

The runtime selects one current world BSP for the active scene or cell. `AW_WorldDestination` selects a single `vfNNNN`; `AW_RegionWorldModel` selects one `bmNNN` or `snNNN` (or a special scene). `SV_SpawnServer` clears map memory before loading the next scene. The audit’s 2,678 rows are candidate maps, not simultaneous residency. Lookahead transitions and global/cache allocations still require the runtime Hunk reports described in [Memory Allocation](MEMORY_ALLOCATION.md).

The worst streamed-map estimate is `seyda.bsp`: **10.94 MiB** modeled loader peak, or **15.94 MiB** including both reserves, leaving a **4.94 MiB shortfall** against the 11 MiB Hunk. `sn012.bsp` peaks at 10.36 MiB and is 4.36 MiB short after reserves. These are estimate results, not target-playtest observations. Clearance below zero means the map needs reduction before it has acceptable headroom.

Roles distinguish exterior regions, full-scene fallbacks and interiors. The `bmmages` and `bmtemple` entries are Balmora interiors; `addamasartus` is also an interior. Coordinates are runtime-local XY bounds. Exterior cell coordinates come from the runtime region directory; dock and courtyard coordinates come from their selector bounds. A dash means the map is a full-scene fallback or interior without a region core.

| Map | Runtime role | Runtime region / selector XY bounds | Faces / planes / nodes / leaves / clipnodes | Visibility MiB | Dominant resident allocation | Loader peak MiB | Headroom / action | Subdivision candidate | Queue |
|---|---|---|---:|---:|---|---:|---|---:|
| `seyda.bsp` | Seyda exterior fallback | — | 36,757 / 58,256 / 23,821 / 4,907 / 39,505 | 2.64 | visibility | 10.94 | needs reduction; headroom deficit 4.94 MiB | no | scene reduction |
| `sn012.bsp` | Seyda exterior | [-768,-768]–[1024,474] | 31,674 / 57,615 / 23,624 / 4,907 / 39,156 | 2.64 | visibility | 10.36 | needs reduction; headroom deficit 4.36 MiB | yes | #01 |
| `sn017.bsp` | Seyda exterior | [-768,474]–[1024,1242] | 28,076 / 50,582 / 21,453 / 4,907 / 36,111 | 2.64 | visibility | 9.60 | needs reduction; headroom deficit 3.60 MiB | yes | #02 |
| `sn013.bsp` | Seyda exterior | [1024,-768]–[1792,474] | 22,976 / 44,265 / 19,802 / 4,907 / 33,656 | 2.64 | visibility | 8.74 | needs reduction; headroom deficit 2.74 MiB | yes | #03 |
| `sn018.bsp` | Seyda exterior | [1024,474]–[1792,1242] | 22,360 / 43,970 / 19,763 / 4,907 / 33,670 | 2.64 | visibility | 8.66 | needs reduction; headroom deficit 2.66 MiB | yes | #04 |
| `sn007.bsp` | Seyda exterior | [-768,-1536]–[1024,-768] | 21,560 / 44,686 / 20,825 / 4,907 / 34,872 | 2.64 | visibility | 8.56 | needs reduction; headroom deficit 2.56 MiB | yes | #05 |
| `intro_docks.bsp` | Seyda exterior | [-240,-1100]–[1120,620] | 18,348 / 38,212 / 18,398 / 4,907 / 31,480 | 2.64 | visibility | 7.95 | needs reduction; headroom deficit 1.95 MiB | no | scene reduction |
| `bm027.bsp` | Balmora exterior | [-768,-768]–[0,0] | 33,909 / 61,892 / 19,919 / 790 / 57,112 | 0.07 | faces | 7.76 | needs reduction; headroom deficit 1.76 MiB | yes | #06 |
| `sncourt.bsp` | Seyda exterior | [-128,-384]–[512,256] | 15,491 / 35,664 / 17,573 / 4,907 / 30,222 | 2.64 | visibility | 7.50 | needs reduction; headroom deficit 1.50 MiB | no | scene reduction |
| `sn022.bsp` | Seyda exterior | [-768,1242]–[1024,2079] | 16,059 / 30,640 / 15,845 / 4,907 / 27,830 | 2.64 | visibility | 7.22 | needs reduction; headroom deficit 1.22 MiB | yes | #07 |
| `sn008.bsp` | Seyda exterior | [1024,-1536]–[1792,-768] | 14,888 / 32,648 / 17,306 / 4,907 / 29,802 | 2.64 | visibility | 7.22 | needs reduction; headroom deficit 1.22 MiB | yes | #08 |
| `sn011.bsp` | Seyda exterior | [-1536,-768]–[-768,474] | 14,559 / 33,073 / 17,534 / 4,907 / 29,916 | 2.64 | visibility | 7.16 | needs reduction; headroom deficit 1.16 MiB | yes | #09 |
| `balmora.bsp` | other named map | [-768,-1536]–[0,-768] | 34,120 / 51,048 / 14,359 / 812 / 36,498 | 0.08 | faces | 7.06 | needs reduction; headroom deficit 1.06 MiB | no | scene reduction |
| `bm019.bsp` | Balmora exterior | [-768,-1536]–[0,-768] | 34,120 / 51,048 / 14,359 / 812 / 36,498 | 0.08 | faces | 7.06 | needs reduction; headroom deficit 1.06 MiB | yes | #10 |
| `bmtemple.bsp` | Balmora interior | — | 35,242 / 58,465 / 11,860 / 2 / 39,864 | 0.00 | faces | 6.98 | needs reduction; headroom deficit 0.98 MiB | no | scene reduction |
| `bm028.bsp` | Balmora exterior | [0,-768]–[768,0] | 32,772 / 45,261 / 13,721 / 946 / 40,463 | 0.11 | faces | 6.84 | needs reduction; headroom deficit 0.84 MiB | yes | #11 |
| `bm020.bsp` | Balmora exterior | [0,-1536]–[768,-768] | 34,376 / 46,103 / 11,248 / 877 / 30,336 | 0.09 | faces | 6.79 | needs reduction; headroom deficit 0.79 MiB | yes | #12 |
| `bm026.bsp` | Balmora exterior | [-1536,-768]–[-768,0] | 32,292 / 47,876 / 12,142 / 866 / 39,469 | 0.09 | faces | 6.73 | needs reduction; headroom deficit 0.73 MiB | yes | #13 |
| `bmmages.bsp` | Balmora interior | — | 40,530 / 26,788 / 6,241 / 2 / 11,366 | 0.00 | faces | 6.68 | needs reduction; headroom deficit 0.68 MiB | no | scene reduction |
| `bm035.bsp` | Balmora exterior | [-768,0]–[0,768] | 31,928 / 48,782 / 13,392 / 737 / 38,459 | 0.06 | faces | 6.59 | needs reduction; headroom deficit 0.59 MiB | yes | #14 |
| `addamasartus.bsp` | Addamasartus interior | — | 23,426 / 80,434 / 20,093 / 3 / 40,199 | 0.00 | planes | 6.53 | needs reduction; headroom deficit 0.53 MiB | no | scene reduction |
| `sn016.bsp` | Seyda exterior | [-1536,474]–[-768,1242] | 11,472 / 25,659 / 15,236 / 4,907 / 26,609 | 2.64 | visibility | 6.45 | needs reduction; headroom deficit 0.45 MiB | yes | #15 |
| `sn023.bsp` | Seyda exterior | [1024,1242]–[1792,2079] | 11,417 / 24,561 / 13,718 / 4,907 / 24,837 | 2.64 | visibility | 6.35 | needs reduction; headroom deficit 0.35 MiB | yes | #16 |
| `sn006.bsp` | Seyda exterior | [-1536,-1536]–[-768,-768] | 10,328 / 26,737 / 15,381 / 4,907 / 26,874 | 2.64 | visibility | 6.34 | needs reduction; headroom deficit 0.34 MiB | yes | #17 |
| `bm018.bsp` | Balmora exterior | [-1536,-1536]–[-768,-768] | 33,673 / 40,443 / 5,905 / 835 / 19,479 | 0.08 | faces | 6.22 | needs reduction; headroom deficit 0.22 MiB | yes | #18 |
| `bm036.bsp` | Balmora exterior | [0,0]–[768,768] | 32,831 / 39,375 / 8,554 / 928 / 24,753 | 0.10 | faces | 6.17 | needs reduction; headroom deficit 0.17 MiB | yes | #19 |
| `bm010.bsp` | Balmora exterior | [-1536,-2304]–[-768,-1536] | 33,941 / 36,691 / 4,062 / 987 / 11,719 | 0.12 | faces | 6.13 | needs reduction; headroom deficit 0.13 MiB | yes | #20 |
| `bm029.bsp` | Balmora exterior | [768,-768]–[1536,0] | 25,627 / 49,977 / 15,967 / 955 / 43,086 | 0.11 | faces | 6.06 | needs reduction; headroom deficit 0.06 MiB | yes | #21 |

## Subdivision queue and causes

All 28 entries are marked `needs reduction`. The queue ranks the 21 failed `snNNN` and `bmNNN` cells by current shortfall; the remaining seven full-scene fallbacks and interiors need scene-specific reduction review. A queue rank indicates memory priority, not approval to change core bounds or coverage without transition, visibility and collision checks.

The 14 Seyda exterior failures include the base/fallback map, dock and courtyard scenes, and 11 sub-cells. Every failing `snNNN` map has 4,907 leaves and a 2,767,103-byte visibility lump (2.64 MiB). Visibility dominates the largest estimates; faces, planes and nodes add substantial resident cost. `sn012` has 31,674 faces, 57,615 planes, 23,624 nodes, 4,907 leaves and 39,156 clipnodes. Earlier content-preserving cleanup saved about 0.39 MiB on `sn012`, far below its 4.36 MiB shortfall.

The 11 Balmora exterior failures use 768×768-unit cores with 896-unit coverage overlap. Their largest costs are decoded faces (about 2.0–2.6 MiB per map), followed by planes and texinfo; `bm027` also carries 57,112 clipnodes. `balmora.bsp` and `bm019.bsp` are byte-identical and use the same arrival-cell bounds; both are audited because one is a fallback candidate and the other is the selected cell. Two additional Balmora failures, `bmmages.bsp` and `bmtemple.bsp`, are interiors and should be handled in the interior scene queue.

`addamasartus.bsp` is the remaining interior failure. It is dominated by 80,434 planes; its visibility payload is only two bytes, so visibility reduction would not address its shortfall.

## Common feature in the remaining 15 trial failures

The visual-coverage reduction trial checks 21 previously failing exterior town
subcells. Six candidates now clear the modeled gate; **15 still fail: nine Seyda
Neen `snNNN` subcells and six Balmora `bmNNN` subcells**. All 15 belong to the
exterior town-overlay/subcell category, rather than the terrain-and-scenery
`vfNNNN` world-cell category. This is a useful shared feature for profiling.

Here, “town overlay” describes content and selection role. It does not establish
that the runtime loads a separate topomap beneath a town BSP: the static loader
trace selects one current world BSP. Investigate retained terrain/visibility in
Seyda and decoded geometry/collision in Balmora instead of assuming two complete
maps are simultaneously resident. Runtime transition traces remain required.

These are candidate estimates after visual-coverage pruning, not an updated
full-map acceptance result or installed playable maps. The retained full audit
still reports 28 failures, including seven aggregate/special maps and interiors
outside this 21-subcell trial. Common category is not proof of a single cause.

## Reduction trials and safe directions

A private 36-cell Seyda trial kept the existing overlap and still left 16 cells below budget, so smaller rectangular cores alone do not solve the worst regions. A clipped-corner placement trial removed 10 models and 1,600 faces, lowering modeled peak by 394,272 bytes, but remained 3,488,816 bytes short; its terrain mask still used the bounding rectangle and it was not installed.

For Seyda, regenerate or compact per-cell visibility only after proving that visible surfaces remain visible from every retained leaf; simple deduplication is insufficient. Reduce repeated world geometry through content-aware subdivisions and BSP compaction while preserving collision and transition continuity.

For Balmora, choose cores based on measured density and map footprints. Cores may use nonuniform or arbitrary polygonal shapes when that fits the scene better than a uniform grid. Keep render, collision, draw-distance, hysteresis and resident gameplay requirements inside measured coverage; do not assume a particular polygon shape is required.

For every candidate, preserve the 3 MiB baseline and 2 MiB safety headroom. Re-run the full final-map gate, then compare target scene-load and transition Hunk reports. Any fallback to full-file loading can add the entire BSP input buffer alongside decoded allocations. Under the separate conservative full-file bound, all 28 failed maps remain short; this is scenario analysis, not a measured allocation. The bound remains in the private investigation until the new direct stream route has target-build and regression evidence.

The public summary contains map statistics only, no BSP, texture, mesh or proprietary asset payload.


## Current rc4 estimate of the retained 64-core proposal

Re-estimated 3 October 2026 after the rc4 node-residency loader change. All 64 candidate BSP SHA-256 identities match the original proposal; geometry was not rebuilt for this comparison. The estimator models the changed loading order and transient hull0/node overlap rather than simply subtracting renderer-record bytes.

| Measure | Earlier rc3 estimator | Current rc4 estimator |
| --- | ---: | ---: |
| Cores within 6 MiB map ceiling | 64 / 64 | 64 / 64 |
| Cores above 5 MiB planning target | 39 | 39 |
| Highest modeled loading peak | 6,271,536 B | 5,886,736 B |
| Smallest growth margin after reserves | 19,920 B (19.5 KiB) | 404,720 B (395.2 KiB) |

The 3 MiB non-map reserve and independent 2 MiB safety headroom are unchanged. These margins are within the map allowance, not total machine free RAM. All 64 native region slots remain occupied. The proposal is not installed and exact packaged runtime acceptance remains pending. The 39 planning-target misses still need attention; no FPS improvement follows from this static estimate.

The heatmap must label current and historical estimates separately. Its full-town polygon background is spatial context, not the geometry or resource count of the 64 individual bounded candidates. See [node residency](NODE_RESIDENCY.md) and [the required watcher/profiler/optimizer pipeline](HEAP_WATCHER.md).
