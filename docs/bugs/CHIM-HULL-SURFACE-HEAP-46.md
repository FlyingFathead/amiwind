# CHIM-HULL-SURFACE-HEAP-46: the walkway collision fix put six frames over the CHIM zone

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 20 October 2026, in v0.0.46-dev1 |
| Where | CHIM heap gate, v0.0.46-dev1: x+17 y+04, x-07 y-04, x-08 y-04, x-11 y+15, x+09 y+02, x+18 y+04 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.46 |
| Severity | high: the full build stops at its CHIM heap gate; no dev1 image |
| Family | Map heap and memory budget (`heap-memory`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_20_v0.0.46-dev1_dev1_f5a1404a |
| From commit | source f5a1404, engine f5a1404, CHIM world f5a1404 |
| CHIM engine version | CHIM 0.2.1, engine f5a1404, world format 0.7 |
| Platform or emulator | not in game (a builder gate stops the build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

<!-- contents start -->
## Contents

- [Status: 20 October 2026](#status-20-october-2026)
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

## Status: 20 October 2026

Fixed in v0.0.46. The maintainer checked the v0.0.46-dev1 playtest on the evening of 20 October 2026: "the heap fix btw IS GOOD".
The text below is the state before the full build.

Cause measured and fixed in the shared converter (not yet in a full build): all six frames fit again in a build of
the problem cells and their neighbours, with the walkway fix kept. Verification waits for the next full build.

## Symptom

The v0.0.46-dev1 build stopped at its CHIM heap gate after 2 h 38 min: six frames over the zone of 6,242,304 bytes
(6,864 KiB minus the two 384 KiB frame-world slots). v0.0.45 passed with the same 1,348 cells.

| Frame | v0.0.45 peak | v0.0.46-dev1 peak | Over by |
| --- | --- | --- | --- |
| x+17 y+04 | 6,164,848 | 6,416,944 | 174,640 |
| x-07 y-04 | 6,223,088 | 6,377,184 | 134,880 |
| x-08 y-04 | 6,220,256 | 6,374,352 | 132,048 |
| x-11 y+15 | 6,195,664 | 6,365,872 | 123,568 |
| x+09 y+02 | 6,040,160 | 6,294,944 | 52,640 |
| x+18 y+04 | 6,021,712 | 6,273,792 | 31,488 |

## Where

The CHIM model builder's convex collision pieces (`tools/mesh_geometry.py` `collision_parts`) of the 484 meshes in
`config/collision-hull-surface.json`: rocks, Telvanni roots and buildings, Daedric and Dwemer ruins, shacks. Every
CHIM frame that places them; 1,196 of the 1,351 frames grew, none shrank.

## How it happened

The fix for [CHIM-VIVEC-DOCK-WALKWAY-43](CHIM-VIVEC-DOCK-WALKWAY-43.md) gave each convex piece of those meshes the
hull of ALL its points whenever the hull of its 14 extreme points left any source point more than 0.5 units outside:
walls, undersides and cliff faces too, not only the surface a player stands on. Every corner of a rock then became a
hull corner. In a placed model each hull facet costs a plane, a node of the point hull and standing-hull clipnodes,
in every scaled or tilted copy of the mesh. `terrain_rock_bc_18` at scale 1: planes 114 to 454, nodes 22 to 167,
clipnodes 28 to 243, faces unchanged (64). Over the whole world the stored model bytes grew by 54.9 MB drawn
(planes and nodes count there) and 10.9 MB collision; the mean active-ring model memory by 14 % (777,716 to
886,955 bytes).

Measured, not guessed: the problem cells and their pocket neighbours (42 frames) built with the CHIM stage alone
(`tools/chim_build.py --chim-regions-cells ... --validate --stats`, the dev1 options) with the walkway rule off
(`AMIWIND_COLLISION_HULL_POINTS=extremes`) are within -5 to +7 KB of v0.0.45 in every frame (x+17 y+04: 6,171,792;
x-07 y-04: 6,218,288). The other changes since v0.0.45 (the scenery root rule, the fog cuts, region weather, the
torch and the reuse keys) account for those few KB.

## Why it was not caught

The walkway fix estimated its memory from the standing-hull bytes alone (clipnodes): at most 110,272 more bytes at a
frame peak, no frame over budget, on the v0.0.43-dev2 world. The planes and the node tree a hull facet adds to every
placed model were not counted, and the estimate was not repeated on the current world before the full build. The
heap gate itself caught it, but only at the end of a 2 h 38 min stage.

## Reproduction

Build the six frames and their neighbours with the CHIM stage alone from the v0.0.46-dev1 commit (f5a1404a), with
and without `AMIWIND_COLLISION_HULL_POINTS=extremes`, and compare `chim-heap.json` (peak bytes) and `chim-stats.json`
(`models.per_model` bytes by name).

## Repair

1. **Hold the walkable surface, not every point** (`mesh_geometry.surface_hull`): a piece whose extreme-point hull
   leaves a point of its walkable faces (normal z at least 0.7, the points the collision surface gate measures) more
   than 0.5 units deep gets those points added, for every hull facet the farthest one beyond it, until none is. The
   sides keep the reduced hull every other mesh has. On the meshes of the six frames: hull facets 32,152 (extreme
   points), 40,926 with the new rule; the rule as first shipped about twice the extreme points.
2. **Faces the stair rules leave deep become plates** (`mesh_geometry.collision_pieces`): where the stair rules then
   change a piece and leave a walkable face more than a step over the pieces (`ex_dae_ruin_entry.max`, one point 49.7
   units after the slanted-riser cut), those faces become authored plates with exact bevels; every point of the
   pieces only if that does not hold them.
3. **Scaled copies of collision-free meshes merged** (`chim.build.snap_scales`; builder switch `--scale-snap on|off`,
   `AMIWIND_SCALE_SNAP`): a placement of a mesh without collision pieces takes the nearest 0.1 of scale, so its
   copies share one model. This changes what is drawn (at most 5 % of the size at scale 1); nothing to collide with.
   Kelp at the Khuul coast was one model per scale two decimals apart. On by default because x-11 y+15 does not fit
   without it: 6,282,384 bytes, over by 40,080 (every other frame fits without it; x+17 y+04 with 10,480 headroom).
   Whether to keep it on is a decision for the maintainer.
4. **`ex_dae_ruin_02_skew` with coarser collision pieces** (the `everywhere-v1` recipe, `collision_tolerance` 4):
   172 to 100 pieces, its walkable surface within 0.05 units of them, drawn unchanged. The mesh is the Daedric ruin
   of cells -9,-4 and -8,-4 on the Bitter Coast (frames x-09 y-04 and x-08 y-04). Without it x-07 y-04 needs
   6,264,336 bytes (over by 22,032) and x-08 y-04 6,261,504 (over by 19,200). The stair walk of the 42 frames is the
   same with and without it (x-08 y-04: 25 ramps passed, 67 advisory, 1 step passed, 4 advisory both ways; no gate
   failure).

The rule as first shipped stays selectable for A/B tests: `AMIWIND_COLLISION_HULL_POINTS=table-whole`.

Peaks in the 42-frame build (bytes; budget 6,242,304):

| Frame | v0.0.45 | v0.0.46-dev1 | Walkway rule off | Repair 1-2 | Repair 1-4 | Headroom |
| --- | --- | --- | --- | --- | --- | --- |
| x+17 y+04 | 6,164,848 | 6,416,944 | 6,171,792 | 6,232,240 | 6,208,560 | 33,744 |
| x-07 y-04 | 6,223,088 | 6,377,184 | 6,218,288 | 6,271,344 | 6,205,408 | 36,896 |
| x-08 y-04 | 6,220,256 | 6,374,352 | 6,215,456 | 6,268,512 | 6,202,576 | 39,728 |
| x-11 y+15 | 6,195,664 | 6,365,872 | 6,199,376 | 6,284,592 | 6,217,088 | 25,216 |
| x+09 y+02 | 6,040,160 | 6,294,944 | 6,043,056 | 6,222,544 | 6,222,544 | 19,760 |
| x+18 y+04 | 6,021,712 | 6,273,792 | 6,028,224 | 6,088,672 | 6,064,992 | 177,312 |

Every one of the 42 frames is at or under its v0.0.46-dev1 peak, and the collision surface gate passes every mesh
(no walkable collision more than a step under its pieces).

Island-wide, measured per mesh (each of the 480 table meshes the build converts, stored once, its convex pieces
by `collision_parts`): hull facets 72,470 with the extreme points, 129,016 with the rule as first shipped (+78 %),
91,548 with the walkable-surface rule (+26 %): two thirds of the added planes are gone. The stored bytes of the
whole world (every scaled and tilted copy) and the frames grown or shrunk over all 1,351 frames come from the next
full build; the 42-frame build has them for its frames only.

The walkway itself: `ex_v_dock_01` with the build's profile has 21 pieces (17 with the extreme points, 22 with
every point) and its planks lie 0.0 units over them (19.4 with the extreme points): the player stands on the planks
as with the fix as first shipped.

The stair walk of the 42 frames passes (no gate failure; advisory: 1,848 against 1,839 with the rule as first
shipped and 2,040 with the walkway rule off; failed steps 232, 229 and 352).

Measured and not used: a tolerance hull of all points (10 % fewer facets than every point); splitting a piece before
adding points (more facets); a coarser surface tolerance (0.5 to 4 units: 3 % fewer facets); holding only larger
walkable faces (fails the surface gate); reduced kelp and Bitter Coast grass (the mesh optimizer's merged
polygons made x-07 y-04 425 KB larger, as at Hla Oad).

## Verification

Done: the 42 frames above (`--validate --stats`), the heap gate and the collision surface gate pass; the
regression tests below. Waiting: the next full build (heap gate over all 1,351 frames, stair walks over the changed
collision, notably the Daedric ruins), then the Vivec dock walkways in game.

## Prevention

`tests/test_hull_surface_loss.py`: a round rock's walkable cap held within 0.5 units by under a quarter of the
planes of the hull of all its points (2,304); the held points only; the rule as first shipped; deep walkable faces
as plates; the scale snap and its switch; the heaviest-frames list.

A converter change that touches many meshes gets a heap check on the heaviest frames before it is merged:
`tools/chim_heaviest_frames.py <last build>/chim-world` lists the frames closest to the zone (under 256 KiB
headroom, at least the 12 tightest) and prints their cells with neighbours for `tools/chim_build.py
--chim-regions-cells ... --validate --stats` (minutes). Run on the v0.0.45 world, its six tightest frames are exactly
the six that failed here. Written into [CHIMPORT](../chim/CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Map heap and memory budget (`heap-memory`). The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. See [families](README.md#families).

- AW-20260929-06 (no report page): Expanded scene exhausts 9 MiB heap
- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone
- [CHIM-ARENA-HUNK-GAP-36](CHIM-ARENA-HUNK-GAP-36.md): The Vivec Arena frame leaves less than 2 MiB of hunk gap (memory review before Vivec stage B)
- [CHIM-AUTO-BANK-CLIFF-51](CHIM-AUTO-BANK-CLIFF-51.md): 32 MB of Fast RAM got no automatic CHIM cache bank: 13 MiB free gave a 7 MiB budget and the first bank needed 8 MiB
- [CHIM-BALMORA-RING-GROWTH-36](CHIM-BALMORA-RING-GROWTH-36.md): Balmora's CHIM ring grew past the zone after v0.0.36-dev3 with the converter mesh method
- [CHIM-BALMORA-RING-OVER-33](CHIM-BALMORA-RING-OVER-33.md): CHIM heap gate fails on Balmora in the first full v0.0.33 build: the south-west active ring needs 136,160 bytes more than the zone holds
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): Two Bitter Coast CHIM frames over the heap zone after the trunk shape guard
- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md): The heap check does not account for a CHIM map's zone bank
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

- [CHIM-VIVEC-DOCK-WALKWAY-43](CHIM-VIVEC-DOCK-WALKWAY-43.md): The player cannot climb the walkway at the Vivec Hlaalu canton dock and gets stuck

<!-- END GENERATED CATEGORY -->
