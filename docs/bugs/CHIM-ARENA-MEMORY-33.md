# CHIM-ARENA-MEMORY-33: The Vivec Arena does not fit the CHIM zone

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM Vivec Arena world: canton body models ex_vivec_c_02 and ex_vivec_c_04 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Blocks the Arena on CHIM (v0.0.33 scope): heap gate fails, and one model needs a 2.5 MB free run in the zone. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 27613e6, engine 27613e6, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 27613e6, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Performance. Found by the CHIM heap gate on the first Vivec Arena CHIM world (milestone M3,
stage A).

## Symptom

Heap gate on the Arena world. The chunk room is 6,242,304 bytes (6,864 KiB zone minus a 768 KiB
frame-world block).

| | Bytes | Positions over (of 2,304) |
| --- | ---: | ---: |
| Active ring peak | 6,492,688 | 60 |
| Load ring peak (892 units) | 6,734,704 | 271 |
| Largest single block (`ex_vivec_c_02`) | 2,514,432 | |

The world itself validates, and the stair gate passes: all 341 flight steps.

## Where

The canton body models of the Arena frame: `ex_vivec_c_02` (7,651 faces, 55,862 standing-hull
clipnodes) and `ex_vivec_c_04` (5,134 faces).

## How it happened

A canton body is one Morrowind mesh the size of a town district, so CHIM stores it as one placed
model. Its whole decoded block must be resident, and find a free run in the zone, whenever any part
of it is in the ring.

## Why it was not caught

The first CHIM towns have house-sized models (largest 478 KB).

## Reproduction

Build `--area vivec_arena` and run the heap gate.

## Repair

In source on v0.0.33-chim-format (34ef145, 9 October 2026), not shipped: the large-model cut
(`tools/chim/cut.py`, WORLD_FORMAT.md "Large-model cut"). A model wider than the area setting
`cut_models_over` is cut once in its own frame into chunk-sized tiles; every face and convex collision
piece goes whole to its tile, so polygons and solid are the model's, and the tiles are shared by all its
placements. Off by default; Vivec turns it on (512 local units).

Measured on the Arena frame with `--cut-models-over 512`: active ring 6,492,688 to 5,337,232 bytes (fits
the 6,242,304-byte chunk room with 905,072 to spare), largest block 2,514,432 to 450,704 bytes, stair gate
passed (3,533 steps), validator passed. Two other cut forms were measured and rejected as defaults:
clipping faces at chunk lines turned clipped slopes into false stair steps (8 failures), and cutting each
placement separately unshared the canton model (8,389,936 bytes). Both stay selectable (`cut_mode`).

## Verification

Pending.

## Prevention

The heap gate's largest-block figure is in every receipt.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec

<!-- END GENERATED CATEGORY -->
