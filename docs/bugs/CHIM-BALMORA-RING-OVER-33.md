# CHIM-BALMORA-RING-OVER-33: Balmora's south-west CHIM ring over the zone after the routed standing hulls

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM heap gate (tools/chim/heap.py), Balmora frame x-03 y-02 |
| Reproduction | always |
| Duplicate of | [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md) |
| Persists in | v0.0.33-dev (last seen) |
| Severity | critical: The release build stops; Balmora is a pure CHIM town |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33 pass 2 full build (p2d-947a90e) |
| From commit | source 947a90e, engine 947a90e, CHIM world 947a90e |
| CHIM engine version | CHIM 0.1.0, engine 947a90e, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 integration line (CHIM builder change f85baa8), with a test. The next
full build verifies.

## Symptom

The first full v0.0.33 build with the CHIM builder for Balmora and Seyda Neen stopped at the CHIM heap
gate: Balmora's frame (x-03, y-02) needs 6,378,464 bytes at one corner of its south-west ring, and the
zone holds 6,242,304. Five of 9,216 sampled positions are over.

## Where

The CHIM variant units' standing hulls (`tools/routed_hull.py`, `--model-hull auto`), measured by the
CHIM heap gate (`tools/chim/heap.py`).

## How it happened

Since the routed standing hulls (COLLISION-HULL-CHAINS-33), every CHIM model with more than 16 convex
pieces gets a qbsp-compiled or routed standing hull with a copy allowance, which takes more bytes than
the chain it replaces. Balmora's south-west ring had only 2,528 bytes of headroom with chains (MiniWind
build mw2-033c: peak 6,239,776 bytes); the larger hulls add 138,688 bytes.

## Why it was not caught

The routed hulls were measured on hull depth and on Seyda Neen's legacy map; no Balmora CHIM build ran
between the change and this full build, and no test pins Balmora's ring against the zone.

## Reproduction

A full build with `--builder chim --chim-area balmora` and the default `--model-hull auto` from
integration head 947a90e.

## Repair

CHIM routes only district-size models (more than 256 convex pieces, such as the Vivec cantons) and
never copies pieces by default; house-size models keep the exact chain. The compiled (qbsp) standing
hull stays selectable (`--model-hull compiled`). Measured on Balmora's frame with the same inputs:
chains 6,239,776 bytes (pass); copy-free routing of every model over 16 pieces 6,244,224 bytes (1,920
bytes over: one clipnode per cut is already too much in that ring); the new default 6,239,776 bytes
(pass, 2,528 bytes of headroom).

## Verification

A test pins that a house-size model's default hull is the chain, byte for byte. Pending: the CHIM heap
gate passes Balmora in the next full build.

## Prevention

The pinning test; the heap gate already stops the build (it did here).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
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
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units

<!-- END GENERATED CATEGORY -->
