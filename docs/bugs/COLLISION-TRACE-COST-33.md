# COLLISION-TRACE-COST-33: Movement traces near large models walk long standing-hull chains

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Standing hulls of house-size and larger placed models (chains), legacy maps and CHIM worlds |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Emulator-relative: a Balmora house costs 12-33 ms per movement trace on the slow preset; not yet measured on hardware. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source b5ae6ad, engine b5ae6ad, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine b5ae6ad, world format 0.5 |
| Unknown because | measured on private CHIM Balmora worlds built from the branch; no numbered build |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open; measured. All times here are relative emulator numbers (FS-UAE, cycle-exact 68040): no
hardware number exists yet. The repair (routed standing hulls for house-size models) is measured,
and the post-rc1 default is being decided against the memory of Balmora's tightest ring. This is
next-release work, not part of v0.0.33.

## Symptom

A converted model's standing hull is a chain of its convex pieces. Every movement trace whose box
touches the model walks that chain, and where the trace crosses a plane, the far side is walked
again for its contents. Balmora's large houses have chains 2,903 to 4,017 clipnodes deep.

Cost of one clipnode visit (the engine's same-side descent loop, a 68k bench in FS-UAE, cycle-exact
68040; general planes / axial planes):

| Profile | General planes | Axial planes |
| --- | ---: | ---: |
| Slow preset, 49.7 MHz | 1.36 us | 0.99 us |
| Benchmark profile, 24.8 MHz | 2.72 us | 1.98 us |

Visits per movement trace on CHIM Balmora models: a port of the engine's trace
(`SV_RecursiveHullCheck` with its split recursion and far-side contents walk), 400 random player
moves of 8 to 24 units starting within 32 units of the model's box. Times are mean visits x 1.36 us
(slow preset).

| Model | Chain depth | Chain: mean visits, slow preset | Routed: depth, mean visits, slow preset |
| --- | ---: | --- | --- |
| `ex_velothi_temple_02` | 4,005 | 24,365, 33.1 ms (p95 123 ms) | 1,824, 2,057, 2.8 ms |
| `ex_hlaalu_b_11` | 4,017 | 19,887, 27.1 ms (p95 93 ms) | 2,002, 2,067, 2.8 ms |
| `ex_hlaalu_b_21` | 3,961 | 17,246, 23.5 ms | 2,096, 2,636, 3.6 ms |
| `ex_hlaalu_b_18` | 2,903 | 9,209, 12.5 ms | 1,595, 2,022, 2.8 ms |
| `ex_velothi_entrance_02` | 741 | 1,392, 1.9 ms | 532, 235, 0.3 ms |
| `terrain_rock_wg_06` | 720 | 651, 0.9 ms | 354, 108, 0.15 ms |

A player frame makes about 8 movement traces, so a frame next to one of these houses spends tens of
milliseconds in collision on the slow preset.

## Where

Standing hulls of placed models, as both the legacy converter (`prepare_mesh_bsp` collider) and the
CHIM builder (`chim.models`) write them. The shipped v0.0.33 default is `--model-hull chain` for
both.

## How it happened

The converters always wrote one chain per model, which is exact and cheap for small models. Routed
hulls (`tools/routed_hull.py`) exist, but the shipped default keeps chains: routing pushed one
open-world flora region past its clipnode reserve (BUILD-ROUTED-FLORA-RESERVE-33), and Balmora's
tightest CHIM ring has only 2,528 B of headroom.

## Why it was not caught

Performance was measured with the JIT emulator, where collision is cheap, and with counts of drawn
faces. No measurement counted clipnode visits per trace.

## Reproduction

Build CHIM Balmora with `AMIWIND_MODEL_HULL=chain` and with `auto`, then count visits per trace on
the models above with a port of the engine trace.

## Repair

In source on v0.0.33-chim-format, for the release after v0.0.33:

- `--model-hull auto` is the default again, for the legacy converter and CHIM. The legacy open-world
  map that went past its flora reserve falls back to chains (BUILD-ROUTED-FLORA-RESERVE-33).
- One rule for the router and the hull audits: `routed_hull.CHAIN_DEPTH_LIMIT` = 256 clipnodes of
  chain depth. CHIM routes every deeper chain, and the audits report it (`hull_chain_audit.over_limit`).
- Heap fallback, in the shared builder (`chim.build.build_areas`), so every caller (chim_build,
  CHIMport) runs it: while a ring does not fit the CHIM zone, the routed mesh with the fewest
  standing clipnodes in its peak ring keeps its chain, and the world is built again. The CHIM receipt
  records it as `hull_fallback` (`kept_as_chain`, `kept_as_chain_for_memory`).

CHIM Balmora, measured:

| Rule | South-west ring | Meshes kept as chains |
| --- | --- | --- |
| Limit 256, no fallback | 1,920 B over | - |
| Limit 1,024, no fallback | 576 B over | - |
| Limit 1,024 with fallback | fits, 240 B headroom | `ex_hlaalu_b_23` |
| Limit 256 with fallback | fits, 240 B headroom | `terrain_rock_wg_12`, `terrain_rock_wg_10`, `siltstrider`, `ex_hlaalu_b_23` |

## Verification

Pending: the rule as the default, the heap gate passing on every frame, and visits per trace
recorded per frame. A hardware number is still needed.

## Prevention

The hull audits read the same limit as the router, so a model deeper than the limit is reported in
every build.

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

<!-- END GENERATED CATEGORY -->
