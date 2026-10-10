# NPC-NEAR-SKIN-TEXELS-33: Original-head models had blurrier bodies than the budget model

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 9 October 2026, in v0.0.34-dev |
| Where | NPC bake skin tiles (tools/npc_geometry.py _bake), raised-limit models |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34-dev (last seen) |
| Severity | medium: Near NPC bodies would look blurrier up close than far away; caught before any build shipped it. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.34-npc-heads, not shipped at the time of writing. Found by the NPC level-of-detail
work in a trial merge, before any build shipped the original-head bake.

## Symptom

Up close, the near NPC model (original head, about 1,000 triangles) showed its body and clothing with a quarter
of the texels per face that the far map model (480 triangles) has: blurrier near than far.

## Where

`tools/npc_geometry.py` `_bake`, for models whose face limit the head rule raised
([NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md)).

## How it happened

Each output face gets its own texture tile. 16-texel tiles fit 960 faces in the renderer's 480-row skin, so
the first version of the head rule put every face of a model past 512 faces on 8-texel tiles, the body
included.

## Why it was not caught

The checks compared triangle counts and skin bounds, not texels per face against the budget model.

## Reproduction

Bake an appearance of about 1,000 triangles with the head rule and compare the skin tile size of a body face
with the budget bake's.

## Repair

`mixed_tile_skin`: one skin with 16-texel tiles where its 480 rows allow and 8-texel tiles for the rest, in
order of priority: the face, the torso, neck and hands, the rest of the body, last the hair or helmet. A
1,005-face model keeps 928 faces on 16-texel tiles; the body never drops below the budget model's tiles.

## Verification

`tests/test_npc_head_detail.py`: a 1,005-face model keeps 16-texel tiles for the face and the body within 480
rows; a model that fits takes 16-texel tiles throughout. Close-up frames of Fargoth were checked privately.

## Prevention

The test above fails if a body face of a near model drops below 16 texels while the skin has room.

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
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
