# CHIM-LAVA-HUNK-GAP-38: lava scene hunk reserve

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 12 October 2026, in v0.0.38-dev1 |
| Where | Lava CHIM exterior first presentation |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | fixed in v0.0.38 |
| Severity | medium: Native hunk gap 2004064 bytes is 93088 bytes below the 2 MiB safety threshold |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | lava-pools MiniWind |
| From commit | source 7e7a467, engine 7e7a467, CHIM world 74c1595 |
| CHIM engine version | CHIM 0.2.0, engine 7e7a467, world format 0.7 |
| Build note | Pinned lava image boots and remains running; first-presentation memory warning requires review |
| Platform or emulator | FS-UAE 3.1.66 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43 (19 October 2026)._

## Symptom

First presentation reports a hunk gap of 2,004,064 bytes, 93,088 bytes below the 2 MiB safety threshold. The scene boots and remains running; this is a memory reserve warning, not an observed crash.

## Where

The lava-pools exterior MiniWind, source 7e7a467, in FS-UAE 3.1.66.

## How it happened

A second native run reproduces the cold peak with 108,384 bytes in the high hunk. Once the temporary block is released, the gap rises to 2,112,448 bytes. A warm reload has a peak gap of 2,112,256 bytes with the same stated zone. A fresh control with quick-character voice disabled keeps the first-presentation peak gap at 2,112,448 bytes. The 108,366-byte character greeting goes through AmiQuake S_LoadSound and COM_LoadStackFile; its temporary allocation including alignment and header is exactly 108,384 bytes. This identifies startup voice staging as the missing reserve component. Disabling voice is diagnostic only, not the repair.

## Why it was not caught

The offline CHIM zone heap audit passed. It does not establish the final native hunk gap after all scene allocations.

## Reproduction

Boot the lava-pools MiniWind and enter the scene. Read the first-presented heap snapshot: low 9,421,888, high 108,384, peak 9,530,272 of 11,534,336 bytes. Reproduced on a second fresh play copy; warm reload does not reproduce the cold peak.

## Repair

Candidate frame generation adds the largest quick-character WAV temporary buffer when the packaged configuration enables skip-census. It follows AmiQuake S_LoadSound stack fallback, 16-byte payload alignment and hunk header, reusing the existing frame reserve mechanism. It preserves voice, heap size and the safety threshold. The configuration and audio content hashes participate in cached frame identity. Native voice-on and ring-fit validation remain pending.

## Verification

Boot and scripted scene survival passed for 57 seconds, then a second first-load/reload diagnostic passed for 62 seconds. That does not establish memory safety, normal collision, lava damage or visual parity with the original.

## Prevention

Bind native first-presentation reserve measurements to the exact packaged image as well as the offline ring audit.

## Evidence update: 2026-10-12 13:44 UTC

Open from **v0.0.38-dev1**; tracked since **2026-10-12**.
Proposed update in **v0.0.38-dev2**, recorded 2026-10-12 13:44 UTC.
History clarified 2026-10-12 13:56 UTC: the scoped evidence below does not close the issue.
Later regressions remain attached to this history and require fresh verification.

Implementation present from v0.0.38-dev2; proposed repair evidence: startup WAV scratch reserve integrated. Scoped voice-on native cold peak gap 2112448 bytes and warm2220640 exceed2097152; cold margin15296. No observed chunk failure or partial activation. Wider cell/performance and maintainer acceptance remain open.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AKULAKHAN-CHAMBER-32MB-STALL-53 (no report page): Akulakhan's Chamber loads three times at 32 MB Fast RAM
- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-CACHE-SURFCACHE-SQUEEZE-57](CHIM-CACHE-SURFCACHE-SQUEEZE-57.md): The larger surface cache took its memory from the CHIM cache: 7 MiB to 5 MiB at 32 MB Fast, and two gate smokes saw the CHIM zone full
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
- CHIM-HEAP-GATE-NONRING-16MB-54 (no report page): At 16 MB the CHIM zone is 6,591 of 6,596 KiB locked: the heap gate predicts only the active ring and misses the chunk index, loading buffer, frame world and streamed statics
- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included
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

<!-- END GENERATED CATEGORY -->
