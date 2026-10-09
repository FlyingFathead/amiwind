# CHIM-FAR-OBJECTS-33: Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM frames: placements past the active ring (636) up to the legacy overlap (896) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Part of v0.0.32's horizon at some poses (Balmora east bank at 18:00): the fog outline of houses across the river is missing on CHIM. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the CHIM world receipt records no commit: world built 8 October 2026 17:54 +03:00 on the v0.0.33-chim-format branch before 8caf66e (CHIM-RECEIPT-COMMIT-33) |
| Build note | found in the far terrain FS-UAE A/B on the CHIM Preview 1 image, 9 October 2026 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Present in CHIM Preview 1 and in the far terrain repair of
[CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md), which restores the ground only.

## Symptom

From Balmora's east bank (global -19300 -11800) looking east at 18:00, v0.0.32 shows the fogged
outlines of the houses across the river against the sky. CHIM shows the land outline (with the
far terrain layer) but none of those houses.

## Where

CHIM frames: placements whose owner chunks lie past the active ring (view distance 540 plus
hysteresis 96) but within the legacy overlap depth (896), in view past the fog plane.

## How it happened

v0.0.32's region maps hold every placement of 896 units of their neighbours, and the far plane
draws each model whose bounding sphere reaches the fog distance, fully fogged. CHIM links only the
placements of active chunks. The far terrain layer adds the ground in that band, not the objects.

## Why it was not caught

Found by the far terrain A/B (CHIM-FAR-TERRAIN-33): with `r_drawentities 0` the v0.0.32 view at
this pose keeps only scattered terrain fragments, so most of its horizon there is houses.

## Reproduction

`dbg tp -19300 -11800`, `dbg set time 1800`, look east (`aw_view` with yaw 0); compare v0.0.32,
CHIM with `chim_far 1` and v0.0.32 with `r_drawentities 0`.

## Repair

Not done. Tried: the drawn boxes of large placements stamped into the far heightfield
(`chim_far_objects 1`, experimental, off by default); on a 128-unit grid a house becomes a steep
peak, not a house. Proposed: each large model converted once to a few dozen triangles (the
distant shell prototype, `tools/mold_shell.py`) and placed by reference from the frame's
placements, drawn by the far terrain rasterizer in the fog colour; sprite trees by their alpha
mask (never rectangles, HORIZON-FLORA-SPRITES-32); memory and slow-preset cost measured first.

## Verification

Pending.

## Prevention

The far terrain A/B includes the legacy view without entities, so the share of objects in the
legacy horizon is measured at every pose.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
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

Related bugs in other categories:

- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky

<!-- END GENERATED CATEGORY -->
