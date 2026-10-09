# BUILD-ROUTED-FLORA-RESERVE-33: routed standing hulls push an open-world map past its flora collision reserve

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | world-flora collision packing (prepare_world_flora.py), region vf0779 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: The full build stops; one of 2,532 open-world regions |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.33 pass 2 full build (p2g-628d39f) |
| From commit | source 628d39f, engine 628d39f, CHIM world 628d39f |
| CHIM engine version | CHIM 0.1.0, engine 628d39f, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Mitigated for v0.0.33: the shipped default is `--model-hull chain` again, the hull form of v0.0.32. The
routed hulls stay in the builder, selectable and tested. The repair is planned for the next release.

## Symptom

The first full v0.0.33 build with routed standing hulls in the legacy open world stopped in the
world-flora stage: region vf0779 found no collision packing within its reserves.

## Where

The world-flora stage (`tools/prepare_world_flora.py`) packs the flora's collision into each open-world
region map and admits the result only under fixed reserves, among them 32,767 clipnodes.

## How it happened

With routed hulls the region's scenery models take one extra clipnode per cut. vf0779 went from 29,347
to 29,829 clipnodes before flora; its aggregate flora packing from 32,614 (accepted) to 33,533 (refused).
The router respects the format's limit of 65,520 clipnodes per map, not the stage's reserve.

## Why it was not caught

The routed hulls were measured on the hull audit, Seyda Neen's map and the CHIM rings; no full build ran
the open world with them before this one.

## Reproduction

A full build from integration head 628d39f with `--model-hull auto`.

## Repair

For v0.0.33: `model_hull` in `config/build-defaults.json` is `chain`. Next release: a router that keeps
each map under the reserves of every later stage, then `auto` again.

## Verification

The next full build with the default passes world-flora on all 2,532 regions.

## Prevention

The default is pinned by `tests/test_build_builder.py`; a router change must pass a full build before it
becomes the default again.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
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

- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"

<!-- END GENERATED CATEGORY -->
