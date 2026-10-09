# CHIM-HULL-CHAIN-COST-33: Large placed models collide through one long chain of convex pieces

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Standing hulls of large placed models (Vivec canton bodies), CHIM and legacy alike |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every movement trace near a canton costs thousands of plane tests on a 68040; the CHIM Arena stair gate took over 20 minutes. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 0560fd4, engine 0560fd4, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0560fd4, world format 0.5 |
| Unknown because | found in source on a CHIM branch; no CHIM world build recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Cause found; fix in progress on v0.0.33-chim-format. Performance.

## Symptom

The CHIM stair gate on the Vivec Arena world ran for over 20 minutes on 4 workers. A profile of one
core shows 369 traces costing 12.3 s. Almost all of it is one placed model: the Arena canton body
`ex_vivec_c_04`, with about 6,570 plane tests per trace. Its standing hull is one chain of 21,497
clipnodes.

## Where

Standing hulls of large placed models. The converter writes each model's convex collision pieces as
one chain (`prepare_mesh_bsp` collider, `chim.models.BrushLumps.collider`): outside one piece, test
the next. The engine walks the same chain for every movement trace near the model, CHIM and legacy
`func_wall` models alike.

## How it happened

Chains are fine for a few pieces. A canton body has hundreds, and its bounding box covers much of
the canton, so most traces in the Arena enter it.

## Why it was not caught

Town models have few pieces; no check counted collision work per trace.

## Reproduction

Profile `chim.collision.stair_task` on a core of the Arena frame.

## Repair

In source on v0.0.33-chim-format (9 October 2026), not shipped:
- Models with more than 16 pieces get their standing hull compiled by qbsp (one BSP of the
  expanded pieces), or routed when qbsp fails.
- qbsp fails on the two canton bodies (`ex_vivec_c_02`, `ex_vivec_c_04`), and the finest routing
  exceeds the clipnode budget: the routing then uses larger parts (8, 32, then 128 pieces per
  part) and keeps the chain only when none fits. Arena stair gate: more than 20 minutes before,
  about 6 minutes after.
- One implementation, `tools/routed_hull.py`, serves the CHIM builder and the legacy converter
  (`prepare_mesh_bsp.collider`). The legacy interiors had the same problem: the Arena Pit's main
  mesh (`in_v_arena_01`, 15,760 faces) was one chain of 36,545 clipnodes, and qbsp fails on it too
  (reported by the Arena interiors job; its own record follows with that job's branch).
- The chain stays selectable: `model_hull` / `--model-hull auto|chain|routed` (`auto` by default),
  exported as `AMIWIND_MODEL_HULL`. `tools/hull_chain_audit.py` lists every brush model's hull
  clipnodes and longest path in any map.

## Verification

Pending: clipnode visits per trace and the stair gate time on the Arena world.

## Prevention

`tests/test_chim_model_hull.py`: the routed hull classifies every point like the chain and visits
far fewer clipnodes.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
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

- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep

<!-- END GENERATED CATEGORY -->
