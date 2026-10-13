# CHIM-BALMORA-RING-GROWTH-36: Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | Balmora CHIM frame ring [-672,-672]; CHIM model images between 3b5e7a9 and d639bb9 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev4 (last seen) |
| Severity | high: the converter mesh method fails the CHIM heap gate by 10,928 B at Balmora; the table method (default) passes with 68,192 B |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | MiniWind v0.0.36-dev4 |
| From commit | source d639bb9, engine d639bb9, CHIM world d639bb9 |
| CHIM engine version | CHIM 0.1.0, engine d639bb9, world format 0.5 |
| Build note | mesh-methods MiniWind A/B, converter method |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Cause found: the build settings, not a change in the code. v0.0.36-dev3 and dev4 are built with
`--chim-terrain-hull compiled --chim-terrain-refs on` (world format 0.7); a build with the defaults uses the routed
terrain hull and no terrain references (format 0.5), which adds 165,776 B of terrain to Balmora's peak ring. With the
converter mesh method that is 10,928 B over the zone; the mesh method table (planar merge, the default) still fits.
Making the compiled terrain hull and terrain references the defaults is an owner decision (flag defaults move only by
owner decision with content proof).

## Symptom

A MiniWind A/B on the mesh-methods line: with `--chim-mesh-method converter` the Balmora frame needs 6,253,232 B at
the ring position [-672, -672]; the zone holds 6,242,304 B, so the CHIM heap gate fails by 10,928 B. The v0.0.36-dev3
build (3b5e7a9) passed the same gate with the converter method.

## Where

The Balmora CHIM frame ring at [-672, -672]; CHIM model images (tools/chim/models.py) between 3b5e7a9 and d639bb9.

## How it happened

The A/B compared a MiniWind with the default terrain settings against dev3, which used the compiled terrain hull and
terrain references: the difference in the ring is the routed terrain hull and the terrain copies per chunk
(165,776 B), not the model changes since dev3.

## Why it was not caught

The heap gate measures each build; no build of the converter method ran between dev3 and the mesh-methods A/B.

## Reproduction

A Balmora MiniWind on d639bb9 with `--chim-mesh-method converter`.

## Repair

None needed for the shipped builds (dev3/dev4 settings, table method). Pending owner decision: the compiled terrain
hull and terrain references as defaults for v0.0.36.

## Verification

Pending.

## Prevention

The heap gate's report per ring lists the largest model images, so a growth points at its models at once.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
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
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
