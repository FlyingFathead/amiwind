# STAIRS-EBONHEART-CHIM-36: Three Ebonheart flights fail the CHIM stair gate in the whole-city Vivec frame

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.36-dev4 at 2026-10-11 05:32 +0300: found: whole-city frame vivec_city stage B, 7 flight steps (refs 113805, 124537, 124459)
- Reported with v0.0.36-dev5 at 2026-10-11 09:41 +0300: PERSISTING: whole-city Vivec with rooms f6e08fe (dev5), accepted by ID for the dev MiniWind: same 7 flight steps
- Reported with v0.0.36-dev5 at 2026-10-11 09:56 +0300: maintainer order (TG): fix for rc1

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | Ebonheart edge of the vivec_city frame (cells 1,-13 and 2,-13): refs 113805, 124537, 124459 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: Flights the player climbs in the original are blocked or start in solid; the whole-city frame cannot pass its stair gate without accepting them |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | offline CHIM world vivec_city (v0.0.36-vivec-b) |
| From commit | source 714d6de, engine unknown, CHIM world 714d6de |
| CHIM engine version | CHIM 0.1.0, engine unknown, world format 0.5 |
| Unknown because | offline CHIM world, no engine built |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Open; persisting since v0.0.36-dev4 (CHIMport one-cell frames 1,-13 and 2,-13 on 9 October 2026, then the
whole-city frame in v0.0.36-dev4 and v0.0.36-dev5, accepted by ID for the dev MiniWinds only).
11 October 2026: repaired in source on the v0.0.36-stairs-rc1 line, verification build pending. rc and final
builds refuse `--accept-known-stair-findings`.

## Symptom

The CHIM stair gate of the `vivec_city` frame fails 18 flight steps. Eleven are the known Temple flights
([VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md)); seven are on three Ebonheart placements at the frame's
west edge:

- ref 113805 (three steps): the walk starts in solid against the neighbouring placement 113744, or is
  blocked at 28.6 degrees.
- ref 124537 (three steps): starts in solid against 113731, or blocked at 28.6 degrees.
- ref 124459 (one step): blocked at 22.9 degrees. This one lies inside the city's player area (core).

## Where

The standing-hull collision of these Ebonheart pieces where they meet their neighbours, as the shared
collision layer builds it.

## How it happened

Traced 11 October 2026 on the f6e08fe whole-city frame (all 7 flight steps reproduced offline). The three
bridges (`ex_imp_bridge_02`) run up through the arches of Ebonheart's walls (`ex_imp_wall_arch_01`, refs 113744,
113731 and 124473). The arch's authored collision (RootCollisionNode) is open: its front and back are flat
plates around the opening. collision_parts turned each flat plate into ONE convex piece, whose hull spans the
opening: the arch was a solid wall across the bridge (start in solid against the arch, or blocked by its vertical
face at the bridge's top). The proxy's fill test samples the triangles' centres, which all lie on the plate, so
a hole in a flat piece was never measured.

## Why it was not caught

They were seen in a CHIMport run and written into a plan note instead of the tracker.

## Reproduction

`tools/chim_build.py --area vivec_city --qbsp ... --sdk ... --validate` (wide coordinates).

## Repair

tools/mesh_geometry.py `collision_parts(..., plates)`: a flat piece whose hull covers more than HOLE_AREA
(32 square units) its own triangles do not becomes the authored plates of its triangles (convex polygons of
the plane, exact standing bevels): the opening stays open. For every mesh with such a plate (island-wide, not
only the arch: 14 plates per arch). The remaining steps that still graze the arch's sides pass along a line
8 units from the bridge's middle (`stair_walk.other_lines`, VIVEC-TEMPLE-STAIRS-33).

## Verification

Offline on the f6e08fe frame with the arches' and bridges' collision recomputed: all 7 flight steps pass.
Synthetic tests: tests/test_stair_rc1_fixes.py (PlateHoleTests). Pending: the whole-city MiniWind on the fixed
builder with no accepted stair findings.

## Prevention

Findings from CHIMport runs are registered at once, like any other.

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
- [STAIRS-MOLAG-ACCESS-38](STAIRS-MOLAG-ACCESS-38.md): Tel Uvirith walkway step and door stairs block normal walking
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- [STAIRS-VIVEC-ROOMS-JOINT-36](STAIRS-VIVEC-ROOMS-JOINT-36.md): Six flight steps in three Vivec rooms are blocked where one stair piece meets the next
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
