# NPC-DAGOTH-BODY-DECIMATION-33: Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Gallery model of r/dagothr.nif (dagoth_ur_1, dagoth_ur_2) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: One model loses 1,351 of 2,254 triangles; the owner wants it whole; needs a format or engine choice. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.34-npc-heads, not shipped at the time of writing: the owner chose option 1, the
shared-vertex encoding. Nothing else changes in the engine.

## Symptom

Dagoth Ur's converted model keeps the mask, crest and neck piece exactly, but his body is reduced from
1,937 to 586 triangles: 903 triangles in all instead of 2,254.

## Where

Both Dagoth Ur records of the base master, `dagoth_ur_1` and `dagoth_ur_2` (creatures), use the same model,
`r\Dagothr.NIF`; no other master (Tribunal, Bloodmoon) has a Dagoth Ur record. The profile is
`config/gallery_model_quality.json` (`dagoth-mask-v1`: budget 1,000, exact neck part, mask and mask part).

## How it happened

The original model has four shapes: `Tri neckpart` 30, `Tri mask` 240, `Tri maskpart` 47 and `Tri body`
1,937 triangles, 2,254 in all, with 1,741 shared source vertices. The converter writes three vertices per
triangle (each face has its own texture tile), and the renderer's extended alias path stops at 1,024
triangles (`MAXALIASVERTS` 3,072, `engine/aga/src/r_local.h`; `AW_AliasBudgetAllows`, `model.c`). The
profile could only protect the mask; the body takes the rest of the 1,000-triangle budget.

## Why it was not caught

The profile was written to keep the mask; no check compared the whole model with its source.

## Reproduction

Convert `r\Dagothr.NIF` with the gallery converter and compare its 903 triangles with the source's 2,254.

## Repair

Options put to the owner: (1) a shared-vertex encoding (chosen), (2) splitting him into at least three alias
models (the body alone is over 1,024 triangles), (3) a larger engine ceiling for one model (its stack work
arrays would not fit the 300,000-byte task stack).

The shared-vertex encoding (`tools/npc_geometry.py` `shared_vertex_mdl`, profile `dagoth-whole-shared-vertex-v1`
with `"encoding": "shared-vertex"` in `config/gallery_model_quality.json`) keeps the source vertices and their
texture coordinates and packs his three original textures (256 x 256, 128 x 128 and 64 x 32) into one 416 x 256
skin. The model has all 2,254 triangles on 1,741 vertices (170,532 bytes); under 2,000 vertices the renderer
takes its original alias path, which has no triangle cap. The gallery cache accepts a shared-vertex model past
1,024 triangles only under 2,000 vertices. The previous profile stays on record (`previous_profiles`).

## Verification

Real data, 9 October 2026: the converted model has 2,254 triangles and 1,741 vertices, the same as the source,
and an offline render matches the original's shape. Colours: the palette mapping still turns his saturated
reds and the gold brown (a separate finding). An in-game check in the gallery remains open.

## Prevention

`tests/test_npc_head_detail.py`: the profile uses the shared-vertex encoding, and the encoding keeps every
original face and vertex under the renderer's 2,000-vertex limit.

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
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
