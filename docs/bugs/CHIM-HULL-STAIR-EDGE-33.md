# CHIM-HULL-STAIR-EDGE-33: With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:chim-stairs |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | CHIM terrain standing hull (tools/chim/build.py frame_input, tools/chim/terrain.py chunk_terrain) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: The CHIM stair gate stops the build: one flight in Balmora cannot be walked (rise 3.98 at a chunk edge). |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | MiniWind v0.0.33-dev1 |
| From commit | source 08d0613, engine 08d0613, CHIM world 08d0613 |
| CHIM engine version | CHIM 0.1.0, engine 08d0613, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-chim-format (4b15583, 9904a04, b9093f3), ported to v0.0.33-miniwind
(76a324f) and v0.0.33-dev1-build; not shipped at the time of writing.

Provenance: found in the AmiWind "MiniWind" Playtester Build run mw-033a, version 0.0.33-dev1,
source v0.0.33-miniwind 08d0613 (engine from v0.0.33-chim-engine 1c65531), CHIM 0.1.0, world
format 0.5.

## Symptom

The CHIM stage stopped: "Stair walkability gate failed on the CHIM world: 1 flight steps cannot be
walked (first frames/x-03/y-02/frame.ccf ref 32841 ..., rise 3.98)". The step lies at a chunk edge.

## Where

`tools/chim/build.py` (`frame_input`: which standing hull a chunk's terrain gets) and
`tools/chim/terrain.py` (`chunk_terrain`), with `tools/collision_bsp.py` (`compile_standing`).

## How it happened

CHIM-SEYDA-MEMORY-33 introduced a standing hull compiled by qbsp (exact union, far fewer clipnodes)
for Seyda Neen's irregular ground, and made it the default whenever the build has qbsp (7e726c9),
which every build has. On Balmora's regular grid the compiled hull differs from the routed chains
by a few hundredths of a unit at chunk edges, enough to block one step of a flight next to it.

## Why it was not caught

The CHIM builder's own Balmora rebuild showed the failure, but it was written down only as a note
on CHIM-SEYDA-MEMORY-33 and fixed on the CHIM branch after the dev1 and MiniWind branches had
taken the earlier commit. The stair gate itself worked: it stopped the build.

## Reproduction

Build Balmora with `--builder chim` from 7e726c9 to 19cb63d: the CHIM stair gate fails on ref 32841.

## Repair

The compiled hull is the default for irregular ground only; regular grids keep the routed chains
(format 0.4's method, which holds them compactly and walks them exactly). Both stay selectable
(`terrain_hull`). The compiled hull's corner lattice went back to 1/64 unit.

## Verification

The CHIM stair gate on the next Balmora build (the gate is the regression check: it stops the build
on any failing flight).

## Prevention

A finding seen by a branch's own build goes into the tracker at once, not into a note on another
bug.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water

Related bugs in other categories:

- [CHIM-SEYDA-MEMORY-33](CHIM-SEYDA-MEMORY-33.md): Seyda Neen's CHIM ring was modelled larger than Balmora's: the irregular ground's routed standing hull

<!-- END GENERATED CATEGORY -->
