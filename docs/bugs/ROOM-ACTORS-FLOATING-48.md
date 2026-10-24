# ROOM-ACTORS-FLOATING-48: regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/actor_grounding.py bake_ground skips CHIM room and shell maps |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | critical: stopped the dev2 image step; every batch room resident would float |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try11_b8c6b6e9 |
| From commit | source b8c6b6e, engine b8c6b6e, CHIM world b8c6b6e |
| CHIM engine version | CHIM 0.2.1, engine b8c6b6e, world format 0.12 |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Cause](#cause)
- [Headroom, coordinates and collision, measured separately](#headroom-coordinates-and-collision-measured-separately)
- [Fix](#fix)
- [How the three initial-placement invariants are met](#how-the-three-initial-placement-invariants-are-met)
- [The 1,662, one by one](#the-1662-one-by-one)
- [Rebuild](#rebuild)
- [Background: why actors start above the floor](#background-why-actors-start-above-the-floor)
- [How modern OpenMW grounds actors](#how-modern-openmw-grounds-actors)
- [The numbers](#the-numbers)
- [What must be shown before it is closed](#what-must-be-shown-before-it-is-closed)
- [Decision](#decision)
  - [The settled design](#the-settled-design)
  - [AmiWind's rule as built](#amiwinds-rule-as-built)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Fixed for v0.0.48 on the branch v0.0.48-fix-room-grounding-chim (from the dev2 line, b8c6b6e9); not yet seen in a
build. On a read-only copy of all 1,132 CHIM rooms of dev2 try 11, of the 1,662 failed residents 1,643 now stand on
their room's floor and pass the actor check; 19 no rule places are kept where the game data puts them, each as an
explicit exception with its own reason (ROOM-RESIDENTS-NO-FIT-48). The actor check after the bake, over all room
actors: passed, 2,341 grounded, 129 explicit exceptions (the 110 of try 11 unchanged, the 19), 0 failed; every ground
resident fitted (require_fitted: 0 missing). The bake took 751 s on 16 workers.

## Symptom

The v0.0.48-dev2 try 11 build stopped in the image step's actor ground check: "Actor placement gate failed: 1662
unresolved cases", every one "Initial mesh contact outside support tolerance", every one an NPC in a batch room (ri*
maps and the Vivec rooms of the batches: CHIM rooms standing on the interior store's models). 795 residents grounded,
110 explicit exceptions. No image was made; nothing shipped with floating actors.

The 1,662 have 22,404 contact samples (the idle soles the check measures): 10,730 supported with gaps -1.8 to 4.0
(median 2.3; tolerance -0.5..1.0), 11,636 with no support within the check's 4-unit reach, 25 blocked, 13 steep.

## Cause

A regression of our own fix ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (dev2 try 7): the ground bake that settles every resident
onto its floor (tools/actor_grounding.py bake_ground) was made to skip CHIM room and shell maps, because it crashed
loading them as classic scenes; nothing else then fitted the residents of batch rooms. A room converted whole was
baked on its classic map before it became a CHIM room; a batch room never had a classic floor in the image (its map is
a shell until the CHIM rooms install), so its residents kept the height the game data gives them. The game data
stores an actor where the editor left it, usually a little above the floor, and the engine settles it at load;
AmiWind does that once at build time, and the batch rooms missed it. Earlier floating actors:
COMBAT-CHASE-CHIM-STUCK-46 (CHIM frames, no baked ground point), CHIM-SEYDA-ACTOR-CONTACT-33 (Seyda Neen, 0.8-3.3
units off the CHIM ground), CHIM-VIVEC-FRAME-WIDE-41 (residents unsupported).

## Headroom, coordinates and collision, measured separately

All on dev2 try 11's own files, read only. Units: AmiWind units, a quarter of a game unit (prepare_quake.SCALE 0.25).

1. Coordinates and scale: no mismatch. Every room resident's origin is its game-data position times 0.25 exactly
   (largest difference 0.0 over all 1,910 residents of batch rooms; reference scale 1.0 for all 2,360). Every room
   record placement is its game-data position times 0.25. In the 450 residents of rooms converted whole, the store
   collision's floor under each equals the classic room map's floor exactly (0.000 over all 450), and the record
   origins equal the classic map's func_wall origins (0.0 over 118 and 167 placements in bmcouncil, bmfighters).
   A scale error would make the headroom grow with height: the headroom regressed on z over 1,899 batch-room
   residents has slope -0.0003 (r -0.08), over 450 whole-room residents 0.0001 (r 0.03). CHIM frame residents
   (Seyda Neen 15, Balmora 18, Vivec 58) and classic maps (456) have authored z equal to the game data times 0.25 too
   (one whole room, vci000 Arena Waistworks, sits 4,608 units below its game-data height with its collision: a room
   translation, its residents grounded on it).
2. Headroom (the editor drop), per actor: batch rooms median 3.2 (90% within 9.1, largest 30.6); rooms converted
   whole median 4.5 (largest 18.3); CHIM frames median 4.8 to 6.7 (largest 25.2); classic maps median 4.1 (largest
   26.7). The same habit in every scene kind. The lowest idle sole is -0.23 to 1.04 units from the origin (median 0.11).
3. CHIM room collision: no general hole. The 11,636 samples with no support in reach, traced 400 units down on the
   room's collision: 11,551 have under the foot the same floor as under the actor's centre (within 4 units), deeper
   than the check's reach: headroom; 6 are a foot over an edge (the floor under it lower than under the centre); 3 a
   foot over a higher surface; 58 have only the room's closing clip floor under them and 18 nothing within 400 units
   (the residents of item 3 of ROOM-RESIDENTS-NO-FIT-48 without a floor); seams are retried 1/16 unit aside.

## Fix

tools/actor_grounding.py bake_room_ground, in the image step after the CHIM rooms install and before the actor
check (tools/build_aga.py): every ground resident of every CHIM room map is fitted by the rule in
[AmiWind's rule as built](#amiwinds-rule-as-built) on exactly the collision the check measures
(chim.room_scene.RoomScene), with the map bake's fields (origin, aw_ground_valid, aw_ground_baked,
aw_authored_origin/z). A spot is accepted only by the contact test on the room's whole collision (a store model's hull
can reach past its model bounds: ri68c97f8719, placement 91935, 1 unit; CHIM-ROOM-CLIP-DRAWN-BOX-48). A probe that
raises the trace visit guard is made again as 8-, 4- or 2-unit pieces (ROOM-TRACE-VISIT-GUARD-48).
Actor states by record: the bake counts the ground residents by record (all 2,360 are NPCs; no creature that flies
or swims and does not walk is a ground resident, and one would stop the bake). The 110 existing exceptions keep their
policy class and are never fitted (108 authored dead, 1 authored, 1 levitating: vivec_god, a creature record with
flags 0x89, no Flies flag, in vpi015, reference 405515, kept at his authored levitating spot by
config/actor_grounding.json). config/actor_room_placements.json holds the residents decided case by case: 'authored'
(kept where the game data puts them, with their reasons; the check reports them as explicit exceptions) and
'placements' (an origin written as given). `AMIWIND_ROOM_ACTOR_BAKE=off` is the method before.

Guard: actor_grounding.require_fitted runs right after the room bake: every ground resident of every map the check
reads (classic maps, CHIM rooms whole or batch; CHIM frame residents are fitted by their town stage and judged through
its results) must carry the mark a ground bake leaves, or the image step stops naming the maps.
tests/test_room_late_passes.py: GroundFitCoverageTests (the image order of bakes over a classic room map and a CHIM
room; the image step's order install, room bake, guard, check) and RoomActorBakeTests (fit, unchanged, refused, an
upper-storey resident never dropped, explicit exceptions and placements, record classes, the build/runtime agreement).

## How the three initial-placement invariants are met

The invariants are described in [the background](#background-why-actors-start-above-the-floor).

1. Position: the bake above; the check measures it.
2. State: a resident spawns with movetype none (no gravity, no velocity: it never falls) and, 0.1 s after spawn, the
   engine's AW_NPCFloor (engine/aga/src/aw_scene.c) keeps a baked resident exactly (origin equal to aw_ground_baked)
   and sets it on the ground (FL_ONGROUND). Build and runtime agree: on the baked copy of all try 11 rooms, all
   2,341 fitted residents are kept exactly by that path; its fallback snap (8 over, 32 under, if the bake fields were
   lost) would move them by a median 0.0 (90% within 0.13, largest 2.24; 98 over 0.5, residents the search moved
   onto a slope), and finds no floor under 3.
3. Pose: a resident starts in its idle frames; an authored-dead one (aw_corpse) spawns in its final death pose and
   never thinks, so no standing frame shows first.

## The 1,662, one by one

Of the 1,662: 1,352 grounded by the vertical fit alone (a median drop of about 3 units), 291 grounded by the nearest
spot of the search, 19 explicit exceptions with their reasons in config/actor_room_placements.json (7 steep, 8 sloped
floors no spot fits, 1 inside a rope bridge's hull, 3 with no floor in reach; listed on ROOM-RESIDENTS-NO-FIT-48).
After the bake every grounded room resident's soles are -0.50 to 1.00 from the floor (lowest sole median 0.33, highest
0.74); their supports are interior architecture (2,219), exterior meshes in rooms (102) and furniture (20: Sixth House
platforms under the Dreamers, two rugs, one table, where the game data has them). The per-resident list is kept with
the maintainer's working notes (residents-1662.csv of the diagnostic).

## Rebuild

Only the image step reruns; the room batches stage, the CHIM rooms stage and their unit caches are unchanged.

## Background: why actors start above the floor

The question the maintainer asked on 23 October 2026: did the original game give actors a little headroom to drop into
place when a scene loads? Many recent big-budget games show characters settling onto the floor just after a load.

In the original data an actor is stored where the editor dropped it, usually a little above the floor. The engine then
places it on the ground after the models have loaded. OpenMW has an operation for exactly this on its actor class
(adjustPosition), and its issue 3219, "NPC and creature initial position tracing down limit is too small" (closed;
created 17 June 2018, imported from the old tracker), describes the original game grounding every NPC and creature
after a cell loads, while OpenMW at the time left them at their placed position in the air. They fell, often showing a
jump animation after entering interiors, and could be hurt or killed if placed too high. The fix concerned how far down
the initial position is traced: the limit was too small. The issue is at
<https://gitlab.com/OpenMW/openmw/-/work_items/3219>. How the original did this exactly is not established by that
evidence.

From the issue thread: in 2016 an OpenMW developer wrote that OpenMW did place actors on the ground at cell load, but
only from up to 500 units above it. The reporter answered that the original game's limit must be higher, since animals
in a landscape mod fell to their death in OpenMW but not in the original. The issue was retitled to the trace-down
limit and closed by OpenMW pull request 1958 (October 2018, OpenMW 0.45), which raised the limit. So the rule reads: an
NPC or creature is attached to the ground below it when the cell loads.

Initial placement is really three separate invariants:

- position: the collision hull sits on the correct supporting surface;
- state: the actor starts grounded, with no falling velocity and no fall damage. OpenMW commit 03aa2705
  (<https://gitlab.com/OpenMW/openmw/-/commit/03aa2705514776f717d1171d43757eccf16793ce>) made physics actors start as
  already grounded, which stopped the jump animation on load;
- pose: the correct animation pose is in place before the actor is visible (no dead body standing for a frame).

The grounding step also served as a general correction for imperfect placement data, sometimes over distances much
larger than a safety clearance: OpenMW's 500-unit limit was too short for some placements. That 500 is in Morrowind
units and our 4-unit check trace is in a different coordinate system, so the two are not directly comparable.

One hypothesis, stated as such: the original engine may have tolerated, or even used, slightly raised placements and
then grounded the actors safely while initialising the cell, to avoid both collision penetration and unintended
falling.

Grounding on load solves two separate problems. One is collision penetration (an actor starting partly inside the
geometry). The other is fall damage: the settling must not count as a fall. Spawning high and letting gravity act does
not avoid that by itself. The engine has to snap the actor onto the ground without simulating a fall, reset its falling
state, or keep the drop too short to count.

Engines commonly let characters start slightly high, for four reasons:

- floating-point precision: a position computed exactly on a surface can end up a hair inside it;
- the collision shape can differ from the visible floor;
- a model's origin is not always at the soles of its feet;
- initialisation order: the actor, its capsule and the world collision become active at different times.

Starting inside the floor is worse than starting above it: the solver pushes the actor out (pops, launches) or leaves it
stuck. Starting a little above lets gravity or an explicit ground snap settle it. Unreal Engine's character movement
does this with a downward capsule sweep (FindFloor), and Godot's character body has a floor snap length that does the
same job.

A visible drop therefore proves that some grounding or correction step ran (a first physics tick after the first
frame, saved coordinates restored before floor contact, gravity acting before the floor is recognised, a streaming or
network correction). It does not prove that the headroom was put there on purpose.

AmiWind settles actors at build time instead. They arrive standing, no CPU is spent settling thousands of stationary
residents at load, nobody sees a drop, and there is no chance of fall damage from initialisation. A tiny justified clearance stays if the engine needs one, and runtime physics
takes over when an actor moves. The bug here is that batch-room residents never got that build-time step.

## How modern OpenMW grounds actors

From the maintainer's review of OpenMW's current source (23 October 2026), checked against the OpenMW 0.51.0 source in
the local image amiwind-openmw:0.51.0 (/src, read only):

- It happens once. When an actor enters the active processing range, the actor processing code checks whether its
  position was already adjusted and, if not, calls adjustPosition() before the character controller update (actors
  outside the range can be deferred).
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/actors.cpp>
- The search starts high. The world's adjustPosition (World::adjustPosition, apps/openmw/mwworld/worldimp.cpp) raises
  the start to the higher of the recorded height and the terrain height, plus 20 game units. In interiors there is no
  terrain, so it starts 20 units above the recorded position. The source comment says this puts the actor above the
  terrain before snapping down.
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwworld/worldimp.cpp>
- The trace distance comes from the worldspace's cell size, not the old fixed 500 units: 8,192 game units for a
  standard Morrowind cell, one cell down. It also allows for the offset between the actor's recorded position and its
  collision object. The lower of the start and the hit is kept.
- The trace is a sweep, not a thin ray. The movement solver's trace-down (MovementSolver::traceDown) calls findGround
  of the actor tracer, a convex sweep of the actor's own collision shape, and places the actor at the hit plus the
  ground offset.
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwphysics/movementsolver.cpp>
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwphysics/trace.cpp>
- A second check runs: a thin downward ray against world geometry and heightmaps. If the ray and the sweep disagree by
  more than 35 game units, or the sweep found an unwalkable slope, the ray result can be used; otherwise the sweep's.
  Its source comment says the ray check is "required for some broken door destinations in Morrowind.esm", which is why
  OpenMW's version is heavier than a build-time rule needs to be.
- A small clearance is left: sGroundOffset is 1.0 game unit.
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwphysics/constants.hpp>
  The trace also sets the actor's grounded and slope state, so the actor does not fall that distance under gravity.
- The grounded state is set separately: the physics actor starts grounded when its creature stats record a fall height
  of zero. An actor with a recorded fall (a saved game, genuinely mid-air) keeps it.
  <https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwphysics/actor.cpp>

What could be borrowed from it (background only; AmiWind's own contract is simpler, see the
[settled design](#the-settled-design)):

- start slightly above the recorded placement;
- sweep the actor's real collision footprint;
- compare with a separate floor ray;
- reject or investigate unsuitable surfaces;
- keep a small justified clearance;
- set the grounded state separately from the position;
- keep flying, swimming and scripted actors distinct;
- do it at conversion time against the final CHIM collision, and leave runtime physics to take over afterwards.

Caution: a large search range does not justify dropping an actor thousands of units. The intended supporting floor must
be found, which matters in multi-storey interiors.

## The numbers

A sample is one foot-contact probe of an actor, not an actor: the 1,662 failed residents gave 22,404 samples.

| Result of the probe | Samples | Share |
| --- | --- | --- |
| Floor found | 10,730 | 47.89 % |
| No floor within reach | 11,636 | 51.94 % |
| Blocked | 25 | 0.11 % |
| Too steep | 13 | 0.06 % |

So the 11,636 are samples, not actors. A sampling scheme can legitimately probe outside the supporting footprint, so the
misses had to be classified: footprint edges, the short trace, or real gaps and coordinate mismatches. The
[measurements above](#headroom-coordinates-and-collision-measured-separately) classify them: 11,551 are headroom deeper
than the check's reach, 6 a foot over an edge, 3 a foot over a higher surface, 58 only the closing clip floor, 18 no
floor within 400 units.

The trace reaches only 4 units, so it censors every gap above 4: a larger real gap shows up as "no floor", and the
recorded gaps (to 4.0) are cut off at that limit.

Correction of an earlier statement: a varying gap does not rule out a scale mismatch. With actor scale s_a, floor
scale s_f, height z and an offset b, the gap is dz = (s_a - s_f) * z + b, which changes with z. Only a pure translation
gives a constant offset. So "the gaps are not one constant" did not exclude a unit or scale error between the actor
coordinates and the store models; the regression of the headroom on z (slope -0.0003 over 1,899 batch-room residents)
does exclude it.

## What must be shown before it is closed

From the maintainer's review of 23 October 2026. Four failure types are measured separately:

| Type | What it looks like | Typical cause |
| --- | --- | --- |
| Actor above a valid floor | a gap over supported floor | headroom, or the bake was skipped (compare height before and after grounding) |
| Actor partly inside the floor | a negative gap | collider origin or foot height mismatch |
| No floor detected | no support under the feet | missing collision, wrong space, short trace, a seam |
| Wrong surface chosen | support on the wrong thing | pylon, furniture, ceiling, overlapping floors |

How an actor must be grounded: by contact, so that actor height = support height - foot offset + a small justified
clearance. Only walkable surfaces count, seams are respected, never a lower storey, never into geometry or furniture. A
longer trace is for diagnosis only, never for moving actors deeper.

Acceptance:

- every one of the 1,662 residents is grounded, or has a documented, justified exception (1,643 grounded, 19 explicit
  exceptions);
- every miss is explained (see the measurements above);
- the actor and CHIM collision coordinates are shown to be compatible (exactly, see the measurements above);
- it works across maps, frames and rooms;
- the 110 explicit pose exceptions keep their positions (unchanged);
- a gate regression test makes sure CHIM rooms cannot bypass grounding again (require_fitted, GroundFitCoverageTests);
- the bug stays open until a packaged build passes (the fix is not yet seen in a build);
- the same diagnostic is run on the exterior actors that floated before.

## Decision

The maintainer's decision of 23 October 2026: AmiWind's initial actor placement follows modern OpenMW's logic, as raised
by pull request 1958. Each NPC and creature that is not in an explicit pose is attached to the first walkable surface
below it when its scene loads. The result is compared with the original game's observed behaviour. AmiWind does this
once, at build time. This matches the project rule that game mechanics follow OpenMW.

The public write-up of this design is [Actor placement](../ACTOR_PLACEMENT.md).

### The settled design

The maintainer and his review settled one grounding contract, with Quake semantics, used in two places:

- Build time is authoritative. The bake writes the grounded position and the image check proves it.
- At runtime, the actor spawn in the game script uses the engine's drop-to-floor as a safety net, and only after the
  room's CHIM collision is registered.

Quake's own pattern: id Software's walking-monster start raises the monster by 1 unit ("raise off floor a bit"), then
calls droptofloor, and it delays this until the other entities (doors) have spawned. The engine side is PF_droptofloor
in <https://github.com/id-Software/Quake/blob/master/WinQuake/pr_cmds.c>. It traces the entity's box down 256 units. It
fails when the trace fraction is 1 (nothing hit) or the trace is all-solid. Otherwise it moves the entity to the end
point and sets the on-ground flag and the ground entity. It does not reject every trace that starts inside solid, so
anything stricter is an AmiWind extension and is documented as one. The 256-unit reach is Quake's choice and is bounded
for actors in multi-storey rooms.

The build-time rule has six steps: identify the intended floor beneath each actor; check that it is a walkable surface;
check whether the actor's collision volume fits at that position; calculate the correct resting height; bake the
position into the converted data; reject ambiguous placements for further analysis. The collision hull is traced
straight down with Quake's droptofloor semantics; there is no runtime convex sweep.

Safeguards kept:

- the walkable-surface check;
- the 110 pose exceptions;
- explicit failure reports;
- the multi-storey guard (the first collision is not always the intended floor: pylons, seams, furniture);
- the diagnostics.

Build and runtime must agree. Grounding an already baked actor again must not move it meaningfully, G(G(p)) close to
G(p), so the game never re-snaps what the build placed. Collision, hull size, scale and precision are the same on both
sides.

Proof required on the real 1,662:

- how many have valid support;
- how many remain, and why;
- whether the runtime reproduces the baked positions;
- whether the original regression check passes.

All four are answered in the [status](#status-23-october-2026) and in
[how the invariants are met](#how-the-three-initial-placement-invariants-are-met).

No more design changes unless the measurements show something new.

The split: stationary actors are grounded at build time now. Moving actors get fuller runtime grounding in v0.0.49.

Why OpenMW's version is heavier: it has to cope with bad placement data in the original game files. Its source comment
about broken door destinations in Morrowind.esm is the maintainer's pointer to that. AmiWind controls its own
converted data and checks it at build time, so it can use the lighter contract above.

### AmiWind's rule as built

AmiWind settles stationary residents once at build time, on the collision the engine uses for the room (the store
models), with a bound against lower storeys: the first walkable surface (a placed mesh of the room, never its closing
clip floor) under the resident within 8 units over and 32 under its recorded spot, the seam retried 1/16 unit aside;
the origin goes 0.25 over it (OpenMW's 1 game unit); every idle sole must then be within -0.5..1.0, else the nearest
half-unit spot within 32 (then 48) units is tried; otherwise the resident is refused and reported. The 32-unit bound
(128 game units) covers the measured headroom of every scene kind above; a first surface further down is never used
without a decision (a balcony resident never ends up downstairs). Differences from OpenMW, on purpose: no lower
storey, steep surfaces refused rather than slid on, refusals reported. This build-time rule covers stationary
residents only; once actors move (levitation, flying creatures, jumps, swimming, knockback, scripted SetPos) runtime
grounding needs the fuller OpenMW-style approach (shape sweep, ray cross-check, grounded state), planned with MWScript
and actor movement behaviour in v0.0.49 (ACTOR-SPAWN-DROPTOFLOOR-49). A slower footprint variant (every sole traced, the
resident's box tested free) stays in the code, off by default (ROOM-BAKE-FOOTPRINT-SLOW-48).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- ACTOR-MOVING-RUNTIME-GROUND-48 (no report page): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-NPC-GROUNDING-48](ROOM-BATCH-NPC-GROUNDING-48.md): The residents of rooms no town list holds have no grounding class: --room-batches 5 is refused (62 NPCs in 22 rooms)
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative
- VIVEC-HOVER-VERIFY-48 (no report page): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect

Related bugs in other categories:

- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- [CHIM-ROOM-CLIP-DRAWN-BOX-48](CHIM-ROOM-CLIP-DRAWN-BOX-48.md): A CHIM room's runtime collision skips a placement by its drawn box, and a store model's hull can reach past that box
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- [ROOM-BAKE-FOOTPRINT-SLOW-48](ROOM-BAKE-FOOTPRINT-SLOW-48.md): The room actor bake's footprint rule with the collision-box test is more than 100 times slower
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- [ROOM-TRACE-VISIT-GUARD-48](ROOM-TRACE-VISIT-GUARD-48.md): Long downward traces on the Hall of Processing's collision raise the trace visit guard (Cyclic or excessive collision tree)

<!-- END GENERATED CATEGORY -->
