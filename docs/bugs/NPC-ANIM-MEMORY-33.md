# NPC-ANIM-MEMORY-33: Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/npc_anim.py profiles; engine/aga/src/model.c AW_ALIAS_STAGING_LIMIT |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Frames cost 4 bytes per vertex and actors share no vertices (3 per face); memory decides which groups ship |
| Family | Map heap and memory budget (`heap-memory`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open: the owner chooses the shipped profile. Measured on the 15 Balmora exterior residents (v0.0.33
MiniWind inputs): idle 3.21 MB in all; react +0.70 MB; move +1.93 MB; full 7.17 MB (+3.96 MB).

## Symptom

Every animation frame adds 28 + 4 bytes per vertex (5,392 to 7,300 bytes per frame, mean 5,860 bytes,
for 448 to 606 faces); a full kit model (53 frames) is 440 to 590 KB.

## Where

`config/npc-anim-kit.json` (profiles), `tools/npc_anim.py`; the engine's alias stream loader stages
models up to 512 KiB (`engine/aga/src/model.c` `AW_ALIAS_STAGING_LIMIT`); larger ones take the generic
loader.

## How it happened

Converted actors give each face its own 16 x 16 skin tile, so faces share no vertices (three per face)
and every frame stores all of them.

## Why it was not caught

Idle-only models had 8 frames (22 % of a model); frame cost did not matter until more groups were added.

## Reproduction

`build.py --npc-anim full`; compare the resident model sizes with an idle build.

## Repair

Options: ship `react` for residents (+22 %) and give movers (companion, followers, fighters) a full
variant loaded when they start moving; fewer frames per group; shared vertices between faces (continuous
skins; a modular-parts design question) would cut the frame cost about three times.

## Verification

Pending the decision; the measurement is repeatable with the kit bake on any build.

## Prevention

Profile sizes are recorded per model (`anim.frame_bytes` in the resident report).

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
- [HEAP-12MB-FAST-ROOM-33](HEAP-12MB-FAST-ROOM-33.md): A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
