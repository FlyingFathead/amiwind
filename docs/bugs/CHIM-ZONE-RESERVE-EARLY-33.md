# CHIM-ZONE-RESERVE-EARLY-33: chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM engine zone allocation (chim_world.c MapBegin) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: The engine's own Hunk safety margin is not enforced on CHIM maps; the heap audit only warns afterwards. |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source edd200f, engine edd200f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine edd200f, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open; cause measured. CHIM area: memory (zone and Hunk). Build: the test image of
CHIM-SEYDA-HUNK-GAP-33 (v0.0.32 release images, CHIM engine of v0.0.33-chim-engine, Seyda Neen
world `seyda-009`).

## Symptom

`chim_reserve_kib` (2,048 KiB) is meant to keep that much of the Hunk free beside the CHIM zone. On
Seyda Neen's CHIM map the Hunk gap still ends at 1,099,456 bytes:

| Map | Hunk low after the BSP | after actors | load peak | peak gap |
| --- | ---: | ---: | ---: | ---: |
| Seyda Neen CHIM (`seyda-chim.bsp`) | 825,744 | 8,832,768 | 10,434,880 | 1,099,456 |
| Balmora CHIM (`balmora-chim.bsp`) | 793,504 | 7,826,848 | 9,431,840 | 2,102,496 |
| Seyda Neen legacy region (`sn029`) | 5,144,832 | 5,497,696 | 7,109,616 | 4,424,720 |

## Where

`engine/aga/src/chim/chim_world.c`, `MapBegin`.

## How it happened

The zone is taken when the frame map starts, from `AW_SceneryBegin` inside `SV_SpawnServer`,
before `ED_LoadFromFile` spawns the map's entities and before the client's per-map allocations. Its
size is limited to what the Hunk has left at that moment less `chim_reserve_kib`. What loads after
it is not counted: on Seyda Neen 978,288 bytes of actors and sprites, then 1,589,344 bytes of
per-map client allocations (the same on every map: 1,589,344 on Balmora and on the prison ship).

## Why it was not caught

Balmora, the only CHIM town run in FS-UAE before, loads little after the zone, and the reserve
check gave no line when it could not hold.

## Reproduction

As CHIM-SEYDA-HUNK-GAP-33.

## Repair

Proposed: the zone is sized so the safety holds after the map has loaded: the frame map states what
the map loads beyond the zone (a worldspawn figure the builder writes from its heap model), the engine
leaves room for it and says when the measured load turned out larger. The builder's heap gate checks
the same whole-map rule, read from `tools/engine_limits.py`.

Builder side, in source on v0.0.33-chim-format (9 October 2026), not shipped: every frame map states
`"_chim_hunk_rest"` (`chim.frame_map.hunk_rest`): the client's per-map Hunk, each sprite that is not
streamed plus 512 bytes, and a 24 KiB margin. The margin comes from the engine's measurements: after
the zone, Balmora loads 20,256 bytes and Seyda Neen 26,432 bytes beyond the client and the sprites,
including a 12,768-byte temporary block. Balmora's frame map has no sprites, so it states 1,613,920
bytes against the 1,609,600 measured. The first load then leaves the 2 MiB gap without having to
learn it (the gap warning seen on MiniWind #3), and Balmora keeps its full 6,864 KiB zone: one 16 KiB
step less and its active ring (6,239,776 bytes) would no longer fit, which a margin above about
26 KB would cause. Seyda Neen's figure is 1,856 bytes higher than its statement; the engine measures it
and keeps it after the first load. Tests: `tests/test_chim_frame_map.py`.

## Verification

Pending.

## Prevention

A host test that the zone leaves the stated room, and the FS-UAE heap audit on every CHIM town.

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
