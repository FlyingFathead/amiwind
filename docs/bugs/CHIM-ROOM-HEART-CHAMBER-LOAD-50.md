# CHIM-ROOM-HEART-CHAMBER-LOAD-50: entering Akulakhan's Chamber ends the game

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 24 October 2026, in v0.0.50 |
| Where | engine/aga/src/chim room load (room rifa4ef181ed); the CHIM chunk zone |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.50 (last seen) |
| Severity | high: The game s final room; the game ends to the console (seen at 32 MB Fast RAM) |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_24_v0.0.50_final_ffb87463 |
| From commit | source ffb8746, engine ffb8746, CHIM world ffb8746 |
| CHIM engine version | CHIM 0.2.2, engine ffb8746, world format 0.12 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.50 (24 October 2026)._

## Status: 24 October 2026

Open. Known in v0.0.50; its repair is the first work of v0.0.51.

## Symptom

Entering Akulakhan's Chamber (the Heart Chamber, the game's final room) shows the loading screen, then the game stops
to the console:

```
CHIM: room rifa4ef181ed: a model of the store could not be loaded
Host_Error: CHIM room map maps/rifa4ef181ed.chim (room rifa4ef181ed): its room record or models cannot be loaded
```

Seen with 32 MB of Fast RAM, FS-UAE with JIT, on the v0.0.50 final image (`2026_10_24_v0.0.50_final_ffb87463`),
entered with `dbg tp heartchamber` from Seyda Neen.

## Where

The CHIM room load (room `rifa4ef181ed`) and the CHIM model zone (`chim_zone.c`, sized by `chim_zone_kib`).

## How it happened

The heap had about 12.7 MB free when the room loaded, but a room's models go into the CHIM model zone, a fixed
6,864 KiB at 16 MB and at 32 MB alike ([CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md)). Right after Seyda Neen was
unloaded, the zone's largest free block was 26,336 bytes. The zone is a least-recently-used cache in which nothing
moves and locked blocks are never evicted, so one of the chamber's large models found no free run that fits, and the
room load ended the game instead of refusing at the door.

## Why it was not caught

The room has been a CHIM room since v0.0.48 ([CHIM-ROOM-CLIPNODE-BUDGET-48](CHIM-ROOM-CLIPNODE-BUDGET-48.md)), and no
check entered it: the boot smokes load Seyda Neen and Balmora only. v0.0.50's named place `dbg tp heartchamber` was the
first thing that went in.

## Reproduction

Always: start a game with 32 MB of Fast RAM, `dbg tp heartchamber`.

## Repair

1. Check whether the outgoing map's zone blocks are unlocked when a map unloads (Seyda Neen, then the chamber).
2. Size the zone from the Fast RAM found at start, as the heap and the cache bank are
   ([CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md)).
3. Check each room's largest model against the zone in the build (the heap gate).
4. A room that cannot load is refused at the door with a message, never a stop to the console.

## Verification

A smoke that enters the heart chamber with `dbg tp heartchamber` at 32 MB and stays in play.

## Prevention

The release smokes enter the game's largest rooms, not only the two towns.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
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
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- [CHIM-ROOM-CLIPNODE-BUDGET-48](CHIM-ROOM-CLIPNODE-BUDGET-48.md): Akulakhan's Chamber cannot be made as a CHIM room: a model's collision exceeds the clipnode budget

<!-- END GENERATED CATEGORY -->
