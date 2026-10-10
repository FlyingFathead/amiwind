# VIVEC-TEMPLE-STAIRS-33: Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Vivec Temple frame (vivec_temple): ex_v_palace_steps_01, ex_vivec_hfq_01, ex_vivec_hfq_04 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Flights the player climbs in the original are blocked; the Temple frame cannot pass its stair gate until repaired. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 2a5bd0e, engine 2a5bd0e, CHIM world 2a5bd0e |
| CHIM engine version | CHIM 0.1.0, engine 2a5bd0e, world format 0.5 |
| Build note | vivec_temple CHIM world built from v0.0.33-chim-format with and without --cut-models-over 512 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open; measured. CHIM area: stairs. Found while measuring the whole of Vivec on CHIM (the canton cut work).
A private -devN DEBUG ONLY sandbox may accept these four placements by ID
(`--accept-known-stair-findings VIVEC-TEMPLE-STAIRS-33`, config/known-stair-findings.json) for the
in-engine walk that decides the repair; rc and final builds refuse it.

## Symptom

The CHIM stair gate stops a build of the `vivec_temple` frame on two meshes:

- `ex_v_palace_steps_01` (ref 428484, ref 428530): steps whose walk starts in solid, or is blocked by
  collision about 64 units above the step (risers 3.8 to 5.1 units).
- `ex_vivec_hfq_01` and `ex_vivec_hfq_04` (High Fane quarters, ref 484457, ref 484458): steps blocked by
  a 26.7-degree collision slope over the tread (risers 3.7 to 4.1 units).

## Where

The standing-hull collision of these meshes, as the shared collision layer builds it
(`mesh_geometry.collision_pieces` and the stair rule). The same flights fail with and without the
large-model cut, so the cut is not the cause.

## How it happened

Partly known (9 October 2026). The High Fane quarters use their authored collision
(`RootCollisionNode`, "approximate convex conversion"): a 26.7-degree ramp over the visible steps, which
the stair rule leaves alone. A traced walk on the frame's standing hull (at 1615.0, ref 484457, going -y)
stands on that ramp; the move up it meets a steep side surface (64 degrees, normal mostly sideways),
apparently the ramp's own side, so the authored ramp is narrower than the standing box. The engine's
movement (SV_FlyMove) slides along such a side plane; the gate's straight walker does not, so it reports
"blocked". Whether a player is really stopped there needs an in-engine walk and an OpenMW A/B. The palace
steps (`ex_v_palace_steps_01`, stair rule "vertical risers") start in solid or meet a vertical surface
64 units over the step: not yet traced. The legacy builder never converted the Temple frame
(VIVEC-HEAP-31 blocked it), so these meshes never met the stair gate before.

## Why it was not caught

The Temple frame had never been built.

## Reproduction

`tools/chim_build.py --area vivec_temple --qbsp ... --sdk ... --validate`.

## Repair

Not yet: inspect the meshes' collision pieces over the failing treads (convex proxy over the steps, or a
slope piece reaching over the riser) and fix at the shared stair rule.

## Verification

Pending: the stair gate on the Temple frame passes; A/B against OpenMW on the palace steps and a High
Fane quarter flight.

## Prevention

Every Vivec frame runs the stair gate; the frame list grows with the whole-city build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
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

<!-- END GENERATED CATEGORY -->
