# Physics: how AmiWind uses Quake's physics

How AmiWind uses the physics of the AmiQuake engine it runs on (movement, collision, water, NPC movement), what
it keeps, what it bypasses and what comes next. Review of 10 October 2026 (v0.0.36 development line), read from the
source; the costs quoted come from the measurements on the linked bug pages (FS-UAE, relative figures).

## Short answer

Movement: yes. The engine's own physics loop is intact (`SV_Physics`, `SV_WalkMove` with step-up, `SV_FlyMove`,
the `SV_RecursiveHullCheck` hull traces, the area node tree and the water checks); AmiWind wraps it and does not
replace it, with the step height and the walkable slope matched to Morrowind.

Collision data: not yet. Placed models collide through standing hulls built as chains of convex pieces instead of
compiled BSP hulls; that is behind most of the stair and invisible-blocker bugs and the slow traces near large
models. NPCs move with AmiWind's own step code (on top of the player's walk), not Quake's monster movement, which is
a deliberate choice. Gravity and speeds were never scaled to Morrowind.

## What is used, area by area

| Area | Quake mechanism | AmiWind | Verdict |
| --- | --- | --- | --- |
| Player walk | `SV_Physics_Client`, `SV_WalkMove` (step up and down, unstick, wall friction), friction and acceleration | kept; wrapped by `AW_WalkPlayer` (two extra ground-support traces, terrain-floor rescue); step height 8.5 units (34 Morrowind units), walkable slope 0.69 (about 46 degrees) as in the original | used properly |
| Gravity, jump, speed | `sv_gravity`, jump velocity, `cl_forwardspeed` | gravity is Quake's 800 in a world scaled 0.25, about 5.7 times the original's; jumps and falls take about a third of the time ([PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md)) | not scaled |
| Water, lava | `SV_CheckWater`, water level, swim and water jump | stock swimming; lava is walked on with damage | used properly |
| Levitation | `MOVETYPE_FLY` with `SV_FlyMove` | not implemented yet; noclip is a debug flight | not used |
| Collision hulls | compiled world hulls (expanded brushes, balanced BSP) | the engine side is right (player hull sized to the humanoid); placed models use chains of convex pieces, only terrain and the humanoid go through the BSP compiler | partly |
| CHIM collision | `SV_ClipMoveToEntity` through the area nodes | CHIM ground is grafted into the world hulls and traced the normal way; CHIM placements use the same hull traversal behind their own two-level cull (chunk, then placement) | partly, sound |
| Legacy scenery collision | area nodes | every placement of a legacy map is tested on every move | bypassed (legacy only) |
| Entities | `SV_LinkEdict`, solid types, touch | NPCs are solid boxes that do not move by physics; statics and flora are static entities; doors are activation records that load the next scene | partly |
| NPC movement | `MOVETYPE_STEP`, `walkmove`, `movetogoal` | AmiWind's `AW_ActorStep` runs the player's walk for each actor step with a trial and roll-back, so actors climb the same stairs the player does; a path ladder modelled on Quake's chase direction | own code, deliberately |
| NPC grounding | `droptofloor` | positions measured at build time; a bounded trace at run time for moved actors | partly, deliberately |
| Doors and platforms | `MOVETYPE_PUSH`, `SV_PushMove`, `SV_PushRotate` | not used; hinged doors cannot open ([AW-20260928-12](bugs/AW-20260928-12.md)) | not used |
| Per-frame cost | `SV_Physics` over all entities | actors outside the CHIM ring are frozen only for moving movetypes; standing residents still run their idle think across the whole frame (not measured) | partly |

## Next steps

In order of player-visible benefit:

1. **Compiled collision for every placed model:** build each model's standing hull with the BSP compiler from its
   authored collision, with today's routed hulls as the fallback and the chains still selectable. One change
   behind most of the collision and stair bugs (COLLISION-TRACE-COST-33, COLLISION-HULL-CHAINS-33,
   COLLISION-CONVEX-LOSS-32, COLLISION-ROUTE-NO-SPLIT-36, the STAIRS-* flights, VIVEC-TEMPLE-STAIRS-33,
   HARVEST-PLANTS-IN-COLLISION-33); checked by the hull-chain audit and the stair-walk gate island-wide.
2. **Hinged doors on Quake's rotating pusher** (`SV_PushRotate`, already in the engine source behind a Quake 2
   switch): a rotating solid door that blocks and pushes bodies (AW-20260928-12).
3. **Motion constants scaled to Morrowind:** gravity, jump and walk and run speeds compared with the original in
   headless OpenMW (fall time, jump arc, metres per second), then written by the builder's game config, today's
   values kept selectable ([PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md)); levitation as `MOVETYPE_FLY`.
4. **Living towns on the existing actor movement:** the residents' original Wander packages through `AW_ActorStep`
   and the path ladder (NPC-WANDER-NOT-EXECUTED-35), with idle thinkers outside the CHIM ring frozen as well.
5. **Physics cost made visible:** moves and trace time per frame in `dbg rcount` and the build's performance
   records, as for visibility; a grid broad phase for legacy scenery.

## Notes

- Hull 2 uses hull 1's data with Quake's own offsets; that is correct only while every moving box is a point or
  the humanoid box. A test keeps it so; a larger creature needs its own hull data first.
- Rotated models are clipped by rotating the trace (Quake 2's method), which is exact for yaw; models tilted in pitch
  or roll keep baked hulls (CHIM-TILT-VARIANTS-SPLIT-33).
