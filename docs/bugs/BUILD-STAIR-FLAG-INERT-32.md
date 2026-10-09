# BUILD-STAIR-FLAG-INERT-32: The stair rule build option does nothing in v0.0.32

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 8 October 2026, in v0.0.32 |
| Where | follow_original_stair_rules (config/build-defaults.json, tools/build.py); no converter read it |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | low: Misleading option with no behaviour change; the v0.0.32 release notes claimed no effect. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32 |
| From commit | source and engine 0f467e4 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-dev with the stair work ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md)),
not shipped at the time of writing. Present in v0.0.32.

## Symptom

v0.0.32's builder has the option `follow_original_stair_rules` (`config/build-defaults.json`,
default true; `--[no-]follow-original-stair-rules`) and prints "Original stair rules: on", but no
converter reads it: switching it off changes nothing. The v0.0.32 release notes do not claim an
effect.

## Where

`tools/build_font_options.py` and `tools/build.py` (the option); the converters' shared collision
function `tools/mesh_geometry.py` (`collision_pieces`) did not consult it in v0.0.32.

## How it happened

The option was added to the builder configuration ahead of the stair rule, which was developed on a
separate branch and was not part of the release.

## Why it was not caught

The option's tests checked how it is resolved (default, configuration file, command line), not
that any build output depends on it.

## Reproduction

On v0.0.32: build with `--no-follow-original-stair-rules` and with the default; the converted maps
are the same.

## Repair

From the stair work merged on v0.0.33-dev: `tools/build.py` exports the resolved option as
`AMIWIND_STAIR_MITIGATION` (`tools/mesh_geometry_env.py`), and the shared collision function and
the image step's stair gate read it.

## Verification

`tests/test_stair_rules_collision.py`: `test_build_option_changes_the_collision_output` exports
the option on and off the way the builder does and checks that a buried staircase fixture gets
different collision (treads free with the option on, buried with it off);
`test_build_setting_reaches_the_shared_function` and `test_builder_exports_follow_original_stair_rules`
cover the plumbing.

## Prevention

A build option ships only with a test that shows a build output changing with it.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
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

<!-- END GENERATED CATEGORY -->
