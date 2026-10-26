# CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43: two Bitter Coast CHIM frames over the heap zone after the trunk shape guard

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 19 October 2026, in v0.0.43-dev4 |
| Where | Bitter Coast frames x-07/y-04 and x-08/y-04 (CHIM heap gate, dev4 try 6) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.44 |
| Severity | high: the build stops at the CHIM heap gate; no image |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.43-dev4_full-batch5-try6_b668b759 |
| From commit | source b668b75, engine b668b75, CHIM world b668b75 |
| CHIM engine version | CHIM 0.2.1, engine b668b75, world format 0.7 |
| Platform or emulator | build (CHIM heap gate) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev4 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 19 October 2026](#status-19-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 19 October 2026

Cause found; fixed in source on the v0.0.43 line, not yet in a build. The next dev4 build checks it at the CHIM
heap gate.

## Symptom

The v0.0.43-dev4 full build stopped at the CHIM heap gate, about 41 minutes in:

```text
CHIM heap gate failed: 2 frame(s) over the zone of 6242304 bytes (6864 KiB zone minus 2 x 384 KiB
frame-world slots): frames/x-07/y-04/frame.ccf needs 6357856 bytes ... over by 115552 bytes (113 KiB, 1.9 %);
frames/x-08/y-04/frame.ccf needs 6355024 bytes ... over by 112720 bytes (110 KiB, 1.8 %)
```

## Where

Two Bitter Coast CHIM frames, x-07/y-04 and x-08/y-04, at their peak ring positions (-928, -672) and
(1120, -672). In v0.0.43-dev3 the same frames passed with 72 KiB and 75 KiB to spare.

## How it happened

Only one part of the peak grew: the drawn models, by 187,296 bytes in both frames. The terrain, collision,
placement records and textures are the same as in dev3, and the ring holds the same 165 models. Comparing
the two builds' frames model by model, the changed models are the Bitter Coast trees (`flora_bc_tree_01` to
`_05`, at every placement scale). Each grew by about 60 %: for example, `flora_bc_tree_04` went from 13,900 to
18,720 bytes in its first lump, with more faces and edges.

The growth comes from the fix for
[CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md). That fix guards the height of every large
part of a flora mesh: when the reduced copy of a trunk keeps less than 90 % of its height, the part is reduced
again with the boundary-locked reducer, or kept as in the source when that fails too. The guard applies to
every `flora_` mesh, not only Azura's Coast trees. The Bitter Coast tree trunks fail the first check, so they
took the boundary-locked copy, which keeps every rim edge and is much heavier.

## Why it was not caught

The guard was measured over the v0.0.43-dev2 world's reduced meshes (+5.3 % triangles per model), but not
against the heap of the frames that hold the most of the changed meshes. The two Bitter Coast frames were
already within 75 KiB of their zone.

## Reproduction

Always: a full build with the v0.0.43-dev4 cell list and the dev3 shape guard stops at the CHIM heap gate on
both frames.

## Repair

The guard now tries the same reducer again before it falls back to the boundary-locked one. A part that loses
its height is reduced again at 1.5, 2, 3 and 4 times its target, smallest first, and the first copy that keeps
90 % of its height is used. Only when none does, the boundary-locked retry and then the source copy follow as
before (`tools/static_lod.py`, `SHAPE_GUARD_STEPS`; the flora profile in `tools/town_regions.py` sets it).
The previous guard stays selectable: a profile without `lod_shape_guard_steps` goes straight to the locked
retry.

Measured on the original meshes, triangles after reduction, old guard and new guard:

| Mesh | Source | Old guard | New guard | Change | Bark height kept |
| --- | ---: | ---: | ---: | ---: | --- |
| `flora_bc_tree_01` | 1,743 | 730 | 542 | -26 % | 93 % |
| `flora_bc_tree_02` | 1,688 | 716 | 553 | -23 % | 93 % |
| `flora_bc_tree_03` | 1,316 | 366 | 252 | -31 % | 93 % |
| `flora_bc_tree_04` | 1,376 | 381 | 222 | -42 % | 93 % |
| `flora_bc_tree_05` | 1,461 | 549 | 434 | -21 % | 97 % |
| `flora_bc_tree_06` | 1,339 | 201 | 169 | -16 % | 97 % |
| `flora_bc_tree_07` | 1,453 | 509 | 365 | -28 % | 93 % |
| `flora_tree_ac_01` | 1,672 | 161 | 161 | 0 % | 100 % |
| `flora_tree_ac_02` | 1,018 | 123 | 128 | +4 % | 100 % |

The other Bitter Coast trees (`_08` to `_12`) do not change. Over these 14 trees: 4,376 triangles with the old
guard, 3,466 with the new one (-21 %). The Azura's Coast trees, the reason for the guard, keep their full trunk
height.

## Verification

- `tests/test_static_lod.py`: the stepped retry is used before the locked one and stops at the first copy that
  fits; a profile without steps is the previous guard; the flora profile sets the steps. With the tester's own
  Morrowind data, `flora_tree_ac_01` still keeps over 90 % of its trunk height.
- To do: the next v0.0.43-dev4 full build passes the CHIM heap gate on both frames, and an in-game look at the
  Bitter Coast trees and at Azura's Coast (cells 16,7 and 16,9).

## Prevention

A change to a shared reducer profile is checked against the CHIM heap gate's tightest frames, not only against
the total triangle count, before it is merged.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan s Chamber (the Heart Chamber) ends the game: a model of its room store does not load, and the engine stops with Host_Error instead of refusing at the door
- [CHIM-SEYDA-HUNK-GAP-33](CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map leaves less than the 2 MiB Hunk-gap safety at the default zone
- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull
- [CHIM-STRIDER-RING-33](CHIM-STRIDER-RING-33.md): The closed-hull strider (MESH-LOD-OPEN-SEAMS-33, variant E) puts CHIM Balmora's active ring over the heap budget
- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner
- [CHIM-ZONE-RESERVE-EARLY-33](CHIM-ZONE-RESERVE-EARLY-33.md): chim_reserve_kib is checked before the map's actors and precaches load, so it cannot keep the Hunk gap
- CRASH-01 (no report page): Heap exhaustion on sn012 after Hors travel from Jiub name entry
- [ENGINE-HEAP-FIXED-SIZE-43](ENGINE-HEAP-FIXED-SIZE-43.md): The game heap is a fixed 11 MiB from the build: with 128 MB of RAM Vivec still runs under the 2 MiB safety gap and loads pause
- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HEAP-12MB-FAST-ROOM-33](HEAP-12MB-FAST-ROOM-33.md): A 12 MiB game heap leaves 342 KB of Fast RAM in one block: the guard torch's 1 MiB probe can never pass
- [HEAP-MODEL-SUM-32](HEAP-MODEL-SUM-32.md): Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)
- HUNK-RESERVE-SN012-29 (no report page): Dev4 first-presented sn012 reserve below 2 MiB target
- [LOADER-STAGING-PEAK-32](LOADER-STAGING-PEAK-32.md): Map loading stages most lumps in temporary memory before decoding, raising the heap peak
- [MAP-UNUSED-HULL2-32](MAP-UNUSED-HULL2-32.md): Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses
- MEM-GEOMETRY-01 (no report page): Light-range sharing could copy a too-short byte span
- MEM-TOWN-02 (no report page): Bounded Balmora maps exceeded the modeled map heap limit
- [NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md): Full animation kit models are 2.2 times the idle models; four Balmora residents exceed the 512 KiB alias staging buffer
- [RAM-REQUIREMENT-32MB-48](RAM-REQUIREMENT-32MB-48.md): 16 MB of Fast RAM no longer holds the whole game: 32 MB is the safe minimum, 16 MB starts with a warning
- ROOM-AKULAKHAN-HEAP-52 (no report page): Akulakhan s Chamber needs 18.8 MB for its models and textures with its activators kept: more than the 14.3 MB the 32 MB minimum gives a room, so the image step stops
- SDK-MALLOC-TRAPS-52 (no report page): The toolchain's malloc never returns NULL: a failed allocation stops the game with Software Failure #80000027 (TRAP #7); 45 engine malloc sites test for a NULL that cannot come
- SKEL-HEAP-ACCOUNTING-52 (no report page): Audit: every heap and size estimate of actor models must count a skeletal model s block (16 bytes a vertex) and its shared table
- SKEL-TABLE-SHARED-FEMALE-52 (no report page): The female animation table repeats the common table whole for its three own groups: 561 KB of Fast RAM, kept all session
- SKEL-TABLE-SIZE-52 (no report page): The shared humanoid animation table is 4.3 MB held in RAM: all 61 skeleton nodes at 15 frames a second, too much beside the game on 16 MB
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it

<!-- END GENERATED CATEGORY -->
