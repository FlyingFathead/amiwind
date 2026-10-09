# CHIM-SEYDA-HUNK-GAP-33: Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM frame map of Seyda Neen (tools/chim/frame_map.py) and the engine's CHIM zone (chim_world.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Below the 2 MiB Hunk-gap safety, a larger load or a later allocation can run the Hunk out on Seyda Neen. |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source edd200f, engine edd200f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine edd200f, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open; measured. CHIM area: memory (zone and Hunk). Build: a test image, not a playtest: the verified
v0.0.32 release images with the CHIM engine of v0.0.33-chim-engine (7e61215 and later), the Seyda
Neen CHIM world `seyda-009` (format 0.5) and its frame map made by `tools/chim/frame_map.py` from the
release image's own region maps; engine defaults `chim_zone_kib` 6,864, `chim_pool_kib` 384.

## Symptom

The engine's heap audit after loading Seyda Neen on CHIM, on the A1200 profile (2 MiB Chip, 16 MiB
Fast, 11 MiB Hunk), every load:

| Map | Hunk low after the BSP | after actors | load peak | peak gap |
| --- | ---: | ---: | ---: | ---: |
| Seyda Neen CHIM (`seyda-chim.bsp`) | 825,744 | 8,832,768 | 10,434,880 | 1,099,456 |
| Balmora CHIM (`balmora-chim.bsp`) | 793,504 | 7,826,848 | 9,431,840 | 2,102,496 |
| Seyda Neen legacy region (`sn029`) | 5,144,832 | 5,497,696 | 7,109,616 | 4,424,720 |

The peak gap ends 997,696 bytes under the engine's 2 MiB safety, and the audit says so ("hunk-gap
safety below 2 MiB") on every load. Balmora on CHIM keeps the safety by 5,344 bytes.

## Where

The frame map `maps/seyda-chim.bsp` (`tools/chim/frame_map.py`) and the engine's CHIM zone
(`engine/aga/src/chim/chim_world.c`, `chim_zone_kib`).

## How it happened

Apart from the zone (7,028,736 bytes), Seyda Neen's CHIM map uses 3,406,144 Hunk bytes at its
peak, Balmora's 2,403,104. The difference is the frame map: it carries all of the town's statics
(229 flora sprites) and its actors at once, 978,288 bytes, where a legacy region map loaded its own
part (`sn029`: 352,864 bytes). The zone default was set on Balmora (CHIM-ZONE-BUDGET-33).

## Why it was not caught

The CHIM heap gate (`tools/chim/heap.py`) checks the ring against the zone only, not the whole
map's Hunk; the engine's own reserve check runs too early (CHIM-ZONE-RESERVE-EARLY-33); no FS-UAE
run had loaded Seyda Neen on CHIM before.

## Reproduction

Load `maps/seyda-chim.bsp` with the default zone and read the heap audit's "peak gap".

## Repair

Builder side, in source on v0.0.33-chim-format (9 October 2026), not shipped and not yet run in
the engine: the frame map's `aw_static` and `aw_flora` entities are tagged to stream with their
chunks (`"_chim_chunk"`, `"_chim_box"`, worldspawn `"_chim_streamed_statics"`), and the worldspawn
states `"_chim_hunk_rest"` without their models. The engine side (skip them at load, build them with
their chunk) is the engine job's. Modelled on `seyda-009` (`chim.heap.frame_map_heap`, the image
step's new frame-map heap gate):
- 229 statics stream in the town map (954,414 bytes of models); the Hunk after the zone drops from
  2,580,400 (measured) to 1,589,344 bytes, so the whole-map rule leaves the full 6,864 KiB zone;
- the models now sit in the ring's chunks, one copy per ring as the engine holds them: the active
  ring grows from 5,683,920 to 5,905,568 bytes, 303,968 bytes of headroom in the 6,209,536-byte
  chunk room (6,130,912 with a copy per chunk); the load ring (6,672,816 bytes) is best-effort
  cache, never locked.
- The engine job measured the two halves together: without streaming the whole-map rule shrinks
  Seyda Neen's zone to 5,889 KiB and chunks fail for room; streaming and the engine's support must
  ship together.

Earlier analysis: the largest zone the rule allows on Seyda Neen is 5,888 KiB (11,534,336 - 2,097,152 -
3,406,144 bytes, rounded down to 16 KiB). Levers, any of them:
- the town's sprite statics streamed with their chunks (the builder's deferred 0.5 static records)
  instead of all in the frame map;
- fewer faces in the ring (distance detail);
- a 12 MiB Hunk, if the whole game keeps enough Fast RAM (to be measured);
- the zone sized from what the map still loads (CHIM-ZONE-RESERVE-EARLY-33), which keeps the safety
  but makes the ring's room smaller.

### Measured with the whole-map rule, 9 October 2026

With the engine's whole-map rule (CHIM-ZONE-RESERVE-EARLY-33) and the 11 MiB heap, the first load of
Seyda Neen in a session takes the full zone (the frame map states no figure yet); the next load leaves
room for the measured 2,580,384 bytes and takes 5,889 KiB. The ring then no longer fits: chunks fail
for room ("model 60, 386,912 bytes; largest free 217,344") and are activated without the model
(`chim_partial 1`, the ground stays). With the town's sprite statics streamed by their chunks the
frame map states 1,589,344 bytes and the rule allows the full 6,864 KiB again, so the engine rule and
the builder's streamed statics have to ship together.

## Verification

Pending.

## Prevention

The builder's heap gate checks the whole map's Hunk against the 2 MiB safety, not only the zone
(stated through `tools/engine_limits.py`), and an FS-UAE load of every CHIM town reads the audit.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
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
