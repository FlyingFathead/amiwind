# NPC-HEAD-DECIMATION-33: NPC heads decimated into unrecognisable faces

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Whole-model NPC bake (tools/npc_geometry.py), every humanoid head |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every NPC face is a handful of wrong triangles; a major visual break met in normal play. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.34-npc-heads, not shipped at the time of writing. Every humanoid model bake
before this change is affected.

## Symptom

The owner saw Fargoth's face badly mangled in game: the head of a converted NPC is a handful of large,
wrong-shaped triangles instead of the original face.

## Where

The whole-model NPC bake, `tools/npc_geometry.py` (`bake_quotas`, `bake`), used by every humanoid model:
world residents (`prepare_area.py`, `import_town.py`), the Seyda Neen actors (`prepare_npcs.py`), combat
and guard models, the intro and the NPC gallery. Creatures are not affected (they have no body parts);
Dagoth Ur's mask was already protected by its quality profile (his body is a separate finding,
[NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md)).

## How it happened

A humanoid is assembled from about 28 body-part shapes (median; up to 88) with 2,450 to 6,277 original
triangles, and the bake fitted the whole outfit into 480 triangles. Each shape got a share by triangle
count (a head counted 1.7 times; residents' heads at most 120 triangles as a floor), and each shape was
simplified on its own. The original heads are dense: the island-wide census of all 3,500 humanoid
appearances (2,675 NPC records, equipped and base) gives head plus hair or helmet a median of 775
original triangles (10th percentile 628, 90th 893, maximum 1,125). The previous bake left them a median of
124 (maximum 170): about a sixth of the face's triangles. Fargoth's head (510) and hair (369), 879
triangles, became 136 to 140.

## Why it was not caught

The bake checked only budgets (faces, vertices, skin size) and shell preservation for large torso panels;
nothing measured what a head kept. Dagoth Ur's mask got a hand-made profile, but the rule was never applied
to the shared humanoid bake.

## Reproduction

Bake any humanoid appearance with `--npc-head-detail budget` (the previous method) and compare the head
shape's output triangles with its source triangles; or look at any NPC's face in game.

## Repair

One shared rule in `tools/npc_geometry.py` (`head_plan`): every shape of body-part slots 0 (head) and 1
(hair or helmet, attached to the head) keeps its exact original triangles, the same exact-face mechanism as
Dagoth Ur's mask profile. Body and clothing keep the share the previous split gave them, as far as the alias
face limit allows, and give up triangles first (at least 4 per shape). The face limit is raised only as far
as needed, to the smallest of 666, 777 and 1,024 that holds the model; a model past 960 triangles keeps the
480-row skin with 8-pixel face tiles, as the gallery already does. If head and hair plus the minimal body
still do not fit in 1,024, the head stays exact and the hair or helmet is reduced, recorded in the plan
(`hair_reduced`); last, large torso panels give up their shell preservation. A head that does not fit alone
stops the bake with an error, never a decimated face.

- Builder switch `--npc-head-detail original|budget` (config `npc_head_detail`, default `original`),
  exported to the converters as `AMIWIND_NPC_HEAD_DETAIL`; `budget` is the previous bake, byte for byte
  (DON'T DELETE ANY METHOD). The mode is part of the NPC model cache key and of every stage fingerprint that
  reaches the bake.
- Models past 2,000 vertices need a byte-matching `model-budgets.txt` line in the engine (the gallery
  already writes one per model). The image step now adds a line for every such model outside the gallery
  (`audit_gallery_budgets.world_allowances`).

Measured over all 3,500 appearances (plan arithmetic with the gallery and resident calls, 9 October 2026):
the heads kept rise from a median of 124 to 751 triangles; the whole model from a median of 466 to 1,010
triangles (3,422 at the 1,024 limit, 78 at 777); body and clothing fall from a median of 343 to 261
triangles (10th percentile 148, minimum 59). 313 appearances (309 records) cannot hold head, hair and the
minimal body in 1,024 triangles: their head stays exact and their hair or helmet is reduced; nine of them
have more than 1,024 head and hair triangles alone (Crazy Batou 1,125; Davas Aralas, Llarel Llenim, Tidros
Indaram and the Dreamers 1,059; Smokeskin-Killer 1,052; Hisin Deep-Raed and Hrargal the Crow 1,047). No head
fails. Details and the drawing cost: [NPC model cache](../NPC_MODEL_CACHE.md#original-heads).

## Verification

`tests/test_npc_head_detail.py`: head and hair triangles equal the source in every frame under the default;
budget mode equals the previous split and bytes; the face limit is raised only as needed; hair is reduced
before the head and a head is never decimated; the switch, its export and the cache key; extended world
models get byte-matching allowance lines. Real-data bakes and offline renders of Fargoth before and after
were checked privately. An in-game check of an image built with the rule remains open.

## Prevention

The rule lives in the one shared bake, so every humanoid path gets it; the tests above fail if a head loses a
triangle under the default or if the previous method stops being reproducible.

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
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
