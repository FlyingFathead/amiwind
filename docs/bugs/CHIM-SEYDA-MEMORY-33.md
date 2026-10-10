# CHIM-SEYDA-MEMORY-33: Seyda Neen's CHIM ring was modelled larger than Balmora's

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | CHIM chunk terrain standing hull (tools/chim/terrain.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Seyda Neen could not run on CHIM in the reference memory profile. |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 7e726c9, engine 7e726c9, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7e726c9, world format 0.5 |
| Unknown because | found in source on the CHIM branch; no CHIM world build |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Cause found and fixed in source on v0.0.33-chim-format (7e726c9), not shipped at the time of
writing. Performance.

## Symptom

The strict CHIM heap gate modelled Seyda Neen's largest active ring at 6,536,720 bytes, more than
Balmora's 6,239,776, for a much smaller town. The engine's chunk room is 6,096 KiB
(6,242,304 bytes): `chim_zone_kib` 6,864 minus a 768 KiB frame-world block.

## Where

`tools/chim/terrain.py` `chunk_terrain`: the standing hull of each chunk's ground.

## How it happened

Breakdown at the peak position (town centre, 32 active chunks, 91 models, 102 textures):

| Bytes in the ring | Routed hull | Compiled hull | Balmora's peak (routed) |
| --- | ---: | ---: | ---: |
| Terrain blocks | 1,496,384 | 643,584 | 300,864 |
| (terrain clipnodes) | (107,506) | (11,984) | (18,848) |
| Models | 4,534,672 | 4,534,672 | 5,637,424 |
| Textures | 432,480 | 432,480 | 200,160 |
| Catalogues | 73,184 | 73,184 | 101,328 |
| Total | 6,536,720 | 5,683,920 | 6,239,776 |

Format 0.5 builds Seyda Neen's ground from the scene stage's own triangles: shoreline samples, and
32 triangles per tile at the port. The 0.4 standing hull chains each triangle's expanded prism and
routes the chains per part of the chunk. With many small pieces, the routing repeats them: a port
chunk held 2,540-7,045 clipnodes.

## Why it was not caught

Balmora's ground has two triangles per tile; the routing was measured only there.

## Reproduction

Build Seyda Neen with `terrain_hull` 'routed' and run the heap gate.

## Repair

- The chunk's prisms, expanded exactly by the standing box, are compiled by qbsp into one BSP
  (`collision_bsp.compile_standing`, as for the models' exact unions), whenever the build has
  qbsp.
- The solid set is the same, and the validator's seam check passes. A port chunk now holds
  456-724 clipnodes, and a flat sea chunk 7 instead of 513.
- The routed chains stay selectable (`terrain_hull`), and they stay the default for a regular
  grid. On Balmora the compiled hull made the stair gate fail one more step: ref 32841, a walk down
  that starts 0.03 units inside a gentle slope at a chunk edge. The compiled hull is the default
  only for irregular ground, where it is the fix.
- The compiled hull's corner lattice stays 1/64, as for the models. At 1/1024, qbsp left slivers,
  and the irregular-ground test found seam holes.
- Seyda Neen's whole terrain on disk: 9.6 MB to 3.9 MB.

Models are now 80 % of the ring. Per model, about 125 bytes per face: the surface (48), nearly one
texinfo per face (44) and its plane (20). Sharing texinfos (as the legacy
`AMIWIND_TEXINFO_SNAP` does) is the next lever; it is not taken without an A/B of the texture
mapping.

## Verification

Heap gate on the Seyda Neen world: peak 5,683,920 bytes, passed, 558,384 bytes of headroom. The
validator, stair gate and frame maps also pass. Pending: the engine's measured locked bytes at the
same position.

## Prevention

`tests/test_chim_ground.py` `CompiledTerrainHullTests`: the compiled hull stands the box at the same
heights as the routed one and uses fewer clipnodes.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
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

- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge

<!-- END GENERATED CATEGORY -->
