# Actor placement: how actors stand, fly, swim and float

_Last updated with AmiWind v0.0.52-dev (26 October 2026)._

<!-- contents start -->
## Contents

- [Contents](#contents-1)
- [Why actors start above the floor](#why-actors-start-above-the-floor)
- [How the original game and OpenMW ground actors](#how-the-original-game-and-openmw-ground-actors)
- [How Quake does it](#how-quake-does-it)
- [Three questions per actor](#three-questions-per-actor)
- [States and AmiWind's rule for each](#states-and-amiwinds-rule-for-each)
- [Flying, and a Levitate spell that is not levitating](#flying-and-a-levitate-spell-that-is-not-levitating)
- [Visual hover is not a grounding error](#visual-hover-is-not-a-grounding-error)
- [AmiWind's contract](#amiwinds-contract)
- [Where this is tracked](#where-this-is-tracked)

<!-- contents end -->

This page explains how AmiWind puts an actor (an NPC or a creature) at its starting position, and why. It is written
from the maintainer's review of how the original game, OpenMW and Quake do it. It is design notes, not a claim that
every part is finished: the tracking is in [ROOM-ACTORS-FLOATING-48](bugs/ROOM-ACTORS-FLOATING-48.md).

## Contents

- [Why actors start above the floor](#why-actors-start-above-the-floor)
- [How the original game and OpenMW ground actors](#how-the-original-game-and-openmw-ground-actors)
- [How Quake does it](#how-quake-does-it)
- [Three questions per actor](#three-questions-per-actor)
- [States and AmiWind's rule for each](#states-and-amiwinds-rule-for-each)
- [Flying, and a Levitate spell that is not levitating](#flying-and-a-levitate-spell-that-is-not-levitating)
- [Visual hover is not a grounding error](#visual-hover-is-not-a-grounding-error)
- [AmiWind's contract](#amiwinds-contract)
- [Where this is tracked](#where-this-is-tracked)

## Why actors start above the floor

The original data stores an actor where the editor dropped it, usually a little above the floor. Engines in general
start characters slightly high: floating-point precision can put an exact position inside a surface, the collision
shape can differ from the visible floor, a model's origin is not always at its soles, and the actor, its capsule and the
world collision become active at different times.

Starting inside the floor is worse than starting above it: a physics solver pushes the actor out (pops, launches) or
leaves it stuck. Starting a little above lets gravity or an explicit ground snap settle it. A visible drop after a load
shows that some correction ran. It does not show that the headroom was put there on purpose.

Grounding on load has to solve two separate problems: collision penetration, and fall damage (settling must not count
as a fall). Spawning high and letting gravity act does not avoid fall damage by itself; the engine has to snap the actor
to the ground, reset its falling state, or keep the drop too short to count.

## How the original game and OpenMW ground actors

In the original game, every NPC and creature is placed on the ground after its cell loads. OpenMW at first did not do
this well. Its issue 3219, "NPC and creature initial position tracing down limit is too small"
(<https://gitlab.com/OpenMW/openmw/-/work_items/3219>), records actors left in the air, falling, showing a jump
animation after entering interiors and sometimes hurt or killed. OpenMW only searched 500 units down; the original's
reach was larger. OpenMW pull request 1958 (October 2018, OpenMW 0.45) raised the limit. How the original did it
internally is not established.

Modern OpenMW does this once, when an actor enters its processing range:

- it starts 20 units above the recorded position (or the terrain, outside);
- it traces down a distance taken from the worldspace's cell size (8,192 units for a standard Morrowind cell);
- the trace is a sweep of the actor's own collision shape, checked against a separate thin downward ray (if the two
  differ by more than 35 units, or the sweep hit an unsuitable slope, the ray can win);
- it leaves a clearance of 1 unit;
- it sets the grounded state: a physics actor with no recorded fall height starts as already grounded (OpenMW commit
  03aa2705, <https://gitlab.com/OpenMW/openmw/-/commit/03aa2705514776f717d1171d43757eccf16793ce>), which stopped the
  jump animation on load.

Initial placement is three separate invariants: position (the collision hull on the right supporting surface), state
(grounded, no falling velocity, no fall damage) and pose (the right animation before the actor is visible). The source
files are listed on the [register page](bugs/ROOM-ACTORS-FLOATING-48.md#how-modern-openmw-grounds-actors).

## How Quake does it

Quake's own pattern for a walking monster is to raise it 1 unit, then call droptofloor, after the other entities (doors)
have spawned. The engine function PF_droptofloor is in
<https://github.com/id-Software/Quake/blob/master/WinQuake/pr_cmds.c>. It traces the entity's box down 256 units. It
fails when nothing is hit or the trace is all-solid. Otherwise it moves the entity to the end point and marks it as on
the ground, with a ground entity. It does not reject every trace that starts inside solid; anything stricter in AmiWind
is an AmiWind extension. The 256-unit reach is Quake's choice, and in multi-storey rooms it has to stay bounded.

## Three questions per actor

Placement asks three separate things about each actor:

- movement capability: can it walk, fly, swim, or levitate by magic? These overlap; OpenMW's creature records expose
  canFly, canSwim and canWalk independently
  (<https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_types.html>);
- current movement state: standing, swimming, flying, falling, jumping, or script-controlled;
- animation and pose: standing, sitting, lying, floating meditation, or a scripted animation.

## States and AmiWind's rule for each

| Actor state | AmiWind rule |
| --- | --- |
| Ordinary standing NPC | ground on spawn |
| Walking land creature | ground |
| Flying creature | keep its airborne position |
| NPC under an active Levitate effect | do not snap |
| Swimming actor | keep its depth |
| Water Walking | water counts as support |
| Jumping or falling | keep the movement state |
| Slow Fall | not levitation |
| Script-positioned | respect the script |
| Special idle animation | ground the collision origin, keep the animation |
| Dead or posed | pose-aware placement |

The one central rule: only ground actors whose current state requires ground support. For every exemption the
converter records the reason (actor, capability, placement, pose, grounding rule, whether visible foot contact is
required). Before the final pass the actors are counted by class: ground-required, naturally flying, initially
levitating, swimming or waterborne, script-positioned, special visual poses, unclassified. The 110 explicit exceptions
each get their own reason, not one collective flag, and the 1,662 batch-room residents are not assumed to all belong on
the floor until their states are checked against records, scripts and animation data.

## Flying, and a Levitate spell that is not levitating

OpenMW decides that an actor is flying (World::isFlying in
<https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwworld/worldimp.cpp>) when the actor is alive, allowed to
fly, and either of a flying creature type or under an active Levitate effect, with collision available. Paralysis and
the game's levitation limits also count.

Knowing a Levitate spell is not levitating. The converter must not exempt an NPC because its spell list contains
Levitate. An airborne state that only starts after a scene has loaded is not active at the original placement.

## Visual hover is not a grounding error

Vivec (the god, a creature record) appears to meditate in the air. This looks like an animation, not an active Levitate
effect: a mod that only makes his vanilla idle repeat exists, and another mod adds combat levitation because the
vanilla one lacks it. If so, his collision origin can be grounded while the model visibly hovers. This is stated as to
be verified from his record and animation before it is treated as settled.

Grounding and visible foot height are different questions. A character whose animation lifts its feet must not be
flagged as badly grounded.

## AmiWind's contract

One grounding contract with Quake semantics, used in two places:

1. Build time is authoritative. The bake writes the grounded position and the image check proves it. The build-time
   rule has six steps:
   1. Identify the intended floor beneath each actor.
   2. Check that it is a walkable surface.
   3. Check whether the actor's collision volume fits at that position.
   4. Calculate the correct resting height.
   5. Bake the position into the converted data.
   6. Reject ambiguous placements for further analysis.
2. At runtime, the actor spawn in the game script uses droptofloor as a safety net, and only after the room's CHIM
   collision is registered.

This is simpler than OpenMW's: there is no convex sweep plus cross-check ray at runtime. The collision hull is traced
straight down, with Quake's droptofloor semantics. OpenMW's approach above is background, not AmiWind's contract.

Build and runtime must agree. Grounding an already baked actor again must not move it meaningfully, so the game never
re-snaps what the build placed. Collision, hull size, scale and precision are the same on both sides.

Safeguards that stay: the walkable-surface check, the pose exceptions, explicit failure reports, the multi-storey guard
(the first collision is not always the intended floor: pylons, seams, furniture) and the diagnostics. A large search
range never justifies dropping an actor thousands of units; the intended supporting floor must be found. Flying,
swimming and scripted actors stay distinct, and every exemption is recorded with its reason.

For the residents of CHIM rooms the build-time step runs in the image, after the rooms install, because a room has
no floor to fit against before that: the early check only classifies a shell room's residents, the image fits them
on the room's store collision, a guard requires that every ground resident went through a bake, and the check then
measures them ([the order, step by step](NPC_GROUND_CONTACT.md#where-a-chim-rooms-residents-are-fitted-v0048)).

Stationary actors are grounded at build time now. Moving actors get fuller runtime grounding in v0.0.49.

## Where this is tracked

[ROOM-ACTORS-FLOATING-48](bugs/ROOM-ACTORS-FLOATING-48.md) holds the regression, the numbers (1,662 residents of batch
CHIM rooms), the acceptance criteria and the decision. It stays open until a packaged build passes. See also
[NPC ground contact](NPC_GROUND_CONTACT.md) and [character states](CHARACTER_STATES.md). The scripted creatures of the
main quest (Dagoth Ur, the Heart of Lorkhan) and Vivec: [scripted actors](SCRIPTED_ACTORS.md).
