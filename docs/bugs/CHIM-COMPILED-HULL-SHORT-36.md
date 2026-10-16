# CHIM-COMPILED-HULL-SHORT-36: Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.36-dev3 |
| Where | tools/collision_bsp.py compile_standing (terrain, CHIM models, legacy converter) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | high: A player box sinks up to 3 units into the ground; the CHIM validation of the 270-frame region build failed after 45 minutes |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.36-dev3 |
| From commit | source 5184581, engine 5184581, CHIM world 5184581 |
| CHIM engine version | CHIM 0.1.0, engine 5184581, world format 0.7 |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Island-wide sweep (10 October 2026)](#island-wide-sweep-10-october-2026)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Open; repaired in source for terrain and models. Every compiled standing hull is checked against the exact union of
its pieces; pieces the compiler lost are patched in (models by default, `--chim-model-hull-patch`), and a terrain
chunk whose hull still fails keeps the routed hull. Found by the CHIM validation of the first full build with CHIM
region cells, the compiled terrain hull and terrain references (v0.0.36-dev3); the island-wide sweep found the same
mechanism in 11 compiled model hulls of Balmora and the Bitter Coast test area. Closed when a build with the repair
has been played.

## Symptom

The CHIM world fails validation with four "standing hull empty ... below the ground under the box (hull 1 seam)"
failures. Near those chunk borders a standing player box sinks up to about 3 units into the ground before the
standing hull holds it.

## Where

`tools/collision_bsp.py` `compile_standing`, for every caller:

- chunk terrain (`tools/chim/terrain.py` `chunk_terrain`: `--chim-terrain-hull compiled`, and the default
  hull for irregular ground);
- CHIM models with exact collision (`tools/chim/models.py` `variant_unit`: the Hlaalu houses, bridges, steps
  and gates, and the Velothi temple of the town converter's profiles);
- the legacy town converter (`prepare_mesh_bsp` with a collision compiler).

The pieces themselves are correct. The routed hull and the exact chain built from the same pieces hold a box
everywhere.

## How it happened

The compiled hull is the same Minkowski-expanded tile pieces compiled into one BSP by qbsp. The compiler snaps
and merges planes. On the shoreline's small, irregular triangles (32-unit samples) this can move the top of the
union down by a few units. Nothing compared the compiled result with the exact union before it was stored.

## Why it was not caught

The validator samples the standing hull only near chunk edges, and only in the build's last step. The scratch
worlds measured for CHIM-REGION-MARGIN-STORAGE-36 had no failing chunk. The compiled hull is not
translation-invariant, so a chunk built in chunk-local units (terrain references) can fail where the same
ground built in frame units passes, and the reverse.

## Island-wide sweep (10 October 2026)

Every compiled standing hull of the CHIM areas built in v0.0.36-dev3 was rebuilt with the check recording
each hull (`AMIWIND_HULL_SWEEP`): Balmora, Seyda Neen and the Bitter Coast test area. The CHIM region cells hold
no compiled model hull: their exact models are homed in Balmora's and the test area's frames.

| Family | Compiled hulls | Exact | Short |
| --- | ---: | ---: | ---: |
| chunk terrain (town frames) | 1,108 | 1,108 | 0 |
| models | 42 | 31 | 11 |

Short models, the worst shortfall under a walkable top (from the CHIM receipt's `compiled_model_hulls`):
ex_dwrv_ruin10 (139 units), ex_hlaalu_b_14 (91), ex_hlaalu_b_01 (60), ex_dwrv_enter00 (49), ex_hlaalu_b_13 (46),
ex_hlaalu_b_24 (44), ex_hlaalu_b_26 (41), ex_hlaalu_b_12 (41), ex_hlaalu_b_17 (34), ex_hlaalu_b_06 (34) and
ex_hlaalu_b_15 (5). At the worst points of
three of them, the exact chain of the same pieces holds the box and the compiled hull does not. Balmora's
interiors build no compiled union (no collision compiler on that path). The terrain chunks that failed were
all on CHIM region cells' shoreline; see the reproduction below.

Without patching (the default), every CHIM gate passes and Balmora's ring peaks at 6,230,992 bytes, 11,312
under the zone. Patching the 11 models (46 to 458 extra nodes each) makes every one exact. Balmora's ring then needs
6,254,704 bytes at one of 9,216 positions, 12,400 over the zone, even after the heap fallback turns six
routed models back into chains. Falling back to the exact chain instead needs 6,665,952 bytes.

## Reproduction

Always, on the same cells. Region cells 13,-15, 13,-14, 14,-15 and 16,-11, built alone with `chim_build
--chim-regions-cells`:

| Hull | References | Validation failures |
| --- | --- | ---: |
| routed | off | 0 |
| compiled | off | 1 (cell 16,-11, chunk 3,13) |
| compiled | on | 4 (as in the full build) |
| routed | on | 0 |

In the full build, three of the four failing chunks are one stored terrain record placed in three frames
(cells 13,-15, 13,-14 and 14,-15). The fourth is cell 16,-11, chunk 3,13. Measured shortfall: 0.88 to 1.05
units at the failing samples, up to 3.08 units along the same edge.

## Repair

One check for every caller, in `tools/collision_bsp.py`:

- `standing_check` compares a compiled hull with the exact union of its pieces, each expanded by the standing
  box exactly and without the compiler's lattice. The columns are a lattice every 8 units (at most 4,096 per
  hull), the validator's seam samples and every piece's centre. On every walkable top of the union (face
  normal z at least 0.7, Quake's floor rule), a box must be held 0.25 units below and be free 0.25 units above.
  A steep face's height is not judged: a lattice step on it is a large vertical difference that changes
  nothing for a standing box.
- `compile_standing_checked` runs the check on every compiled hull and caches the verdict with the hull. It
  names the pieces under every short top. `patch_holes` then leads every empty leaf of the compiled tree to one
  shared chain of those pieces, each exactly expanded; at most three rounds. The patched hull never reaches
  past the pieces.
- Chunk terrain uses it strictly: a hull still inexact after patching makes the chunk keep the routed hull of
  the same pieces (`compiled_hull_fallbacks` in the CHIM receipt). The unit's fingerprint carries the check
  (`hull-check-2`).
- Models record the check in their unit, and the CHIM receipt lists every inexact and every patched model
  (`compiled_model_hulls`). Patching is on by default (`--chim-model-hull-patch`, `chim_build.py
  --model-hull-patch`); `off` keeps the hull as compiled. The compiled, routed and chained methods all stay
  selectable. With the checked compiled terrain hull, Balmora's ring has room for the patches: 6,093,376 bytes
  with them, 6,065,216 without, of 6,242,304 (the town frames built with the v0.0.36-dev3 inputs). The 50 model
  variant units of the exact-collision models are built again once (their key names the patch).
- `AMIWIND_HULL_SWEEP=<file>` appends every compiled hull's check as one JSON line: the island-wide sweep.

## Verification

The four cells built alone with the repair:

- compiled hull: 1 fallback (cell 16,-11, chunk 3,13, short by 1.43 units), 0 validation failures;
- compiled hull with references: 4 fallbacks (three placements of one record, short by 8.70 units, and cell
  16,-11, chunk 3,13), 0 validation failures.

The heap gate, the zone walk and the stair gate passed. Regression tests: `tests/test_chim_hull_check.py` (the check, the walkable rule, the patch of a lost piece,
the terrain fallback).

## Prevention

The check runs on every compiled chunk hull when it is built. Each frame's terrain is checked as soon as it is
built ([BUILD-CHIM-VALIDATE-LATE-36](BUILD-CHIM-VALIDATE-LATE-36.md)), and the whole-world validation still runs
at the end.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [BUILD-CHIM-HEAP-GATE-LATE-36](BUILD-CHIM-HEAP-GATE-LATE-36.md): The CHIM heap gate runs after the stair walk: a ring over the zone is found 69 minutes late
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36](BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): CHIM frames are stair-walked again on every build: about 69 minutes for 270 frames
- [BUILD-CHIM-VALIDATE-LATE-36](BUILD-CHIM-VALIDATE-LATE-36.md): The CHIM world is validated only after the whole chim stage: a bad chunk is found 45 minutes in
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): The image step of a CHIM-native town read legacy region maps that are never built: the Bitter Coast test build failed at the end of its image step on maps/bc000.bsp
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning
- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ALIAS-STATIC-HUNK-35](CHIM-ALIAS-STATIC-HUNK-35.md): Streamed alias statics load into the cache mid-map without being counted in the map's Hunk rest
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-EMPTY-POINT-HULL-36](CHIM-EMPTY-POINT-HULL-36.md): A CHIM model without collision has no point-hull node: the engine reads it as solid, or refuses it on load
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
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PACK-LRU-STREAM-35](CHIM-PACK-LRU-STREAM-35.md): A streamed model keeps a sector file handle the four-file cache may close: the next stream step reads a closed file
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PREDICT-VIVEC-LOW-36](CHIM-PREDICT-VIVEC-LOW-36.md): The CHIM memory predictor under-predicts every Vivec district frame by 28-54 %: Vivec architecture decodes to 1.3-2.3 times the bytes per triangle it was fitted on
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-RECIPE-APRON-SCOPE-41](CHIM-RECIPE-APRON-SCOPE-41.md): Regional aprons lose original-cell visual recipes and regress the memory gate
- [CHIM-REGION-DIVIDED-CELLS-36](CHIM-REGION-DIVIDED-CELLS-36.md): Most converted land cells cannot switch to CHIM inside the open world: the legacy builder split them over several maps and a region frame replaces exactly one
- [CHIM-REGION-MARGIN-STORAGE-36](CHIM-REGION-MARGIN-STORAGE-36.md): One-cell CHIM region frames store about 3.5 times their cell's terrain (the terrain-only margin)
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
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
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold
- [CHIMPORT-OCEAN-LAND-41](CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells (land records entirely under water) are marked open ocean: CHIMport never plans them and the ocean admission refuses them
- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): CHIMport --retry-failed cannot rerun a lava cell of the island run: its stored source stage predates the lava conversion

<!-- END GENERATED CATEGORY -->
