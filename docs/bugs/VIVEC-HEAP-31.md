# VIVEC-HEAP-31: dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31-dev |
| Where | Vivec dry-run maps against the loader heap budget |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev (last seen) |
| Severity | high: Dense Vivec regions and interiors exceed the heap, so Vivec cannot ship as built. |
| Family | Map heap and memory budget (`heap-memory`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Measured in the Vivec dry run with the repaired converter; nothing
shipped.

## Symptom

With VIVEC-TEXINFO-31, MESH-EXTENT-GRID-31 and LIGHTMAP-TAIL-31 repaired, the
next limit in Vivec is the engine's loader heap (budget 11,534,336 bytes,
estimated by `tools/check_world_map_heap.py` after the map optimizer):

- 18 of the 192 exterior regions of the three Vivec frames are over, by
  89,460 to 3,202,244 bytes. All 18 are regions that stopped on texture
  mappings before: the Temple and Ministry area (cells 3,-13 / 3,-12 /
  4,-13 / 4,-12, 11 regions) and cells 6,-10 / 6,-9 / 7,-10 (7 regions, which
  are also over 220 inline models).
- 4 of the 146 interiors are over: St. Delyn Underworks +964 bytes, Telvanni
  Tower +141,380, Telvanni Plaza +144,452 (also 267 inline models), Hlaalu
  Underworks +769,028 (also 225 inline models).

## Where

Map size against the engine's heap: decoded faces, their staged copy during
loading, planes and texture mappings dominate (see the Vivec sections study:
faces and their staged copy are 53-55 % of the loader peak).

## How it happened

Vivec's canton and Temple meshes are dense, and the regions use Balmora's
layout (768-unit cores, 896 overlap, draw distance 540).

## Why it was not caught

Earlier limits stopped these maps first.

## Reproduction

Convert Vivec's frames centred on cells 3,-10 / 3,-13 / 6,-10 and its
interiors with the town and interior converters at Balmora's settings, run the
map optimizer and the heap check.

## Repair

Not done. Measured options from the earlier sweep and sections study: finer
region cores (384), a shorter draw distance (360, a visible change and owner
decision), interior sections at real doors, 32-pixel textures on props, and
sprite flora. Each needs a rerun of this measurement.

## Verification

Pending.

## Prevention

The builder's heap gate already rejects such maps; the planned limits check
reports every limit per map.

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
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
