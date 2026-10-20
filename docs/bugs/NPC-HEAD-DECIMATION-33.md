# NPC-HEAD-DECIMATION-33: NPC heads decimated into unrecognisable faces

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 17:55 +0300: maintainer: Angahran (Morag Tong Guild) has a dark gash/hole in the head mesh at close range; check head triangles against the original NIF
- Reported with v0.0.43-dev2 at 2026-10-18 17:58 +0300: maintainer: Shannat Pansamsi (Morag Tong Guild, ref 67641, a_76b87bee3530.mdl) has a crude, flattened face
- Reported with v0.0.44-dev1 at 2026-10-19 11:30 +0300: image step stopped on the Argonian female player body with the locked head reducer, fixed by the same fallback as the NPC bake

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Whole-model NPC bake (tools/npc_geometry.py), every humanoid head |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every NPC face is a handful of wrong triangles; a major visual break met in normal play. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 9 October 2026](#status-9-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bounded character-menu preview quality follow-up, 14 October 2026](#bounded-character-menu-preview-quality-follow-up-14-october-2026)
- [Persisting in v0.0.43-dev2; the locked head reducer, 18 October 2026](#persisting-in-v0043-dev2-the-locked-head-reducer-18-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Fixed in source on v0.0.34-npc-heads, not shipped at the time of writing. Every humanoid model bake
before this change is affected.

## Symptom

The maintainer saw Fargoth's face badly mangled in game: the head of a converted NPC is a handful of large,
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

## Bounded character-menu preview quality follow-up, 14 October 2026

The exact v0.0.40-dev1 native Nord-male to Nord-female character-change control
shows a distorted head in the appearance-menu preview, while the subsequent
inventory body display is valid as a limited rendering observation. The original
snapshot is retained privately. This does not establish complete appearance
quality or diagnose a new decimation failure: the selected head/hair identity,
preview transform, camera, geometry and skin mapping still need comparison
against the original. Relation to the historical whole-NPC reduction cause
above is unproven; do not borrow its source repair as preview acceptance.

The same control confirms and remains at the same world point. Health changes
from 55 to 50 with the expected character-stat rebuild; carried original
clothing remains equipped with quantity one, gold remains 87, and Luminous
Russula quantity one remains in Ingredients. This is scoped state preservation,
not verification of every character field, race, save/load path or visual.

## Persisting in v0.0.43-dev2; the locked head reducer, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: Angahran (Morag Tong Guild) has a dark gash in her head, Shannat
Pansamsi a crude, flat face. Cause: the original-head bake above ships off; the shipped default
`npc_head_detail` auto resolves to `budget` (decided for the project, 10 October 2026: original heads are
experimental), so every humanoid head is still reduced by the previous split and the previous reducer.
Measured on the maintainer's own data: Angahran's head keeps 57 of 450 triangles, her hair 30 of 325; Shannat's
head 101 of 524, his hair 42 of 326. The previous reducer (fast_simplification) does not keep a shape's rim:
it pulls the head away from where it meets the neck and the hair away from the head, and leaves cracks
(Angahran's head: 10 open edges in the source, 15 after it, a hole; Shannat's hair: 0 and 2 before, 32 and 6
after).

Decided for the project, 18 October 2026 (the maintainer, option "3b"): the whole-model triangle budget stays,
and head and hair are reduced with the boundary-locked reducer of the static meshes
(`npc_geometry.simplify_head_locked`: `mold_shell.quadric_simplify` with every rim vertex locked, the face turn
limit `static_lod.LOCKED_MAX_TURN`, the rule of MESH-LOD-OPEN-SEAMS-33). Builder switch `--npc-head-reducer
locked|default` (config `npc_head_reducer`, default `locked`, `AMIWIND_NPC_HEAD_REDUCER`); `default` is the
previous reducer, byte for byte. A larger head share (option "3c") is not decided: it waits for a Balmora crowd
A/B of the frame cost.

Island-wide, all 2,675 NPC records (budget plan, rest pose): with the previous reducer every one of them has a
head or hair shape whose rim changes; with the locked reducer none. The locked reducer keeps a few more
triangles where a rim leaves too few collapses: median 10 per model, 90th percentile 51, maximum 227 (head and
hair 296,355 to 349,622 triangles in total). 18 models then pass the 666-face limit at the first budget; all 18
bake with the existing retry at budget 384 (the body gives up the triangles), checked one by one. Angahran:
head 58 triangles, 10 open edges (the source's); hair 25 and 18. Shannat: head 100, 10 open edges; hair 28 and
14 with the source's open edges.

`tests/test_npc_head_reducer.py`: the rim is kept on a synthetic head, the previous reducer moves it; the
`default` setting reproduces the previous bake's bytes (SHA-256 recorded from the code before the change); the
switch, its builder option and the gallery cache key; original heads unchanged. Checked privately on the maintainer's data: Angahran's and
Shannat's head and hair keep every rim, within 8 triangles of their share. The faces still keep only 13 to 19 % of their triangles: the flat look remains until a larger head share.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player
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
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
