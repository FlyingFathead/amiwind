# HEAP-12MB-FAST-ROOM-33: A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Fast RAM outside the game heap (aw_guard_torch.c probe, model.c staging, aw_worldui.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Only with --heap-mb 12 (not the default): guard torches stay unlit and large allocations outside the heap have little room. |
| Family | Map heap and memory budget (`heap-memory`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open; measured. Applies only to a build with `--heap-mb 12` (the default is 11 MiB, which the
builder, the boot check and the engine treat as the measured safe size; 12 warns).

## Symptom

The full-game heap test, FS-UAE A1200 profile (2 MiB Chip, 16 MiB Fast), the verified v0.0.32
release image with the CHIM engine and Seyda Neen on CHIM, the same route at 11 and 12 MiB (prison
ship, Census and Excise Office, Seyda Neen CHIM, Caius Cosades' house, Balmora `bm019`, the Vivec
Arena `va010`, the NPC gallery, the menu, quick save in Balmora and load from Seyda Neen and the
Arena). The engine's heap audit, least values over the route:

| Heap | Seyda Neen CHIM peak gap | Fast RAM free | Largest free Fast block |
| ---: | ---: | ---: | ---: |
| 11 MiB | 1,099,424 | 1,429,312 | 1,390,824 |
| 12 MiB | 2,148,000 | 380,864 | 342,240 |

Every stop loaded and the save loaded back at 12 MiB. But the guard torch admission
(`aw_guard_torch.c`) probes 1 MiB of Fast RAM in one block before it loads a guard's torch pose;
with 342,240 bytes left in one piece it always defers ("Guard torch deferred: low memory"), so
guards never light their torches. Other allocations outside the heap get little room: alias
staging copies up to 512 KiB (`model.c`, falls back when they fail), the world map screen's
250,520-byte map (`aw_worldui.c`), the movie buffers.

## Where

Fast RAM outside the game heap: `aw_guard_torch.c` (1 MiB probe), `model.c` (alias staging),
`aw_worldui.c` (world map), `aw_movie.c`.

## How it happened

The 16 MiB Fast profile holds the engine, the heap and everything allocated outside it. With 11 MiB
the rest keeps about 1.4 MB in one piece, which the guard torch probe was sized against; one more
MiB of heap takes it.

## Why it was not caught

No run had used a heap other than 11 MiB before `--heap-mb` existed.

## Reproduction

Build with `--heap-mb 12`, play at night near a torch-carrying guard; or read `fast_largest` in the
engine's heap audit log.

## Repair

None needed for the default. Options if a 12 MiB heap is wanted: size the guard torch probe from
the torch pose's own size instead of a fixed 1 MiB, or allocate the pose inside the heap.

## Verification

The heap audit of the run above (both heap sizes, same route).

## Prevention

`AMIWIND_HEAP_SAFE_MB` stays 11: a larger heap prints its warning in the build, the engine receipt,
the boot check and the engine's start. The memory guide states the 12 MiB figures.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner
- [CHIM-ZONE-RESERVE-EARLY-33](CHIM-ZONE-RESERVE-EARLY-33.md): chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap
- CRASH-01 (no report page): Heap exhaustion on sn012 after Hors travel from Jiub name entry
- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
