# Step movement: Morrowind's stair and slope rules in AmiWind

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Short answer](#short-answer)
- [Units](#units)
- [OpenMW's rules](#openmws-rules)
- [AmiQuake's rules (AmiWind today)](#amiquakes-rules-amiwind-today)
- [Side by side](#side-by-side)
- [Differences that change what can be climbed](#differences-that-change-what-can-be-climbed)
- [The method](#the-method)
  - [(a) The engine: step like OpenMW](#a-the-engine-step-like-openmw)
  - [(b) The data: traversable by construction](#b-the-data-traversable-by-construction)
- [Prototype test results](#prototype-test-results)
- [Evidence: the stair meshes of the v0.0.47-dev2 build](#evidence-the-stair-meshes-of-the-v0047-dev2-build)
- [Proposal (the maintainer's decision)](#proposal-the-maintainers-decision)
- [References](#references)

<!-- contents end -->

Status: 22 October 2026 (v0.0.48 development). A design note and a prototype behind a console variable,
`aw_step_rules`, default 0: the shipped behaviour does not change. Bug register:
[STEP-MOVEMENT-OPENMW-RULES-48](bugs/STEP-MOVEMENT-OPENMW-RULES-48.md). Related:
[Morrowind collision meshes](COLLISION_MESHES.md) ("Stairs and ramps", "Stair collision method 1"),
[CHIM-STAIR-COLLISION-MESH-47](bugs/CHIM-STAIR-COLLISION-MESH-47.md).

The question, from the maintainer: how does OpenMW make Morrowind's stairs and slopes traversable, and how does
that compare with AmiQuake's movement, so that a stair works by rule, with no brute-force walk? "We already have
the data."

The rules below are read from the OpenMW 0.51.0 source (GPL-3.0, like this project) and reimplemented in
AmiWind's own engine code; no OpenMW code is copied. OpenMW is the reference for the logic; the original game data
is the reference for what the stairs are.

## Short answer

- The player's box is the same in both: Morrowind's humanoid bounding box, 29.28 x 28.48 x 133 Morrowind units, is
  AmiWind's standing hull 14.64 x 14.24 x 33.25 at the converter's scale 0.25.
- The step height is nearly the same (34 Morrowind units, 8.5 map units), and so is the walkable slope (46 degrees
  against AmiWind's 46.4). The other rules differ: how a step is tried, how far the ground is followed down, and
  what a too-steep slope does.
- Morrowind's stairs are traversable because of their authored collision, not the step: the collision of a stair
  is a ramp at or under 45 degrees ([Stairs and ramps](COLLISION_MESHES.md#stairs-and-ramps)). With those ramps as
  the collision and the engine's slope rule at 46 degrees, a stair is traversable by construction. One check by
  arithmetic per mesh shows it, with no walk.
- The prototype, `aw_step_rules 1`, steps by OpenMW's rules. Over synthetic risers, ramps, lips and drops its
  results match OpenMW's rules in every case (the table below); the Quake rules differ in 9 of the 25 cases.
- On the 97 exterior meshes with flights of stairs in the v0.0.47-dev2 build, the step rules with stair collision
  method 1 built for them pass the check on 87. The other 10 are named below.

## Units

Morrowind units convert to map units at 0.25 (`tools/chimport.py` `SCALE`, the scale of every converted frame;
`tools/player_hull.py`: "NIF base_anim collision half extents (29.28,28.48,66.5), at world scale .25"). In this
note "MW" is Morrowind units and "units" are map units.

| Quantity | Morrowind units | Map units |
| --- | --- | --- |
| Step up (`sStepSizeUp`) | 34 | 8.5 |
| Step down (`sStepSizeDown`) | 62 | 15.5 |
| Ground offset (`sGroundOffset`) | 1 | 0.25 |
| Second and third step tries (`sMinStep`, `sMinStep2`) | 10, 20 | 2.5, 5 |
| Collision margin (`sCollisionMargin`) | 0.2 | 0.05 |
| Player box half extents | 29.28, 28.48, 66.5 | 7.32, 7.12, 16.625 |

## OpenMW's rules

From OpenMW 0.51.0, `apps/openmw/mwphysics/` and `components/misc/constants.hpp`:

- **Constants.** `components/misc/constants.hpp`: `sStepSizeUp = 34`, `sMaxSlope = 46` (degrees).
  `apps/openmw/mwphysics/constants.hpp`: `sStepSizeDown = 62`, `sMinStep = 10`, `sMinStep2 = 20`,
  `sGroundOffset = 1`, `sCollisionMargin = 0.2`, `sMaxIterations = 8`, `sDoExtraStairHacks = true`. These are code
  constants, not game settings: OpenMW does not read a step or slope GMST for the player's movement. The same two
  numbers also set the navigation mesh (`components/detournavigator/settings.cpp`: `mMaxClimb = sStepSizeUp`,
  `mMaxSlope = sMaxSlope`).
- **Walkable slope** (`movementsolver.hpp` `isWalkableSlope`): a surface is standable when its normal's z is
  strictly greater than cos 46 degrees (0.694658).
- **The player's shape** (`actor.cpp`): a box with the half extents of the model's collision box
  (`base_anim.nif`: 29.28, 28.48, 66.5); the default setting `actor collision shape type = 0` is an axis-aligned
  box that does not turn with the actor. The box rides `sGroundOffset` (1 unit) over the ground it stands on.
- **The move** (`movementsolver.cpp` `MovementSolver::move`): the box is swept along its velocity, up to 8 times
  a frame. When it hits something that is not an actor, and the contact point is lower than `sStepSizeUp` over the
  box's bottom, a step is tried. When the step fails, the box slides along what it hit. If the box was on the
  ground and what it hit is too steep to stand on, its normal is laid flat (z = 0) first, so a steep slope is a wall.
  The slide never raises the box's vertical speed on a too-steep surface ("Do not allow sliding up steep slopes").
- **The step** (`stepper.cpp` `Stepper::step`):
  1. up: the box is swept up by `sStepSizeUp` (stopped by a ceiling, less the margin);
  2. forward, at that height, in up to three tries: the frame's own move; then a fixed 10 units; then a fixed
     20 units (the second and third only on the first bounce of the frame; the code calls them work-arounds for
     the original assets);
  3. down: by the forward distance plus the height gained plus `sStepSizeDown` (62), or for the third try only
     back to the start height;
  4. the step holds when the down sweep lands on a walkable slope that is not an actor; in the air it may not end
     lower than it rose.
- **The ground test** (end of `MovementSolver::move`): a box that was on the ground is swept down by
  `sStepSizeDown + 2 x sGroundOffset` (64) and put on what it finds. On a walkable slope it stands there; on a
  steeper one it is "on a slope" and slides.

## AmiQuake's rules (AmiWind today)

From `engine/aga/src`:

- **Walkable slope** (`quakedef.h`): `AW_WALKABLE_Z 0.69` (normal z at least 0.69, about 46.4 degrees), raised from
  Quake's 0.7 so the 45-degree Hlaalu stair ramps hold ("Inspected Hlaalu stair ramps reach normal Z=0.69766").
- **The player's shape** (`model.c` `Mod_LoadClipnodes`, `tools/player_hull.py`): hull 1, the box 14.64 x 14.24 x
  33.25, swept through the map's precompiled clipping hull. The box rests 0.03125 units over the ground (Quake's
  `DIST_EPSILON`).
- **The move** (`sv_phys.c` `SV_FlyMove`): the box is swept along its velocity, up to 4 bumps, and the velocity is
  clipped along each plane it hits. A plane with normal z 0 (a wall), or a walking box's plane steeper than walkable,
  marks the move as blocked by a step.
- **The step** (`sv_phys.c` `SV_WalkMove`, `STEPSIZE 8.5`): only when the move was blocked by a step and the box was
  on the ground before the move (not while jumping): back to the start, up by 8.5, the frame's move again (a full
  slide move), then down by 8.5 (less the velocity's own fall). The step holds when the down sweep lands on a
  walkable plane; otherwise the plain move is kept.
- **The ground** (`aw_walk.c` `AW_WalkPlayer`): a box supported within 0.5 units on a walkable plane walks along the
  plane's tangent with no gravity; after the move, a box that was supported is put back on the ground found within
  8.75 units under it. Deeper, it falls.
- Monsters (`sv_move.c` `SV_movestep`, `STEPSIZE 8.5`) and the actor trial step (`aw_walk.c` `AW_ActorStep`, a rise
  or fall of 8.75 plus what the slope gives) are separate; scripted actors walk through `AW_WalkPlayer` as the player
  does.

## Side by side

| Rule | OpenMW 0.51 (MW) | OpenMW in map units | AmiWind today (units) |
| --- | --- | --- | --- |
| Highest riser climbed | under 35 (34 from the box's bottom, which rides 1 over the ground) | under 8.75 | 8.53 (8.5 + 0.03125) |
| Walkable slope | normal z > 0.694658 (under 46.0 deg) | same | normal z >= 0.69 (up to 46.4 deg) |
| When a step is tried | any non-actor hit with its contact lower than a step | same | a wall or a too-steep slope blocked the move |
| Step reach | the frame's move, then 10, then 20 | frame's move, 2.5, 5 | the frame's move |
| Step down after the step | move + rise + 62 | move + rise + 15.5 | 8.5 |
| Step while in the air | yes, never ending lower than it rose | yes | no (only in water) |
| Ground followed down while walking | 64 | 16 | 8.75 |
| Too-steep slope, on the ground | a wall (normal laid flat) | a wall | the velocity is clipped along it: a fast walker gains height |
| Too-steep slope, in the air | slides, never gains vertical speed | same | slides along it |
| Gap kept to surfaces | 0.2 margin, 1 over the ground | 0.05, 0.25 | 0.03125 |
| Player box | 29.28 x 28.48 x 133 | 14.64 x 14.24 x 33.25 | 14.64 x 14.24 x 33.25 |
| What the box is swept against | the collision triangles themselves (Bullet) | - | the precompiled clipping hull (brushes expanded by the box, with bevels) |

## Differences that change what can be climbed

Each can make a Morrowind stair or slope climbable in OpenMW but not in AmiWind, or the other way round.

1. **Slopes between 46.0 and 46.4 degrees** (normal z 0.6900 to 0.6947): walkable in AmiWind, not in OpenMW. A
   collision ramp in that band climbs in AmiWind and is a wall in OpenMW. Measured meshes: the authored Hlaalu ramps
   are 45 degrees and under (inside both); the 46-degree faces of `ex_hlaalu_dsteps_01` sit at the edge. Stair
   collision method 1 builds its ramps with AmiWind's 0.69, so some of its ramps fall in the band (below).
2. **Risers of 34.1 to 35 MW**: OpenMW measures the step from the box's bottom, which rides 1 unit over the ground,
   so it climbs risers up to just under 35; AmiWind's box rests 0.125 MW over the ground and climbs up to 34.1.
   Morrowind's regular risers are 32 or less ([Stairs and ramps](COLLISION_MESHES.md#stairs-and-ramps)), so this
   matters only on odd pieces.
3. **Short steep lips**: OpenMW's third try reaches 20 MW on, so a face too steep to stand on but lower than a step
   and at most 20 MW deep is stepped over (the 55-degree, 27 MW face of `ex_hlaalu_dsteps_03` runs 18.9 MW). AmiWind
   reaches only the frame's own move (8 MW at 160 MW/s and 20 frames a second), lands on the steep face and refuses.
4. **Crawling up too-steep slopes**: in AmiWind the push into a slope steeper than walkable turns into speed along
   it; at higher speeds or frame rates that beats gravity and the walker climbs a 50-degree slope (measured below:
   400 MW/s at 20 fps, 160 MW/s at 50 fps). In OpenMW the slope is a wall. AmiWind's result depends on the frame
   rate, which an Amiga varies with the scene.
5. **Going down**: OpenMW keeps a walking box on the ground over drops up to 64 MW a frame; AmiWind follows only
   35 MW and falls for the rest (a flight of 36-62 MW drops: 12-16 frames in the air under the Quake rules, none
   under OpenMW's). The walker arrives either way; in the air it cannot step or jump.
6. **Stepping in the air**: OpenMW steps while jumping or falling if it does not end lower than it rose (a jump onto
   a ledge catches its edge); AmiWind does not step in the air.
7. **What the box is swept against**: OpenMW sweeps against the collision triangles; AmiWind against a clipping hull
   compiled from convex pieces. Convex pieces can invent steep faces or bury authored surfaces
   ([COLLISION-CONVEX-LOSS-32](bugs/COLLISION-CONVEX-LOSS-32.md)). That is a data difference, not a rule difference:
   part (b) of the method.

The step gate (OpenMW tries a step on any hit lower than a step; AmiWind only when blocked by a wall or a too-steep
slope) and the extra bounces (8 against 4) change where a step starts, not what is climbable.

## The method

### (a) The engine: step like OpenMW

The prototype (`aw_step_rules 1`; `engine/aga/src/sv_phys.c` `SV_StepRulesStep` and `SV_FlyMove`,
`engine/aga/src/aw_walk.c`, `engine/aga/src/quakedef.h` `AW_WALKABLE`):

- walkable means normal z over cos 46 degrees (`AW_OPENMW_WALKABLE_Z` 0.69465837), in the player's move, its step,
  its ground support and its ground following;
- a step is tried when the move was blocked by a wall or a too-steep slope (the Quake gate, with the new slope
  limit), also in the air;
- the step: up by 8.75 (OpenMW's 34 over its ground offset, stopped by a ceiling less the margin); forward the
  frame's move, else 2.5, else 5 units; down by the reach plus the rise plus 15.5 (the third try only back to the
  start height); it holds on a walkable surface of the world; in the air it may not end lower than it rose;
- a too-steep slope is a wall to a walker that stood on the ground (its normal laid flat), and never raises a
  walker's vertical speed;
- a walker on the ground follows it down 16 units (64 MW) instead of 8.75.

Cost on a 68040: with `aw_step_rules 0` the code is the same as before plus one test of a float per walkable test.
With 1, a plain move costs the same traces as before; a blocked move costs one up sweep plus two sweeps per try
(forward and down): 3 sweeps in the common case, 7 at most, against Quake's step of 3 to 6. It runs once per player
move (and per scripted actor's walk), never per placement.

### (b) The data: traversable by construction

The converter work that the maintainer approved for the next dev build (another branch,
`v0.0.48-authored-collision`) makes the authored collision the collision: the `RootCollisionNode` as the collision
source in every converter, authored ramps kept as ramps, and stair collision method 1 by default. This note does not
change converter code; it states how the engine rules combine with that default:

1. **One set of numbers.** The converter's rule constants (`tools/player_hull.py` `STEP_HEIGHT`, `WALKABLE_Z`) are
   the engine's (`quakedef.h`, `sv_phys.c`). With the step rules they become 8.75 and cos 46 degrees. Method 1
   builds its ramps no steeper than walkable; built with AmiWind's 0.69, a ramp can fall in the 46.0-46.4 band that
   the step rules do not stand on (two meshes below). Built with the step rules' numbers, it never does.
2. **An authored ramp is traversable by arithmetic.** A RootCollisionNode stair is a ramp: its upward faces have
   normal z over cos 46 (the Hlaalu ramps: 0.707 at 45 degrees, 1 degree of margin), it runs from the lowest tread
   to the top within a step of each drawn tread, and the box's height is free over it. Then the box stands on every
   point of it and walks it by the slope rule alone; no step is needed.
3. **Steps where there are steps.** Where the collision keeps real steps (`ex_vivec_b_wb_01`,
   `in_v_l_int_stairs_03`) or method 1 builds one block per tread, every rise between neighbouring standing places
   must be under the step (8.75 units), and every tread must have a place where the box fits and stands.
4. **The check is the proof.** `tools/stair_mesh.py` `check_flight` already does this arithmetic over every drawn
   tread and every seam between treads (the standing box's footprint on the collision's planes; [Stair collision
   method 1](COLLISION_MESHES.md#stair-collision-method-1-the-default)), and takes the step and the walkable slope
   as arguments. A method 1 build keeps each mesh's check in its mesh unit (`stair-check.json` per CHIM work folder,
   `chim-world/chim-stair-check.json` collected), so it is computed once per mesh and collision, and again only when
   the mesh, its collision or the rule numbers change: the rule numbers belong in the unit's key. No walk.
5. **What the check leaves out**, each only letting more through, so its verdicts are on the safe side: the step
   rules' third try over a short steep lip (a face lower than a step and at most 5 units deep), and the deeper ground
   following.

## Prototype test results

`tests/aga_step_rules_test.c` (run by `tests/test_aga_native_source.py`
`test_step_rules_match_openmw_over_synthetic_stairs_and_slopes`) drives the engine's own walk (`aw_walk.c`
`AW_WalkPlayer`, `sv_phys.c` `SV_WalkMove` and `SV_FlyMove`) over synthetic shapes: a flight of 4 risers with
48 MW treads, a ramp 128 MW high, a 55-degree lip with a flat top, a flight going down. The world is a few convex
solids swept exactly against the standing box. A case climbs when the walker ends on the top. Each case runs at
160 and 400 MW/s and at 20 and 50 frames a second; the table shows 160 MW/s at 20 fps, with the other runs where
they differ. The test fails if a step-rules result differs from what OpenMW's rules say, or if the Quake rules lose
a climb they had.

| Case | Quake rules (`aw_step_rules 0`) | Step rules (`aw_step_rules 1`) | OpenMW's rules say |
| --- | --- | --- | --- |
| riser 8 MW | climbs | climbs | climbs |
| riser 16 MW | climbs | climbs | climbs |
| riser 18 MW | climbs | climbs | climbs |
| riser 24 MW | climbs | climbs | climbs |
| riser 32 MW | climbs | climbs | climbs |
| riser 34 MW | climbs | climbs | climbs |
| riser 34.8 MW | blocked | climbs | climbs |
| riser 36 MW | blocked | blocked | blocked |
| riser 40 MW | blocked | blocked | blocked |
| ramp 30 deg | climbs | climbs | climbs |
| ramp 44 deg | climbs | climbs | climbs |
| ramp 45 deg | climbs | climbs | climbs |
| ramp 45.9 deg | climbs | climbs | climbs |
| ramp 46 deg | climbs | blocked | blocked |
| ramp 46.2 deg | climbs | blocked | blocked |
| ramp 46.5 deg | blocked (climbs at 400 MW/s at 20 fps, and at both speeds at 50 fps) | blocked | blocked |
| ramp 50 deg | blocked (climbs at 400 MW/s at 20 fps, and at both speeds at 50 fps) | blocked | blocked |
| lip 55 deg, 27 MW high, 18.9 deep | blocked | climbs | climbs |
| lip 55 deg, 34 MW high, 23.8 deep | blocked | blocked | blocked |
| lip 55 deg, 40 MW high, 28.0 deep | blocked | blocked | blocked |
| down 34 MW drops | on the ground | on the ground | on the ground |
| down 36 MW drops | falls (12 frames in the air) | on the ground | on the ground |
| down 48 MW drops | falls (16 frames) | on the ground | on the ground |
| down 62 MW drops | falls (16 frames) | on the ground | on the ground |
| down 70 MW drops | falls (16 frames) | falls (16 frames) | falls |

All the step-rules results match OpenMW's rules at both speeds and both frame rates. The Quake rules differ in 9 of
the 25 cases: the 34.8 MW riser, the 46 and 46.2-degree ramps (climbed, OpenMW does not), the 46.5 and 50-degree
ramps (climbed at some speeds and frame rates), the 27 MW lip, and the 36-62 MW drops.

## Evidence: the stair meshes of the v0.0.47-dev2 build

`tools/step_rules_survey.py RUN --out DIR` builds each flight mesh's collision as the converter does and runs the
check under both rule sets. It reads the run only and walks nothing. It ran over the v0.0.47-dev2 build
(`2026_10_21_v0.0.47-dev2_dev2-try3_c20bc0d8`, read only on the build volume): 1,350 region frames, 1,380 distinct
meshes, 97 with flights of stairs (132 flights), on 6 workers in 123 s. Method 0 is today's collision, method 1 is
stair collision method 1 built with today's numbers, and "method 1, step-rules numbers" is method 1 built with
the step rules' step and slope (part (b) 1).

| Collision | Quake rules: meshes passing (flights failing) | Step rules: meshes passing (flights failing) |
| --- | --- | --- |
| Method 0 (today) | 73 of 97 (34) | 74 of 97 (33) |
| Method 1 | 86 of 97 (21) | 85 of 97 (22) |
| Method 1, step-rules numbers | 84 of 97 (23) | **87 of 97 (20)** |

- (a) + (b): **87 of the 97 stair meshes pass**, against 73 today.
- The step rules alone (method 0) pass `ex_hlaalu_bal_02` too. Method 1 built with today's numbers loses
  `ex_hlaalu_b_06` and `ex_hlaalu_b_24` under the step rules: their built ramps are steeper than 46 degrees. Built
  with the step rules' numbers, all three pass.
- Not traversable under (a) + (b), 10 meshes:

| Mesh | Flights failing | Collision source | What the check finds |
| --- | --- | --- | --- |
| `r/siltstrider` | 1 of 1 | RootCollisionNode | no place on a tread for the standing box |
| `x/ex_ashl_tent_03` | 3 of 5 | RootCollisionNode | no place on a tread for the standing box |
| `x/ex_common_house_tall_02` | 1 of 1 | RootCollisionNode | a gap to the next tread; no place on a tread |
| `x/ex_dae_ruin_02_skew` | 2 of 4 | drawn mesh | blocked passage, a lip over a step |
| `x/ex_dae_ruin_04_skew_01` | 2 of 5 | RootCollisionNode | blocked passage; no place; a standing surface too steep |
| `x/ex_dae_ruin_entry` | 1 of 1 | drawn mesh | no place on a tread; a standing surface too steep |
| `x/ex_de_shack_04` | 1 of 1 | RootCollisionNode | no place on a tread for the standing box |
| `x/ex_de_ship` | 6 of 7 | RootCollisionNode | no floor under a tread; blocked; no place; a rise over a step |
| `x/ex_de_shipwreck` | 2 of 5 | RootCollisionNode | no place on a tread; a standing surface too steep |
| `x/ex_hlaalu_dsteps_01` | 1 of 1 | RootCollisionNode | no place on a tread for the standing box |

These are the meshes method 1 cannot fix yet ([Stair collision method 1](COLLISION_MESHES.md#stair-collision-method-1-the-default)).
Most fail because there is no place on a tread where the box fits: narrow treads, ladders and decks under a roof.
For a box of OpenMW's size some of these may also be impassable in OpenMW (the check does not know). That is to
check in game, not by a walk.

## Proposal (the maintainer's decision)

The default is not changed. The proposal:

1. Turn `aw_step_rules` on by default in the same dev build that takes the authored collision and method 1 by
   default (`v0.0.48-authored-collision`), with the converter's numbers (`tools/player_hull.py`) set to the step
   rules' (8.75, cos 46 degrees). Then the engine, the converter and the check use one set of numbers, and the check
   is the proof that a stair is traversable.
2. Before that, the maintainer plays the named stairs with `aw_step_rules 0` and `1` (the Balmora Hlaalu stairs and
   `ex_hlaalu_dsteps_03`, the Vivec arena steps, a 46-degree slope, a steep hillside): like for like, the same place
   and the same frame rate on both sides.
3. Add the lip rule (a too-steep face under a step and at most 5 units deep is passable) to `check_flight`, and put
   the rule numbers into the mesh unit's key.
4. Leave monsters (`sv_move.c`) as they are; scripted actors already walk by the player's rules.

## References

- OpenMW 0.51.0 (GPL-3.0), the reference for the rules: `apps/openmw/mwphysics/stepper.cpp`,
  `apps/openmw/mwphysics/movementsolver.cpp` and `.hpp`, `apps/openmw/mwphysics/constants.hpp`,
  `apps/openmw/mwphysics/actor.cpp`, `components/misc/constants.hpp`, `components/detournavigator/settings.cpp`,
  `files/settings-default.cfg` (`actor collision shape type`). Read from the project's `amiwind-openmw:0.51.0`
  image; reimplemented, not copied.
- AmiWind: `engine/aga/src/sv_phys.c`, `engine/aga/src/aw_walk.c`, `engine/aga/src/quakedef.h`,
  `engine/aga/src/sv_move.c`, `engine/aga/src/model.c`; `tools/player_hull.py`, `tools/chimport.py`,
  `tools/stair_mesh.py`, `tools/stair_mesh_survey.py`, `tools/step_rules_survey.py`;
  `tests/aga_step_rules_test.c`.
