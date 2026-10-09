# Stairs: Morrowind's own rules, and a gate that proves them

Status: 8 October 2026 (v0.0.32 development). Bug record:
[COLLISION-STAIR-SLOPE-32](bugs/COLLISION-STAIR-SLOPE-32.md). Background:
[collision meshes](COLLISION_MESHES.md), [stair ramp walkability](STAIR_RAMP_WALKABILITY.md).

## The rules we follow

Think in Quake first, then check the original:

| | Quake / AmiWind engine | Morrowind (OpenMW 0.51 source) |
|---|---|---|
| Step up | `STEPSIZE` 8.5 (`sv_move.c`, `sv_phys.c`) | `sStepSizeUp` 34 units = 8.5 here (`components/misc/constants.hpp` line 43) |
| Walkable slope | normal z >= `AW_WALKABLE_Z` 0.69, about 46.4 degrees (`quakedef.h`) | `sMaxSlope` 46 degrees (`components/misc/constants.hpp` line 44; `isWalkableSlope`, `apps/openmw/mwphysics/movementsolver.hpp` line 30) |
| Step down | 8.75 support glue (`aw_walk.c`) | `sStepSizeDown` 62 units = 15.5 here (`apps/openmw/mwphysics/constants.hpp` line 6) |
| Small-slope hack | none | `sMinStep` 10 / `sMinStep2` 20 (lines 8-9), `sDoExtraStairHacks` (line 12); not used here |
| Collision source | brushes; converted meshes as convex proxies | the authored triangles: the NIF `RootCollisionNode`, otherwise every triangle (`components/nifbullet/bulletnifloader.cpp` lines 139-222) |

Morrowind never collides against a convex hull, so its stairs are always the authored
surfaces: real steps, or (for most stair models) an authored ramp of at most 45 degrees.
Quake mappers make stairs walkable by clipping them with an invisible ramp brush. Our convex
proxies can do the opposite: a hull that takes in a wall, a railing arc or a block next to a
flight closes the treads or turns them into a slope steeper than walkable.

## The stair rule (shared collision layer)

`tools/mesh_geometry.py`, used by every converter (towns, open world, interiors, census, prison
ship; `prepare_mesh_bsp._prepare_model` and the size estimates call `collision_pieces`):

- `stair_treads(v, f)`: the stair treads of a mesh: level triangles joined by a riser (a group
  of near-vertical triangles at least 4 units wide) to another level triangle 1..8.5 lower.
  Rock ledges, leaves and trinkets without such steps have none.
- `mitigate_stairs(v, f, pieces, mode)`: a convex piece that buries a tread (the face above it
  stands more than 0.5 over it and is too steep to stand on, or more than a step over it)
  becomes the authored surface plates with exact standing bevels; past
  `STAIR_PLATE_BUDGET` plates, or in mode `ramps`, a walkable clip ramp through the nosings.
  A walkable ramp through the nosings is left alone; risers above 8.5 are not stairs (a wall
  stays a wall).
- Surface-plate meshes (interiors, Balmora's architecture list) that contain stairs get exact
  standing bevels on all their plates: an approximate (axial) standing hull of a turned or
  sloped plate grows into a spiral stairwell.

Interface for both builders (legacy and CHIM): `collision_pieces(v, f, profile, stairs=None)`
returns `(pieces, exact, note)`; `exact` is `True` (every piece) or a set of piece positions
that need exact standing bevels; `stairs` is `'on'`, `'ramps'` or `'off'` (default: the build
setting, `mesh_geometry.stair_mitigation_mode()`).

## The switch

`follow_original_stair_rules` in `config/build-defaults.json` (true), or
`--follow-original-stair-rules` / `--no-follow-original-stair-rules`, recorded in the build
receipt. `tools/build.py` exports it to every worker as `AMIWIND_STAIR_MITIGATION`
(`tools/mesh_geometry_env.py`: `on`, `ramps` as a measurement variant, `off` for debugging).
Off keeps the plain convex proxy and skips the gate.

## Large models: the routed standing hull

A placed model's standing hull is a chain of its convex pieces unless qbsp compiles it: a trace
that reaches the model's box walks the chain piece by piece, so its depth is its length (the
Arena Pit's main mesh was one chain of 36,545 clipnodes, and its stair gate ran 95 minutes on one
core). `tools/routed_hull.py`, shared by the legacy converter (`prepare_mesh_bsp`) and the CHIM
builder (`chim.models`), writes the same solid set as short chains behind axial clipnodes at the
expanded pieces' edges, cutting in x, y and z. Each cut is chosen by expected cost (the planes a
point test walks on each side, weighted by the side's share). Pieces that straddle a cut are copied
into both sides while a copy allowance lasts (1x, then 0.25x the chain's clipnodes) and are chained
at the cut after that; with no copies every piece is written once, so the routed hull fits wherever
the chain fits. In the legacy converter every model of a map shares one clipnode budget, so it routes
without copies: a model never takes more than its chain plus one clipnode per cut (with copies, Seyda
Neen's scene map went from 57,181 clipnodes past the 65,520 limit). The chain stays only when even that
does not fit (recorded in the converter's report, `model_hull`). Measured on the island's 20 worst meshes: 3 to 22 times fewer clipnodes visited per
test (COLLISION-HULL-CHAINS-33).

`model_hull` in `config/build-defaults.json` (`chain` in v0.0.33), or
`--model-hull auto|chain|routed|balanced`, exported as `AMIWIND_MODEL_HULL`: `chain` keeps the
earlier form (one chain per model; the v0.0.33 default, because routed hulls can push a legacy map
past its collision reserve: BUILD-ROUTED-FLORA-RESERVE-33), `auto` routes models above 16 convex
pieces (CHIM models above 256), `routed` routes every model, `balanced` is the first routing (parts of at most 8, 32
or 128 pieces, xy cuts). A model compiled by qbsp keeps its compiled union.
`tools/hull_chain_audit.py MAPS...` lists every brush model's hull clipnodes and longest path,
worst first.

## The gate

`tools/stair_walk.py`, run by the image step on the final maps (`stair-walk.json`) when the rules
are on. It finds the visible steps and route ramps of every placed model in every map (town
regions in their cores, interiors and open-world regions whole), and walks the standing box
over each step with the engine's movement rule (move; when blocked, step up 8.5, move on,
settle on a floor with normal z >= 0.69), up and back down, from visible ground with the
player's height and box free.

- A build fails on any step of a flight (3+ steps in a row with 2+ vertical risers) that the box
  cannot climb or descend: blocked, or collision solid where the visuals are open. The report
  gives the map, reference, model (when known), position, rise, the blocking surface angle and
  the collision surface over the step.
- What the walk counts as a step, a start and an obstacle (9 October 2026, from the last four
  failing flights; tests in `tests/test_stair_walk_cases.py`):
  - A riser is a drop at the shared edge of two level faces, not a difference of their mean
    heights: two tilted cave-floor triangles meeting along one edge are not a step
    ([STAIRS-ADDAMASARTUS-32](bugs/STAIRS-ADDAMASARTUS-32.md)).
  - The walk settles from 8 units above the start; when that point is solid (a low arch lintel
    over the foot of a flight whose authored collision ramp runs through the nosings, above the
    visible tread), it settles from the highest free point of the column between the start and
    there. A column with no free point is still "start in solid"
    ([STAIRS-BALMORA-B01-32](bugs/STAIRS-BALMORA-B01-32.md)).
  - Collision plates stand 0.2 off every visible surface (`shell_collision_parts`). A start box
    that comes closer than 0.25 to a visible wall or post (the gate's own visual check allows
    0.5) is not an open start: the line is retried up to 3 units to either side, then further
    back; a walk that is blocked where the box, grown by 0.25 sideways, meets visible geometry is
    untestable ("visible geometry in the way"), not a collision failure
    ([STAIRS-SEYDA-WAREHOUSE-32](bugs/STAIRS-SEYDA-WAREHOUSE-32.md),
    [STAIRS-BALMORA-WESTSOUTH-32](bugs/STAIRS-BALMORA-WESTSOUTH-32.md): a closed hinged door at
    the foot of a flight). Collision solid where nothing visible is near still fails.
- Advisory (reported, not failing): lone steps (curbs, ledges), route ramps (a local walk cannot
  tell a reachable ramp from a slope inside a hidden cavity), collision lower than the visuals
  and collision missing under the approach ([COLLISION-CONVEX-LOSS-32](bugs/COLLISION-CONVEX-LOSS-32.md)).
- The recorded Seyda Neen stage (BUILD-SEYDA-REGEN-30) is reported but does not fail the build.

Interface for both builders: `check_polys(polys, scene, core=None, contents=None, proxy=None)`:
`polys` as `stair_walk._faces` returns them (`[(points, ref)]`, `'world'` for terrain),
`scene` anything with `.trace(start, end)` like `audit_walkability.Scene` on hull 1.
