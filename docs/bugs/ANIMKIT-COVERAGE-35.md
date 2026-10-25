# ANIMKIT-COVERAGE-35: NPCs that move or fight have no walk, run or attack animation

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Repeated maintainer report: Seyda Neen guards and other NPCs chase without running animation.
- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Exact RC1 reload loses registered movers while damage continues. Source reset and real mover regression pass focused checks; repaired target/native/image pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Scoped native reload now activates full guard mover and changing chase/attack poses with health damage. Authored spear, other NPCs, complete RC2 package and maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Original group availability confirmed; full NPC mapping includes swim/idle while player move profile excludes them. This source finding does not implement or accept player water/torch.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | animation kit profile assignment (react standing vs full movers), Seyda Neen residents |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35, v0.0.39-rc1 (last seen) |
| Severity | high: Any resident who turns hostile or follows looks broken; the kit is meant to cover every NPC |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3cbe85a, engine 3cbe85a, CHIM world 3cbe85a |
| CHIM engine version | CHIM 0.1.0, engine 3cbe85a, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Swimming follow-up, 12 October 2026](#swimming-follow-up-12-october-2026)
- [Repeated maintainer report, 13 October 2026](#repeated-maintainer-report-13-october-2026)
- [RC1 reload reproduction and source candidate, 13 October 2026](#rc1-reload-reproduction-and-source-candidate-13-october-2026)
- [Scoped native reload improvement, 13 October 2026](#scoped-native-reload-improvement-13-october-2026)
- [Original water and equipment group audit, 13 October 2026](#original-water-and-equipment-group-audit-13-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Open (maintainer playtest of v0.0.35).

## Symptom

Fargoth in Seyda Neen has no walk animation at all. When he fights the player he does not punch: he hops straight at
the player with no walk or attack animation.

Other Seyda Neen villagers do the same: when they come at the player they glitch forward with no proper walk or
run animation. So it is not one NPC but (at least) the town's residents.

## Where

The animation kit's profile assignment: residents get the standing set (react) and only movers get the full set
(walk, run, attack); a resident who turns hostile or follows the player moves without the frames for it. To be
confirmed in the build's kit receipt for Seyda Neen.

## How it happened

The kit (on by default since v0.0.35) decides per NPC which animation groups to bake. An NPC classified as standing
gets no locomotion or attack groups, but scripts and combat can still make it move and fight.

## Why it was not caught

No check compares the groups an NPC can need (it can move, fight, swim) with the groups baked for it; playtests
covered the Balmora movers and the Arena fighters.

## Reproduction

Always: provoke Fargoth in Seyda Neen and watch him approach and fight.

## Repair

Planned: every NPC that can move or fight (every NPC outside a fixed scripted pose) gets walk, run, swim and attack
groups, island-wide; plus a builder audit that fails when an NPC lacks a group it can need, so no NPC is left out.

## Verification

To do: Fargoth walks, runs and punches in a MiniWind Seyda Neen sandbox; the audit reports every NPC covered.

## Prevention

The coverage audit runs in every build that bakes NPCs.


## Swimming follow-up, 12 October 2026

The maintainer reports that the player uses walking poses at the surface and when
submerged in v0.0.38-dev2. Audit original swim/dive animation groups and their
state selection for the player and relevant NPCs, including companion movement.
See WATER-GAMEPLAY-PARITY-38 for movement and breath/damage verification; visual
pose alone does not establish missing swimming physics. No repair accepted.

## Repeated maintainer report, 13 October 2026

In v0.0.39-rc1, Seyda Neen guards and other NPCs chase the player without a
running animation. The maintainer identifies this as a repeated flaw. This remains
open and blocks RC2 acceptance; no new duplicate chase ID is created. Verify
the exact packaged resident/mover models and layouts, runtime chase group,
phase advancement and normal-speed in-game motion. A movement or damage check
alone does not establish visible animation. The guard spear regression is
recorded separately as [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md).

## RC1 reload reproduction and source candidate, 13 October 2026

Exact RC1 model/layout readback confirms all eight distinct ordinary Seyda resident movers include run and attack groups. In the diagnostic same-map reload, animation state survived because the world-model pointer was reused, while SV_SpawnServer cleared precache names. AW_AnimPrep then returned for the old model slot and failed to register the mover; combat printed `mover not registered` and the guard still delivered health damage using its standing model. Intro boat/dock guards are separate legacy assets.

The source candidate calls AW_AnimSceneReset immediately after server state clearing and before actor spawning, clearing parsed layouts, worn mappings and lazy mover names. It reuses Quake server-spawn lifecycle and lazy model loading without eager bakes or per-frame allocation. A real engine-glue mover fixture reproduces the old same-pointer/fresh-precache failure, then checks lazy registration, run/attack frame advancement, cache release and repeated reloads with the reset. Seven animation,21 combat and42 NPC focused checks pass, including UBSAN native fixtures. This is source/focused validation only: new Amiga compilation, native repaired chase/attack, exact RC2 model readback and maintainer acceptance remain pending. Guard spear stance is a separate open check.

## Scoped native reload improvement, 13 October 2026

Source4b968c2 passes the Amiga compile gate. After the same-map reload that failed in RC1, the guard now uses progs/a_40c7bfe774f5_m.mdl (entity10, reference128967), with the full run4/attack5 layout and changing attack frames36 and35. The earlier mover-not-registered/fallback warning is absent. Original footage shows the guard changing leg/body pose while closing the gap and attacking, and the console records continuing health damage. First/third-person camera switches and the actual AmigaDOS exit were observed; post-exit engine/bootcheck/catalogue hashes match.

This is the new runtime engine with unchanged exact RC1 NPC assets, not a complete RC2 image or package. It supports the specific reload/mover repair; it does not establish original authored spear stance, all NPCs, normal-speed performance or maintainer acceptance. The previous RC1 failure and receipts remain historical evidence.

## Original water and equipment group audit, 13 October 2026

Original human/beast swim and torch groups are confirmed. npc_anim already maps swimwalkforward and idleswim, with base fallback for missing female overrides; a full NPC mover can declare these while the player move profile omits them. Therefore original clip presence, sampled NPC layout, player-body bake, runtime state and native gameplay must remain separate coverage facts. The source availability audit does not repair or accept first/third-person water mechanics, player torch equipment or authored spear animation; existing issue IDs retain their open status.

## Post-pin RC2 package observation, 14 October 2026

Exact RC2 package readback covers all 20 player appearances and their torch/held/swim companions. Scoped Nord package native footage verifies punch changes, carried torch, swim poses and underwater first-person fists. Original group availability and binary declarations still do not establish every actor/equipment animation or all-appearance acceptance.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
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
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach

<!-- END GENERATED CATEGORY -->
