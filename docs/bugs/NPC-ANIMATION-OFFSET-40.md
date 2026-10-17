# NPC-ANIMATION-OFFSET-40: Simplified actor vertices keep a fixed offset while limbs rotate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | Offline actor mesh conversion: npc_geometry._bake vertex transfer |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev2 (last seen) |
| Severity | high: A correctly rotating source limb can become distorted in converted animation frames. |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | mutable v0.0.40-dev2 source |
| From commit | source 407795c, engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | Synthetic converter fixture; no running game executable is involved. |
| Platform or emulator | not in game (Synthetic full-bake rotation reproduction. The visible contribution to the reported running and leg problems is not yet isolated.) |

<!-- END GENERATED FACTS -->

## Symptom

A simplified vertex can drift from a rigidly rotating source limb even when
all original vertices follow the correct transform. This is a reproducible
conversion defect; its contribution to reported in-game thin legs or coarse
gait remains unverified.

## Where

The shared actor converter in `tools/npc_geometry.py`, when transferring
simplified vertices to the original triangle's animated poses. Protected
original geometry bypasses this transfer. Existing delivered models are
unchanged by editing the converter.

## How it happened

The previous transfer clamped barycentric weights to an original triangle,
then added the rest-pose residual as the same world-space vector in every
frame. Translation worked, but rotation and scale did not carry that residual
with the limb. More aggressive simplification can leave larger residuals;
that is not proof that this defect alone caused a particular playtest image.

## Why it was not caught

Earlier checks covered budgets, frame counts, rest-pose bounds and translation.
Those properties can pass while an offset is wrong in later rotating frames.
The historical v0.0.38 control is not an independent proof that this shared
converter behavior was correct.

## Reproduction

The new synthetic full-bake fixture supplies a simplified calf triangle with
both in-plane and depth offsets. It rotates the original surface by ninety
degrees, with translation and optional uniform scale. Before correction the
rotation and scaled-rotation checks fail; translation passes. No game assets
are included in these fixtures.

## Repair

The source correction retains a clipped barycentric surface anchor and
carries the remaining offset with the source triangle's best-fit proper
rotation and RMS scale. This preserves rigid rotation, translation and uniform
scale while bounding offset length even on thin triangles. It does not claim
exact general skin deformation. Degenerate references retain the previous
translation fallback; degenerate later frames can lose orientation information.
The floating-point rest pose is preserved. Different animated bounds can still
change the alias model's shared quantization grid, so decoded models need checks.

AmiQuake's existing alias-frame mechanism is reused: the converter writes the
corrected frames and the renderer selects them as before. No runtime skinning,
extra alias frames, increased model budget or renderer arithmetic is introduced.
Texture sampling, topology and the original ready-pose choice are unchanged.
Converter-source hashes participate in the existing conversion cache identity.

## Verification

Two intended failures were reproduced in the prior converter; nine focused
checks pass with the correction. They cover actual bake rotation and scaling,
translation, arbitrary rigid transforms, surface deformation, a degenerate
reference, a collapsed later frame, thin triangles and bounded nonuniform scale. The broader 115-check converter suite also passes.
Original-asset rebakes, model budgets, native gait/anatomy and matched original
comparisons must still pass before an inspection candidate is shipped.
The issue and the related leg/gait reports remain open; no maintainer acceptance
or repaired-package claim follows from synthetic tests.

## Prevention

Keep the full-bake rotation tests alongside converter tests, retain exact
before/after source and model hashes, and verify silhouettes through the
animation rather than accepting only frame count or rest-pose bounds.

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
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

Related bugs in other categories:

- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation

<!-- END GENERATED CATEGORY -->
