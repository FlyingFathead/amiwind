# NPC-BAKE-VERTEX-32: NPC resident baking can exceed the alias vertex budget

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | NPC model baker and exterior residents, including Seyda Neen |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev, v0.0.40-dev2 (last seen) |
| Severity | critical: Original-data exterior resident conversion stops, blocking the complete dev2 playable. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Overflow repair candidate - 15 October 2026

Expanded original-cell coverage admitted Tarhiel at his original transform.
His extravagant robe has disconnected panels: whole-shape reduction discarded
complete panels, causing the existing shell guard to retain excessive geometry.

After a real budget-mode overflow only, the candidate reuses the existing
connected-component and simplification machinery. Every original component
must retain the same 80% area and 70% extent guards, with the combined guard
also enforced. Successful original bakes keep their path. Existing AmiQuake
alias limits and the resident 512 KiB cap remain unchanged.

The optional full-sample size check makes the existing geometry-budget ladder
try smaller geometry before texture work. It preserves all 64 sample indices,
group counts and stored timing in the original-data Tarhiel proof:
432 triangles, 1,296 vertices, 487,192 bytes. Forty-nine isolated checks pass,
including unchanged-success and rejected-collapsed-component controls.
Fifty-two integrated NPC/writer checks also pass with unchanged source.
The failed original carrier is preserved. The subsequent complete source-only
carrier and independent resident/model/animation/voice readback pass.
Native appearance/contact and package verification remain pending.

## Original carrier failure: 15 October 2026

The v0.0.40-dev2 original-data Seyda carrier build stops at the original NPC
identifier agronian guy with Alias vertex budget exceeded. The original record
belongs to Tarhiel, a male Wood Elf; the identifier does not name his race.
The failure occurs in prepare_area.build_resident after its existing
480-to-192 reduction ladder. Source and all original inputs stayed unchanged.
Earlier Telvanni and Godros findings remain historical evidence.

Severity is raised to critical because the complete playable cannot be built.
No resident omission, animation-frame removal or engine-limit increase is
accepted as a repair. Separate CHIM geometry conversion can continue.
Carrier completion, original-reference readback and native checks are pending.

## Source carrier completion: 15 October 2026

The repaired source carrier now completes and preserves all original actors.
Tarhiel's moving model is byte-identical to the 64-sample proof above; its
standing model carries the expected 17 poses. All 13 resident model sets pass
independent serialized model/animation/tag/voice checks under unchanged limits.
This does not close broader appearance, contact or package acceptance.

## Status: 9 October 2026

The NPC level-of-detail survey (`tools/npc_lod.py survey`, 149 of the 2,675 NPC records, the
equipped appearance with the residents' eight idle frames) hits the same failure for Godros: every
budget of the resident ladder, 480 down to 192, still overflows 666 faces. So about one record in
150 cannot be baked as a resident. The gallery bakes such models with its 1024-face fallback; the
resident path has no fallback yet.

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Baking the models of two Telvanni canton residents fails at every reduction step down to 192
vertices, which stopped the whole Telvanni conversion until they were excluded.

## Where

The NPC model baker (`tools/npc_geometry.py`).

## How it happened

Unknown: likely heavy equipment meshes.

## Why it was not caught

First conversion of these residents.

## Reproduction

Import the Telvanni canton without the exclusions.

## Repair

The earlier proposal to skip a failing resident is superseded for the complete
candidate. Find the specific fitting failure and repair canonical model
selection while preserving original identity, appearance and animation groups.
Do not omit the resident or raise the runtime budget to clear the build.

## Verification

Pending.

## Prevention

Importer reports per-resident failures.

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

- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
