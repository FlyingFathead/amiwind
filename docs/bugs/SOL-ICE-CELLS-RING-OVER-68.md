# SOL-ICE-CELLS-RING-OVER-68: Two Solstheim ice coast cells convert but their memory ring is far above the budget: every tilted iceberg shard is stored as a model of its own

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.68-dev1 at 2026-11-20 18:27 +0200: A third ice coast cell, -26,25, passes the memory check but its ring measured alone is more than twice the budget: ice chunks and iceberg shards again.
- Reported with v0.0.68-dev1 at 2026-11-20 21:20 +0200: Measured as built (each cell as the frame a build installs, with its neighbours' edge), the glacier's eight neighbouring cells need 39 to 57 MB of memory ring against 6.2 MB: the glacier's icebergs reach into each of their frames.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 20 November 2026, in v0.0.68-dev1 |
| Where | CHIM import of Solstheim cells -25,26, -27,26 and -26,27: the memory ring check (chim heap gate) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.68-dev1 (last seen) |
| Severity | high: the cells cannot go into a game image: the ring would not fit the memory the game requires, even measured alone |
| Family | Map heap and memory budget (`heap-memory`) |
| Playtest version | CHIM import run of the v0.0.68-dev1 line, Solstheim run 1 |
| From commit | source 0c482ce, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.5 |
| Unknown because | a CHIM import run converts cells only: it builds no engine and no game world image |
| Build note | a CHIM import run of 48 cells, not a game image |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-20: reported in v0.0.68-dev1
- 2026-11-20 18:27 +0200: seen again in v0.0.68-dev1: A third ice coast cell, -26,25, passes the memory check but its ring measured alone is more than twice the budget: ice chunks and iceberg shards again.
- 2026-11-20 21:20 +0200: seen again in v0.0.68-dev1: Measured as built (each cell as the frame a build installs, with its neighbours' edge), the glacier's eight neighbouring cells need 39 to 57 MB of memory ring against 6.2 MB: the glacier's icebergs reach into each of their frames.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- [AKULAKHAN-CHAMBER-32MB-STALL-53](AKULAKHAN-CHAMBER-32MB-STALL-53.md): Akulakhan's Chamber does not fit in 32 MB of Fast RAM: its room models need more memory than is free
- [AW-20260929-06](AW-20260929-06.md): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [BUILD-EDGE-PIN-SHARED-SHAPES-63](BUILD-EDGE-PIN-SHARED-SHAPES-63.md): The shared actor shapes changed the model loader without re-pinning its packed-edge heap policy
- [CENSUS-COURTYARD-REENTRY-CRASH-68](CENSUS-COURTYARD-REENTRY-CRASH-68.md): Going back into the census office from its courtyard after a played session stops the game with a model cache error
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-CACHE-SURFCACHE-SQUEEZE-57](CHIM-CACHE-SURFCACHE-SQUEEZE-57.md): The larger surface cache took its memory from the CHIM cache: 7 MiB to 5 MiB at 32 MB Fast, and two gate smokes saw the CHIM zone full
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-HEAP-GATE-NONRING-16MB-54](CHIM-HEAP-GATE-NONRING-16MB-54.md): At 16 MB the CHIM zone is 6,591 of 6,596 KiB locked: the heap gate predicts only the active ring and misses the chunk index, loading buffer, frame world and streamed statics
- [CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68](CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68.md): The CHIM memory report counts the planes used only by a model's standing hull as drawn bytes, so collision-heavy models look like drawn geometry
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan's Chamber when it cannot load stops the game with an error at the console instead of refusing at the door
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner
- [CHIM-ZONE-RESERVE-EARLY-33](CHIM-ZONE-RESERVE-EARLY-33.md): chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap
- [CHIMPORT-HEAP-NOT-BUILD-FRAMES-68](CHIMPORT-HEAP-NOT-BUILD-FRAMES-68.md): Each cell of a CHIM import is built with older terrain storage settings than a build uses and without its neighbouring cells in the memory ring, so the memory use recorded for the cell differs from what a build measures for it
- CRASH-01 (no report page): Heap exhaustion on sn012 after Hors travel from Jiub name entry
- [ENGINE-HEAP-FIXED-SIZE-43](ENGINE-HEAP-FIXED-SIZE-43.md): The game heap is a fixed 11 MiB from the build: with 128 MB of RAM Vivec still runs under the 2 MiB safety gap and loads pause
- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HEAP-12MB-FAST-ROOM-33](HEAP-12MB-FAST-ROOM-33.md): A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- [HOLLOW-COLLISION-PLATE-PER-TRIANGLE-64](HOLLOW-COLLISION-PLATE-PER-TRIANGLE-64.md): A hollow model gets one exact-bevel collision plate per authored collision triangle, and a visual recipe ratio reduces only the drawn mesh
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- [MEM-EXTRA-HDF-27](MEM-EXTRA-HDF-27.md): Map loads bypassed the engine's file search paths: a map on an extra world disk image fell back to a whole-file read
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- [MEMCENSUS-OWNERS-START-STALL-64](MEMCENSUS-OWNERS-START-STALL-64.md): An engine with the first per-asker block count stalled at the start: every free searched the whole count table once its removal markers filled it
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [RAM-REQUIREMENT-32MB-48](RAM-REQUIREMENT-32MB-48.md): 16 MB of Fast RAM no longer holds the whole game: 32 MB is the safe minimum, 16 MB starts with a warning
- ROOM-AKULAKHAN-HEAP-52 (no report page): Akulakhan s Chamber needs 18.8 MB for its models and textures with its activators kept: more than the 14.3 MB the 32 MB minimum gives a room, so the image step stops
- [ROOM-LOAD-FAIL-LEAKS-FAST-RAM-64](ROOM-LOAD-FAIL-LEAKS-FAST-RAM-64.md): A room load that fails and returns to the town leaves about 1.4 MB less Fast RAM free than before
- [ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64](ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64.md): Entering a large room from a town keeps the town's CHIM model cache, so the room can run out of Fast RAM at 32 MB although it fits on its own
- SDK-MALLOC-TRAPS-52 (no report page): The toolchain's malloc never returns NULL: a failed allocation stops the game with Software Failure #80000027 (TRAP #7); 45 engine malloc sites test for a NULL that cannot come
- [SKEL-HEAP-ACCOUNTING-52](SKEL-HEAP-ACCOUNTING-52.md): Audit: every heap and size estimate of actor models must count a skeletal model s block (16 bytes a vertex) and its shared table
- [SKEL-TABLE-SHARED-FEMALE-52](SKEL-TABLE-SHARED-FEMALE-52.md): The female animation table repeats the common table whole for its three own groups: 561 KB of Fast RAM, kept all session
- [SKEL-TABLE-SIZE-52](SKEL-TABLE-SIZE-52.md): The shared humanoid animation table is 4.3 MB held in RAM: all 61 skeleton nodes at 15 frames a second, too much beside the game on 16 MB
- [SMOKE-16MB-MAPLOAD-54](SMOKE-16MB-MAPLOAD-54.md): Below the 32 MB requirement: at 16 MB Fast RAM the boot smoke loads no map (dbg tp to Seyda Neen)
- [STORE-MODELS-VIS-PLANES-BLOAT-64](STORE-MODELS-VIS-PLANES-BLOAT-64.md): Placed CHIM store models carry visibility data the engine may not read, and over-budget models stored as tiles repeat planes and visibility per tile
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom
- [ZONE-FREE-SHRINK-63](ZONE-FREE-SHRINK-63.md): The largest free block of the small memory zone shrinks about 140 bytes with every load

Related bugs in other categories:

- [CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68](CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68.md): A large model's tiles that lie beyond a CHIM frame's edge are all given to its edge chunks, so one memory ring at the frame's corner holds every tile of the model

<!-- END GENERATED CATEGORY -->
