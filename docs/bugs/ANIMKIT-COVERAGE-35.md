# ANIMKIT-COVERAGE-35: NPCs that move or fight have no walk, run or attack animation

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 5 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Repeated maintainer report: Seyda Neen guards and other NPCs chase without running animation.
- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Exact RC1 reload loses registered movers while damage continues. Source reset and real mover regression pass focused checks; repaired target/native/image pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Scoped native reload now activates full guard mover and changing chase/attack poses with health damage. Authored spear, other NPCs, complete RC2 package and maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Original group availability confirmed; full NPC mapping includes swim/idle while player move profile excludes them. This source finding does not implement or accept player water/torch.
- Reported with v0.0.57-dev2 at 2026-10-30 15:34 +0200: Settlement sweeps of v0.0.57-dev1/dev2 (full images 2a4027c, d725e23): 6 actor models (a_1dcc5b3c7087, a_58e45a4e1b26, a_709cdbfab122, a_7344d695fce0, a_793d9337b532, a_92f05fa2ec5b) logged Animation layout invalid, idle only, 52 times: their models were known by name only at spawn (0 frames), so every group failed the frame check and they kept only their idle. Fix: the layout is checked against the frames when the model loads (aw_anim.c AW_AnimPrep, branch v0.0.57-animfull).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | animation kit profile assignment (react standing vs full movers), Seyda Neen residents |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.57 |
| Severity | high: Any resident who turns hostile or follows looks broken; the kit is meant to cover every NPC |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3cbe85a, engine 3cbe85a, CHIM world 3cbe85a |
| CHIM engine version | CHIM 0.1.0, engine 3cbe85a, world format 0.5 |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-10: reported in v0.0.35
- 2026-10-12: BUILD-LAVA-CORE-BOUNDS-38: ANIMKIT-COVERAGE-35 (2026-10-12): Roadmap explicitly retains full player/NPC animation coverage, including swimming/diving and companion needs.
- 2026-10-13: seen again in v0.0.39-rc1: Repeated maintainer report: Seyda Neen guards and other NPCs chase without running animation.
- 2026-10-13: seen again in v0.0.39-rc1: Exact RC1 reload loses registered movers while damage continues.
- 2026-10-13: seen again in v0.0.39-rc2: Scoped native reload now activates full guard mover and changing chase/attack poses with health damage.
- 2026-10-13: seen again in v0.0.39-rc2: Original group availability confirmed; full NPC mapping includes swim/idle while player move profile excludes them.
- 2026-10-13: DOCS-CHANGELOG-STALE-39 and DOCS-RC1-PREFLIGHT-39: ANIMKIT-COVERAGE-35 (2026-10-13, RC2 follow-up): RC1 recurrence reproduced after same-map reload: actual packaged Seyda run/attack mover assets exist, but mover registration is lost when ...
- 2026-10-14: Renewed RC2 gameplay reports: ANIMKIT-COVERAGE-35: 13 October 2026, RC1 report / RC2 follow-up: Still present in v0.0.39-rc1 (maintainer, 13 October 2026): Seyda Neen guards and other NPCs chase without running animation.
- 2026-10-30 15:34 +0200: seen again in v0.0.57-dev2: Settlement sweeps of v0.0.57-dev1/dev2 (full images 2a4027c, d725e23): 6 actor models (a_1dcc5b3c7087, a_58e45a4e1b26, a_709cdbfab122, a_7344d695fce0, a_793d9337b532, a_92f05fa2ec5b) logged Animation layout invalid, idle only, 52 times ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 5 times; something has to be done](#persisting-reported-5-times-something-has-to-be-done)
- [Timeline](#timeline)
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

- ACTOR-AMBIENT-STALE-EDICT-57 (no report page): Teleporting from Seyda Neen to the Ascadian Isles crashes the game: NUM_FOR_EDICT: bad pointer (ambient slots of the old map)
- ACTOR-AMBIENT-WALK-COST-59 (no report page): Walking residents can cost 170 to 300 ms each per think in Seyda Neen
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-GROUNDING-CENSUS-CONFLICTS-67](ACTOR-GROUNDING-CENSUS-CONFLICTS-67.md): The exterior grounding census measures seven people listed as standing on the ground as off the ground, and cannot read five effect models as support
- [ACTOR-LEVELLED-INVENTORY-ONE-PICK-66](ACTOR-LEVELLED-INVENTORY-ONE-PICK-66.md): An actor's levelled inventory is chosen once when the game is built, not when the actor is made
- [ACTOR-LEVELLED-NO-WANDER-56](ACTOR-LEVELLED-NO-WANDER-56.md): Levelled creatures (most wild creatures) never wander or aggro: the Wander table held placed actors only
- [ACTOR-PACK-GUAR-MESH-BROKEN-64](ACTOR-PACK-GUAR-MESH-BROKEN-64.md): The pack guar at Ahemmusa Camp is drawn with its body parts scattered apart
- [ACTOR-PACKAGES-NOT-HELD-66](ACTOR-PACKAGES-NOT-HELD-66.md): Travel, follow and escort packages of the people and creature records are not carried by the build
- [ACTOR-QUEUE-OTHER-MAP-67](ACTOR-QUEUE-OTHER-MAP-67.md): Actors still queued when the map changes spawn in the next map at the old map's coordinates
- [ACTOR-RANGED-COMBAT-MISSING-66](ACTOR-RANGED-COMBAT-MISSING-66.md): People and creatures that carry a bow, crossbow or thrown weapon fight hand to hand or with a melee weapon
- [ACTOR-RESPAWN-CORPSE-RULES-66](ACTOR-RESPAWN-CORPSE-RULES-66.md): Dead bodies are never cleared away; the death rules over time need the original numbers
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- [ACTOR-STATE-NOT-READ-ON-SPAWN-54](ACTOR-STATE-NOT-READ-ON-SPAWN-54.md): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- [ACTOR-STATE-POOL-LIMITS-54](ACTOR-STATE-POOL-LIMITS-54.md): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- [ACTOR-STORM-POSE-51](ACTOR-STORM-POSE-51.md): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- [ACTOR-TABLE-SAME-MAP-RELOAD-67](ACTOR-TABLE-SAME-MAP-RELOAD-67.md): A reload of the map in play joins none of its actor table cells: no creatures until the next map change
- [ACTOR-WANDER-AGGRO-52](ACTOR-WANDER-AGGRO-52.md): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
- [AMBIENT-RESIDENTS-NOT-VISIBLE-54](AMBIENT-RESIDENTS-NOT-VISIBLE-54.md): From the matched pose OpenMW shows four residents on the Seyda Neen square, AmiWind one far figure
- [AMBIENT-UNSTUCK-FLOOD-61](AMBIENT-UNSTUCK-FLOOD-61.md): Walking residents in Seyda Neen keep falling back to the stuck-movement retry
- [AMBIENT-WALK-STUCK-COLLISION-54](AMBIENT-WALK-STUCK-COLLISION-54.md): Eight of 15 resident walks in the Seyda Neen MiniWind ended stuck: the step trace against the CHIM frame collision blocks most routes
- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- [AW-20260928-05](AW-20260928-05.md): Dock guard misses approach interception
- [AW-20260929-01](AW-20260929-01.md): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [BALMORA-PEOPLE-FLOATING-65](BALMORA-PEOPLE-FLOATING-65.md): In Balmora several people stand in the air above the street, as in early versions
- BARTER-SOLD-ITEM-LOST-58 (no report page): A thing the player sells to a merchant who does not stock it leaves the game instead of going into the merchants stock
- [BUILD-ACTOR-SPEC-EMPTY-ROOMS-66](BUILD-ACTOR-SPEC-EMPTY-ROOMS-66.md): The image stage stopped on the actor spec check: the check did not read the room batch stage's new list of empty cells, so the one NPC of an empty Tribunal cell counted as missing
- [BUILD-ACTOR-SPEC-UNSPAWNABLE-67](BUILD-ACTOR-SPEC-UNSPAWNABLE-67.md): The actor spec check counted every actor table row outdoors as placed, also rows the game cannot spawn
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- [CENSUS-GUARD-NO-PATH-TO-THIEF-65](CENSUS-GUARD-NO-PATH-TO-THIEF-65.md): A theft in the census office brings the guard only when he can walk to the player: across the table he cannot
- [CENSUS-NPC-NO-ATTACK-ANIM-65](CENSUS-NPC-NO-ATTACK-ANIM-65.md): The opening's people fight back with no attack animation
- CHARGEN-BIRTHSIGN-REVIEW-58 (no report page): Character creation on the v0.0.58-dev5 image: the birthsign step jumps to the confirm box, the review sheet shows an empty name, and Questions is not greyed out without Morrowind.ini
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48](CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48.md): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- [COMBAT-ACTOR-VS-ACTOR-62](COMBAT-ACTOR-VS-ACTOR-62.md): A dialogue answer that sets two characters against each other does nothing: only fights with the player are carried out
- COMBAT-DEAD-ACTOR-RELOAD-59 (no report page): A killed actor briefly starts combat when its scene loads again
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- [COMBAT-PACK-SLOTS-57](COMBAT-PACK-SLOTS-57.md): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- [COMBAT-PLAYGROUND-CREATURE-HUMANOID-61](COMBAT-PLAYGROUND-CREATURE-HUMANOID-61.md): The combat playground group mode draws a cliff racer as a humanoid figure walking on the ground
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMBAT-SUMMON-ALLY-62](COMBAT-SUMMON-ALLY-62.md): A summoned creature does not fight for the player: the fight has no side where one actor attacks another
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CORPSE-CLOTHES-NOT-UPDATED-62](CORPSE-CLOTHES-NOT-UPDATED-62.md): Clothing, armour and held items taken from a body or a living actor stay drawn on it
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- [CREATURE-BONES-OVER-MAX-54](CREATURE-BONES-OVER-MAX-54.md): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- [CREATURE-COMBAT-FRAMES-MISSING-61](CREATURE-COMBAT-FRAMES-MISSING-61.md): In a fight the ancestor ghost asks its model for frames it does not have: "No such frame" fills the console
- [CREATURE-COMBAT-WEAPON-54](CREATURE-COMBAT-WEAPON-54.md): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points
- [CREATURE-FLOATING-SHALK-64](CREATURE-FLOATING-SHALK-64.md): Shalks on Azura's Coast hang high in the air
- [CREATURE-NETCH-BULL-LEG-REDUCED-58](CREATURE-NETCH-BULL-LEG-REDUCED-58.md): The netch bull's reduced model loses a long stretch of one leg (up to 20 units from the source surface)
- [CREATURE-NIXHOUND-HUMAN-MOVES-67](CREATURE-NIXHOUND-HUMAN-MOVES-67.md): A nix-hound moves like a person and attacks with a weapon swing, and its model looks wrong
- CREATURE-RACER-DRAWN-TINY-57 (no report page): The cliff racer is drawn many times too small: a dark speck the size of a bird while its hit box is a full cliff racer
- [CREATURE-RACER-MESH-SPIKE-58](CREATURE-RACER-MESH-SPIKE-58.md): The cliff racer's model is drawn broken: the wings do not join the body, the parts sit apart, and a long spike runs far below
- [CREATURE-SCALE-KEYS-54](CREATURE-SCALE-KEYS-54.md): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- [CREATURE-SCALE-NOT-HELD-66](CREATURE-SCALE-NOT-HELD-66.md): A creature record's own size (scale) is not carried by the build
- [CREATURE-SUMMONED-62](CREATURE-SUMMONED-62.md): The 16 creatures that summoning spells call up are not built: a summoning has no creature to show
- [CREATURE-TABLE-ROOT-TRAVEL-67](CREATURE-TABLE-ROOT-TRAVEL-67.md): A creature whose root bone is not named Bip01 keeps its walk and run travel in its own animation table: its drawn poses are coarse and it is drawn away from its place
- [DAGOTH-IDLE-BASE-CHECK-66](DAGOTH-IDLE-BASE-CHECK-66.md): The image stage stopped on Dagoth Ur: its actor-frames check took his idle at frames 30 to 37 for a fault, though his map entity loops exactly that span
- [DAGOTH-UR-NO-ANIMATIONS-65](DAGOTH-UR-NO-ANIMATIONS-65.md): Dagoth Ur in Akulakhan's Chamber has no running and no attack animations
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- [DIALOGUE-FIGHT-DISPOSITION-57](DIALOGUE-FIGHT-DISPOSITION-57.md): Requested: disposition drives combat as in the original: a low-disposition NPC turns hostile (effective Fight from disposition), Taunt can start a fight
- [DIALOGUE-TEXT-LINKS-57](DIALOGUE-TEXT-LINKS-57.md): Requested: topic names inside an answer are plain text; the original draws them as blue links that ask about the topic
- [DIALOGUE-WINDOW-LAYOUT-57](DIALOGUE-WINDOW-LAYOUT-57.md): Requested: the dialogue window has no disposition bar, no Persuasion and no service entries, as the original has
- [ESSENTIAL-DEATH-MESSAGE-66](ESSENTIAL-DEATH-MESSAGE-66.md): The essential character death message is shown only for deaths in a fight
- [FARGOTH-STANDING-NO-LAYOUT-66](FARGOTH-STANDING-NO-LAYOUT-66.md): Fargoth's and the opening Imperial guard's standing models carry no animation layout
- [FP-TORCH-OUT-OF-HAND-67](FP-TORCH-OUT-OF-HAND-67.md): In first person a held torch floats away from the left hand: a regression, the torch was held in the hand before
- [GAENOR-ATTACKS-AT-START-67](GAENOR-ATTACKS-AT-START-67.md): Two Gaenors, one of them at level 50, attack a new player in the Temple Courtyard
- [GUARD-WALK-REGRESSION-62](GUARD-WALK-REGRESSION-62.md): The guard at the start turns on the spot on his way to his post beside the door and then stands in the player's route into the Census and Excise Office
- [GUARDS-FIGHT-EACH-OTHER-65](GUARDS-FIGHT-EACH-OTHER-65.md): Two guards who come after the player in Seyda Neen start fighting each other
- [HAIR-CHECK-ACTOR-GROUND-1999-54](HAIR-CHECK-ACTOR-GROUND-1999-54.md): The actor ground check still refused skeletal models past 1,999 vertices
- [HALLOWEEN-SCENE-53](HALLOWEEN-SCENE-53.md): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- [HEART-EFFECT-SHELLS-OPAQUE-64](HEART-EFFECT-SHELLS-OPAQUE-64.md): The Heart of Lorkhan is baked with its fire shield and its hidden death glows as opaque skin, so the heart itself is covered and its own texture is not seen
- [HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65](HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65.md): In Akulakhan's Chamber the Heart of Lorkhan leaves its place and follows Dagoth Ur to attack the player
- [HELD-MODEL-GAPS-54](HELD-MODEL-GAPS-54.md): 17 of 65 shields have no held model
- [HELD-WEAPON-WRONG-MODEL-62](HELD-WEAPON-WRONG-MODEL-62.md): An actor's held weapon is drawn with another actor's model after the opening is skipped
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [INTRO-DOCK-GUARD-BLOCKS-DOOR-62](INTRO-DOCK-GUARD-BLOCKS-DOOR-62.md): Opening: the dock guard turns on the spot on his way to the Census and Excise Office and stops in the doorway
- INVENTORY-PREVIEW-BAKED-BODY-59 (no report page): Inventory preview draws the race's baked body with its own outfit, not what the player wears
- [MERCHANT-ITEM-CAP-58](MERCHANT-ITEM-CAP-58.md): An actor keeps only 12 item changes, so a merchant refuses the thirteenth kind of item sold to it
- [MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58](MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58.md): With the CHIM cache turned off for one start, the game reports its script instance table full and then freezes with a message box up
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-ATTACK-ANIMS-MISSING-65](NPC-ATTACK-ANIMS-MISSING-65.md): Most creatures play only six baked animation groups: no knockdown, spell cast, second or third attack
- [NPC-BAKE-FALLBACK-62](NPC-BAKE-FALLBACK-62.md): Characters the new seam and floor bake cannot fit in the alias budget are baked a second time with the v0.0.62-dev1 body rules
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-CAST-MAGICKA-NOT-PAID-66](NPC-CAST-MAGICKA-NOT-PAID-66.md): A fighter's spell costs it no magicka: the cast's payment names the wrong stat
- [NPC-CONVERSATION-FACING-23](NPC-CONVERSATION-FACING-23.md): NPCs do not turn to face the player in conversation
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HAIR-BACK-MISSING-53](NPC-HAIR-BACK-MISSING-53.md): Some Suran dancers have no hair at the back of the head
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-HEAD-STARVED-WHOLE-HAIR-54](NPC-HEAD-STARVED-WHOLE-HAIR-54.md): With whole hair some heads got only 28 to 52 triangles: Dark Elf women in robes
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-IDLE-TRACK-PLAYER-67](NPC-IDLE-TRACK-PLAYER-67.md): Requested: an idle character turns its head and body slowly towards the player and follows the player's movements (the dock guard in the opening, the clerk of the Census and Excise Office)
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-NO-SPELLCASTING-65](NPC-NO-SPELLCASTING-65.md): Hostile characters never cast spells in a fight
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-RECIPE-FILES-ROOM-HELD-60](NPC-RECIPE-FILES-ROOM-HELD-60.md): With the earlier recipe files, a room's table stays held outdoors and the town's own cells are not read
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-VOICE-TABLE-ADDONS-54](NPC-VOICE-TABLE-ADDONS-54.md): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [NPC-WEREWOLF-NO-MODEL-66](NPC-WEREWOLF-NO-MODEL-66.md): The werewolf NPCs of Bloodmoon get no model: their hair part has no attached geometry
- [OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67](OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67.md): The dead bodies the original places outdoors show only when the player arrives in their cell, never when their cell joins around the player
- [OUTDOOR-CREATURES-HOME-CELL-67](OUTDOOR-CREATURES-HOME-CELL-67.md): The cell the player arrives in has none of its levelled creatures: the window's home frame never joins the actor table
- [OUTDOOR-CREATURES-REGRESSION-66](OUTDOOR-CREATURES-REGRESSION-66.md): Regression: no outdoor creatures spawn, no mudcrabs or slaughterfish, though earlier versions had them
- [OUTDOOR-DEAD-BODY-GONE-66](OUTDOOR-DEAD-BODY-GONE-66.md): An outdoor body is gone at once on a later visit: it cannot be looted after leaving
- PICKUP-E-OWNED-NO-TAKE-58 (no report page): On the v0.0.58-dev5 image the activate key on an aimed owned item (the Census Office Quill Pen, red name, red E: Steal) takes nothing; it is not in the inventory after a save and reload
- [PIER-GUARD-WALKS-INTO-DOOR-65](PIER-GUARD-WALKS-INTO-DOOR-65.md): After the race choice the dock guard walks against the office door for about half a minute before stepping aside
- PLAYER-BODY-THIRD-PERSON-GEAR-59 (no report page): Third-person view: the assembled player body shows no worn clothes or armour, and the shield is not drawn
- [PLAYER-ROBE-RUN-ANIM-67](PLAYER-ROBE-RUN-ANIM-67.md): With a robe on, the player's run animation does not play in third person
- [PLAYER-ROBE-WAIST-SEAM-67](PLAYER-ROBE-WAIST-SEAM-67.md): With a robe on, the third-person player body shows a cut at the waist: the robe's skirt and the upper body do not join
- [PLAYER-SPELL-CAP-58](PLAYER-SPELL-CAP-58.md): The player can hold only 8 spell changes, so a ninth bought spell is refused
- [PLAYER-VANITY-WALK-STUCK-67](PLAYER-VANITY-WALK-STUCK-67.md): After the idle vanity camera starts, the player's walk and run animations stop in third person until the next map load
- [PLAZA-FABRICANTS-LIVE-AT-START-67](PLAZA-FABRICANTS-LIVE-AT-START-67.md): Plaza Brindisi Dorom holds the fabricants of a later quest from the start of a new game, one ready to attack on sight
- [RANDOM-SPAWN-IDLE-63](RANDOM-SPAWN-IDLE-63.md): Creatures from the Ghostgate random spawn stand idle next to the player instead of attacking
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-LEVELLED-INTRO-ROOMS-62](ROOM-LEVELLED-INTRO-ROOMS-62.md): Addamasartus and Tharys Ancestral Tomb have no levelled creatures: the intro scene converts their rooms without the levelled creature points
- [ROOM-NPC-DEFERRED-VIVEC-66](ROOM-NPC-DEFERRED-VIVEC-66.md): Two interior NPCs of Vivec are not placed: one in the Telvanni Mage room, one in The Lizard's Head
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- [SCRIB-NO-ATTACK-65](SCRIB-NO-ATTACK-65.md): A scrib walks its path but never attacks the player on its own
- [SKEL-ANIM-STAGE-52](SKEL-ANIM-STAGE-52.md): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- [SKEL-TABLE-VIVEC-LAYERED-54](SKEL-TABLE-VIVEC-LAYERED-54.md): Vivec's animation table is layered over the whole humanoid base table: 141 groups, 684 KB
- [SKEL-VERTEX-LIMIT-52](SKEL-VERTEX-LIMIT-52.md): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices
- [SUMMON-SPAWN-FRAME-62](SUMMON-SPAWN-FRAME-62.md): The frame a summoned creature appears in takes about 570 ms: its model files and the actor table are read in that frame
- [SWEEP-SEYDA-EIGHT-FAIL-59](SWEEP-SEYDA-EIGHT-FAIL-59.md): dbg sweep reports 8 failing entities in Seyda Neen on a v0.0.59-dev3 MiniWind with the placed world items; the Census Office map reported 3 in v0.0.58 sessions
- [SWIM-BAKED-CLOTHES-60](SWIM-BAKED-CLOTHES-60.md): Swimming in third-person view shows default clothes instead of the player's own
- [TOMB-NO-CREATURES-60](TOMB-NO-CREATURES-60.md): Samarys Ancestral Tomb has no ghosts, skeletons or other creatures
- [WANDER-DOOR-RULE-66](WANDER-DOOR-RULE-66.md): A wandering resident can stop at a destination right by a door and stand there; the original sends an idle wanderer near a door walking

<!-- END GENERATED CATEGORY -->
