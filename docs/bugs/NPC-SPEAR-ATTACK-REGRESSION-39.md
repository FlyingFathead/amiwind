# NPC-SPEAR-ATTACK-REGRESSION-39: Seyda Neen guard spear attack animation is missing in first-person view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Seyda Neen guard combat viewed in first person |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | critical: The maintainer reports a regression in visible guard combat during the stopped RC1 playtest. |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Symptom

In first-person view the maintainer no longer sees the guard spear-attack animation that worked before. The maintainer separately confirms the guard can kill the player; missing attack animation and actual combat damage are different observations.

## Where

Seyda Neen guard combat viewed in first person. Reported in v0.0.39-rc1 on 13 October 2026.
Exact running binary, map pose and appearance details require capture/readback.

## How it happened

Cause is not yet established. Do not substitute an implementation hypothesis for the maintainer observation.

## Why it was not caught

Earlier scoped checks did not establish this exact visual behavior in the maintainer scenario. Successful damage, movement, model parsing or unrelated animations do not prove this animation or shape is correct.

## Reproduction

In Seyda Neen, view a spear-equipped guard from first person, provoke combat and capture successive attacks, pursuit and recovery. Compare the same guard, equipment and view in the previous working build and original-game reference.

## Repair

No repair is claimed. RC2 is required; final release preparation and delivery were stopped. Inspect the inherited alias animation/input or mesh pipeline before designing the correction.

## Verification

Maintainer-reported regression; exact first failing version, package/model/layout binding and previous working capture still require comparison. Existing [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md) tracks broader NPC animation coverage; this report preserves the specific spear regression.

## Prevention

Require an exact-package native reproduction and repaired capture of this scenario, with unaffected first/third-person behavior and normal-speed timing as controls. Keep automated checks, target observation and maintainer acceptance separate.

## Activation and authored stance are separate, 13 October 2026

The exact RC1 diagnostic confirms that same-map reload can prevent the packaged guard mover from activating while combat damage continues. The shared NPC mover reset is a source candidate; it has no repaired native/package acceptance. Separately, ordinary resident attack sampling in npc_anim.py selects the generic hand-to-hand attack group, while prepare_combat.py has weapon-specific stance mapping for selected Arena fighters. This mapping predates RC1 and does not by itself prove the reported regression. Verify the actual guard weapon, authored spear stance and visible timing before calling the spear animation repaired; restoring generic mover activation alone is insufficient.

## Authored spear attack candidate, 14 October 2026

RC2 source selects authored weapontwowide attack/hit for equipped weapon type6 in resident conversion. Forty-three focused tests pass; unchanged runtime damage/mover ABI. The generic-pose mismatch predates RC1; same-map mover registration is a separate repaired regression. Exact affected assets, native package and maintainer acceptance remain pending.

The original steel spear has weapon type 6. Its two-hand-wide chop/hit keys replace generic hand-to-hand sampling for live equipped resident movers; other weapon types keep their prior behavior. Reuse existing alias animation timing and item attachment machinery. Dead static bodies are unaffected.

## Post-pin RC2 package observation, 14 October 2026

Exact-source 690 staged diagnostic footage shows guard pursuit and changing strike poses, with hits reducing health 995 to 899 then 882.3. Post-exit readback verifies 21 movers plus engine, bootcheck and catalogue (24 files). This supports scoped chase/attack and preserved damage, not damage balance or complete spear attachment alignment. Final RC2 disk readback separately verifies the 21 equipped-resident files and palette binding; it does not turn the staged diagnostic into final-package guard native acceptance. Matched OpenMW and maintainer acceptance remain pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STATE-NOT-READ-ON-SPAWN-54 (no report page): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- ACTOR-STATE-POOL-LIMITS-54 (no report page): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- ACTOR-WANDER-AGGRO-52 (no report page): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
- AMBIENT-RESIDENTS-NOT-VISIBLE-54 (no report page): From the matched pose OpenMW shows four residents on the Seyda Neen square, AmiWind one far figure
- AMBIENT-WALK-STUCK-COLLISION-54 (no report page): Eight of 15 resident walks in the Seyda Neen MiniWind ended stuck: the step trace against the CHIM frame collision blocks most routes
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
- CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48 (no report page): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- CREATURE-BONES-OVER-MAX-54 (no report page): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- CREATURE-COMBAT-WEAPON-54 (no report page): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- CREATURE-SCALE-KEYS-54 (no report page): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- HAIR-CHECK-ACTOR-GROUND-1999-54 (no report page): The actor ground check still refused skeletal models past 1,999 vertices
- HALLOWEEN-SCENE-53 (no report page): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- HELD-MODEL-GAPS-54 (no report page): 17 of 65 shields have no held model
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HAIR-BACK-MISSING-53](NPC-HAIR-BACK-MISSING-53.md): Some Suran dancers have no hair at the back of the head
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-HEAD-STARVED-WHOLE-HAIR-54](NPC-HEAD-STARVED-WHOLE-HAIR-54.md): With whole hair some heads got only 28 to 52 triangles: Dark Elf women in robes
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- NPC-VOICE-TABLE-ADDONS-54 (no report page): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- SKEL-ANIM-STAGE-52 (no report page): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- SKEL-TABLE-VIVEC-LAYERED-54 (no report page): Vivec's animation table is layered over the whole humanoid base table: 141 groups, 684 KB
- SKEL-VERTEX-LIMIT-52 (no report page): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices

<!-- END GENERATED CATEGORY -->
