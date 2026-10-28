# CHIM-AUTO-BANK-CLIFF-51: 32 MB of Fast RAM got no automatic CHIM cache bank

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 24 October 2026, in v0.0.50 |
| Where | engine/aga/src/chim/chim_zone.h CHIM_AUTO_FIRST; Chim_MemoryStart at start-up |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.50 (last seen) |
| Severity | high: At the 32 MB minimum Akulakhan's Chamber (10.1 MiB of models) cannot load and Seyda Neen's zone fills, chunks retry |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_24_v0.0.50_final_ffb87463 |
| From commit | source ffb8746, engine ffb8746, CHIM world ffb8746 |
| CHIM engine version | CHIM 0.2.2, engine ffb8746, world format 0.12 |
| Platform or emulator | FS-UAE, JIT, A1200 profile, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.51 (24 October 2026)._

## Status: 24 October 2026

Open. Fixed in source on v0.0.51-dev, not shipped at the time of writing. Checked in FS-UAE at 32 MB with the
repaired engine on the v0.0.50 final image: `Memory: 13 MiB Fast RAM free of 32 MiB; CHIM cache 7 MiB in 1 bank
(automatic)`, Seyda Neen without zone-full retries, and Akulakhan's Chamber loaded in play (135 models, 10,014 KiB,
5.0 seconds).

## Symptom

At the 32 MB minimum the start printed `Memory: 13 MiB Fast RAM free of 32 MiB; CHIM cache off (not enough extra Fast
RAM, standard memory)`. Without the bank, Akulakhan's Chamber (10.1 MiB of models) ended the game at its load
([CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)) and Seyda Neen's CHIM zone filled up, so
chunks waited ("zone full ... retrying").

## Where

`engine/aga/src/chim/chim_zone.h` `CHIM_AUTO_FIRST` (the least size of the first automatic bank) and
`chim_zone.c ChimZone_AutoStep`, used by `chim_world.c Chim_MemoryStart` at start-up.

## How it happened

The automatic bank takes the free Fast RAM beyond a margin left to the system: 2 MiB plus an eighth of all Fast RAM,
6 MiB at 32 MB. The first bank needed at least 8 MiB. On 23 October the 32 MB profile had 14 MiB free, so an 8 MiB
bank; the v0.0.50 build left 13 MiB free, a 7 MiB budget, under the 8 MiB least, so no bank at all. One MiB less
free memory took away 8 MiB of cache.

## Why it was not caught

The builder's model of a 32 MB start (`tools/engine_limits.py MEASURED_FAST`) had the 23 October measurement, so it
kept planning rooms with the 8 MiB bank, and the boot smokes load Seyda Neen and Balmora, which play on without it.

## Reproduction

Always: the v0.0.50 image with 32 MB of Fast RAM (FS-UAE, A1200 profile).

## Repair

The first bank needs 4 MiB, as every later one: a 7 MiB budget gives one 7 MiB bank. The 16 MB baseline still gets
none. The look-ahead keeps its step at 8 MiB of cache. The builder's model has the v0.0.50 measurement (13 MiB free),
so a room's 32 MB mark counts the 7 MiB bank (the 32 MB room holds 14,336,000 bytes).

## Verification

`tests/aga_chim_zone_test.c` (the 32 MB start of v0.0.50 gives a 7 MiB bank), `tests/test_door_graph.py`,
`tests/test_chim_room_fast_ram.py`; in the game, `dbg tp heartchamber` at 32 MB.

## Prevention

The memory line of every start is read in the release smokes, and a smoke enters the largest room at 32 MB.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AKULAKHAN-CHAMBER-32MB-STALL-53 (no report page): Akulakhan's Chamber loads three times at 32 MB Fast RAM
- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
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
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [RAM-REQUIREMENT-32MB-48](RAM-REQUIREMENT-32MB-48.md): 16 MB of Fast RAM no longer holds the whole game: 32 MB is the safe minimum, 16 MB starts with a warning
- ROOM-AKULAKHAN-HEAP-52 (no report page): Akulakhan s Chamber needs 18.8 MB for its models and textures with its activators kept: more than the 14.3 MB the 32 MB minimum gives a room, so the image step stops
- SDK-MALLOC-TRAPS-52 (no report page): The toolchain's malloc never returns NULL: a failed allocation stops the game with Software Failure #80000027 (TRAP #7); 45 engine malloc sites test for a NULL that cannot come
- SKEL-HEAP-ACCOUNTING-52 (no report page): Audit: every heap and size estimate of actor models must count a skeletal model s block (16 bytes a vertex) and its shared table
- SKEL-TABLE-SHARED-FEMALE-52 (no report page): The female animation table repeats the common table whole for its three own groups: 561 KB of Fast RAM, kept all session
- SKEL-TABLE-SIZE-52 (no report page): The shared humanoid animation table is 4.3 MB held in RAM: all 61 skeleton nodes at 15 frames a second, too much beside the game on 16 MB
- SMOKE-16MB-MAPLOAD-54 (no report page): Below the 32 MB requirement: at 16 MB Fast RAM the boot smoke loads no map (dbg tp to Seyda Neen)
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
