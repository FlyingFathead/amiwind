# NPC-NO-RUN-ANIM-35: Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | Builder default --npc-anim idle; engine walk/run selection (aw_anim.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | high: Player-visible in every town: followers and fighters slide or walk while they should run |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.34 release |
| From commit | source 70b04e2, engine 70b04e2, CHIM world 70b04e2 |
| CHIM engine version | CHIM 0.1.0, engine 70b04e2, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

Playing v0.0.34: a companion and hostile NPCs only ever walk, never run, and their walk looks wrong (feet
sliding). Wider than COMPANION-NO-RUN-ANIM-33, which named the companion only.

## Where

The builder's default animation profile (`--npc-anim idle` in `tools/build.py`) and the engine's walk/run
selection (`engine/aga/src/aw_anim.c`, `AW_AnimMoveGroup`).

## How it happened

The engine already picks walk or run by an actor's speed, but only for models that carry those groups. The
animation kit that bakes them stayed opt-in, so release residents carried 8 idle frames; fighters fell back
from run to walk, and moving actors slid.

## Why it was not caught

No playtest build used the kit; the default build had no moving-actor check.

## Reproduction

Any v0.0.34 build: `dbg companion test`, run; or start a fight in a town.

## Repair

The kit is the default (`--anim-kit on`, the `react+full` profile: a standing model plus a full model worn
while moving). `--anim-kit off` keeps the previous idle frames. `dbg animkit` switches and inspects it in
game. The walk and run rules and their sources: [ANIMKIT.md](../ANIMKIT.md).

## Verification

tests/test_animkit.py (default on, off = idle, the console parser and group table, the preset); an
in-game check with `--miniwind-animkit` is pending.

## Prevention

The default build carries the kit; the MiniWind preset makes the check a few-minute build.

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
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
