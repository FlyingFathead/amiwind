# BUILD-HULL-ROUTE-BUDGET-33: Routed standing hulls with copies overflow a legacy map's shared clipnode budget

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Legacy converter collider (prepare_mesh_bsp) with --model-hull auto, tools/routed_hull.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: A legacy map build stops: Seyda Neen's scene map went from 57,181 clipnodes past the 65,520 limit. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-chim-format (c04404f), not shipped. Found before any build used it.

## Symptom

`prepare_mesh_bsp` stops with "Clipnode budget exceeded" while writing Seyda Neen's scene map with
`--model-hull auto`: the map reaches 65,008 of 65,520 clipnodes at its 86th model. With chains the same
map has 57,181 clipnodes.

## Where

`tools/routed_hull.py` (nested routing with a copy allowance) as called by the legacy converter's
collider in `tools/prepare_mesh_bsp.py`.

## How it happened

The nested routing copies pieces that straddle a cut into both sides while an allowance lasts (1x, then
0.25x the model's own chain), and falls back step by step when the clipnode budget runs out. A CHIM model
is its own brush image with its own 65,520-clipnode budget, so that is safe there. In a legacy map every
model shares one budget: the first large models spent their allowance, and later models no longer fit.

## Why it was not caught

The routing was measured one mesh at a time against a full budget (COLLISION-HULL-CHAINS-33), and the
unit tests used single-model maps. The in-map check (a real map rebuilt with `--model-hull auto`) found
it.

## Reproduction

Rebuild a legacy scene with many large models with `--model-hull auto` on 5303a46: Seyda Neen's scene
map (`prepare_mesh_bsp.py --scene ... --out ...`).

## Repair

Legacy maps route without copies (`routed_hull.routing(mode, shared_budget=True)`): a model never takes
more than its chain plus one clipnode per cut, so the routed map fits wherever the chained map fits.
CHIM models keep the copy allowance.

## Verification

Seyda Neen's scene map rebuilt with `--model-hull auto`: 57,637 clipnodes (+456), 20 models routed, no
chain fallbacks; the worst chains 1.3 to 3.2 times shallower (the lighthouse 3,172 to 1,170, the thatch
tower 1,888 to 593). Tests: `tests/test_routed_hull.py`
(`test_a_map_shares_its_budget_so_the_legacy_routing_copies_nothing`).

## Prevention

Any change to collision layout in the legacy converter is checked on a real multi-model map, not only
per mesh; the hull audit (`tools/hull_chain_audit.py`) reports each map's clipnode total.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [COLLISION-TRACE-COST-33](COLLISION-TRACE-COST-33.md): Movement traces near large models walk long standing-hull chains: tens of ms per trace on a slow 68040 (emulator-relative)
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

Related bugs in other categories:

- [BUILD-CHIM-HULL-RING-33](BUILD-CHIM-HULL-RING-33.md): Routed and compiled CHIM model hulls grew Balmora's ring past the zone

<!-- END GENERATED CATEGORY -->
