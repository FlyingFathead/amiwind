# STAIRS-VIVEC-ROOMS-JOINT-36: Six flight steps in three Vivec rooms are blocked where one stair piece meets the next

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.36-dev4 at 2026-10-11 08:37 +0300: found: whole-city Vivec with rooms try2 3734cf5, 6 flight steps in vdi012, voi025, vri000
- Reported with v0.0.36-dev5 at 2026-10-11 09:41 +0300: PERSISTING: whole-city Vivec with rooms f6e08fe (dev5), accepted by ID for the dev MiniWind: same 6 flight steps
- Reported with v0.0.36-dev5 at 2026-10-11 09:56 +0300: maintainer order (TG): fix for rc1

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | Vivec rooms vdi012, voi025, vri000: stair piece joints (room converter collision) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: Flights the player climbs in the original block at the joint step; the rooms cannot pass the image stair gate without accepting them |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | MiniWind v0.0.36-dev4 (vivec-city-chim) |
| From commit | source 3734cf5, engine 3734cf5, CHIM world 3734cf5 |
| CHIM engine version | CHIM 0.1.0, engine 3734cf5, world format 0.5 |
| Build note | run 2026_10_11_v0.0.36-dev4_miniwind-vivec-city-chim-vivec-whole-city-with-rooms-try2_3734cf5 |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Open; persisting since v0.0.36-dev4 (whole-city Vivec with rooms, try2 3734cf5, and again in v0.0.36-dev5
f6e08fe; accepted by ID for the dev MiniWinds only). 11 October 2026: repaired in source on the
v0.0.36-stairs-rc1 line, verification build pending. rc and final builds refuse
`--accept-known-stair-findings`.

## Symptom

The image step's stair walk fails 6 of 37,357 steps and ramps in the 130 rooms: in `vdi012` (ref 180421),
`voi025` (ref 181885) and `vri000` (ref 187806, ref 187808, ref 187809, ref 187813). Each is the top step (rise 3.16 units)
of one stair piece, blocked by the next piece's collision at 50.2 degrees.

## Where

The rooms' standing hulls where two stair modules meet (the shared room converter, the Balmora interior policy).

## How it happened

Traced 11 October 2026 (reproduced with the maintainer's mesh in a private lab: two chained pieces fail exactly
as in the rooms). All six are joints of `in_velothismall_stairs_01`. Its authored collision is a landing, a
26.8-degree ramp, and at the foot of the ramp a 50.2-degree toe 2.9 units tall. Where one piece's top landing
meets the next piece's foot, a standing box walking up steps up onto the toe: a step-up that moves forward
less than the toe's width (2.4 units) comes down on the 50-degree face, which is too steep to stand on, so
the step is refused (the gate moves 2 units per step; the engine refuses the same step at high frame rates).

## Why it was not caught

These rooms had never been converted (the Vivec district rows were never built with their rooms).

## Reproduction

The whole-city MiniWind (`--miniwind-preset vivec-city-chim`), image stair walk.

## Repair

tools/mesh_geometry.py `plate_toes` (in collision_pieces, for authored plates: rooms and exterior
architecture kept as authored surfaces): a plate steeper than walkable but not vertical, at most a step tall,
whose top edge lies on a walkable authored surface (a ramp or a tread) is replaced by a vertical plate through
its top edge, so the box steps over it as over any riser. One rule for every mesh with such a toe; the
receipt note says how many toes were cut.

## Verification

Private lab (the maintainer's mesh, three chained pieces): 2 flight steps failed at the joints before, 27 of 27
pass with the rule. Synthetic tests: tests/test_stair_rc1_fixes.py (ToeTests: the toe becomes vertical at the
ramp's foot; two chained pieces walk up with the rule and are blocked without it). Pending: the whole-city
MiniWind with rooms on the fixed builder with no accepted stair findings.

## Prevention

Every converted room runs the stair walk; a steep toe under a step is never kept as a slope.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-ACTOR-GATE-CHIM-FRAMES-36](BUILD-ACTOR-GATE-CHIM-FRAMES-36.md): The actor placement gate ignores CHIM frame residents: a CHIM-only build fails with no actors, and a blocked frame resident passes silently
- [BUILD-FLORA-STAIR-PLATES-BUDGET-36](BUILD-FLORA-STAIR-PLATES-BUDGET-36.md): The stair-plate collision rules raised a legacy open-world map past the BSP clip-node limit: world-flora failed on vf0779 (33,172 aggregate clipnodes > 32,767)
- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [CHIM-SEYDA-EXPANDED-STAIRS-40](CHIM-SEYDA-EXPANDED-STAIRS-40.md): Expanded Seyda CHIM frame fails stair walks at two original references
- [CHIM-STAIR-GATE-POOL-BROKEN-42](CHIM-STAIR-GATE-POOL-BROKEN-42.md): The CHIM stair gate of a whole-Vivec MiniWind stopped the build: a walk worker was killed
- [CHIM-VIVEC-DOCK-WALKWAY-43](CHIM-VIVEC-DOCK-WALKWAY-43.md): The player cannot climb the walkway at the Vivec Hlaalu canton dock and gets stuck
- [CHIM-VOS-TEMPLE-WALKWAY-41](CHIM-VOS-TEMPLE-WALKWAY-41.md): Vos walkway stair starts inside the Velothi temple's collision and fails the stair gate
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-ROUTE-NO-SPLIT-36](COLLISION-ROUTE-NO-SPLIT-36.md): Routed standing hulls of dense flora (kelp, kreshweed) stay one chain 277-305 clipnodes deep: the router finds no cut, so the cell stays hull-pending
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [COLLISION-TRACE-COST-33](COLLISION-TRACE-COST-33.md): Movement traces near large models walk long standing-hull chains: tens of ms per trace on a slow 68040 (emulator-relative)
- [COLLISION-TRACE-LIMIT-ROUTED-ROOM-36](COLLISION-TRACE-LIMIT-ROUTED-ROOM-36.md): The tool collision tracer stops on the Vivec Arena Pit's routed hull (visit limit), so its start spot cannot be traced
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIR-DETECT-POSITION-41](STAIR-DETECT-POSITION-41.md): Stair step detection depends on where a frame puts the placement: a few borderline steps are found in one frame's copy and not in another's
- [STAIR-FLIGHT-CORE-SPLIT-41](STAIR-FLIGHT-CORE-SPLIT-41.md): The stair gate marks flights per 1024-unit core: a flight that crosses a core line loses its flight mark, so its failures do not stop a build
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-EBONHEART-CHIM-36](STAIRS-EBONHEART-CHIM-36.md): Three Ebonheart flights fail the CHIM stair gate in the whole-city Vivec frame
- [STAIRS-MOLAG-ACCESS-38](STAIRS-MOLAG-ACCESS-38.md): Tel Uvirith walkway step and door stairs block normal walking
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
