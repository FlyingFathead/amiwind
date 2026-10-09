# CHIM-STRIDER-RING-33: The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM Balmora heap gate (tools/chim/heap.py) with the strider profile of MESH-LOD-OPEN-SEAMS-33 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev, v0.0.33 (last seen) |
| Severity | high: The strict CHIM heap gate would fail the Balmora build once the fix and the CHIM builder are merged together |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3dbaf00, engine 3dbaf00, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 3dbaf00, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source for v0.0.34, not shipped yet. The strider profile is now boundary-locked 0.45
(variant D at 0.45, [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md)): seams closed, CHIM block
464,336 B, Balmora's active ring peak 6,226,544 B of 6,242,304 B (15,760 B headroom; the v0.0.33
build left 2,528 B). E stays selectable and still does not fit.

## Symptom

On CHIM the strider is one model block in the zone. Variant E keeps the shell, arms and legs
unreduced, so the block grows, and Balmora's largest active ring no longer fits the zone budget at
the engine's default memory.

## Where

CHIM Balmora (frame -3,-2) and Seyda Neen, built with the CHIM builder of v0.0.33-chim-chunkload plus
the strider fix (v0.0.33-strider 9582693), with the v0.0.32 release run as the legacy input (harvest,
town flora). Block sizes are the target ABI's (`chim.heap.image_bytes`, `chim.zone_sim.block_sizes`).
Variants: B = the shipped profile (ratio 0.5), D = boundary-locked 0.5, E = the fix.

| | B | D | E |
| --- | ---: | ---: | ---: |
| Strider block (Balmora / Seyda Neen) | 477,616 / 477,680 | 489,632 / 489,776 | 754,576 / 754,704 |
| Largest block of the world | the strider (Balmora); a 506,000 B model (Seyda Neen) | same | the strider in both |
| Balmora ring at 636 units (budget 6,242,304) | 6,074,016 (ok, +168,288) | 6,086,032 (ok) | 6,350,976 (over by 108,672, 1 position) |
| Balmora ring at 892 units | 7,391,456 (476 positions over) | 7,403,472 (480) | 7,668,416 (546) |
| Seyda Neen ring at 636 | 5,683,920 (ok) | 5,696,016 (ok) | 5,960,944 (ok, +281,360) |
| Seyda Neen ring at 892 | 6,417,728 (29 over) | 6,429,824 (31) | 6,694,752 (181) |
| Zone walk, Balmora lawnmower (6,111 steps): holes / loads without room / partial | 0 / 30 / 25 | 0 / 29 / 24 | 0 / 51 / 39 |
| Zone walk, owner's route twice (1,192 steps) | 0 / 26 / 19 | 0 / 31 / 22 | 0 / 37 / 27 |
| Zone walk, Seyda Neen lawnmower (4,674 steps) | 0 / 14 / 10 | 0 / 13 / 9 | 0 / 14 / 10 |

The load-radius ring (892) is over the budget for every variant already
([CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md)); the strict heap gate counts the active
ring (636), and that is what E breaks for Balmora.

## How it happened

E adds about 277 KB to the strider's block (5,385 faces instead of 3,266); Balmora had 168,288 B of
ring headroom.

## Why it was not caught

The fix was measured on the legacy maps (heap gate per map) only; the CHIM heap gate runs in the
CHIM builder, which is on a separate branch.

## Reproduction

Build CHIM Balmora with the strider profile of v0.0.33-strider and run the CHIM heap gate
(`chim.heap.ring_peak`) and the zone walk (`chim.zone_sim`).

## E-lite candidates (measured 9 October 2026)

Shell kept unreduced in every candidate; boundary-locked reduction elsewhere; sky-through over the
16 one-sided views; torn seam length 0 % in every candidate.

| Candidate | Faces | Sky-through | Strider block | Balmora ring at 636 | at 892 | Seyda ring at 636 | Zone walk Balmora: lawnmower / route (loads without room; 0 holes) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E (shell, arms, legs kept; claws 0.5) | 5,385 | 0 % | 754,576 | over by 108,672 | 546 over | +281,360 | 51 / 37 |
| L0 (claws only, 0.2) | 5,139 | 0 % | 721,184 | over by 75,280 | 537 over | +314,736 | 38 / 39 |
| L1 (shell, arms kept; legs and claws 0.75) | 4,977 | 0.26 % (legs thinner) | 699,536 | over by 53,632 | 534 over | +336,368 | 35 / 34 |
| L2 (shell, arms kept; legs and claws 0.6) | 4,482 | 1.4 % (legs thinner) | 631,856 | fits, +14,048 | 522 over | +403,984 | 31 / 38 |
| D (all locked 0.5) | 3,403 | 1.8 % | 489,632 | fits, +156,272 | 480 over | +546,288 | 29 / 31 |
| B (shipped) | 3,266 | 8.8 % (open seams) | 477,616 | fits, +168,288 | 476 over | +558,384 | 30 / 26 |

Every leg reduction thins the legs (any ratio below 1 on the leg shapes gave sky-through above 0 %:
0.08 % at 0.9), so no candidate with 0 % sky-through fits Balmora's ring at the default zone; the
smallest that fits is L2.

## Repair

v0.0.34: variant D at ratio 0.45 (boundary-locked, every part reduced). Measured on CHIM worlds built
from the v0.0.33 release run's inputs with the v0.0.34 builder (control: the v0.0.33 profile gives the
released peak, 6,239,776 B, exactly):

| | v0.0.33 profile (B) | D 0.5 | D 0.45 (v0.0.34) |
| --- | ---: | ---: | ---: |
| Strider block, Balmora | 477,568 | 489,584 | 464,336 |
| Balmora active ring peak (budget 6,242,304) | 6,239,776 | 6,251,792 (over, 1 position) | 6,226,544 |
| Seyda Neen active ring peak | 5,683,920 | 5,696,016 | 5,670,768 |

The other options (a larger zone, CHIM-ZONE-BUDGET-33; a split strider block) stay open for variant E.

## Verification

Numbers above (private receipt of the measurement).

## Prevention

The CHIM heap gate fails the build; this entry exists so the merge of the fix with the CHIM builder
is not a surprise.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
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

- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams

<!-- END GENERATED CATEGORY -->
