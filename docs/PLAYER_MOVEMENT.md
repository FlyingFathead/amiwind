# Player scale, collision and camera motion

_Last updated with AmiWind v0.0.69-dev5 (26 November 2026)._

<!-- contents start -->
## Contents

- [Movement speed](#movement-speed)
- [Water Walking](#water-walking)
- [Breath and drowning](#breath-and-drowning)
- [Verified base dimensions](#verified-base-dimensions)
- [Physical recheck, v0.0.24-dev2](#physical-recheck-v0024-dev2)
- [Original race-based heights](#original-race-based-heights)
- [Matching the baked map](#matching-the-baked-map)
- [Ground support and feel](#ground-support-and-feel)
- [Bodies that overlap, and arriving next to an actor](#bodies-that-overlap-and-arriving-next-to-an-actor)
- [Checkpoint-013 architectural ghost volumes](#checkpoint-013-architectural-ghost-volumes)
- [Eye-height audit, checkpoint-016 development](#eye-height-audit-checkpoint-016-development)
- [Dev1 regression comparison, 28 September 2026](#dev1-regression-comparison-28-september-2026)
- [dev4 Balmora stair entrance](#dev4-balmora-stair-entrance)

<!-- contents end -->

The maintainer reported blocked stairs, excessive resistance on mild slopes and
idle downhill sliding in checkpoint-011. The old standing player used Quake's
32 x 32 x 56 box although the imported Morrowind world is scaled by 0.25.

## Movement speed

From v0.0.48-dev2 the player walks, runs and swims at the original game's speed, worked out from the
character's own Speed, Athletics and Strength, the carried load and the race, by the rules the OpenMW
engine implements (OpenMW 0.51 `mwclass/npc.cpp` getMaxSpeed / getWalkSpeed / getRunSpeed,
`mwclass/actor.hpp` swim speed, `mwclass/actor.cpp` current speed and load, `mwmechanics/character.cpp`
race weight, strafing and movement fatigue; [PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md)).
Before it, walking and running used fixed speeds of 120 and 216 units/s whatever the character, which
crossed the island far faster than a new character can. The maintainer asked for this on 23 October 2026
and for the old speeds to stay as a debug mode, **superspeed**.

**The rules** (original units/s; AmiWind units are a quarter of that, the world's 0.25 scale):

```text
walk  = (fMinWalkSpeed + Speed/100 x (fMaxWalkSpeed - fMinWalkSpeed)) x (1 - fEncumberedMoveEffect x load)
run   = walk x (fBaseRunMultiplier + Athletics/100 x fAthleticsRunBonus)
swim  = (walk or run) x (fSwimRunBase + Athletics/100 x fSwimRunAthleticsMult)
load  = carried weight / (fEncumbranceStrMult x Strength); over 1: the player cannot move
moved = speed x input (0..1) x 0.75 when strafing x race weight (male/female, from the race record)
```

The settings are the master file's own (`combat/settings.txt`, "move" lines written by the builder from
the user's Morrowind.esm). Diagonal input is no longer faster than straight input.

**Read live.** Speed, Athletics, Strength and the load are read from the character sheet every frame,
never baked at build time or at character creation: a level-up, a skill gain, a scripted change, and
later a Fortify or Drain effect change the speed at once. `superspeed` with no argument turns superspeed the
other way and prints the current walk, run and swim speed with the stats it used.

| Character | Walk (units/s) | Run (units/s) | Old walk / run |
| --- | ---: | ---: | ---: |
| New Nord male Barbarian (Speed 50, Athletics 35, nothing carried) | 46.9 | 98.4 | 120 / 216 |
| Speed 100, Athletics 100, Nord male | 62.5 | 171.9 | 120 / 216 |

**Fatigue.** Running costs fFatigueRunBase + fFatigueRunMult x load per second of full input, swimming
fFatigueSwimWalkBase or fFatigueSwimRunBase, a jump fFatigueJumpBase + fFatigueJumpMult x load; walking
costs nothing, and no cost goes below 0 (OpenMW lets only a fight's damage take fatigue below 0). The
fatigue comes back as before (fFatigueReturnBase + fFatigueReturnMult x Endurance per second). Godmode
pays nothing.

**Superspeed** (`dbg superspeed [on|off]`, also plain `superspeed`; on/off, true/false or 1/0, no word turns it
the other way; default off, not saved): the earlier movement exactly as it was, `cl_forwardspeed`, Shift x
`cl_movespeedkey`, `sv_maxspeed`, water x 0.7. Since v0.0.62 the stamina is endless while it is on: whatever spends
fatigue (a run, a jump, a swing, a block, a blow taken) is filled again at the next move, and the movement rules read
Speed, Athletics and Acrobatics as 100, the skill and attribute maximum; the character sheet itself is not changed,
so off gives the real values back at once. For debugging and fast travel checks. The same no-word rule holds for
every on/off debug command (`tests/test_console_toggles.py` checks the whole catalogue).

Every factor of the OpenMW rules, and where it comes from in AmiWind:

| Factor | OpenMW | In AmiWind | From |
| --- | --- | --- | --- |
| Speed attribute | walk speed | now | character sheet (base + race/birthsign modifiers - damage) |
| Athletics skill | run and swim speed | now | character sheet |
| Strength | carrying capacity | now | character sheet |
| Carried weight | load | now | owned items x catalogue weight, a running total kept by the item table (v0.0.61; [INVENTORY.md](INVENTORY.md#carry-weight)) |
| Over the limit | no movement or jump, "You are over-encumbered." | now (the message since v0.0.61) | sNotifyMessage59, raised while the player tries to move |
| Race weight | movement scale | now | race record, male/female (builder) |
| Running | run speed, fatigue | now | Shift held |
| Swimming | swim speed, fatigue | now | the water movement path |
| Strafing | x 0.75 | now | sideways input (first-person rule) |
| Input amount | x 0..1 | now | the movement command |
| Knocked down / out | speed 0 | now | combat state |
| Dead | speed 0 | now | health |
| Godmode | no fatigue cost, Burden ignored | now | dbg godmode |
| Running / swimming / jump fatigue | fatigue loss | now | character sheet fatigue (the HUD bar) |
| Fatigue return | fatigue gain | now (before this change) | combat rules, Endurance |
| Fatigue at or below 0 | knocked out | now, for a fight's damage | combat rules; movement never takes it below 0 |
| Sneaking | x fSneakSpeedMultiplier on the walk (0.75 in Morrowind.esm), no running, fatigue | v0.0.58; the key toggles since v0.0.69 | the sneak key (Left Ctrl): one press on, the next off; Options > Controls "Sneak key: Hold" or `aw_sneak_toggle 0` sneaks while the key is held (OpenMW 0.53's toggle sneak setting); a script's ForceSneak |
| Paralysis | speed 0 | later | magic effects (none yet) |
| Feather / Burden | load | in (v0.0.61, `AW_EncumbranceSetEffects`): the spell effects Burden and Feather feed the carry weight | magic effects |
| Fortify / Drain / Damage Speed, Athletics, Strength, Acrobatics | the stats | later (the sheet's damage field already counts) | magic effects |
| Swift Swim | swim x (1 + magnitude/100) | later | magic effects |
| Levitate | fly speed from fMinFlySpeed / fMaxFlySpeed | later (the effect only stops a fall's damage so far) | magic effects |
| Jump effect, Acrobatics, load, fatigue | jump height (getJump) | later (rule written and tested, not applied) | needs the gravity scale first ([PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md)) |
| Acrobatics | in-air control (fJumpMoveBase / fJumpMoveMult) | later | Quake air control is kept |
| Slowfall | the falling speed, no fall height | v0.0.62 | the factor 1 - magnitude x 0.005 once each 1/60 s of falling; the engine's gravity stays Quake's |
| Acrobatics, Jump, fatigue | fall damage on landing (fFallDamageDistanceMin, fFallDistanceBase/Mult, fFallAcroBase/Mult) | v0.0.62 | [MWSCRIPT_BYTECODE.md "Held actors and falls"](MWSCRIPT_BYTECODE.md#held-actors-and-falls); no knockdown yet |
| Water Breathing | no breath used under water | v0.0.63 | [Breath and drowning](#breath-and-drowning) |
| Water Walking | the water's surface is ground: stand, walk, run, jump and land on it; no swimming and no breath used while on it | v0.0.68 | [Water Walking](#water-walking) |
| Werewolf | run x fWereWolfRunMult | later (the werewolf form itself is in since v0.0.68; its run multiplier is not applied yet) | the player in werewolf form is drawn as the werewolf, see the [release notes](releases/notes/RELEASE-v0.0.68.md#the-werewolf) |

The rules are pure functions in `engine/aga/src/aw_move_rules.c` (tested against hand-worked OpenMW
values in `tests/aga_move_rules_test.c`); `engine/aga/src/aw_move.c` gathers the inputs into one
structure (`aw_move_inputs_t`, a field per factor above, 0 = no effect) and applies them in
`sv_user.c`, so a later effect only fills its field. `tests/aga_move_test.c` checks the engine side:
the old numbers under superspeed, the live sheet, the load, the fatigue costs and the command. In-game
timing against the original is not measured yet.

## Water Walking

From v0.0.68 a Water Walking effect on the player (a spell, a potion, a scroll, an enchanted item, an ability, or a
script's SetWaterWalking / ModWaterWalking) holds him on the water as on ground, as the original does (the rule as
OpenMW 0.51 implements it in `mwphysics/physicssystem.cpp`, `mwphysics/actor.cpp` and `mwphysics/mtphysics.cpp`,
written independently in `engine/aga/src/aw_walk.c`):

| What | Rule |
| --- | --- |
| The surface | while the magnitude is over 0, the water's surface stops the player as ground does: he stands, walks, runs and jumps on it, lands on it from a fall (a fall still hurts, as on land) and steps onto it from a shore or a quay |
| Under the water when it starts | lifted onto the surface at once when the way up is clear; under a roof or a ledge he stays and swims |
| When it ends | nothing holds him: he drops into the water and swims as before |
| Lava | walked on already ([LAVA.md](LAVA.md)); Water Walking does not change it |
| Swimming | unchanged |

The surface is read from the level's own water (the height where the water above the feet ends), never an assumed sea
level. While the player stands on it the walk tests about ten points and sweeps the box once a frame; the effect is
asked only while his feet are in the water. `tests/aga_waterwalk_test.c` drives the engine's own walk over a synthetic
sea. Not done yet: the original refuses the spell on someone too deep under the water to be lifted.

## Breath and drowning

From v0.0.63 the player holds his breath under water as in the original (the rules as OpenMW 0.51 implements
them in `mwmechanics/actors.cpp` updateDrowning and `mwgui/hud.cpp`, written independently in
`engine/aga/src/aw_breath_rules.c`, applied by `engine/aga/src/aw_breath.c` once a frame after the lava damage):

| What | Rule |
| --- | --- |
| Under water | the head (the eyes) in a water volume; standing in shallow water or wading is not |
| Breath | fHoldBreathTime (20) seconds, falling while under water; full again at once on the surface |
| Drowning | once the breath is gone, fSuffocationDamage (3) health a second, continuously; the game's "drown" sound plays while it lasts |
| Water Breathing | no breath used at all while any magnitude of it is on the player: a race's ability (the Argonians'), a potion, a spell, a worn Constant Effect item, a script's ModWaterBreathing |
| The bar | a red bar at the top of the view, in the middle, while the breath is under its full time; it flashes once the breath is gone |
| God mode | no drowning damage (the one world-damage check, below) |

The two settings and the sound come from the player's own master file at build time (`combat/settings.txt`
"breath" lines, `tools/prepare_combat.py`); an image without them uses the original's values. The breath is not
kept in saved games: a load, a new map or New Game gives a full breath, and it stays full in noclip. Scripts read
and change Water Breathing with GetWaterBreathing, SetWaterBreathing and ModWaterBreathing. `dbg breath` prints
the breath left, whether the head is under water, the Water Breathing magnitude, the drowning damage taken and
what god mode held back. Measured in game: not yet.

God mode (`dbg god`) holds back every kind of damage to the player: a blow in a fight, the lava volume and a lava
script's HurtStandingActor, a fall, drowning (all through `AW_CombatHurtPlayer` in `engine/aga/src/aw_combat.c`),
and any loss of health from a script or a spell effect (SetHealth, ModCurrentHealth, Damage Health, poison, the
elements; `player_store` in `engine/aga/src/aw_mwhost.c`), where a heal still lands (GODMODE-LAVA-DEATH-62).

## Verified base dimensions

The maintainer's `meshes/base_anim.nif` Bounding Box gives half extents approximately
29.28 x 28.48 x 66.5 and centre z=66.5. OpenMW reads that collision box in
`mwphysics/actor.cpp`. `Npc::adjustScale(..., false)` in `mwclass/npc.cpp` does
not apply race height/weight to collision; those proportions affect rendering.
An individual reference scale still applies. This prototype uses reference
scale 1 and a centred player hull:

| Quantity | AmiWind world units |
| --- | --- |
| Minimum | -7.32, -7.12, -16.625 |
| Maximum | 7.32, 7.12, 16.625 |
| Full body dimensions | 14.64 x 14.24 x 33.25 |
| Eye above origin | Selected eye above feet minus 16.625; dev2 pre-creation 14.551 |
| Eye above feet | Race/sex Camera-bone sample; dev2 pre-creation 31.176 |

This replaces a footprint about 2.2 times too wide. It is a base humanoid
collision profile. The dev2 eye-height selection is independent of this box.

## Physical recheck, v0.0.24-dev2

The maintainer reports being too tall relative to both Seyda Neen and Balmora. A live
Amiga calibration room compares body and point sweeps against known flat walls,
floor and ceiling. This tests the effective baked collision, not just constants:

| Axis | Negative body / point stop | Positive body / point stop | Measured full size |
| --- | --- | --- | --- |
| X | -56.64875 / -63.96875 | 56.64875 / 63.96875 | 14.640 |
| Y | -56.84875 / -63.96875 | 56.84875 / 63.96875 | 14.240 |
| Z | 16.65625 / 0.03125 | 43.34375 / 59.96875 | 33.250 |

The common trace epsilon cancels in each difference. No hidden doubled height or
vertical hull-origin shift is present. The original full collision dimensions
are 58.56 x 56.96 x 133; scenery, terrain and player all use the same 0.25 scale.
The two reported Balmora passages also fit this body against original triangles;
their converted concave collision was obstructing the routes. Source triangle
tests include larger-body positive controls. See the full symptom/cause/fix
record in [mesh notes](MESH_TIPS_AND_TRICKS.md#balmora-underpasses-and-global-player-height-v0024-dev2).

Dev1 nevertheless applies the Nord eye fixture to every character. Dev2 exports
the ordinary idle Camera bone (124.7052 source units) and each race/sex height
into an optional AWE1 catalogue trailer. It uses the source Player race before
creation, applies confirmed choices immediately, and reapplies the selected eye
after scene/save restoration. Dark Elf/Imperial eyes are 31.176 units above feet,
Nord 33.047, High Elf 34.294, Breton female 29.617 and Wood Elf male 28.059.
Legacy catalogues retain their baked eye fallback. Physical collision is unchanged.
Host checks cover catalogue bounds, legacy data, pre-creation selection,
confirmation/cancellation and unchanged physical bounds. The native rebuilt
catalogue reports 31.176 before creation.

Keep **90-degree horizontal FOV** and the existing Quake bob. The optional slider
in the roadmap must pass a performance comparison and is not a world-scale fix.
These measurements do not establish original-game animated camera parity or
close the maintainer's broader assessment of player proportions.

## Original race-based heights

Read directly from the owned base `Morrowind.esm` playable RACE records, RADT
male/female height fields (30 September 2026). These are relative height
multipliers, not metres and not the separate weight fields.

| Race | Male height | Female height |
| --- | --- | --- |
| Argonian | 1.03 | 1.00 |
| Breton | 1.00 | 0.95 |
| Dark Elf | 1.00 | 1.00 |
| High Elf | 1.10 | 1.10 |
| Imperial | 1.00 | 1.00 |
| Khajiit | 1.00 | 0.95 |
| Nord | 1.06 | 1.06 |
| Orc | 1.05 | 1.05 |
| Redguard | 1.02 | 1.00 |
| Wood Elf | 0.90 | 1.00 |

Nords are taller than the 1.00 baseline; High Elves are taller still. This is
source-defined character stature, not an AmiWind invention. Dev2 uses these
values for `eye above feet = sampled first-person Camera height * 0.25 * race/sex
height`. It does not multiply the base collision box by race height. The earlier
fixed Nord camera incorrectly applied the 1.06 proportion to all choices.

References inspected at OpenMW revision
`46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:
[actor.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwphysics/actor.cpp),
[npc.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwclass/npc.cpp),
[movement constants](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/misc/constants.hpp),
[physics constants](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwphysics/constants.hpp).
No OpenMW implementation is incorporated into the runtime.

## Matching the baked map

Changing the player box alone is insufficient: Quake standing collision is
pre-expanded into a BSP hull. The converter compiles an anisotropically scaled
copy of the world with external unmodified qbsp, then transforms the standing
clip planes back, including the vertical origin offset. It grafts only that
standing hull into the visible world and expands architectural proxies using
the same profile. The image builder rejects a scene without the matching
`tes3-humanoid-v1` marker. Old compiled scenes must be rebuilt.

Visible surfaces, point traces and visibility data remain separate. Building
proxies remain approximate convex unions. Yaw-rotated proxies also rotate the
pre-expanded player footprint; they are not exact arbitrary-orientation AABB
sweeps. This limitation still needs targeted corner/stair tests.

## Ground support and feel

Step-up height is 8.5 units (OpenMW's 34 at scale 0.25). Downward support
is deliberately limited to 8.75 units in this prototype, rather than copying
OpenMW's larger 62-unit descent allowance. Slightly tilted riser planes can
request the same step test as an exactly vertical riser.

A confirmed walkable support suppresses gravity-driven downhill creep and
follows the uphill tangent without reducing the commanded horizontal speed.
Supported walking can follow a bounded downward step. A jumping, falling,
swimming or noclip player must not be glued to nearby ground. The native
step-down code must test the hit object's solidity, not the player's solidity,
before restoring grounded state.

Keep the maintainer's preferred Quake camera motion: `cl_bob 0.02`,
`cl_bobcycle 0.6`, `cl_bobup 0.5`. These defaults and the view code are unchanged.
Collision fixes must not remove bob or replace it with a motionless camera.

RC1 uses the shared `AW_WALKABLE_Z = 0.69f` floor-normal threshold. An authored
Hlaalu stair ramp measured `0.6976600289` and failed the former `0.7` cutoff.
This recurring geometry/movement mismatch and its validation are documented
in [Stair ramp walkability](STAIR_RAMP_WALKABILITY.md). Keep movement, support
and placement tests consistent when changing the threshold.

See checkpoint-012 validation for native evidence and remaining limitations.

## Bodies that overlap, and arriving next to an actor

From v0.0.66 two bodies whose boxes already overlap (the player, residents and creatures, Quake's
`SOLID_SLIDEBOX`) collide as the original game's actors do, by the rule OpenMW 0.51 states in
`apps/openmw/mwphysics/actorconvexcallback.cpp`: overlapping actors collide as cylinders whose diameter is the
distance between them. Only a move that heads horizontally toward the other body's centre is stopped, at once,
on the upright plane facing away from that centre; a move away, along the other body, up or down passes it, so
the two can always walk apart. Quake clips the sum of the two boxes instead: a sweep that starts inside that
sum is solid until a single frame's move leaves it whole, so neither body could move. Bodies that do not overlap
still block each other exactly as before, and a position test (a box at one point) still counts every body, so
the placement searches keep bodies apart. The code is `engine/aga/src/world.c` `AW_BodyOverlap`, called for
each body a sweep meets.

Quake's stuck search (`sv_phys.c` `SV_CheckStuck`, run before every walking step of the player and of each
walking resident) is for the world's clipping hull. It now leaves other bodies out of its position tests
(`SV_TestWorldPosition`, OpenMW's `movementsolver.cpp` unstuck leaves actor-on-actor contacts out too): with an
actor on the player's spot it used to fail every frame, for the player and for the actor's own steps, with up to
164 position tests and the developer message "player is stuck." each time.

A door, a teleport or a crossing places the player on the destination's standing spot, and that check keeps
clear of the bodies that stand there at that moment. Outdoors the scene's actors join after it: they are queued
with the arrival's ring, spawned over the next ticks and then moved to where the saved changes left them. So a
wandering guard who had stopped by the Seyda Neen census office's street door, 8 units from its arrival point,
came back onto the player. For three seconds after an arrival, while the player still stands where it arrived,
each frame asks whether a body overlaps the player's box; the first one found steps the player once to the
nearest clear standing spot beside the point: the same standing-spot rule, 16 and then 32 units out, the
directions away from the actor first, and only to a spot that a straight sweep from the point reaches past every
wall. The console says `Arrival: NAME (ref N) stood on the arrival point; the player stands beside it at X Y Z.`
The original and OpenMW put the player on the marker and leave the overlap to the physics; with the rule above
the player could walk out anyway (shown by the native tests; to be confirmed by the opening journey), and this step keeps
the view from starting inside the actor.

Both are switches, on by default and written into `id1/default-game.cfg`: `aw_body_overlap 0` gives Quake's box
clip and stuck search back, `aw_arrival_clear 0` leaves the arrival where it is. The native tests are
`tests/aga_body_overlap_test.c` (the engine's own collision, stuck search and walk, with the boxes and positions
of that arrival) and the arrival case in `tests/aga_scene_test.c`.

## Checkpoint-013 architectural ghost volumes

The maintainer reported an invisible square obstruction after slopes/stairs improved.
Expanding only a convex piece's facet planes creates large solid spikes at acute
corners. Add six axial support limits before expanding each piece by the standing
player box. Point traces retain their original hull: the extra limits are only
needed for the expanded standing hull, saving memory and visibility-trace work.

A host grid found 246 old solid hits outside expanded model bounds and zero after
the change. Native comparison reproduced a false-solid point at (0,136,90): old
code refused to leave noclip, while the corrected image grounded the player and
walked across the square. This is a reproduced local defect, not proof that it is
the exact spot in the maintainer's screenshot or that all collision is now exact.
Use `aw_pos` and `aw_blockers` to report any remaining location.

## Eye-height audit, checkpoint-016 development

The maintainer's low-camera report is credible: the existing `view_ofs.z=13.3`
places the nominal eye 29.925 runtime units above the feet (119.7 source units),
before bob and network quantization. That value was a prototype choice, not
verified first-person parity.

The already-converted first-person skeleton's Camera bone is at 31.187569
runtime units above the source origin in the sampled unarmed pose. The owned
Nord race record gives male height 1.05999994: applying that scale gives about
33.0588 runtime units (132.235 source units). This is roughly 10.5% higher than
the old nominal eye. Verify reference origin, animated camera motion and race
transform against an original/OpenMW view before declaring exact parity.

At the pinned OpenMW revision, first-person camera tracking uses the animation's
Camera node (Head fallback), not the constructor's 124-unit third-person height.
Reference: [camera.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwrender/camera.cpp),
`calculateTrackedPosition` and `processViewChange`. This is a behaviour audit;
no implementation is copied. The collision footprint should not be widened to
correct an eye-height discrepancy.

Checkpoint-016 now bakes this calibrated eye offset into `aw_eye_height` in both
worlds. Local first-person rendering reads the exact server value to avoid the
legacy signed-byte network view-height quantization. Quake walk bob remains.
`dbg eyeheight` prints the current values; an optional 4..24 offset permits A/B
comparison. This corrects the documented prototype value, not a claim of exact
animated camera parity for every race/equipment combination.

## Dev1 regression comparison, 28 September 2026

Maintainer reported that guards seemed smaller or the player taller. Recompiled the
maintainer's v0.0.17 snapshot and compared it with v0.0.18-dev1 on the same HDF,
scene, spawn and emulator configuration. Both native logs report eye offset
16.434 / eye above feet 33.059, player origin (16,44,60), and identical placed
NPC coordinates. Fargoth/guard MDLs and both BSP files are byte-identical to
the pre-UI scene. The matched native screenshots show the nearest guard at
roughly 89 pixels in both builds.

The UI reserves 48 bottom rows: the 3D viewport is now 320x152, compared with
320x200 when the previous debug strip was off. Horizontal FOV, pixel aspect,
projection scale, collision hull and eye offset are unchanged. The visual centre
moves upward by 24 pixels. FS-UAE scaling is another presentation variable;
these captures held it fixed. Do not rescale actors to compensate for framing.

Original-data caveat: free exploration still uses the calibrated Nord male
first-person fixture. The base master's pre-creation Player record is Dark Elf.
Creation must choose race/sex eye proportions explicitly; existing calibration
is not proof of every original in-game camera or character appearance.


## dev4 Balmora stair entrance

The Nord report at XYZ925,-290,62 identifies `ex_hlaalu_b_17`, reference 32631.
Its convex collision approximation seals the authored stair opening. Preserve
the authored surfaces as thin collision shells for both placements, 32631 and
32644. Native walking reaches XYZ1078,-292,144 through the previously blocked
entrance. Physical dimensions, selected race/sex eye height, step/slope rules,
bob and 90-degree FOV remain unchanged. The later deformed stair report at
XYZ613,-125,59 is a different asset and remains open; see the dev4 investigation.
