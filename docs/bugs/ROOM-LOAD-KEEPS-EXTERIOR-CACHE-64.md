# ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64: Entering a large room from a town finds less free Fast RAM than the room heap check assumes

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.64-dev3 at 2026-11-10 17:17 +0200: Fast RAM outside the Hunk, measured (session console.log of MiniWind v0.0.64-dev3 akulakhan-chamber census6 (73e5aeb6), FS-UAE 32 MB Fast): about 6 MiB free after the boot's 6 MiB CHIM bank; Balmora after its actors 4,346,264 (about 1.7 MB taken by its map and actors), scene ready 3,482,552 (0.9 MB more); at the chamber load 2,956 KiB free, largest block 2,751 KiB, after 74 KiB given back.
- Reported with v0.0.64-dev3 at 2026-11-10 19:13 +0200: Census (MiniWind akulakhan-chamber census7): nothing among the engine's checked allocations of 4 KiB or more is kept per area: the same 24 blocks (4,520 KiB) in Balmora, after the failed chamber load, inside a small room and back. They are session-wide buffers made on the first map: the video buffers (about 2.2 MB), the script result tables, the alias staging buffer, the area cache and others. Fast RAM free in Balmora: 2,399 KiB.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 10 November 2026, in v0.0.64-dev2 |
| Where | the engine's map change from a CHIM town into a CHIM room (chim_world.c room load, the CHIM cache) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.64-dev2 (last seen) |
| Severity | high: Every large room reached from a town may fail to load at the 32 MB requirement |
| Family | Map heap and memory budget (`heap-memory`) |
| Playtest version | MiniWind v0.0.64-dev2 akulakhan-chamber try3 |
| From commit | source 8b67157, engine 8b67157, CHIM world 8b67157 |
| CHIM engine version | CHIM 0.2.2, engine 8b67157, world format unknown |
| Unknown because | read from the session console, not from the build receipt |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.64-dev3 (10 November 2026)._

## Status: 10 November 2026

Open. The first reading of this entry (that the town's CHIM model cache stays held across the map change) was
corrected the same day: the town's model bank is already given to the room as purgeable memory, and the "cache" figure
of the heap lines is Quake's own cache inside the Hunk, which the room's allocations take back. What is short is Fast
RAM outside the Hunk. A per-asker count of the engine's allocations (aw_memcensus owners, on from the start of a
measuring session) shows the same 4,520 KiB in the same 24 blocks of 4 KiB or more in every area: session-wide buffers
made on the first map (the video buffers, about 2.2 MB, the script result tables, the alias staging buffer, the area
cache and others), nothing kept per area. In Balmora in play 2,399 KiB of Fast RAM are free. Akulakhan's Chamber needs
18,130 KiB for its models and gets 14,787 KiB from the zone, the banks and the Hunk.

## Symptom

At 32 MB of Fast RAM, Akulakhan's Chamber does not load when it is entered from Balmora: a model of its store cannot be
loaded and the game returns to Balmora.

## Where

The room load's growth (the room's bank of free Fast RAM, then the Hunk's rest) and the session's Fast RAM use.

## How it happened

The room heap check of the build was last measured on 26 October 2026 with 5,512 KiB in the largest free block when a
room is entered from a town; the game now leaves 2,751 KiB there, so the room's bank of free Fast RAM is no longer
taken.

## Why it was not caught

The check uses a stored measurement and never measures the room as entered from its town on the current engine.

## Reproduction

Build the akulakhan-chamber MiniWind, start it at 32 MB Fast RAM, type `dbg tp heartchamber` in Balmora.

## Repair

The cached area tables are now given back before a room grows (the area memory rule: what stays across an area change
is a purgeable cache). The chamber's own store bytes are the larger part: see STORE-MODELS-VIS-PLANES-BLOAT-64.

## Verification

The chamber loads at 32 MB Fast RAM from Balmora, and the room heap check reports what the room really meets.

## Prevention

The room heap check measures a room as entered from its town.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- [AKULAKHAN-CHAMBER-32MB-STALL-53](AKULAKHAN-CHAMBER-32MB-STALL-53.md): Akulakhan's Chamber does not fit in 32 MB of Fast RAM: its room models need more memory than is free
- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- BUILD-EDGE-PIN-SHARED-SHAPES-63 (no report page): The shared actor shapes changed the model loader without re-pinning its packed-edge heap policy
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-CACHE-SURFCACHE-SQUEEZE-57](CHIM-CACHE-SURFCACHE-SQUEEZE-57.md): The larger surface cache took its memory from the CHIM cache: 7 MiB to 5 MiB at 32 MB Fast, and two gate smokes saw the CHIM zone full
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- CHIM-HEAP-GATE-NONRING-16MB-54 (no report page): At 16 MB the CHIM zone is 6,591 of 6,596 KiB locked: the heap gate predicts only the active ring and misses the chunk index, loading buffer, frame world and streamed statics
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan's Chamber when it cannot load stops the game with an error at the console instead of refusing at the door
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner
- [CHIM-ZONE-RESERVE-EARLY-33](CHIM-ZONE-RESERVE-EARLY-33.md): chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap
- CRASH-01 (no report page): Heap exhaustion on sn012 after Hors travel from Jiub name entry
- [ENGINE-HEAP-FIXED-SIZE-43](ENGINE-HEAP-FIXED-SIZE-43.md): The game heap is a fixed 11 MiB from the build: with 128 MB of RAM Vivec still runs under the 2 MiB safety gap and loads pause
- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HEAP-12MB-FAST-ROOM-33](HEAP-12MB-FAST-ROOM-33.md): A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- HOLLOW-COLLISION-PLATE-PER-TRIANGLE-64 (no report page): A hollow model gets one exact-bevel collision plate per authored collision triangle, and a visual recipe ratio reduces only the drawn mesh
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- MEMCENSUS-OWNERS-START-STALL-64 (no report page): An engine with the first per-asker block count stalled at the start: every free searched the whole count table once its removal markers filled it
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [RAM-REQUIREMENT-32MB-48](RAM-REQUIREMENT-32MB-48.md): 16 MB of Fast RAM no longer holds the whole game: 32 MB is the safe minimum, 16 MB starts with a warning
- ROOM-AKULAKHAN-HEAP-52 (no report page): Akulakhan s Chamber needs 18.8 MB for its models and textures with its activators kept: more than the 14.3 MB the 32 MB minimum gives a room, so the image step stops
- ROOM-LOAD-FAIL-LEAKS-FAST-RAM-64 (no report page): A room load that fails and returns to the town leaves about 1.4 MB less Fast RAM free than before
- SDK-MALLOC-TRAPS-52 (no report page): The toolchain's malloc never returns NULL: a failed allocation stops the game with Software Failure #80000027 (TRAP #7); 45 engine malloc sites test for a NULL that cannot come
- SKEL-HEAP-ACCOUNTING-52 (no report page): Audit: every heap and size estimate of actor models must count a skeletal model s block (16 bytes a vertex) and its shared table
- SKEL-TABLE-SHARED-FEMALE-52 (no report page): The female animation table repeats the common table whole for its three own groups: 561 KB of Fast RAM, kept all session
- SKEL-TABLE-SIZE-52 (no report page): The shared humanoid animation table is 4.3 MB held in RAM: all 61 skeleton nodes at 15 frames a second, too much beside the game on 16 MB
- SMOKE-16MB-MAPLOAD-54 (no report page): Below the 32 MB requirement: at 16 MB Fast RAM the boot smoke loads no map (dbg tp to Seyda Neen)
- STORE-MODELS-VIS-PLANES-BLOAT-64 (no report page): Placed CHIM store models carry visibility data the engine may not read, and over-budget models stored as tiles repeat planes and visibility per tile
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom
- ZONE-FREE-SHRINK-63 (no report page): The largest free block of the small memory zone shrinks about 140 bytes with every load

<!-- END GENERATED CATEGORY -->
