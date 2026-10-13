# ANIMKIT-COVERAGE-35: NPCs that move or fight have no walk, run or attack animation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | animation kit profile assignment (react standing vs full movers), Seyda Neen residents |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35 (last seen) |
| Severity | high: Any resident who turns hostile or follows looks broken; the kit is meant to cover every NPC |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3cbe85a, engine 3cbe85a, CHIM world 3cbe85a |
| CHIM engine version | CHIM 0.1.0, engine 3cbe85a, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Open (owner playtest of v0.0.35).

## Symptom

Fargoth in Seyda Neen has no walk animation at all. When he fights the player he does not punch: he hops straight at
the player with no walk or attack animation.

Other Seyda Neen villagers do the same: when they come at the player they glitch forward with no proper walk or
run animation. So it is not one NPC but (at least) the town's residents.

## Where

The animation kit's profile assignment: residents get the standing set (react) and only movers get the full set
(walk, run, attack); a resident who turns hostile or follows the player moves without the frames for it. To be
confirmed in the build's kit receipt for Seyda Neen.

## How it happened

The kit (on by default since v0.0.35) decides per NPC which animation groups to bake. An NPC classified as standing
gets no locomotion or attack groups, but scripts and combat can still make it move and fight.

## Why it was not caught

No check compares the groups an NPC can need (it can move, fight, swim) with the groups baked for it; playtests
covered the Balmora movers and the Arena fighters.

## Reproduction

Always: provoke Fargoth in Seyda Neen and watch him approach and fight.

## Repair

Planned: every NPC that can move or fight (every NPC outside a fixed scripted pose) gets walk, run, swim and attack
groups, island-wide; plus a builder audit that fails when an NPC lacks a group it can need, so no NPC is left out.

## Verification

To do: Fargoth walks, runs and punches in a MiniWind Seyda Neen sandbox; the audit reports every NPC covered.

## Prevention

The coverage audit runs in every build that bakes NPCs.


## Swimming follow-up, 12 October 2026

The owner reports that the player uses walking poses at the surface and when
submerged in v0.0.38-dev2. Audit original swim/dive animation groups and their
state selection for the player and relevant NPCs, including companion movement.
See WATER-GAMEPLAY-PARITY-38 for movement and breath/damage verification; visual
pose alone does not establish missing swimming physics. No repair accepted.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
