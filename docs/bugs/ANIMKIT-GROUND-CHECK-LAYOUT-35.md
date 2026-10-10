# ANIMKIT-GROUND-CHECK-LAYOUT-35: With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/check_actor_ground.py contact_samples; tools/actor_grounding.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: Every default build failed in the image step once the kit became the default (first seen in a MiniWind build) |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.35-dev1 MiniWind animkit 853d9b2 |
| From commit | source 853d9b2, engine 853d9b2, CHIM world 853d9b2 |
| CHIM engine version | CHIM 0.1.0, engine 853d9b2, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line before any image shipped with it.

## Symptom

The first MiniWind build with the animation kit on stopped in the image step with "Undeclared
ground-resident pose layout".

## Where

`tools/check_actor_ground.py` (`contact_samples`, the model reader) and `tools/actor_grounding.py`.

## How it happened

The ground check samples the feet of every frame of a resident model and accepted only the 8-frame idle
cycle. With the kit as the default, residents also carry walk, run and other frames.

## Why it was not caught

The gates do not build an image; the kit became the default in the same release.

## Reproduction

Any image build with `--anim-kit on` (the default) and residents.

## Repair

A kit model has its layout beside it (`<model>.anm`); the checker reads the idle group from it and checks
those standing poses, as before. A kit model without its layout, or a layout without an idle group, still
fails: the check is never skipped.

## Verification

tests/test_actor_ground.py `test_animation_kit_models_are_checked_on_their_idle_group`: a model with idle and
floating walk frames passes with its layout, fails without it, and floating idle feet still fail.

## Prevention

The MiniWind animation kit sandbox builds an image in minutes; it is the check before a release build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
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
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
