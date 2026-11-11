# AKULAKHAN-CHAMBER-32MB-STALL-53: Akulakhan's Chamber loads three times at 32 MB Fast RAM

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.64-dev2 at 2026-11-10 11:48 +0200: MiniWind akulakhan-chamber (2026_11_10_v0.0.64-dev2_miniwind-akulakhan-chamber-try3_8b67157), FS-UAE 32 MB Fast: dbg tp heartchamber from Balmora fails: the room's models need about 18,130 KiB, the zone and banks give 14,787 KiB after growing, a store model cannot be loaded, the load returns to Balmora (twice). The heart and Dagoth Ur are therefore not seen.
- Reported with v0.0.64-dev2 at 2026-11-10 12:13 +0200: Byte measurement of the room's 148 store models (18,579,456 bytes): planes 42.4 %, visibility 17.9 %, clipnodes 13.8 %, surfaces 9.3 %, texinfo 7.4 %, vertices and edges 3.2 %; textures 210,688 bytes. Cutting triangles moves little; the shortfall in the sandbox is the town cache held across the map change (ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 27 October 2026, in v0.0.53 |
| Where | room load of Akulakhan's Chamber at 32 MB Fast RAM |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.53 (last seen) |
| Severity | medium: A slow room load at the required memory size; the room does load. |
| Family | Map heap and memory budget (`heap-memory`) |
| Playtest version | 2026_10_27_v0.0.53_final_45f4c426 |
| From commit | source 45f4c42, engine 45f4c42, CHIM world 45f4c42 |
| CHIM engine version | CHIM 0.2.2, engine 45f4c42, world format 0.13 |
| Platform or emulator | FS-UAE, 32 MB Fast, JIT off |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.64-dev2 (10 November 2026)._

## Status: 10 November 2026

Open and persisting. In the akulakhan-chamber MiniWind of the v0.0.64-dev2 line (FS-UAE, 32 MB Fast RAM) the chamber
did not load at all when it was entered from Balmora: its models need about 18,130 KiB, the memory zone and its banks
gave 14,787 KiB after growing, one store model could not be loaded and the game returned to Balmora, twice. The cause
of the shortfall is filed as ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64: the town's model cache (3,888,880 bytes) is still held
when the room loads.

## Symptom

At 32 MB Fast RAM the chamber loaded three times before it was drawn (fill, grow by the free Fast RAM, grow by the
rest of the Hunk), which looked like a stall on the slow emulator preset. On the v0.0.64-dev2 line, entered from a
town, it does not load.

## Where

Akulakhan's Chamber (the Heart Chamber), the room's model store and the engine's room load.

## How it happened

The chamber is the largest room of the game: 148 store models of 18,579,456 bytes. Measured per model on
10 November 2026: planes 42.4 %, visibility 17.9 %, collision nodes 13.8 %, surfaces 9.3 %, texture info 7.4 %,
vertices and edges 3.2 %; the room's 62 textures take 210,688 bytes. The room needs more than half of the memory the
32 MB requirement leaves, so anything still held from the place before it decides whether it fits.

## Why it was not caught

The room heap check of the build measures each room on its own, with nothing loaded before it; it passed the chamber at
32 MB with 896 KB to spare.

## Reproduction

Build the akulakhan-chamber MiniWind, start it at 32 MB Fast RAM and type `dbg tp heartchamber` in Balmora.

## Repair

First the room load gives back the town's model cache before it grows its banks (ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64).
The chamber's own bytes are mostly planes, visibility and collision nodes, not triangles, so a triangle cut alone would
move little; what the engine reads of those parts for a placed model is measured before any builder change.

## Verification

The chamber loads at 32 MB Fast RAM from Balmora in the MiniWind, the heart and Dagoth Ur are listed and drawn, and the
same on the Raspberry Pi 4B.

## Prevention

A room heap check that also counts what the largest town keeps across a map change.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

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
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan s Chamber (the Heart Chamber) ends the game: a model of its room store does not load, and the engine stops with Host_Error instead of refusing at the door
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
- [ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64](ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64.md): Entering a large room from a town keeps the town's CHIM model cache, so the room can run out of Fast RAM at 32 MB although it fits on its own
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
