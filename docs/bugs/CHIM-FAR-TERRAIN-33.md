# CHIM-FAR-TERRAIN-33: A CHIM frame has no distant ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM frames (engine draw, builder data): no resident low-detail terrain layer; CHIM Preview 1 build |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Release blocker: the distant view is worse than v0.0.32's HORSTATOR APPROVED horizon in many places. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source cd01c08, engine cd01c08, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine cd01c08, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

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

Repaired in source on branch v0.0.33-chim-farterrain (not merged, not yet in a build); release
blocker for v0.0.33 until the owner has seen it in a build. Present in CHIM Preview 1 and every
CHIM build before the repair. Design and measurements: [FAR_TERRAIN.md](../chim/FAR_TERRAIN.md).

## Symptom

On CHIM the ground ends where the active ring ends. Beyond the view distance there is only fog and
sky colour, so valleys look empty (the owner's frame beyond the Balmora bridge at -17541 -15916) and
Vivec is not visible from the world. The legacy region maps draw these places much better: the
owner rated them "5/5 (or 4/5) in many places with the old one".

## Where

CHIM frames, in the builder data and the engine draw: there was no resident low-detail terrain
layer. Seen in the CHIM Preview 1 build.

## How it happened

v0.0.32 draws no separate distant world. Each region map holds 896 units of its neighbours' real
terrain on every side; the far plane keeps every BSP node that straddles the fog distance; the
palette fog paints that ground in the full fog colour; and the sky's lowest band is the same
colour. The result is the fogged land outline of the HORSTATOR APPROVED horizon. A CHIM frame
map's world is the frame world, which holds only the chunk ring (view distance plus hysteresis).
Beyond the ring, and past the frame's edge, there was no ground for the far plane and the fog to
work on. The original streamer plan included a resident layer of terrain and mold shells; it was
not built.

## Why it was not caught

The CHIM A/B poses were inside towns, where the ring holds everything in view.

## Reproduction

On a CHIM map, look across open ground past the view distance, for example from global -19300
-11800 east at 18:00 (`dbg tp -19300 -11800`, `dbg set time 1800`): v0.0.32 shows a fogged land
outline and houses against the sky, CHIM Preview 1 shows sky down to the near river bank.

## Repair

A far terrain layer per frame, stored once, small, resident for the whole map:

- Builder (`tools/chim/far.py`, a step of the CHIM build, on by default): the frame's exact LAND
  heights every 512 units over the frame plus one cell (Balmora 81 x 81 samples), the water level
  below it, and the drawn boxes of large placements as separate object stamps. The image step
  copies it beside each frame map as `maps/<frame map>.far` (a sidecar like a Quake `.lit` file;
  not part of the world format).
- Engine (`chim/chim_far.c`, `aw_horizon.c` `AW_HorizonGrid`): read at map start into the low
  Hunk (13,222 bytes for Balmora), drawn after the fog pass past the fog plane in the full fog
  colour, depth tested (resident geometry always wins), whole blocks culled, back faces skipped,
  up to the legacy overlap depth (`chim_far_reach` 896). It adds nothing to the BSP, the PVS or
  the entity lists.
- `chim_far 0` keeps the first method (no far land), `chim_far_reach 0` draws the whole layer,
  `chim_far_objects 1` (experimental, off) raises the object stamps.

## Verification

- Tests: the rasterizer against an independent ray oracle at 18 camera poses with pixel-exact
  block culling; the loader on the builder's files (damaged, foreign-frame, short and missing
  files refused; the Hunk reserve); the frame map's layer through the CHIM world test; the
  builder (exact LAND samples, stamps, file versions 1 and 2).
- FS-UAE, standard profile, headlamp off and on, at the owner's bridge poses (19:54, 19:58), the
  HORIZON-HOLES-31 east-bank position (18:00), the town centre north and south (13:00), the west
  at 19:30 and a raised view south-west: v0.0.32 release image, CHIM Preview 1, the repair at the
  default depth, CHIM before on the same engine (`chim_far 0`), the whole layer, legacy region
  maps in the same image with and without entities, and a drift-control rerun (identical
  counters). The renderer counters for the world and entities (`bm`, `bf`, `e`, `pl`) are equal
  with `chim_far` 1 and 0.
- At the owner's bridge pose v0.0.32 itself shows sky in the band below the horizon past the fog
  distance; the repair adds the fogged land outline there, as v0.0.32 drew it, continuous instead
  of the legacy far plane's fragments. At the east-bank pose most of v0.0.32's outline is houses
  (CHIM-FAR-OBJECTS-33); the ground layer does not replace them.
- Slow FS-UAE preset (68040, x14 cycle-exact; emulated time, relative): 30.6 to 43.7 ms a frame at
  the default depth (measured with object stamps on), 3 to 5 % of the frame; the whole layer 194 to 229 ms.
- Not yet: a build from the repository builder with the layer, Seyda Neen in FS-UAE (no CHIM image
  of it yet), the owner's look.

## Prevention

Every CHIM milestone A/Bs distant views against the last legacy release, not only town poses. The
far layer's own counters are in `chim` and on the `dbg rcount` line, so a missing layer (`far
off`) is visible in every counter table.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ALIAS-STATIC-HUNK-35](CHIM-ALIAS-STATIC-HUNK-35.md): Streamed alias statics load into the cache mid-map without being counted in the map's Hunk rest
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-FAIL-NO-FLOOR-35](CHIM-GRAFT-FAIL-NO-FLOOR-35.md): A CHIM map whose frame world cannot start loses its far terrain too: the player may spawn over void
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-MEASURE-EMPTY-FRAME-33](CHIM-MEASURE-EMPTY-FRAME-33.md): CHIM world measurement stops on a frame without models (every empty sea cell)
- [CHIM-MIPTEX-OFFSET-UNCHECKED-35](CHIM-MIPTEX-OFFSET-UNCHECKED-35.md): CHIM texture mip offsets are taken from disk unchecked: a wrong offset makes the rasterizer read past its block
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PACK-LRU-STREAM-35](CHIM-PACK-LRU-STREAM-35.md): A streamed model keeps a sector file handle the four-file cache may close: the next stream step reads a closed file
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-STATIC-PLACE-HOST-ERROR-35](CHIM-STATIC-PLACE-HOST-ERROR-35.md): Bad flora data at CHIM chunk activation ended the session with zone locks held; the next map then stopped the program
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-TILT-VARIANTS-SPLIT-33](CHIM-TILT-VARIANTS-SPLIT-33.md): Tilted placements each get their own model variant: 39,103 extra model variants on the base island, breaking store-once
- [CHIM-UNIT-CACHE-RACE-33](CHIM-UNIT-CACHE-RACE-33.md): Two processes storing the same CHIM unit at once: the second rename fails
- [CHIM-UNIT-FP-SOURCE-LAYOUT-33](CHIM-UNIT-FP-SOURCE-LAYOUT-33.md): The same mesh is converted again for every source stage: CHIM mesh unit fingerprints include archive offsets and texture list positions
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-VIEW-LEAF-NO-PVS-35](CHIM-VIEW-LEAF-NO-PVS-35.md): A view leaf without a visibility row draws everything, with no counter saying so
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33](CHIM-WINDOW-MOUNT-CROSS-CELL-33.md): A one-cell CHIM frame stops when a window placed in it mounts on a façade placed in the next cell
- [CHIM-WORLD-AUDIT-SCALING-33](CHIM-WORLD-AUDIT-SCALING-33.md): The CHIM world audits grow much faster than the world: the heap gate took 3.6 s for 171 frames, 473 s for 331, and over an hour for 844
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold

Related bugs in other categories:

- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view

<!-- END GENERATED CATEGORY -->
