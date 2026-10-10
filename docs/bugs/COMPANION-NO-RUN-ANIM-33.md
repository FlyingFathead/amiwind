# COMPANION-NO-RUN-ANIM-33: The companion slides instead of walking or running, and mimic mode does not mirror the gait

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | resident models (idle-only default profile); aw_companion.c animate; aw_npcpath.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | medium: The follower moves with an idle pose: it visibly slides behind the player. |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found in the owner's playtest with Dralsea Arethi (Balmora) as the companion. The animation
side belongs to the animation kit line (walk and run cycles); the follow rules to the companion code.

## Symptom

The companion follows the player but keeps its idle pose and slides. In mimic mode (`dbg companion
mimic speed on`) it should follow and mirror the player's gait, walking when the player walks and
running when the player runs.

## Where

- Resident models: `tools/npc_anim.py` `selected_profile` defaults to the idle-only profile
  (8 idle frames), so release builds have no walk or run frames
  ([NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md), [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md)).
- `engine/aga/src/aw_companion.c` `animate`: with a layout (`<model>.anm`) it already picks walk or
  run by the speed it moves (`aw_anim.c` `AW_AnimMoveGroup`, rate matched to the cycle's own speed);
  without one it keeps the idle frames (or the old 21-frame town walk).
- `engine/aga/src/aw_npcpath.c` `AW_PathSpeed`: mimic mode copies the player's speed (plus a quarter
  to catch up); otherwise it runs beyond twice the follow distance.

## How it happened

The follower was built and tested on models with walk frames; the release line ships residents with
the idle-only profile while the animation kit is kept on its own line.

Reference (OpenMW 0.51 `aifollow.cpp`): a follower moves to its target and sets the run flag when the
target is farther than 450 units, back to walk below 325 (a dead zone so it does not flip at the edge);
the walk or run animation follows that flag. The original has no gait mirroring: mirroring the
player's walk/run in mimic mode is an AmiWind extension (label it so).

## Why it was not caught

No check that a moving actor plays a moving animation group; the companion tests run on synthetic
layouts.

## Reproduction

Always in a v0.0.33 build: pick a resident as companion and walk or run.

## Repair

Not yet. (1) Residents get walk/run cycles: the animation kit profile in the release builder
(animation kit line; the engine side is ready). (2) Mimic mode, an AmiWind extension: the companion
copies the player's gait state (walk or run, from the player's speed against the walk/run threshold)
rather than only the speed, so the chosen group always matches the player's. (3) Without mimic: the
original's run/walk switch at 450/325 units (112.5/81.25 AmiWind units) instead of "twice the follow
distance". (4) A moving actor with only idle frames gets a console note once (no silent slide).

## Verification

None yet: a companion fixture checks the group chosen for walking and running players in mimic mode,
the 450/325 hysteresis without mimic, and an in-game clip of the follower walking and running.

## Prevention

A gate that a resident model used by a moving actor has walk and run groups (or is reported).

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
