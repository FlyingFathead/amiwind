# CHIM-REBUILD-COST-33: Each CHIM crossing rebuilds the whole frame world; the cost is not measured

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | CHIM frame-world rebuild per chunk crossing (engine) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.33 |
| Severity | medium: Each crossing rebuilds the whole frame world: 95-184 ms in a cycle-exact run, a visible hitch. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine unknown, world format unknown |
| Unknown because | registered before found-in-build records existed; found on a CHIM development branch, the finding commit and world format were not recorded |

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
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Fixed in source on v0.0.33-chim-engine (839b36e; dev1 memory defaults 0d8bf4f), not shipped at the time of
writing. Measured in FS-UAE with the JIT; the cycle-exact measurement is pending (deferred by the maintainer).
Found by the second CHIM engine slice (terrain in the world tree).

## Symptom

Every crossing copies the whole ring into a new pool and relinks every static entity (up to 512) and edict
(up to 600); peak memory is old plus new pool (estimate about 350 KB for a Balmora ring). A rebuild that
cannot get memory evicts every unlocked cache block first, throwing away prefetched data.

## Where

`engine/aga/src/chim/chim_graft.c`; `Cache_Alloc` behaviour.

## How it happened

Simplest correct rebuild first.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

Count and time rebuilds on a Balmora walk.

## Repair

The incremental frame world (`chim_graft_mode 1`, the default; docs/chim/ENGINE.md "The frame world"):

- every index-addressed array of the pool (nodes with their hull-0 clipnodes, leaves, marks, surfaces,
  surfedges, edges with their edge cache words, vertexes, planes, hull-1 clipnodes) has free ranges; a
  chunk that joins the ring is copied into free ranges, one that leaves gives its ranges back;
- nothing else moves: surfaces keep their surface cache blocks, leaves keep their efrags, edicts keep
  their leaf numbers. Only the entities in the leaves that change (the leaving chunk's and the grid's
  empty leaves) are taken out (`R_RemoveEfrags`) and linked again, and only edicts with a leaf there or a
  box over a changed chunk are linked again (`SV_LinkEdict`), as Quake does for a moving entity;
- the grid and the leaf PVS rows are rewritten (small); an update is planned on a copy of the free ranges
  first and either fits or becomes a repack (the whole ring laid out again in place, counted and said);
- a per-frame budget: chunks join nearest first, `chim_graft_kib` (16 KiB) plus one chunk a frame; chunks
  within the world's collision margin never wait (loads and joins, counted as urgent);
- prefetch ahead in the walking direction (`chim_lookahead`, default the prefetch margin);
- the full rebuild stays selectable (`chim_graft_mode 0`, DON'T DELETE ANY METHOD).

Counters: dbg rcount `rb` updates and their time, `gr` chunks joined/left/repacks and KiB copied, `cw`
CHIM work per frame, `sm` the nearest chunk without ground, `ur` urgent joins/loads, `zl` locked zone
bytes now/peak.

## Verification

9 October 2026, host tests (tests/test_chim_engine_native.py): frame by frame on a 400-frame walk with a
jump, the incremental frame world equals the full rebuild (leaves by chunk and template leaf, contents,
vis rows, ground traces, placement and static efrags, edict leaves); on a Balmora-sized frame it copies
669 chunks where the full rebuild copies 66,081. At one chunk a frame, the nearest chunk without ground
stays 456 units away (collision margin 224), with no urgent join and no repack after the first layout.

9 October 2026, FS-UAE with the JIT, busy host (relative numbers), Balmora's CHIM frame map, the same walk
per variant (1,536 units east and back, noclip), one session with a drift-control rerun:

| Variant | Updates | us per update median / max | KB copied per update (max) | Chunk copies | Nearest chunk without ground |
|---|---|---|---|---|---|
| Full rebuild (mode 0) | 122 | 907 / 2,301 | 405 | 4,504 | 603 |
| Incremental, no budget | 114 | 485 / 2,365 | 27 | 73 | 589 |
| Incremental, 16 KiB, no look-ahead | 140 | 510 / 2,846 | 16 | 89 | 251 |
| Incremental, 16 KiB, look-ahead (default) | 131 | 424 / 1,723 | 16 | 85 | 577 |
| Full rebuild again (drift) | 102 | 1,663 / 5,718 | 405 | 3,721 | 532 |

On the five benchmark cameras both methods give identical counters (entities sent, BSP nodes per clipped
face 8.6-9.9 against 27-52 for the legacy region maps). The per-second timing and frame peaks of that
session are not quoted: with `chim_debug 1` each update wrote a console line through the remote console
(REMOTE-CONSOLE-LOG-COST-32). The cycle-exact run (`chim_debug 0`) is pending.

8 October 2026, FS-UAE (emulator numbers are relative until a hardware number exists): one
frame-world rebuild per chunk crossing costs 0.7-3.5 ms under JIT, but 95-184 ms for 30-40 chunks
in a cycle-exact run (JIT off, CPU multiplier 7, busy host). On a 68040 that is a visible hitch at
every crossing. Suggested direction: an incremental frame-world pool that touches only the chunks
that changed. Pending: a hardware number.

## Prevention

Update time, bytes copied, chunks joined and left, repacks, CHIM work per frame and the safety margin in
the CHIM counters; a host test that the incremental frame world equals the full rebuild frame by frame;
a budget test that keeps the ground under the player.

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
- [CHIM-BALMORA-INSET-SLIVERS-43](CHIM-BALMORA-INSET-SLIVERS-43.md): Balmora's town frame hands over 96 units inside its cells: the 8 cells around the town keep classic strips, built as 15 legacy maps (11.5 MB) with every object of those cells
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-COMPILED-HULL-SHORT-36](CHIM-COMPILED-HULL-SHORT-36.md): Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units
- [CHIM-CROSSING-SLUGGISH-43](CHIM-CROSSING-SLUGGISH-43.md): Crossing between CHIM cells is sluggish, worst at cell corners
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
- [CHIM-PREDICT-VIVEC-LOW-36](CHIM-PREDICT-VIVEC-LOW-36.md): The CHIM memory predictor under-predicts every Vivec district frame by 28-54 %: Vivec architecture decodes to 1.3-2.3 times the bytes per triangle it was fitted on
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
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
- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold
- [CHIMPORT-OCEAN-LAND-41](CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells (land records entirely under water) are marked open ocean: CHIMport never plans them and the ocean admission refuses them
- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): CHIMport --retry-failed cannot rerun a lava cell of the island run: its stored source stage predates the lava conversion
- [CHIMPORT-SEABED-NO-ISLAND-42](CHIMPORT-SEABED-NO-ISLAND-42.md): Seabed cells measured as empty sea lose their island in the tracker: they drop out of the published reference and the build calls them unknown

Related bugs in other categories:

- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)

<!-- END GENERATED CATEGORY -->
