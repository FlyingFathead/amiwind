# NPC-SPEAR-ATTACK-REGRESSION-39: Seyda Neen guard spear attack animation is missing in first-person view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Seyda Neen guard combat viewed in first person |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | critical: The owner reports a regression in visible guard combat during the stopped RC1 playtest. |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Owner named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

## Symptom

In first-person view the owner no longer sees the guard spear-attack animation that worked before. The owner separately confirms the guard can kill the player; missing attack animation and actual combat damage are different observations.

## Where

Seyda Neen guard combat viewed in first person. Reported in v0.0.39-rc1 on 13 October 2026.
Exact running binary, map pose and appearance details require capture/readback.

## How it happened

Cause is not yet established. Do not substitute an implementation hypothesis for the owner observation.

## Why it was not caught

Earlier scoped checks did not establish this exact visual behavior in the owner scenario. Successful damage, movement, model parsing or unrelated animations do not prove this animation or shape is correct.

## Reproduction

In Seyda Neen, view a spear-equipped guard from first person, provoke combat and capture successive attacks, pursuit and recovery. Compare the same guard, equipment and view in the previous working build and original-game reference.

## Repair

No repair is claimed. RC2 is required; final release preparation and delivery were stopped. Inspect the inherited alias animation/input or mesh pipeline before designing the correction.

## Verification

Owner-reported regression; exact first failing version, package/model/layout binding and previous working capture still require comparison. Existing [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md) tracks broader NPC animation coverage; this report preserves the specific spear regression.

## Prevention

Require an exact-package native reproduction and repaired capture of this scenario, with unaffected first/third-person behavior and normal-speed timing as controls. Keep automated checks, target observation and owner acceptance separate.

## Activation and authored stance are separate, 13 October 2026

The exact RC1 diagnostic confirms that same-map reload can prevent the packaged guard mover from activating while combat damage continues. The shared NPC mover reset is a source candidate; it has no repaired native/package acceptance. Separately, ordinary resident attack sampling in npc_anim.py selects the generic hand-to-hand attack group, while prepare_combat.py has weapon-specific stance mapping for selected Arena fighters. This mapping predates RC1 and does not by itself prove the reported regression. Verify the actual guard weapon, authored spear stance and visible timing before calling the spear animation repaired; restoring generic mover activation alone is insufficient.

## Authored spear attack candidate, 14 October 2026

RC2 source selects authored weapontwowide attack/hit for equipped weapon type6 in resident conversion. Forty-three focused tests pass; unchanged runtime damage/mover ABI. The generic-pose mismatch predates RC1; same-map mover registration is a separate repaired regression. Exact affected assets, native package and owner acceptance remain pending.

The original steel spear has weapon type 6. Its two-hand-wide chop/hit keys replace generic hand-to-hand sampling for live equipped resident movers; other weapon types keep their prior behavior. Reuse existing alias animation timing and item attachment machinery. Dead static bodies are unaffected.

## Post-pin RC2 package observation, 14 October 2026

Exact-source 690 staged diagnostic footage shows guard pursuit and changing strike poses, with hits reducing health 995 to 899 then 882.3. Post-exit readback verifies 21 movers plus engine, bootcheck and catalogue (24 files). This supports scoped chase/attack and preserved damage, not damage balance or complete spear attachment alignment. Final RC2 disk readback separately verifies the 21 equipped-resident files and palette binding; it does not turn the staged diagnostic into final-package guard native acceptance. Matched OpenMW and owner acceptance remain pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Owner acceptance and final v0.0.39 clearance remain pending.

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
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
