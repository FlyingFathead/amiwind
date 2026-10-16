# CHIM-FRAME-EDGE-EFRAG-CRASH-36: R_StoreEfrags: Bad entity type 270440 ends the game: a leaf link to an entity whose model is NULL (normal play in Seyda Neen; noclip past the Vivec frame edge)

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.36-dev5 at 2026-10-11 11:33 +0300: README shots session, whole-city Vivec MiniWind, FS-UAE interpreter: noclip view past the frame edge
- Reported with v0.0.36-dev5 at 2026-10-11 13:09 +0300: owner, dev5 playtest build 6c29a23, FS-UAE JIT, normal play: Seyda Neen near the shack, backing off from a hostile NPC
- Reported with v0.0.36-dev5 at 2026-10-11 13:19 +0300: owner, dev5 playtest build, FS-UAE: frozen frame during combat in Seyda Neen, punch sound and music looping (a hang; same corruption suspected, not proven)
- Reported with v0.0.36-dev5 at 2026-10-11 13:32 +0300: owner, dev5 playtest build, FS-UAE: same message outside Balmora by the bridge with the pylon, player idle, the vanity camera orbiting

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | engine cl_main.c CL_RelinkEntities (cause); r_efrag.c R_StoreEfrags, R_RemoveEfrags |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | critical: Ends the game in normal play of a shipped playtest (Seyda Neen); blocks v0.0.36-rc1 |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | Platform: FS-UAE 3.1.66, JIT, A1200 68040; dev5 playtest build 6c29a23 (owner) and MiniWind f6e08fe (README session) |
| Platform or emulator | FS-UAE, JIT (owner, dev5 playtest build); FS-UAE interpreter (README session) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Status: 11 October 2026](#status-11-october-2026)
- [Symptom](#symptom)
- [Evidence](#evidence)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 11 October 2026

Open and PERSISTING: four reports, three in normal play of the v0.0.36-dev5 playtest. **Root cause found and confirmed**
by a same-scene comparison: the third-person view's player body overwrote the client's entity loop pointer
(`cl_main.c`, `CL_RelinkEntities`). The fix of that line lands separately (the third-person bug's branch). This page's
safety nets and the CHIM link order are in source and gated (gate 2091). This bug blocks v0.0.36-rc1 until both are in.

## Symptom

The game stops and the AmigaDOS shell shows "AmiWind v0.0.36-dev5 crashed! Crash details: R_StoreEfrags: Bad entity
type 270440", or the game freezes with its audio looping. Reports:

| Report | Build | Platform | What the player did |
| --- | --- | --- | --- |
| 11 October 2026, README screenshot session | MiniWind f6e08fe (whole-city Vivec) | FS-UAE 3.1.66 | a noclip view to local (0, -7500, 500), outside the frame (+/-5,376) |
| 11 October 2026 13:09, owner | dev5 playtest 6c29a23 | FS-UAE, JIT | normal play in Seyda Neen near the shack, backing away from a hostile woman, after switching between first and third person (owner, 14:09) |
| 11 October 2026 13:19, owner | dev5 playtest 6c29a23 | FS-UAE | combat with an NPC in Seyda Neen: the frame froze, the punch sound and a short piece of music looped (a hang, no error screen) |
| 11 October 2026 13:32, owner | dev5 playtest 6c29a23 | FS-UAE | outside Balmora by the bridge with the pylon, before entering the town, player idle, the idle (vanity) camera orbiting |
| Total | 2 builds | FS-UAE | 3 crashes with the same message and value, 1 hang |

After the crash the AmigaDOS shell and the next run also mangled the keyboard
([ENGINE-CRASH-EXIT-KEYBOARD-36](ENGINE-CRASH-EXIT-KEYBOARD-36.md)).

## Evidence

The value 270440 is not a model type. `R_StoreEfrags` reads `clmodel->type`, 68 bytes into `model_t`. With a NULL
model that read goes to Amiga address 0x44, which does not fault on a 68k Amiga and returns the same long every time.

Same scenes, same dev5 playtest image, FS-UAE JIT, scripted engine smokes (`tools/engine_smoke.py --script`).
"Nets only" is the engine with this page's safety nets; "with the fix" adds the separate body pointer in
`CL_RelinkEntities`:

| Scene | Nets only | Nets and the fix |
| --- | --- | --- |
| Balmora south (dbg tp -20480 -15500), idle camera orbiting for about 5 minutes | the safety net caught a bad link within 45 s (2 of 2 runs) | no bad link the whole time (1 of 1) |
| Seyda Neen (-12631 -72274): third person, walk and attack, back to first person, back off and attack, three times | the game froze about 4 s after entering third person, clock stopped (2 of 2) | ran to the end, no bad link (2 of 2) |
| Total | 4 of 4 runs damaged or frozen | 3 of 3 clean |

Without the safety nets, the dev5 engine read the same damage as the crash or the freeze. Earlier engine smoke runs
past the Vivec frame edge did not repeat the first report (4 runs), and neither did six other spots around Balmora.

## Where

- **The cause:** `engine/aga/src/cl_main.c`, `CL_RelinkEntities`. The third-person hook replaced the loop's entity
  pointer with the player body's: `ent = aw_view_body (ent)`.
- Where it showed:
  - `engine/aga/src/r_efrag.c`: `R_StoreEfrags` (the error) and `R_RemoveEfrags` (walks through a damaged link).
  - The CHIM streamer's link bookkeeping (`chim/chim_chunks.c` `Deactivate`, `chim/chim_statics.c` `Unplace`):
    correct with intact data, hardened here.

## How it happened

`CL_RelinkEntities` walks the client's entities with one pointer, `ent`, advanced by the loop (`ent++`). The
third-person view (added 10 October 2026) draws the player's body in place of the player's entity. It did so by
assigning the body to that same pointer: `ent = aw_view_body (ent)`. The body is one static entity in `aw_view.c`.

From then on, every later entity of that frame was walked in the memory after the body. The loop wrote into it
(model cleared for "not in the last packet", positions, the forcelink flag) and called `R_RemoveEfrags` on whatever
efrag pointer it found there. That left damaged links in the world's leaves: links to an entity without a model, links
without a leaf, loops.

Later the renderer met them:
- a link with a NULL model ended the game with this message;
- a looping chain froze the frame while the audio buffer kept playing.

It needed the third-person, idle (vanity) or death camera, but the damage stayed after switching back to first person.
That explains the owner's Seyda Neen crash after "juggling between first and third person".

## Why it was not caught

- The engine smokes and the gate run in first person; no step switched to third person or waited for the idle camera.
- No test or check walked the leaves for links to entities without a model.
- `R_StoreEfrags` was Quake's own check: a damaged link ended the game instead of being reported.

## Reproduction

Always within a minute, before the fix:
- dev5 playtest, FS-UAE JIT, Seyda Neen, switch to third person and walk (the freeze);
- or idle at Balmora's south approach until the idle camera orbits (a damaged link; the dev5 engine crashes when the
  renderer meets it).

## Repair

1. **The cause** (the third-person bug's branch): the body is drawn through its own pointer, and `ent` stays in
   `cl_entities`. Verified as above.
2. **Labelled safety nets** (in source, gate 2091), so a damaged link can never end the game or hang it again:
   - `R_StoreEfrags` leaves an entity without a valid model out of the frame;
   - `R_StoreEfrags` and `R_RemoveEfrags` cut a looping leaf chain;
   - `R_RemoveEfrags` does not walk a link without a leaf (that walk read and wrote low Amiga memory, the CPU's
     exception vectors).

   Every use is counted (`aw_efrags_bad`, the state file's `efrags_bad`), and the entity and the reason are printed
   once on the console. The engine smoke fails when the net was used.
3. **CHIM link order:** `Deactivate`, `Unplace` and `ChimChunks_ReleaseEfrags` remove an entity's links before
   clearing its model, whatever its counters say.

## Verification

- The comparison table above (the cause).
- `tests/test_efrag_safety_source.py`: the nets, the loop cuts, the CHIM order, the smoke failing on the count.
- `tests/aga_remote_test.c`: the state file line.
- Gate 2091: 3,902 tests, 0 failures, engine 0 warnings, boot smoke.

## Prevention

- The engine smoke fails whenever the safety net was used.
- Scripted smokes for third person, the idle camera and switching back to first person (the scripts above) belong in
  the regression set for the camera code.
- The same-pointer pattern: an entity loop never reassigns its own loop pointer (review rule for every hook in
  `CL_RelinkEntities` and the renderer's loops).

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
- [CHIM-COMPILED-HULL-SHORT-36](CHIM-COMPILED-HULL-SHORT-36.md): Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units
- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-EMPTY-POINT-HULL-36](CHIM-EMPTY-POINT-HULL-36.md): A CHIM model without collision has no point-hull node: the engine reads it as solid, or refuses it on load
- [CHIM-FAR-BAND-GAP-36](CHIM-FAR-BAND-GAP-36.md): From a CHIM area's border the ground ends at the frame edge: up to 476 units with no land before the fog plane
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FERN-NCO-SOLID-38](CHIM-FERN-NCO-SOLID-38.md): Fire ferns marked NCO become solid in CHIM mesh conversion
- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)
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

Related bugs in other categories:

- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person

<!-- END GENERATED CATEGORY -->
