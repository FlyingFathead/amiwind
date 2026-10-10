# NPC-ANIM-IDLE-ONLY-33: NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/prepare_area.py build_resident (idle_times(8) only); engine/aga/src/aw_companion.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: A walking companion or fighter slides in its idle pose; no footsteps |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Repair in source on v0.0.33-anim-kit, not yet in a build: the character animation kit
([ANIMATION.md](../ANIMATION.md)) samples walk, run, swim, hit, knockdown, death and a hand-to-hand
attack from the original text keys (`build.py --npc-anim react|move|full`), the engine picks the group
from the actor's speed with a speed-matched rate and plays the original footstep sounds. `idle` (the
previous 8 idle frames, byte-identical models) stays the default until the owner accepts a profile
([NPC-ANIM-MEMORY-33](NPC-ANIM-MEMORY-33.md)).

## Symptom

The NPC companion test walks after the player in its idle pose (the feet do not move); fighters and
residents have no hit, death or walk animation except the Arena fighters' own small set; no footsteps.

## Where

`tools/prepare_area.py` `build_resident` samples only `idle: start` to `idle: stop` (8 frames);
`engine/aga/src/aw_companion.c` steps walk frames 13 to 20 only on the 21-frame intro actors.

## How it happened

The resident converter was written for standing town actors; walking actors came later (companion,
combat) and reused the idle-only models.

## Why it was not caught

Residents never moved before the companion test; the companion test report named it ("pretty good
otherwise except for the missing animations").

## Reproduction

Any build: `dbg companion test`, walk away; the companion slides in its idle pose.

## Repair

`tools/npc_anim.py` (groups from the skeleton's text keys, in-place moving loops with the removed root
motion kept as the group speed, female groups from base_anim_female.nif, footstep events and the actor's
boot class), `tools/prepare_area.py` and `tools/import_town.py` (all residents, both paths), the layout
beside each model (`<model>.anm`), `engine/aga/src/aw_anim.c` (layout, group by speed, stepping,
footsteps), builtin #81 `aw_animprep` called by the resident spawn function, the companion and the
combat default layout use it.

## Verification

`tests/test_npc_anim.py` and `tests/aga_anim_test.c`; the idle profile reproduces the MiniWind
residents byte for byte; FS-UAE sandbox on the MiniWind (CHIM Balmora) with a walking companion.

## Prevention

The kit is the one sampler for every actor path (residents, companion copies, fighters through
`npc_anim.in_place`); new groups are a row in `config/npc-anim-kit.json`.

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
