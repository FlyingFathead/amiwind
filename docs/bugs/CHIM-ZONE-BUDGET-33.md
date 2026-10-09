# CHIM-ZONE-BUDGET-33: The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | CHIM engine zone default (chim_world.c chim_zone_kib) and builder heap gate (chim/heap.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: The active ring of Seyda Neen and Balmora's south-west corner exceeds the default CHIM zone. |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source fca02e9, engine fca02e9, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine fca02e9, world format 0.5 |
| Unknown because | found in source on the CHIM branch; no CHIM world build |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
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

## Status: 8 October 2026

Open; performance. Found by the strict CHIM heap gate (`tools/chim/heap.py`) on the first Seyda Neen
world (milestone M2) and on Balmora's format 0.5 world, both built from the owner's own data.

## Symptom

The gate computes, at player positions every 64 units, what the engine's active ring needs at
once. The ring is the chunks whose box lies within the view distance plus hysteresis of the
player (`chim_chunks.c`: `Distance`, `ChimChunks_ActiveRadius`); the gate adds their terrain
blocks, the models they place, those models' textures and the chunk catalogues. Blocks are sized
as `AW_BrushBound` sizes them, with the target ABI. The decoded size is 1.31 times the disk
bytes, as the engine's own "CHIM: bound" log lines show (1.25-1.31). With the engine default
`chim_zone_kib` 6,656 KiB minus two 512 KiB frame-world slots (5,767,168 bytes):

| World | Peak | Where | Positions over budget | Benchmark cameras |
| --- | ---: | --- | ---: | --- |
| Seyda Neen | 6,536,720 B | town centre (224, -32) | 187 of 7,056 | 1, 2, 5 over (6.1-6.4 MB); 3, 4 under |
| Balmora | 6,239,776 B | south-west corner (-672, -672) | 36 of 9,216 | all 5 under (3.3-4.8 MB) |

FS-UAE runs of Balmora (the cameras and the street loop) showed no shortage, which fits: none of
them visits the south-west corner.

## Where

Engine `chim/chim_world.c` (`chim_zone_kib`), builder `tools/chim/heap.py` (`ZONE_KIB`).

## How it happened

The zone size was tuned on Balmora's walk (CHIM-ZONE-RING-THRASH-33) before a gate looked at
every position. Seyda Neen packs the ship, the silt strider and most of its 91 models into the
ring at the town centre.

## Why it was not caught

No heap gate covered CHIM worlds before format 0.5.

## Reproduction

`tools/chim_build.py --area seyda ... --validate --sdk SDK` with `ZONE_KIB` 6656: the heap gate
fails and names the position.

## Repair

Proposed, owner decision pending:
- Interim (option A): a 7,680 KiB zone. The builder's `ZONE_KIB` is 7,680 and the engine cvar
  default must follow; a test checks that they agree. Seyda Neen then has 279,024 bytes of
  headroom, Balmora 575,968.
- Design (option B): the builder writes each world's required bank into `world.cwi`, the
  engine allocates that bank, and the gate checks it against the Hunk the map leaves.

## Verification

Pending: the engine default changed and FS-UAE runs at the peak positions.

### Measured: the Hunk room around the zone, 9 October 2026

FS-UAE (A1200 profile, 2 MiB Chip + 16 MiB Fast, 11 MiB Hunk), the verified v0.0.32 release
images with the CHIM engine of v0.0.33-chim-engine and B's CHIM worlds (Balmora `balmora-008`,
Seyda Neen `seyda-009`; frame maps built by `tools/chim/frame_map.py` from the release image's
own region maps), engine defaults `chim_zone_kib` 6,864 and `chim_pool_kib` 384. The engine's
heap audit after loading (peak = the load peak; the gap is what the Hunk has left):

| Map | Hunk low after the BSP | after actors | load peak | peak gap | Fast RAM free (largest) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Balmora CHIM (`balmora-chim.bsp`) | 793,504 | 7,826,848 | 9,431,840 | 2,102,496 | 1,432,320 (1,400,176) |
| Seyda Neen CHIM (`seyda-chim.bsp`) | 825,744 | 8,832,768 | 10,434,880 | **1,099,456** | 1,432,320 (1,399,168) |
| Seyda Neen legacy region (`sn029`) | 5,144,832 | 5,497,696 | 7,109,616 | 4,424,720 | 1,533,432 |
| Prison ship (`prison`, no zone) | 4,583,232 | 4,590,560 | 6,336,464 | 5,197,872 | 1,531,336 |
| Census and Excise Office (no zone) | 3,223,984 | 3,235,024 | 4,824,368 | 6,709,968 | 1,531,336 |
| Caius Cosades' house (no zone) | 1,845,968 | 1,848,448 | 3,448,832 | 8,085,504 | 1,531,336 |

The zone (7,028,736 bytes) is taken from the Hunk when a CHIM map starts and goes back at the next
map change; maps without a frame take none, so the ship and interiors do not limit it. Apart from
the zone, Balmora's CHIM map uses 2,403,104 Hunk bytes at its peak and Seyda Neen's 3,406,144:
Seyda's frame map carries all of the town's statics (229 flora sprites) and actors at once, where
a legacy region map carried its own part (`sn029`: 352,864 bytes for actors and statics, against
978,288 for the whole frame map). So the largest zone that keeps the engine's 2 MiB Hunk-gap
safety (11,534,336 - 2,097,152 - the map's other Hunk use, rounded down to 16 KiB):

- Balmora CHIM: 6,864 KiB (the default; 5,344 bytes to spare);
- Seyda Neen CHIM: 5,888 KiB. With the default 6,864 KiB the gap ends at 1,099,456 bytes, under
  the safety by 997,696, and the heap audit warns ("hunk-gap safety below 2 MiB") on every load;
- the ship and the interiors: not limited by the zone (no zone on those maps).

A zone of about 7.7 MB keeps the safety on neither town. `chim_reserve_kib` (2,048) does not
prevent this: it is checked when the zone is taken, before the frame map's actors, sprites and
precaches load. Fast RAM left about 1.40 MB in one piece on both towns, so one more MiB of Hunk
(`AMIWIND_HEAP_MB` 12) would fit with about 350 KB of Fast RAM to spare; untried.

### Measured: sharing texture mappings saves almost nothing, 9 October 2026

Faces' texture mappings (texinfo, 40 bytes on disk, 44 decoded) are about 38 of a face's bytes in
the ring. The builder already stores each mapping once per model (`tools/chim/models.py`
`texinfo_index`); what remains is distinct because Morrowind's UVs give almost every triangle its
own mapping. Over the worlds above and the Vivec Arena (`arena-001`):

| World | Texinfo per face | Distinct if shared per sector | Distinct if shared world-wide |
| --- | ---: | ---: | ---: |
| Balmora | 0.86 (86,395 records) | 98.6 % | 97.2 % |
| Seyda Neen | 0.63 (23,884 records) | 96.6 % | 95.4 % |
| Vivec Arena | 0.88 (31,811 records) | 97.2 % | 89.5 % |

An exact shared table saves 1.4-4.6 % of the texinfo of Balmora and Seyda Neen (under 1 % of
the ring's bytes) and 10.5 % in the Arena: not worth a format change. Rounding the mappings
changes the pixels and saves little (axes to 1/64 and offsets to 1 texel: about 7 % fewer; even a
visibly wrong 1/8 and 4 texels: 27 % in Balmora, 11 % in Seyda Neen). Unmeasured option: drop the
decoded `mipadjust` (44 to 40 bytes, about 9 % of texinfo; computed when needed, same pixels).
The levers that remain are fewer faces (distance detail) and the Hunk itself.

## Prevention

The strict heap gate runs on every CHIM build (`--builder chim`).

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

- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes

<!-- END GENERATED CATEGORY -->
