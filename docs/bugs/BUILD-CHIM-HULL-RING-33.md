# BUILD-CHIM-HULL-RING-33: Routed and compiled CHIM model hulls grew Balmora's ring past the zone

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM variant hulls (chim.models variant_unit, model_image_lumps) with --model-hull auto |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: The pure-CHIM release build stopped at the CHIM heap gate: Balmora's south-west ring 136,160 B over the zone. |
| Family | Map heap and memory budget (`heap-memory`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-chim-format (f85baa8, gate 577), not shipped. Found by the release's pure-CHIM
build. [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md), the same failure registered by the
integration job, is closed as its duplicate.

## Symptom

The CHIM heap gate stops the pure-CHIM release build on Balmora: the frame's active ring peaks at
6,378,464 bytes at (-672, -672), 136,160 bytes over the 6,242,304-byte chunk room. MiniWind #3, built
before the change, peaked at 6,239,776 bytes in the same frame (2,528 bytes of headroom).

## Where

`tools/chim/models.py` (`variant_unit`, `model_image_lumps`) and `tools/routed_hull.py`.

## How it happened

With `--model-hull auto` (from COLLISION-HULL-CHAINS-33), every CHIM model with more than 16 convex
pieces got its standing hull compiled by qbsp, or routed with a copy allowance when qbsp failed. Both
take more bytes than the chain they replace. A CHIM model's bytes are resident in every ring that holds
it, and Balmora's south-west ring holds several such houses. Routing without copies still adds one
clipnode per cut: measured 6,244,224 bytes, 1,920 over.

## Why it was not caught

The routing was measured for trace cost and for legacy map clipnode budgets, not for CHIM ring bytes,
and the heap gate only runs on a full CHIM world build. A second fault hid it for a while: the CHIM unit
cache did not key variants on the hull mode, so a build with another mode reused the first build's hulls
(fixed on both lines; see also BUILD-CHIM-UNIT-HULL-KEY-33).

## Reproduction

Build Balmora's CHIM world with the heap gate (`tools/chim_build.py --area balmora --sdk ... --validate`)
on 947a90e with the default `--model-hull auto`.

## Repair

CHIM routes only district-size models (more than 256 convex pieces: the Vivec canton bodies, the Arena)
and never copies by default; no qbsp union for large models unless asked (`--model-hull compiled`).
House-size models keep the chain, byte for byte. The hull mode is part of a variant's cache fingerprint.

## Verification

Balmora's CHIM world, the same inputs, three builds: chain 6,239,776 bytes (passes); routing every model
over 16 pieces without copies 6,244,224 (fails by 1,920); f85baa8 default 6,239,776 (passes). Test:
`tests/test_chim_model_hull.py` `test_auto_routes_only_large_models` (a 60-piece model's auto hull equals
its chain).

## Prevention

A change to model collision layout is measured on a real CHIM world's heap gate before it is merged.
Balmora's ring has only 2,528 bytes of headroom: any byte added to its models tips it over.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
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

Related bugs in other categories:

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget

<!-- END GENERATED CATEGORY -->
