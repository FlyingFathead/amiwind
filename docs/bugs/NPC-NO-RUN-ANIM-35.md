# NPC-NO-RUN-ANIM-35: Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Repeated maintainer report: Seyda Neen guards and other NPCs chase without running animation.
- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Exact RC1 reload loses registered movers while damage continues. Source reset and real mover regression pass focused checks; repaired target/native/image pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Scoped native reload now activates full guard mover and changing chase/attack poses with health damage. Authored spear, other NPCs, complete RC2 package and maintainer acceptance pending.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | Builder default --npc-anim idle; engine walk/run selection (aw_anim.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34, v0.0.39-rc1 (last seen) |
| Severity | high: Player-visible in every town: followers and fighters slide or walk while they should run |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.34 release |
| From commit | source 70b04e2, engine 70b04e2, CHIM world 70b04e2 |
| CHIM engine version | CHIM 0.1.0, engine 70b04e2, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 13 October 2026](#status-13-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Repeated maintainer report, 13 October 2026](#repeated-maintainer-report-13-october-2026)
- [RC1 reload reproduction and source candidate, 13 October 2026](#rc1-reload-reproduction-and-source-candidate-13-october-2026)
- [Scoped native reload improvement, 13 October 2026](#scoped-native-reload-improvement-13-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 13 October 2026

Still reported in RC1. Earlier source-only repair claims did not establish the current packaged chase behavior.

## Symptom

Playing v0.0.34: a companion and hostile NPCs only ever walk, never run, and their walk looks wrong (feet
sliding). Wider than COMPANION-NO-RUN-ANIM-33, which named the companion only.

## Where

The builder's default animation profile (`--npc-anim idle` in `tools/build.py`) and the engine's walk/run
selection (`engine/aga/src/aw_anim.c`, `AW_AnimMoveGroup`).

## How it happened

The engine already picks walk or run by an actor's speed, but only for models that carry those groups. The
animation kit that bakes them stayed opt-in, so release residents carried 8 idle frames; fighters fell back
from run to walk, and moving actors slid.

## Why it was not caught

No playtest build used the kit; the default build had no moving-actor check.

## Reproduction

Any v0.0.34 build: `dbg companion test`, run; or start a fight in a town.

## Repair

The kit is the default (`--anim-kit on`, the `react+full` profile: a standing model plus a full model worn
while moving). `--anim-kit off` keeps the previous idle frames. `dbg animkit` switches and inspects it in
game. The walk and run rules and their sources: [ANIMKIT.md](../ANIMKIT.md).

## Verification

tests/test_animkit.py (default on, off = idle, the console parser and group table, the preset); an
in-game check with `--miniwind-animkit` is pending.

## Prevention

The default build carries the kit; the MiniWind preset makes the check a few-minute build.

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

## Post-pin RC2 package observation, 14 October 2026

Exact-source 690 staged diagnostic footage shows guard pursuit and multiple strike poses, with health 995 to 899 then 882.3. Guest exit reaches AmigaDOS and 24 played-file hashes pass. This extends scoped mover evidence after the same-map reset; all-NPC, matched original, final-package guard and maintainer acceptance remain separate.

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
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach

<!-- END GENERATED CATEGORY -->
