# CHIM-CHUNK-LOAD-FAIL-33: Balmora chunks fail to load on CHIM, never recover, and leave holes without ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM chunk loading/zone: Balmora, Dwemer follow-up and Seyda native terrain allocation |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33-dev, v0.0.38, v0.0.39-rc1, v0.0.40-dev1, v0.0.41, v0.0.42-dev1 (last seen) |
| Severity | high: Whole areas of Balmora are missing and the player falls through the ground. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the CHIM world receipt records no commit: world built 8 October 2026 17:54 +03:00 on the v0.0.33-chim-format branch before 8caf66e (CHIM-RECEIPT-COMMIT-33) |
| Build note | first seen in a development emulator session of the same Balmora world on 8 October 2026 (a3ef932); the maintainer saw it in CHIM Preview 1 on 9 October 2026 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Maintainer follow-up, 13 October 2026: Dwemer exterior cell (9,2)](#maintainer-follow-up-13-october-2026-dwemer-exterior-cell-92)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Seyda native allocation retry, 14 October 2026](#seyda-native-allocation-retry-14-october-2026)
- [Repeated Seyda allocation failure, 14 October 2026](#repeated-seyda-allocation-failure-14-october-2026)
- [Khajiit follow-up diagnostic, 14 October 2026](#khajiit-follow-up-diagnostic-14-october-2026)
- [Nord gait diagnostic, 14 October 2026](#nord-gait-diagnostic-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Historical 9 October checkpoint: cause measured, repaired in source on
v0.0.33-chim-chunkload (see Repair), not in a build at that checkpoint. Present in the private CHIM preview (the v0.0.32
disks with the CHIM engine of v0.0.33-chim-engine 0d8bf4f and a format 0.4 Balmora world) and in the
v0.0.33-dev engine source up to the repair.

CHIM area: streaming. Build: "CHIM Preview 1", engine commit 0d8bf4f, world format 0.4, base source
0f467e4, world builder commit unknown (the preview receipt records no builder commit,
CHIM-RECEIPT-COMMIT-33).

## Symptom

Maintainer playtest of the private CHIM preview, Balmora on CHIM, 9 October 2026. The console repeats
"CHIM: chunk N not loaded (zone full or bad data); retrying" and the chunks never arrive:

| Global position | Chunks named | What was seen |
| --- | --- | --- |
| -20081 -18113 272 | 89, 59, 60 | bridge area; message only |
| -23807 -15931 570 | 92, 106, 102 | message; buildings missing |
| -25296 -12545 1026 | 272, 274, 278, 277 | a whole area missing, flat fog and sky colour where buildings and ground should be |
| -24721 -11329 -1378 | 252 | the player fell through the ground |
| -22906 -14199 951 | 92, 87, 91, 98 | ground missing between buildings; an actor standing over the void |
| -18541 -13591 362 | 287, 86, 90 | message; a few minutes into play, failures all over Balmora |

## Where

CHIM engine: `chim/chim_chunks.c` (ring scheduler: activation, `Failed`), `chim/chim_zone.c` (the
non-moving zone allocator), `chim/chim_models.c` (model blocks). Builder: `tools/chim/heap.py` (the
heap gate's model of the ring). The world data is not affected (see below).

## How it happened

Measured in FS-UAE on fresh copies of the preview's disks, at the maintainer's poses in his order (the same
chunk numbers fail at the same poses: 92 and 102 at -23807 -15931), and with the map reloaded before
each pose:

1. Not bad data. Every chunk, model and texture record of the world reads back with its size and CRC
   (the builder's `chim.validate.load_world`), and every failure was an allocation that found no room:
   the decode bound was computed, the zone refused the block.
2. The zone is full of locked data. At -23807 -15931 the zone (6,864 KiB, one bank, never moved) held
   6,111 KiB locked with the map reloaded just before (5,573 KiB after the route); 1,181 KiB were free
   but the largest free piece was 211 KiB, while the house models the ring needs decode to
   258,336 bytes (`ex_hlaalu_b_11`) and 291,728 bytes (`ex_hlaalu_b_24`); the silt strider is
   477,568 bytes. A block that does not fit evicts every unlocked block and still fails, because the
   locked blocks split every gap.
3. Chunks stay locked out to the load radius. A chunk is activated (catalogue, terrain and models
   locked) within the active radius (636 units: view 540 + hysteresis 96) but released only past the
   load radius (892: + prefetch 256). The heap gate counts the active ring at one position: at most
   6,239,776 bytes against 6,242,304 for Balmora (2,528 bytes of headroom, nothing for fragmentation);
   counting everything a moving player can hold locked (the load radius), 661 of 9,216 positions are
   over the budget, peak 7,661,472 bytes; at the maintainer's poses 5.6-7.5 MB.
4. The ground waits for every building. A chunk is activated, and its terrain joins the frame world,
   only when all models its placements use are resident. One house model without room keeps the ground
   of its chunk out: a hole, and with no collision there the player falls.
5. It never recovers. A failed chunk waits 50 ticks and tries again, but nothing it can do unlocks
   anything; while the player stands still the same request fails forever. The route run also shows the
   cache thrashing at the last pose (964 model loads at one pose).
6. Failures grow with play. With the map reloaded before each pose only the two densest poses fail
   (-23807 -15931 and -22906 -14199: 28 failed loads); along the route the same disks fail at four of
   seven poses (152 failed loads), because locked blocks left by earlier rings split the zone further.

The two far views without a message (-17541 -15916, looking west) are not failures: that ground is
past the view distance and the active radius; nothing draws it in a CHIM frame (there is no resident
far terrain layer).

## Why it was not caught

The heap gate sums one position's active ring and so cannot see fragmentation in a zone that never
moves a block, nor the hysteresis band out to the load radius. Emulator runs before the preview walked
straight lines through the town centre with an earlier zone size; none visited the dense west and
south-west streets, and the preview's memory defaults were not run in the emulator before release.

## Reproduction

Fresh copies of the preview disks; `dbg tp -21800 -12300` into Balmora; `chim_tp` to -20081 -18113,
then -23807 -15931; `chim` shows "N failed" and the console the failing chunks 92 and 102 (model 165,
197,620 bytes on disk, 258 KB decoded).

## Repair

In source on v0.0.33-chim-chunkload (CHIM engine; each method selectable, 0 being the first method,
documented in `docs/chim/ENGINE.md`, "When the zone is full"):

- A loading chunk keeps what it has (`chim_release 1`): while a chunk within the active radius loads its
  terrain or a model, its catalogue, terrain and resident models are locked. The first method could
  evict them to make room for the next model, and a chunk whose models did not fit together loaded them
  in turn for ever (the cache thrash: about a million model loads over the maintainer's route in the
  simulation, 964 at one pose in FS-UAE).
- Nearer chunks win (`chim_release 1`): a chunk within the active radius that finds no room releases the
  active chunk farthest from the player that is farther than itself and outside the collision margin
  (the hysteresis band past the active radius first) and tries again. A released chunk is not activated
  again for 50 ticks unless the player comes within the collision margin of it; every release lets the
  waiting chunks try again at once; a chunk without ground within the collision margin that failed
  tries again on the next tick instead of after 50.
- The ground never waits for a building (`chim_partial 1`): a chunk whose model has no room is activated
  without it; its ground, collision and other placements are there, and the model follows when there is
  room (a reach copy draws the placement meanwhile when another chunk holds the model).
- Small blocks from the zone's high end (`chim_zone_ends 64`): blocks under 64 KiB (textures, catalogues,
  terrain, small models) come from the top of the zone, larger ones first fit from the bottom, as
  Quake's Hunk keeps a low and a high end; the zone map at the first failure showed 2 KB textures locked
  by cached models scattered through the whole zone (2.5 MB free, largest piece 187 KB).
- The failure line says which part failed and why (`zone full (model 165, 236576 bytes; largest free
  187280, free 2522208, locked 4489968 of 7028736)` or `bad data in ...`), once per chunk and 50 ticks;
  the first one of a map prints the zone's layout; `chim` reports the largest run without a lock, the
  failures by reason, releases and partial activations.

Tried and measured worse, not kept: eviction of the cheapest run of unlocked blocks (thrash: 1.3 million
model loads on the sweep) and least-recently-used eviction restricted to such runs (more failures than
evicting all unlocked blocks, which leaves the most contiguous room).

A larger zone helps further (simulated over the maintainer's route with all methods on: 30 loads without room
at 6,864 KiB, 14 at 7,680 KiB); the budget stays CHIM-ZONE-BUDGET-33's project decision.

## Verification

The engine's own zone allocator over walks (simulation, `tools/chim/zone_sim.py`, Balmora world, target
ABI block sizes; holes = steps with a chunk within the collision margin without its ground):

| Methods | Maintainer's route twice (1,192 steps) | Sweep of the frame (6,111 steps) | Teleports to the poses x3 |
| --- | --- | --- | --- |
| first methods (preview, dev1 engine) | 701 failed, 860 holes, 1,010,584 model loads | 382 failed, 231 holes | 70 failed, 180 holes |
| all methods, zone_ends 0 | 52 failed, 0 holes, 1,105 model loads | 42 failed, 0 holes | 16 failed, 0 holes |
| all methods, zone_ends 64 (default) | 30 failed, 0 holes, 997 model loads | 34 failed, 0 holes | 14 failed, 0 holes |

Seyda Neen (CHIM world seyda-009, format 0.5; its ring also overflows the zone at the load radius:
6,417,728 bytes against 6,242,304 at 29 positions), sweeps of the frame with rows 256 and 128 units apart:
first methods 28 and 107 holes (45 and 178 failed loads); all methods 0 and 0 holes (16 and 44 failed
loads, 11 and 31 partial activations).

FS-UAE, fresh copies of the same disks (v0.0.32 release image plus the format 0.4 Balmora world), the
maintainer's poses in order, twice, with a short walk at each; the engine's nearest chunk without ground
(collision margin 224 units):

| Engine | Nearest chunk without ground, worst | Failed load attempts | Data read | Notes |
| --- | --- | --- | --- | --- |
| A0 preview (0d8bf4f) | 69 units, inside the collision margin at 5 poses | 180 | 24.8 MB | |
| B2 v0.0.33-dev1 (f95cf75) | 94 units, same poses | 152 | 24.7 MB | 1,124 streamed model loads; stopped answering after 11 of 14 poses |
| C2 repair, chim_zone_ends 0 | 229 units | 137 | 20.1 MB | 12 loads left without room, 44 chunks released inside the ring |
| D2 repair, all defaults | 438 units | 95 | 16.7 MB | 11 loads left without room (7 partial activations), 25 released inside the ring, 0 bad data |

An earlier run of the preview engine over the route three times stopped answering at the seventh pose
(the game froze with the cache thrashing: a chunk within the collision margin loads past the frame's
budget, and its models evicted each other). No run of the repaired engine froze. No run printed a texture
fallback ("drawn untextured") or bad data.

Remaining: the maintainer's playtest of a build with the repaired engine.

## Prevention

- The builder's zone walk gate (`tools/chim/zone_sim.py`, run by `chim_build.py --validate` after the
  heap gate): the engine's `chim_zone.c` built for the host, driven by the ring rules of `chim_chunks.c`
  with the engine's defaults (read from the engine source through `tools/engine_limits.py`), over a walk
  through every frame; it fails when a step leaves the player without ground or a chunk fails for bad
  data, and reports loads without room, releases, partial activations and loads.
- Host tests: `fullzone` (a starved zone: no hole under the player, partial activation, the model arrives
  when there is room, no thrash; the first methods leave the hole) in `tests/aga_chim_world_test.c`; the
  zone's failure count, largest unlocked run and layout in `tests/aga_chim_zone_test.c`;
  `tests/test_chim_zone_sim.py`.

## Maintainer follow-up, 13 October 2026: Dwemer exterior cell (9,2)

A maintainer screenshot shows a visible Dwemer structure and `CHIM: chunk 116 not
loaded: zone full ... retrying` at global XYZ (77750,20044,1980), exterior cell
(9,2). Its receipt identifies the v0.0.38 full-image WinUAE playtest. Evidence
`OWNER-20261013-DWEMER-CHUNK116` binds the private original, SHA-256
`4dab41e7209ea102524a6718089b4ab94f01088652aa63890e619a06e03ba173`.
Other warning numbers overlap text and are not reliably transcribed.

The maintainer reports heavy loading but working access. That does not establish
complete geometry, a measured load time or recovery of every chunk. The warning
does not prove the earlier Balmora fragmentation cause. Reproduce the exact
image at normal speed; record allocation details, recovery, visible/collision
coverage, loading time and audio service separately. Keep the issue open for
v0.0.40 work.

## Exact RC1 evidence, 13 October 2026

13 October 2026, v0.0.39-rc1: exact-package save/death inspection of vf1703
still logs repeated chunk20 zone-full retries for model4251 (314,736 bytes).
Later reports show 389,616 bytes free but largest free block 59,184, with
5,694,976 of 7,025,392 bytes locked. This is current allocation/retry evidence
under the existing streaming issue. It does not alone prove a visible hole,
ground loss or eventual recovery. Scoped save/reload survival and package
inclusion do not close streaming/residency or performance coverage.

## Seyda native allocation retry, 14 October 2026

During normal male-Nord S/D movement in the exact v0.0.40-dev1 Seyda CHIM
diagnostic, chunk 249 terrain (45,840 bytes) cannot load: the largest free run
is 15,824 bytes despite 80,336 total free bytes, with 6,837,552 bytes locked
of a 6,962,880-byte zone. The runtime reports zone full and retrying.

This is allocation/residency evidence under the existing streaming issue.
It does not alone establish a visible terrain hole, falling, eventual recovery,
measured FPS impact or that inventory caused the pressure. Preserve the warning
and exact native source/world binding for further investigation. No new cell
coverage, memory repair or maintainer acceptance is claimed.

## Repeated Seyda allocation failure, 14 October 2026

The same exact native diagnostic later repeats chunk 107 allocation refusal
during the Fargoth exchange: model 1408 requires 386,448 bytes; largest free
block is 98,016 bytes, total free 173,648, with 6,559,152 of 6,962,880 bytes
locked. The log explicitly retries. This is further evidence under the existing
allocation/residency issue, without a new visible-hole, recovery, performance,
cause or CHIM-coverage conclusion.

## Khajiit follow-up diagnostic, 14 October 2026

Test source `90ba44c2cc079de50e50b8e1a8cde76dd2bcf318`, engine SHA-256 `166ffbecbcd399f9d9fe3ed2d5f3bdc259bf17a0bfe7f1e933a1222bf264b2a2`, using the previously delivered v0.0.40-dev1 world. The post-Census diagnostic character was changed through the actual appearance menu. This is an unreleased diagnostic, not a new shipment.

Seyda chunk 107 / model 1408 repeatedly refused a 386,448-byte allocation with 11,872 bytes in the largest free run, 138,672 bytes free overall and 6,691,616 bytes locked of 6,962,880. Gameplay continued. No specific missing face or original reference is identified by this warning alone. Existing coverage counts and failed/held states are retained; no cell completion or conversion is added.

The separate normal shutdown check records actual emulator-parent and container exit status 0, followed by 194 resource checks, 33 key bindings and a valid bitmap. This does not retroactively repair the earlier failed shutdown receipt. Played disks remain diagnostic evidence only.

## Nord gait diagnostic, 14 October 2026

Test source `90ba44c2cc079de50e50b8e1a8cde76dd2bcf318`, engine SHA-256 `166ffbecbcd399f9d9fe3ed2d5f3bdc259bf17a0bfe7f1e933a1222bf264b2a2`, with the previously delivered v0.0.40-dev1 world. This is an unreleased diagnostic, not a new package or acceptance. The original emulator frames were retained; warp was visibly disabled before recording.

Chunk224 requested 38,144 terrain bytes with 7,600 in the largest free run, 111,712 free overall and 6,631,168 locked of 6,962,880 bytes. Chunk248 requested 52,752 terrain bytes with 27,424 in the largest free run, 135,472 free overall and 6,826,736 locked. These repeated refusals do not identify an absent face or establish the cause of a blocked route. Existing failed/held cells and all coverage counts remain unchanged.

The run closed normally and passed its separate post-exit resource readback. Its played disk is diagnostic evidence only. All related gameplay reports remain open.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [BUILD-CHIM-HEAP-GATE-LATE-36](BUILD-CHIM-HEAP-GATE-LATE-36.md): The CHIM heap gate runs after the stair walk: a ring over the zone is found 69 minutes late
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36](BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): CHIM frames are stair-walked again on every build: about 69 minutes for 270 frames
- [BUILD-CHIM-VALIDATE-LATE-36](BUILD-CHIM-VALIDATE-LATE-36.md): The CHIM world is validated only after the whole chim stage: a bad chunk is found 45 minutes in
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): The image step of a CHIM-native town read legacy region maps that are never built: the Bitter Coast test build failed at the end of its image step on maps/bc000.bsp
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning
- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTOR-TABLE-OFF-IN-GAME-47](CHIM-ACTOR-TABLE-OFF-IN-GAME-47.md): The actor table ships in v0.0.47-dev2, but the engine does not read it by default
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47](CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): With the type 1 window and the actor table, a town is empty after the player comes back into it from the region frames
- [CHIM-ALIAS-STATIC-HUNK-35](CHIM-ALIAS-STATIC-HUNK-35.md): Streamed alias statics load into the cache mid-map without being counted in the map's Hunk rest
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BALMORA-INSET-SLIVERS-43](CHIM-BALMORA-INSET-SLIVERS-43.md): Balmora's town frame hands over 96 units inside its cells: the 8 cells around the town keep classic strips, built as 15 legacy maps (11.5 MB) with every object of those cells
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-COMPILED-HULL-OVERFILL-46](CHIM-COMPILED-HULL-OVERFILL-46.md): CHIM model standing hulls without edge bevels are solid where their own collision pieces leave room: up to 82 units, mostly in open air
- [CHIM-COMPILED-HULL-SHORT-36](CHIM-COMPILED-HULL-SHORT-36.md): Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units
- [CHIM-CROSSING-SLUGGISH-43](CHIM-CROSSING-SLUGGISH-43.md): Crossing between CHIM cells is sluggish, worst at cell corners
- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-EMPTY-POINT-HULL-36](CHIM-EMPTY-POINT-HULL-36.md): A CHIM model without collision has no point-hull node: the engine reads it as solid, or refuses it on load
- [CHIM-EXTERIOR-ACTORS-MISSING-46](CHIM-EXTERIOR-ACTORS-MISSING-46.md): Most outdoor NPCs and every outdoor creature are missing: region frames place no actors (93 of 566 exterior NPC references, 0 of 5,415 creature references)
- [CHIM-FAR-BAND-GAP-36](CHIM-FAR-BAND-GAP-36.md): From a CHIM area's border the ground ends at the frame edge: up to 476 units with no land before the fog plane
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FERN-NCO-SOLID-38](CHIM-FERN-NCO-SOLID-38.md): Fire ferns marked NCO become solid in CHIM mesh conversion
- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md): R_StoreEfrags: Bad entity type 270440 ends the game: a leaf link to an entity whose model is NULL (normal play in Seyda Neen; noclip past the Vivec frame edge)
- [CHIM-FRAME-GROUND-TRACE-38](CHIM-FRAME-GROUND-TRACE-38.md): CHIM image assembly exceeds collision traversal guard in cell 6,-5
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-FAIL-NO-FLOOR-35](CHIM-GRAFT-FAIL-NO-FLOOR-35.md): A CHIM map whose frame world cannot start loses its far terrain too: the player may spawn over void
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
- [CHIM-HANDOFF-POPIN-36](CHIM-HANDOFF-POPIN-36.md): Most of a CHIM area's objects are not drawn from the legacy side and appear at the handover (Gnaar Mok, a Dwemer ruin)
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HEAP-INT-MATMUL-36](CHIM-HEAP-INT-MATMUL-36.md): The CHIM heap scan multiplies 0/1 tables as int32: numpy's plain loop, 6 of 24 cores, about 60 s per check
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL-ROUTE-NO-CUT-43](CHIM-HULL-ROUTE-NO-CUT-43.md): Two flora meshes keep a standing hull that is one chain over the depth limit although routed: 14 cells fail the hull audit (hull policy pending)
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LAVA-RECOVER-38](CHIM-LAVA-RECOVER-38.md): Debug recovery fails to find a clear spawn after lava contact
- [CHIM-LAVA-TERRAIN-AUDIT-37](CHIM-LAVA-TERRAIN-AUDIT-37.md): Terrain validation omits lava beds, surfaces and contents
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-MEASURE-EMPTY-FRAME-33](CHIM-MEASURE-EMPTY-FRAME-33.md): CHIM world measurement stops on a frame without models (every empty sea cell)
- [CHIM-MESH-PROFILE-SPLIT-36](CHIM-MESH-PROFILE-SPLIT-36.md): Seyda Neen converts the same meshes with other profiles than the other CHIM areas (texture size 64 against 32, no surface collision rule), so they are stored twice
- [CHIM-MIPTEX-OFFSET-UNCHECKED-35](CHIM-MIPTEX-OFFSET-UNCHECKED-35.md): CHIM texture mip offsets are taken from disk unchecked: a wrong offset makes the rasterizer read past its block
- [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md): Placed CHIM models reserve renderer nodes that their point-hull loader never allocates
- [CHIM-MOLAG-MEMORY-38](CHIM-MOLAG-MEMORY-38.md): Tel Uvirith exterior cell (10,1) exceeds the CHIM active-ring memory budget
- [CHIM-OCEAN-CELL-RECORD-CLASSIC-43](CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md): 14 open-sea cells with a CELL record and no LAND stay classic: the build keeps a legacy map for each, the tracker counts them as open ocean and no cell list selects them
- [CHIM-OCEAN-CELL-RECORD-ROUTING-43](CHIM-OCEAN-CELL-RECORD-ROUTING-43.md): The dev3 full build stops 30 minutes in, in world terrain: the 14 open-sea cells with a CELL record are routed as map-less ocean cells although each has an open-world map
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PACK-LRU-STREAM-35](CHIM-PACK-LRU-STREAM-35.md): A streamed model keeps a sector file handle the four-file cache may close: the next stream step reads a closed file
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PLACEMENT-MARGIN-COPIES-46](CHIM-PLACEMENT-MARGIN-COPIES-46.md): Every object placement is stored in about 3.5 frames (the region frame margins) plus 619,074 reach copies: 52 MB of placement records for 132,369 objects
- [CHIM-PLANE-TYPE-ALL-SLANTED-46](CHIM-PLANE-TYPE-ALL-SLANTED-46.md): Every CHIM plane is stored as slanted (type 3), so axial planes never take Quake's fast paths in collision and drawing
- [CHIM-PREDICT-VIVEC-LOW-36](CHIM-PREDICT-VIVEC-LOW-36.md): The CHIM memory predictor under-predicts every Vivec district frame by 28-54 %: Vivec architecture decodes to 1.3-2.3 times the bytes per triangle it was fitted on
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-RECIPE-APRON-SCOPE-41](CHIM-RECIPE-APRON-SCOPE-41.md): Regional aprons lose original-cell visual recipes and regress the memory gate
- [CHIM-RED-MOUNTAIN-SOLID-SKY-43](CHIM-RED-MOUNTAIN-SOLID-SKY-43.md): On the Red Mountain summit (cell 2,9) the player ends up inside solid and only the sky is drawn, no terrain
- [CHIM-REGION-DIVIDED-CELLS-36](CHIM-REGION-DIVIDED-CELLS-36.md): Most converted land cells cannot switch to CHIM inside the open world: the legacy builder split them over several maps and a region frame replaces exactly one
- [CHIM-REGION-MARGIN-STORAGE-36](CHIM-REGION-MARGIN-STORAGE-36.md): One-cell CHIM region frames store about 3.5 times their cell's terrain (the terrain-only margin)
- [CHIM-REGION-POCKET-TOWN-CELLS-42](CHIM-REGION-POCKET-TOWN-CELLS-42.md): The legacy-pocket rule counts cells wholly inside a town frame as legacy: CHIM region cells around a town are left out for nothing
- [CHIM-REGION-SEABED-NO-HEIGHTS-42](CHIM-REGION-SEABED-NO-HEIGHTS-42.md): The full build refuses the 98 heightless seabed cells as region cells (no original LAND), without naming the cell, although CHIMport converts them
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43](CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43.md): CHIM model variants take only the mesh-wide exact-bevel flag: stair plates marked for exact standing bevels get the approximate axial hull
- [CHIM-STAIR-STEPS-SOLID-43](CHIM-STAIR-STEPS-SOLID-43.md): Three stair meshes fail the CHIM stair walk: Redoran steps start in solid (Ald-ruhn, Maar Gan), Hlaalu steps blocked (Suran), a rope bridge starts in solid (0,8)
- [CHIM-STATIC-PLACE-HOST-ERROR-35](CHIM-STATIC-PLACE-HOST-ERROR-35.md): Bad flora data at CHIM chunk activation ended the session with zone locks held; the next map then stopped the program
- [CHIM-STATICS-FALLBACK-41](CHIM-STATICS-FALLBACK-41.md): A frame map with more than 512 streamed statics crashes when its CHIM world cannot load, instead of running without its chunks
- [CHIM-STITCH-SHORELINE-36](CHIM-STITCH-SHORELINE-36.md): A CHIM area in the legacy world has no shoreline refinement: steps of up to 28 units at its border
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-TILT-VARIANTS-SPLIT-33](CHIM-TILT-VARIANTS-SPLIT-33.md): Tilted placements each get their own model variant: 39,103 extra model variants on the base island, breaking store-once
- [CHIM-TOWN-HEAP-ROUTED-HULL-36](CHIM-TOWN-HEAP-ROUTED-HULL-36.md): With the routed terrain hull for every chunk, Balmora and Seyda Neen rings no longer fit the CHIM zone
- [CHIM-UNIT-CACHE-RACE-33](CHIM-UNIT-CACHE-RACE-33.md): Two processes storing the same CHIM unit at once: the second rename fails
- [CHIM-UNIT-FP-SOURCE-LAYOUT-33](CHIM-UNIT-FP-SOURCE-LAYOUT-33.md): The same mesh is converted again for every source stage: CHIM mesh unit fingerprints include archive offsets and texture list positions
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VARIANT-YAW-DUPLICATES-36](CHIM-VARIANT-YAW-DUPLICATES-36.md): One CHIM model variant is stored several times: each frame builds it at the yaw of its own first placement
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-VIEW-LEAF-NO-PVS-35](CHIM-VIEW-LEAF-NO-PVS-35.md): A view leaf without a visibility row draws everything, with no counter saying so
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33](CHIM-WINDOW-MOUNT-CROSS-CELL-33.md): A one-cell CHIM frame stops when a window placed in it mounts on a facade placed in the next cell
- [CHIM-WORLD-AUDIT-SCALING-33](CHIM-WORLD-AUDIT-SCALING-33.md): The CHIM world audits grow much faster than the world: the heap gate took 3.6 s for 171 frames, 473 s for 331, and over an hour for 844
- [CHIM-WORLD-INDEX-FILE-LIMIT-36](CHIM-WORLD-INDEX-FILE-LIMIT-36.md): The engine refuses a CHIM world index with more than 4096 file rows; the dev3 coast world has 7,236, so every CHIM frame map fails
- [CHIM-YAW-PLAYER-BOX-TURNS-46](CHIM-YAW-PLAYER-BOX-TURNS-46.md): The player collision box turns with a yawed CHIM model (OpenMW keeps it world-aligned)
- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold
- [CHIMPORT-OCEAN-LAND-41](CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells (land records entirely under water) are marked open ocean: CHIMport never plans them and the ocean admission refuses them
- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): CHIMport --retry-failed cannot rerun a lava cell of the island run: its stored source stage predates the lava conversion
- [CHIMPORT-SEABED-NO-ISLAND-42](CHIMPORT-SEABED-NO-ISLAND-42.md): Seabed cells measured as empty sea lose their island in the tracker: they drop out of the published reference and the build calls them unknown
- [COMBAT-PURSUIT-SLOPE-STALL-46](COMBAT-PURSUIT-SLOPE-STALL-46.md): A pursuer stops on a walkable slope: an actor step was refused when it moved more than a stair height along the slope

Related bugs in other categories:

- [CHIM-ZONE-BUDGET-33](CHIM-ZONE-BUDGET-33.md): The engine's default CHIM zone does not hold the active ring of Seyda Neen or of Balmora's south-west corner

<!-- END GENERATED CATEGORY -->
