# IMAGE-ROOM-MAPS-LATE-PASSES-48: image checks after the CHIM rooms install skipped the CHIM rooms

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 22 October 2026, in v0.0.48-dev2 |
| Where | tools/build_aga.py finalize: check_actor_ground x.bsp glob, entity_tracker room entities only |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | high: the checks silently miss every CHIM room |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-chim_f577f015 |
| From commit | source f577f01, engine f577f01, CHIM world f577f01 |
| CHIM engine version | CHIM 0.2.1, engine f577f01, world format 0.12 |
| Platform or emulator | not in game (seen in the build receipts of the A/B images) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Status: 22 October 2026](#status-22-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [The sweep: every step after the install](#the-sweep-every-step-after-the-install)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 22 October 2026

Repaired on the v0.0.48 room-passes branch (22 October 2026); not in a build yet. Found in the in-game A/B of the
MiniWind Balmora rooms: A = today's room maps (2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-bsp_1336ba94), B = CHIM
rooms (2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-chim_f577f015).

## Symptom

The receipts of B, against A:

- entity tracker: 47 converted cells against 52; missing Dralcea Arethi's House, Dralosa Athren's House, Drarayne
  Thelas' Storage, Rarayn Radarys' House and Tharys Ancestral Tomb (their room maps and records are on B's disk);
- dressing track: 81 pieces in 18 maps against 99 in 19 (bmkarlirah missing);
- actor initial contact: 0 placements checked against 93.

## Where

`tools/build_aga.py` `finalize_image`: the CHIM rooms install (`chim.interior.install`, after the cell number pass,
IMAGE-ROOM-MAPS-SKIP-PASSES-48) turns every room map into `maps/<room>.chim` and moves its placed meshes out of the map
into the room record `chimi/rooms/<room>.crm`. The checks after it:

- `tools/check_actor_ground.py` `audit`: `maps.glob('*.bsp')`, so no CHIM room was read;
- `tools/entity_tracker.py` `refs_by_map` (the tracker and the dressing track): it read `.chim` files, but only their
  entities; a CHIM room's placed meshes are record placements, not entities, so rooms whose converted things were all
  placed meshes vanished and others lost their meshes.

## How it happened

The install moved to the end of the room passes, and each check kept its own way of finding maps (a literal glob, or
the map's entity lump). No check knew that a CHIM room keeps half its placements outside its map.

## The sweep: every step after the install

| step | what it read | now |
| --- | --- | --- |
| optimizer receipt | rooms joined unchanged (IMAGE-ROOM-MAPS-OPTIMIZER-RECEIPT-48) | unchanged |
| harvest install | `interior_rows`: x.bsp room maps only | a CHIM room's harvestable plants are listed per room in `harvest-staging.json` `chim_rooms_not_harvestable` and printed: they stay placed meshes (no catalogue for CHIM rooms yet) |
| actor initial contact | x.bsp | x.bsp and CHIM room maps (`map_files.scene_maps`); a room's actors stand on its store models, each moved and turned by its record (`chim.room_scene.RoomScene`); every room row and `chim_rooms` say so |
| empty MiniWind actor evidence | x.bsp | `scene_maps` |
| entity tracker, dressing track | entities of every map | plus the room record's placements (`chim.interior.installed_room_refs`) |
| actor table | `*.chim` files with `_chim_frame` | frame maps by their key (`map_files.frame_maps`) |
| arrivals, night lighting, legacy area removal, payload pruning | exterior maps only | unchanged (no room is read) |
| direct start (`--start` in a room) | `maps/<room>.bsp`, the map's own collision | `map_file`; a CHIM room's standing spot on its store collision (`chim.room_scene.room_collision`) |
| guard torches, engine map limits | `map_files` | unchanged |
| world map heap | every map as BSP: a CHIM room only as its shell | plus a zone gate per CHIM room: its models and textures against the zone the room map leaves (`chim.heap.require_room_map_heap`, `chim-room-heap.json`) |
| legacy maps summary | rooms counted as "interiors and other maps" | own kind "CHIM room maps" |
| content fingerprint | fixed before (IMAGE-ROOM-MAPS-FINGERPRINT-48) | unchanged |

The passes before the install (interior sky, hidden surfaces, hand metadata, cell numbers) run while the rooms are
still room maps, so their `.bsp` selection is right there.

## Repair

`tools/map_files.py`: `room_maps`, `scene_maps` (every x.bsp and every CHIM room map, never a frame map) and
`room_record_path`. `tools/chim/interior.py`: `installed_room`, `installed_room_refs`, `store_model_images` (only the
packs a room uses). `tools/chim/room_scene.py` (new, apart from the stair walk code of `tools/chim/collision.py`): `RoomScene`, `room_collision`. `tools/chim/heap.py`: `room_map_heap`,
`require_room_map_heap`. The steps above use them.

What is not checked yet, said in the receipts: the engine's piece tables (it tries them first for a turned
placement; the check uses the model's own hulls, cut from the same collision), and pickable plants in CHIM rooms.

## Verification

`tests/test_room_late_passes.py`: one room built in both forms (room map; CHIM room on a one-model store) gives the
same tracker placements, the same dressing pieces, the same actor contact (grounded on the store floor, and a floating
actor fails in both forms), the same direct start spot; the CHIM form's harvest plant is listed; its zone is checked.

Expected on B rebuilt with this repair (counted from B's own disk, not run yet): 52 converted cells, 99 dressing
pieces in 19 maps and 93 actor placements checked, as A.

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
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
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
- CHIM-FRAME-16MB-REFUSAL-48 (no report page): Five CHIM region frames are over or within 64 KiB of the 16 MB heap budget: on 16 MB of Fast RAM (or with Extra RAM off) their rings may not fit the zone
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
- CHIM-ROOM-16MB-REFUSAL-48 (no report page): On 16 MB of Fast RAM (or with Extra RAM off) a CHIM room larger than the zone ended the game with a host error at its door
- [CHIM-ROOM-EFRAG-LIMIT-48](CHIM-ROOM-EFRAG-LIMIT-48.md): The efrag pool limit can leave CHIM room placements undrawn in large rooms
- [CHIM-ROOM-ESTIMATE-48](CHIM-ROOM-ESTIMATE-48.md): 27 rooms set aside as too large for a CHIM room by a wrong estimate
- [CHIM-ROOM-HARVEST-DOUBLE-48](CHIM-ROOM-HARVEST-DOUBLE-48.md): CHIM rooms kept harvestable mushrooms in their room records: the image stopped on addamasartus (8 record placements not in the room map), and batch rooms had unpickable mushrooms
- [CHIM-ROOM-STORE-SWITCH-DROPS-MODELS-48](CHIM-ROOM-STORE-SWITCH-DROPS-MODELS-48.md): Switching CHIM room stores drops the kept models
- [CHIM-ROOM-SURFCACHE-LIGHT-48](CHIM-ROOM-SURFCACHE-LIGHT-48.md): The surface cache must rebuild when the same model is drawn at different room light levels
- [CHIM-ROOMS-WATER-LAVA-48](CHIM-ROOMS-WATER-LAVA-48.md): Rooms with water or lava are not converted to CHIM rooms yet
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
- IMAGE-FORMATS-CHIM-ROOMS-48 (no report page): The payload preflight stops a CHIM rooms build: the image step does not know the room store and room record formats
- IMAGE-ROOM-MAPS-ENGINE-REFUSED-48 (no report page): Every CHIM room is refused at its door and the game hangs on Loading: the engine accepts a .chim map only with a CHIM frame key
- IMAGE-ROOM-MAPS-FINGERPRINT-48 (no report page): A CHIM rooms build stops at the content fingerprint: it requires maps/<room>.bsp after the room became maps/<room>.chim
- IMAGE-ROOM-MAPS-OPTIMIZER-RECEIPT-48 (no report page): A CHIM rooms build stops at the map optimizer check: the room maps are staged but not in the optimizer receipt
- IMAGE-ROOM-MAPS-SKIP-PASSES-48 (no report page): CHIM rooms were installed before the image passes that write a room worldspawn, so CHIM room maps would miss interior sky, hand metadata and cell numbers

Related bugs in other categories:

- [ROOM-PYLON-ROOF-48](ROOM-PYLON-ROOF-48.md): Grand Inquisitor and Tamira Vian (Hall of Processing) stand inside collision: a convex piece of ex_stronghold_pylon01 slopes 14 units over the floor they stand on

<!-- END GENERATED CATEGORY -->
