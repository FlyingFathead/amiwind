# CHIM-SEYDA-ACTOR-CONTACT-33: Seyda Neen's actors do not stand on the CHIM frame's ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | image step, tools/chim/frame_map.py actor_contact, Seyda Neen frame |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.41 |
| Severity | critical: The release candidate build stops |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33-rc1 from-scratch build (rc1-a18be05) |
| From commit | source a18be05, engine a18be05, CHIM world a18be05 |
| CHIM engine version | CHIM 0.1.0, engine a18be05, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [Combined-world readback, 15 October 2026](#combined-world-readback-15-october-2026)
- [Expanded-cell contact findings: 15 October 2026](#expanded-cell-contact-findings-15-october-2026)
- [Original height comparison: 15 October 2026](#original-height-comparison-15-october-2026)
- [Terrain repair and remaining grounding check: 15 October 2026](#terrain-repair-and-remaining-grounding-check-15-october-2026)
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

## Combined-world readback, 15 October 2026

The successor completes structural, heap, zone-walk and stair validation with
source and inputs unchanged. Six paired boundaries agree for terrain/water;
static scenery differs at the southern Seyda boundary. Model/sprite, final
actor contact, native and package acceptance remain pending.
[Static boundary finding](CHIM-FRAME-STATIC-SEAM-40.md).
Earlier failed or pending checkpoints below remain historical evidence.


## Expanded-cell contact findings: 15 October 2026

The v0.0.40-dev2 source-only actor carrier is integrated with the expanded
Seyda CHIM frame. All 1,390 scenery references match in both directions.
The canonical grounding pass records 13 supported placements and two held
findings: Nels Llendo (original reference 204678, blocked) and the dreamer
(reference 297837, unresolved mesh contact after the existing bounded search).
Both retain authored positions; no tolerance or exclusion was changed.

The subsequent final frame-map contact function also rejects both actors.
Neither its height nor bounded horizontal refit resolves them. Nels starts
inside collision even eight units above his authored origin. The dreamer has
sole gaps spanning 0.419 to 3.468 units; no single vertical correction satisfies
the unchanged -0.5 to 1.0 contact band.
The failure is preserved; no position, tolerance or omission was changed.
Matched original-game views, actual native contact and package checks remain
pending; historical town results below do not cover the expanded frame.

## Original height comparison: 15 October 2026

The original LAND samples match the terrain-source audit. At the two actor
centres inside cell (0, -9), the converted 128-unit triangles are approximately
8.8 and 4.2 local units above the fine source-grid surfaces. Direct collision
probes reproduce those converted heights. Coarse sampling therefore explains
terrain distortion at these sites; a cell-edge offset has not been established.

A local detail proposal is under review using existing terrain subdivision and
shared-edge sampling. It must preserve source heights, coordinate scale,
neighboring cell/chunk edges and the current contact guards. Exact original
triangle topology and matched native views remain separate checks. The fine
source slope under the dreamer still exceeds the whole-sole contact band, so
restoring detail alone is not established as a complete actor-contact repair.

The implementation reuses the existing terrain mesh and AmiQuake collision
trace path. Actual-game suspect-geometry captures are pending a native build
with the combined world and correct actor routing. No capture or seam acceptance
is claimed. Converted-cell totals are unchanged; both contacts remain open.

## Terrain repair and remaining grounding check: 15 October 2026

The current source restores the two measured dry LAND tiles at original spacing
and applies the reference diamond pattern. All 49 source cells and 207,025
coordinate round trips agree exactly; 5,460 shared-cell samples agree. The
26 port boundary segments and 68 affected chunk-edge subdivisions also agree
in the source geometry. Compiled and native seams remain unverified.

Nels has a feasible source-only origin height interval of approximately
133.146 to 133.373 local units under the unchanged contact band. This does not
yet establish final compiled collision support. The dreamer remains open:
its original-grid surface produces a whole-sole gap spread of 2.024 units,
exceeding the 1.5-unit band. Screening all 12,853 existing horizontal offsets
with the unchanged vertical bound finds no feasible whole-sole interval.
No actor positions were written and no path-clearance acceptance is implied.

Original runtime observation finds both actors present and reports ground
contact in six samples each, with natural horizontal and vertical position drift.
Their authored origins are not their final observed positions. Final original
views show the actors and slope, but rendered sole contact was not measured.
LAND ray heights follow the reference's accelerated-ray diagonal, which differs
from its render/contact triangle pattern; keep these measurements separate.

Compare original runtime grounding, model bottom and idle foot pose before
changing the actor policy. Keep source terrain correctness and actor contact
as separate gates. No actor exclusion or contact tolerance change is included.

## Status: 9 October 2026

Historical v0.0.33 correction and test; the expanded v0.0.40-dev2 findings
above remain open in the canonical register.

## Symptom

The v0.0.33-rc1 from-scratch build stopped in the image step: the CHIM frame map of Seyda Neen was refused
because nine residents stand between 1.2 units below and 3.3 units above the CHIM ground (tolerance -0.5
to 1.0).

## Where

`tools/chim/frame_map.py` (`actor_contact`), the parity check that every ground actor of a frame map stands
on the frame's own collision.

## How it happened

Seyda Neen's actors are baked by the actor stage on the recorded v0.0.31 region maps
(BUILD-SEYDA-REGEN-30), whose terrain was triangulated by an older converter. The CHIM frame's terrain is the
current builder's and lies up to about 4 units off at some spots; a few spots are steeper than the sole band
allows.

## Why it was not caught

The check was added on 9 October with fixture tests only; no full build with Seyda Neen on CHIM ran between
its addition and the release candidate.

## Reproduction

A full build with Seyda Neen on CHIM (the v0.0.33 default) from integration head a18be05.

## Repair

`actor_contact` refits a ground actor that fails on the frame with the legacy actor fitter's own rules: the
height alone within 4.5 units of the baked height, else the nearest offset spot of `actor_grounding` (up to
32 units) within 8 units of height, with support within 16 units of the original and a clear path from it.
Only the frame-map row changes; the region maps keep their placements. Each refit is recorded; anything
farther still refuses the map.

## Verification

On the rc1 stage: Seyda Neen 12 of 12 actors grounded, 9 refitted (6 by height only, -4.19 to +0.34 units;
3 moved 1.8 to 10.4 units); Balmora 18 of 18, none refitted. `tests/test_chim_frame_map.py` covers a refit
and a refusal beyond the limits.

Combined-world preparation stopped before a complete world and its validation
were produced. Preserve the passing source checks separately; this incomplete
output establishes no compiled contact, seam, native or package acceptance.

## Prevention

New frame-map gates run on a full build of every CHIM area before they are merged.

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
- [IMAGE-ROOM-MAPS-LATE-PASSES-48](IMAGE-ROOM-MAPS-LATE-PASSES-48.md): Image checks after the CHIM rooms install skip CHIM rooms: entity tracker 47 cells against 52, dressing 81 pieces against 99, actor contact 0 placements against 93
- IMAGE-ROOM-MAPS-OPTIMIZER-RECEIPT-48 (no report page): A CHIM rooms build stops at the map optimizer check: the room maps are staged but not in the optimizer receipt
- IMAGE-ROOM-MAPS-SKIP-PASSES-48 (no report page): CHIM rooms were installed before the image passes that write a room worldspawn, so CHIM room maps would miss interior sky, hand metadata and cell numbers

Related bugs in other categories:

- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md): Terrain triangle diagonals differ from the OpenMW 0.48 reference
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it

<!-- END GENERATED CATEGORY -->
