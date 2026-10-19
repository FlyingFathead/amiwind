# COLLISION-NC-FLAGS-32: Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 5 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 18:42 +0300: maintainer: four red editormarker meshes drawn under a bridge in the West Gash (cells -9,14 and -10,13; refs 481808, 481815; placements 263124, 256282)
- Reported with v0.0.43-dev2 at 2026-10-18 18:45 +0300: maintainer: editor markers in Khuul too; decided: ignored by default wherever placed, filtered out before any rendering
- Reported with v0.0.43-dev2 at 2026-10-18 19:20 +0300: Recorded 18 October 2026: the maintainer saw red editor-marker shapes under the West Gash bridges (cells -9,14, -10,13, -10,14) and in a Khuul longboat.
- Reported with v0.0.43-dev2 at 2026-10-18 20:27 +0300: maintainer: another red editor marker in Vivec Hlaalu canton by the dock (cell 2,-11, local -2255 1067 141); the pick hits the dock ex_v_dock_01
- Reported with v0.0.43-dev2 at 2026-10-18 20:51 +0300: maintainer: another editormarker under a pier/bridge, cell 2,-9 (CHIM placement 25089, ref 474259); fixed in the line (ee7be41), hidden from the next build

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Mesh converters (prepare_scenery.py collision flags) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev, v0.0.43-dev2 (last seen) |
| Severity | medium: Banners, rugs, hooks and waterfalls are solid where Morrowind lets the player pass. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 5 times; something has to be done](#persisting-reported-5-times-something-has-to-be-done)
- [Status: 18 October 2026](#status-18-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Partly fixed. The editor-marker part (MRK, hidden markers) is repaired for v0.0.43-dev4. The
no-collision part (NC, NCC, AvoidNode) is still open. Found by the collision census
([COLLISION_MESHES.md](../COLLISION_MESHES.md)); the maintainer saw the marker part in
v0.0.43-dev2.

Decided for the project, 18 October 2026: Morrowind's editor markers are ignored by default wherever
they are placed. They are filtered out at the builder input, before any rendering, across the whole
island. Marker objects that have a role (a sound or a particle effect) stay as invisible
objects; only the marker shape and its collision are dropped.

## Symptom

Morrowind NIFs mark models that do not block the player with a root `NiStringExtraData`:

- `NC...` (in the base game always `NCO`): no collision;
- `NCC`: camera collision only.

`MRK` hides `Tri EditorMarker` shapes, and `AvoidNode` subtrees are NPC pathfinding avoid
shapes. In the base game 373 NIFs carry `NCO`, 48 `NCC`, 9 `MRK` and 6 have an `AvoidNode`.

The mesh converters read none of them. The flagged models become solid:

- banners, tapestries, rugs (`furn_rug_big_*`), hooks and candles;
- ground flora placed in rooms;
- the Vivec banners (`ex_v_ban_*`) and waterfalls.

Placements that Morrowind does not collide with: Balmora exterior 220 of 1,519, Seyda Neen
exterior 214 of 635, Vivec Arena 109 of 433, Balmora rooms 1,177 of 3,408, Seyda Neen rooms 277
of 1,004.

Editor markers were drawn. In v0.0.43-dev2 the maintainer saw red marker shapes:

- under the West Gash bridges: cell -9,14 reference 481808 (CHIM placement 263124), cell -10,13
  reference 481815 (256282), cell -10,14 reference 481812 (256724), each a `Sound_Boat_Creak00`
  sound activator;
- in a Khuul longboat (cell -9,17): reference 465744 `Sound_Boat_Hull00`, a sound activator
  placed inside the boat `Ex_longboat02` (313081). The boat's own mesh has no marker shape; the
  boat's collision in front of the marker made a click pick the boat.

## Where

`tools/prepare_scenery.py` `model_geometry` and `export_refs`, and every converter that uses them
(towns, Seyda Neen, rooms, census, prison ship, world scenery). Only the flora sprite path
(`tools/prepare_tree_sprites.py` `collision_metadata`) honours `NC`/`NCO`; it does not know
`NCC`.

The editor markers reached the drawn scenery through `tools/import_town.py`
`split_references` (the source stage of every CHIM town and region frame). It left out only models
named `marker_*`, so `EditorMarker.nif` and the other MRK models went through.

## How it happened

The converter only distinguishes visual and `RootCollisionNode` triangles; the root string flags
were never read. The marker rule was a name test (`marker_*`), repeated with small differences
in each converter, never the rule the game uses.

## Why it was not caught

No comparison with Morrowind's collision rules (OpenMW
`components/nifbullet/bulletnifloader.cpp` `handleRoot`) existed until this census. No check
looked for marker shapes in a built world.

## Reproduction

List the root `NiStringExtraData` strings of each placed model. Every model with `NC*` is
converted with a solid collision proxy (`collision_pieces` without `collision_none`).

Editor markers: before the repair, a CHIM frame of any cell with a sound activator (for example
West Gash -9,14) placed `meshes/editormarker.nif` in its scenery index.

## Repair

Editor markers (v0.0.43-dev4). The rules are learned from OpenMW 0.51 and written as our own code
in one place, `src/mwad/markers.py`:

- rule from OpenMW `components/misc/resourcehelpers.cpp` (`isHiddenMarker`, used by
  `apps/openmw/mwworld/scene.cpp`): the placed objects `NorthMarker`, `PrisonMarker`,
  `DivineMarker` and `TempleMarker` have no model;
- rule from OpenMW `components/nifosg/nifloader.cpp`: a root `MRK` string hides the model's
  shapes named `Tri EditorMarker...` (any case);
- rule from OpenMW `components/nifbullet/bulletnifloader.cpp`: the same shapes leave the
  collision too; a `RootCollisionNode` stays (the invisible walls `EditorMarker_box_01/02`).

`TravelMarker` and `DoorMarker` are never placed in the masters; door and travel destinations live
in the doors' own records, which the builder already reads.

Where the rule is applied:

- `model_geometry` (the NIF reader of every converter) drops the marker shapes from the drawn and
  the collision geometry. A model left with nothing to draw stops with a named error;
- `tools/editor_markers.py` classifies each placement before any conversion. A marker placement
  leaves the drawn scenery and stays as a deferred record with its role: sound emitter, effect
  emitter, collision marker, script marker or hidden marker. Used by `import_town.split_references`
  (every CHIM town and region frame and the footprint probe) and the world survey; the room
  converter (`mwad.interior.omission_reason`) also refuses the hidden markers by id;
- the source stage writes `emitters.json`: one row per kept invisible marker (reference, cell,
  position, kind, object, script, sound and sound file, volume and ranges from the sound record,
  effect mesh). The engine does not use it yet; it is for the ambient sound and particle work.
  The table is built from the player's own game data and lives only in the build output;
- `export_refs` refuses a hidden marker, and after each scenery export the source stage checks that
  no placement is a marker and no model kept a marker shape (`require_none_drawn`). Either stops
  the stage and names the reference.

The invisible chargen walls keep working as before: `tools/prepare_character.py` reads them from
the master as collision boxes.

No-collision flags (NC, NCC, AvoidNode): not yet. Planned with COLLISION-RCN-SCOPE-32, in one
shared function:

- `NC*` and `NCC` mean `collision_none` for the player (AmiWind has no camera collision);
- `AvoidNode` subtrees are excluded.

Rooms and towns then lose these solids, so the actor-ground and walkability gates must be rerun.

## Verification

Editor markers, island-wide census of the original data (`tools/editor_markers.py census`, all
three masters): 4,705 marker placements in 177 exterior and 1,313 interior cells:

| Kind | Placements | Exterior | Interior |
| --- | ---: | ---: | ---: |
| Sound emitter (a script plays a looped sound) | 2,565 | 200 | 2,365 |
| Effect emitter (mist, steam, Ghostgate particles, water spray) | 778 | 421 | 357 |
| Hidden marker (north, prison, divine, temple) | 1,318 | 19 | 1,299 |
| Collision marker (invisible wall) | 30 | 24 | 6 |
| Script marker (script only) | 14 | 6 | 8 |

Every sound emitter names its sound record. 9 NIFs carry `MRK`. In each one the only drawn shape is
the marker, so no ordinary mesh loses a shape. The four reported references are sound emitters in
the emitter table. Synthetic tests in `tests/test_editor_markers.py`. In-game check of the West
Gash bridges and Khuul on the next build: pending.

## Prevention

- one rule (`src/mwad/markers.py`) and one classifier (`tools/editor_markers.py`) for every
  converter path, tested on synthetic NIFs;
- the source-stage check `require_none_drawn` and the run check `tools/editor_markers.py
  check-built RUN` fail when a built world would draw a marker;
- the emitter table has a schema (`validate_emitters`), checked when it is written.

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
- [STAIRS-VIVEC-ROOMS-JOINT-36](STAIRS-VIVEC-ROOMS-JOINT-36.md): Six flight steps in three Vivec rooms are blocked where one stair piece meets the next
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
