# CHIM-COLLISION-UNION-FALLBACK-41: Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 16 October 2026, in v0.0.41-dev3 |
| Where | CHIM region frames near Hla Oad: (-8,-5) (-8,-4) (-7,-5) (-7,-4) (-6,-4) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41-dev3 (last seen) |
| Severity | high: five ring-3 cells stay out of CHIM; any cell with large irregular ruins can hit it |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev3_full-rings0123-r3_b00e9c4 |
| From commit | source b00e9c4, engine b00e9c4, CHIM world b00e9c4 |
| CHIM engine version | CHIM 0.2.0, engine b00e9c4, world format 0.7 |
| Platform or emulator | not in game (the CHIM heap gate refuses the frames at build time) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43 (19 October 2026)._

## Symptom
The v0.0.41-dev3 build refused three ring-3 cells at the CHIM heap gate: frames (-8,-5),
(-8,-4) and (-7,-5) need 7,048,640 to 7,298,624 bytes against a 6,242,304-byte zone. They
stayed in the classic world, and so did their neighbours (-7,-4) and (-6,-4), left out so that no
classic cell is enclosed by CHIM cells. A five-cell rebuild (16 October 2026) peaks at 7,079,104
to 7,320,256 bytes.

## Where
The Daedric ruin of Ashurnibibi, Bitter Coast near Hla Oad. Five `ex_dae_ruin_*` meshes hold
67 % of the worst frame's peak. Their bytes are mostly collision, not drawn geometry:

| Model | Image bytes | Planes | Hull clipnodes | Nodes | Faces lump |
| --- | --- | --- | --- | --- | --- |
| `ex_dae_ruin_03` | 1,100,088 | 632,020 | 200,048 | 118,704 | 35,000 |
| `ex_dae_ruin_01` | 1,003,968 | 552,920 | 179,216 | 109,896 | 36,980 |
| `flora_bc_tree_02` (for scale) | 51,300 | 13,880 | none | 2,472 | 9,720 |

About 31,000 planes for about 1,750 drawn faces.

## How it happened
A large model's standing hull is compiled into one compact tree from its convex collision pieces
(`collision_bsp.compile_standing_checked`, the model's collision optimizer). For `ex_dae_ruin_01`,
`ex_dae_ruin_03` and `ex_dae_ruin_04_skew_02` that compile failed, and the converter kept the raw
chain of convex pieces (`collision_union_fallbacks` in the CHIM receipt). The irregular ruin surfaces
split into thousands of small pieces (`mesh_geometry.collision_parts`, 2-unit tolerance), each with its
own planes. The heap fallback then kept six ruin meshes as chains (`hull_fallback.kept_as_chain`).
The compile fails because qbsp refuses the brushes: `CheckFace: Found a non-convex face` (error size
0.01 to 28 units). A piece's hull comes from `ConvexHull`, which triangulates every flat side; the
triangles' normals differ by rounding, so one side was written as several almost identical planes and
qbsp made sliver faces of them. The receipt recorded only the mesh, and the stored error text was the
last 200 characters of qbsp's output, which were warning lines.

## Why it was not caught
- The heap report counts planes and nodes as "models_drawn"; only clipnodes count as collision, so the
  report pointed at drawn geometry and the mesh optimizer.
- A union fallback is listed in the receipt but is not an audit finding, and its error text is not
  recorded (it should name the mesh, its input hash and the check that failed).
- The tracker's memory-fit audit passed these cells while the build's heap gate refused them.

## Reproduction
`tools/chim_build.py --chim-regions-cells "-8,-5:l -8,-4:l -7,-5:l -7,-4:l -6,-4:l"` with
`--validate --sdk` at 87f6534: the CHIM heap gate fails on frame x-08/y-05 with 7,079,104 bytes.

## Repair
- Every fallback is logged and recorded with its reason (`collision_union_fallback_reasons` in the CHIM
  receipt: mesh, variant, packet SHA-256, error); a compile error leads with qbsp's exit code and error lines.
- `collision_bsp.compile_standing_checked`: a hull refused with a non-convex face is compiled once more with
  near-coplanar facets merged (qhull `C-0.01`). Hulls that compiled before are unchanged (same brushes, same
  cache key); the retry passes the same standing check (exactness against the pieces, hole patch).

Measured on the five cells (16 October 2026): no fallbacks left; frame peaks 5,878,528 / 5,882,688 /
6,119,680 / 6,116,944 / 2,258,560 bytes, all under the 6,242,304-byte zone; 10 compiled hulls checked,
0 inexact; validation passed; stair gate 8,202 steps and ramps, 0 failed. The dev4 world had 24 meshes
with this fallback (Dwemer ruins, Holamayan, a stronghold pylon, Telvanni and Vivec pieces); all take the
retry in the next build.

The mesh optimizer on every mesh does not help: it leaves the ruins as they are and makes merged
flora larger (frame x-07/y-04 peak 7,320,256 to 9,052,640 bytes).

## Verification
Builder side done (above). Pending: the five cells in a playtest build, and the ruin walked in game.

## Prevention
CHIMport cells report every collision union fallback as a finding with its reason, and the heap report
splits collision planes and nodes from drawn geometry. Guide: [CHIMport, when a cell does not fit](../chim/CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- [CHIM-LAVA-HUNK-GAP-38](CHIM-LAVA-HUNK-GAP-38.md): Lava MiniWind first presentation falls below the 2 MiB hunk-gap safety
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
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

<!-- END GENERATED CATEGORY -->
