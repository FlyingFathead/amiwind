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

_Last updated with AmiWind v0.0.43 (19 October 2026)._

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

- AKULAKHAN-CHAMBER-32MB-STALL-53 (no report page): Akulakhan's Chamber loads three times at 32 MB Fast RAM
- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- CHIM-HEAP-GATE-NONRING-16MB-54 (no report page): At 16 MB the CHIM zone is 6,591 of 6,596 KiB locked: the heap gate predicts only the active ring and misses the chunk index, loading buffer, frame world and streamed statics
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
- SMOKE-16MB-MAPLOAD-54 (no report page): Below the 32 MB requirement: at 16 MB Fast RAM the boot smoke loads no map (dbg tp to Seyda Neen)
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- WORLD-FLORA-HEAP-010 (no report page): Seyda sprite payload exceeds the final map heap headroom

Related bugs in other categories:

- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units

<!-- END GENERATED CATEGORY -->
