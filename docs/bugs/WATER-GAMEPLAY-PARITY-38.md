# WATER-GAMEPLAY-PARITY-38: Water gameplay completeness and original behavior audit

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 6 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): RC1: absent swimming/diving, maintainer reports sinking; underwater upright pose inspected. Missing swim groups source-confirmed; physics/reference comparison pending.
- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Maintainer repeats missing swimming AND diving animation in BOTH first-person and third-person views. Keep four view/action acceptance items distinct; no repaired water candidate.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Original third-person swim families confirmed; no dedicated dive key in16 base NIF/KF members. First-person visuals need state/camera/fallback parity; local0.52 source is not native0.48 acceptance.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Maintainer requires reported swimming/diving in RC2. Both-view original 0.48 reference and source integration in progress; clip inventory is separate. Native/package/maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-14 (time not recorded): 20 swim companions built; native water selects and animates them. No-input sinking reproduced at 42 units/s. Remove Quake idle descent in source; native/reference repair checks pending.
- Reported with v0.0.39-rc2 at 2026-10-14 (time not recorded): Maintainer repeats sinking and upright submerged body in RC2. Private screenshot retained; earlier short depth-hold/pose controls do not accept this scenario.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Surface, swimming and submerged gameplay; screenshot in Grazelands cell 12,6 |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2, v0.0.39-rc1, v0.0.39-rc2 (last seen) |
| Severity | high: Repeated maintainer-visible failure in RC1; exact repair remains unverified. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM 0.2.0, engine c2eaa5a, world format unknown |
| Unknown because | Exact loaded cell format and spell state not captured. |
| Platform or emulator | unknown (Screenshot does not identify emulator.) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-12: reported in v0.0.38-dev2
- 2026-10-13: seen again in v0.0.39-rc1: RC1: absent swimming/diving, maintainer reports sinking; underwater upright pose inspected.
- 2026-10-13: seen again in v0.0.39-rc1: Maintainer repeats missing swimming AND diving animation in BOTH first-person and third-person views.
- 2026-10-13: seen again in v0.0.39-rc2: Original third-person swim families confirmed; no dedicated dive key in16 base NIF/KF members.
- 2026-10-13: seen again in v0.0.39-rc2: Maintainer requires reported swimming/diving in RC2.
- 2026-10-13: STAIRS-MOLAG-ACCESS-38: WATER-GAMEPLAY-PARITY-38: 13 October 2026: reconciled 1 maintainer screenshot(s) with evidence IDs and original hashes.
- 2026-10-14: seen again in v0.0.39-rc2: 20 swim companions built; native water selects and animates them.
- 2026-10-14: seen again in v0.0.39-rc2: Maintainer repeats sinking and upright submerged body in RC2.
- 2026-10-14: UI-INVENTORY-INTEGRATION-40: scoped native equipment: UI-INVENTORY-INTEGRATION-40/INVENTORY-CATALOG-LOOKUP-40: actual names/icons, equip, modal pause and Russula persistence scoped; missing resources separate.
- 2026-10-14: Renewed RC2 gameplay reports: WATER-GAMEPLAY-PARITY-38:20swim companions bake; ordinary-collision native selects moving swim body but reproduces idle descent42units/s.
- 2026-10-14: Development audit: WATER-GAMEPLAY-PARITY-38: exactRC2 Nord/Seyda WALK3/noclipoff/water3 at (704,-320,-25) holds6s; down-pitch forward changes depth then velocity/depth settle.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
- [Timeline](#timeline)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Related reports](#related-reports)
- [Maintainer follow-up, 12 October 2026](#maintainer-follow-up-12-october-2026)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [RC1 maintainer evidence, 13 October 2026](#rc1-maintainer-evidence-13-october-2026)
- [Both-view swimming and diving follow-up, 13 October 2026](#both-view-swimming-and-diving-follow-up-13-october-2026)
- [Original clip inventory and both-view reference limits, 13 October 2026](#original-clip-inventory-and-both-view-reference-limits-13-october-2026)
- [Required RC2 swimming and diving scope, 13 October 2026](#required-rc2-swimming-and-diving-scope-13-october-2026)
- [Native candidate findings, 14 October 2026](#native-candidate-findings-14-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Renewed maintainer sinking and upright-body report, 14 October 2026](#renewed-maintainer-sinking-and-upright-body-report-14-october-2026)
- [Development audit, 14 October 2026](#development-audit-14-october-2026)
- [Scoped female-Nord mechanical control, 14 October 2026](#scoped-female-nord-mechanical-control-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Water gameplay lacks a demonstrated comparison against original Morrowind/OpenMW
across surface, swimming and submerged states. Related maintainer reports identify
apparent water-walking while equipment is readied and lighting a torch underwater.
This is an audit gap; not every behavior below is established to be broken.

## Where

Full v0.0.38-dev2 exterior water. The supplied underwater torch screenshot shows
Grazelands cell 12,6, global position 99333,49260,-466, time 02:37.

## How it happened

Source review, 13 October 2026: AmiQuake SV_CheckWater in sv_phys.c samples feet,
body and view height through SV_PointContents. SV_ClientThink in sv_user.c uses
SV_WaterMove when waterlevel is at least two, except for lava and noclip. This
movement dispatch does not depend on the readied equipment state.

The player-body profiles in prepare_player_view.py do not request swim or
swimidle groups. aw_anim.c falls back to walk or idle when those groups are
absent. This explains a source-level animation gap, not physical water-walking.
The active world.qc player callbacks have no drowning update. The inherited
PF_WaterMove drowning code is behind QUAKE2 in pr_cmds.c, which the normal Amiga
build does not enable; these callbacks do not invoke it either. Its breath
duration and damage rules must not be enabled blindly as Morrowind behavior.

OpenMW 0.48 tracks breath while submerged or knocked out underwater, exempts
Water Breathing, and uses game settings for breath time and suffocation damage.
Recovery resets breath. Its swimming and submerged tests use different height
thresholds, so neither should be equated with an AmiQuake waterlevel without
scene calibration. See the original [actor rules](https://raw.githubusercontent.com/OpenMW/openmw/openmw-0.48.0/apps/openmw/mwmechanics/actors.cpp)
and [water-depth tests](https://raw.githubusercontent.com/OpenMW/openmw/openmw-0.48.0/apps/openmw/mwworld/worldimp.cpp).

## Why it was not caught

No complete matched reference/native state-transition matrix is attached.
Existing visual appearance checks do not establish gameplay equivalence.

## Reproduction

Compare identical original/OpenMW and target scenes while entering water,
wading, swimming at the surface, diving, remaining submerged and leaving water.
Record depth, position, movement type, waterlevel, health, fatigue, breath and
active effects where supported. Cover sheathed and readied fists/weapons, torch
equipping/lighting/extinguishing, attacks and casting. Check Water Walking and
Water Breathing separately, including expiry, transitions and save/load.
Record unsupported mechanics explicitly rather than assuming parity.
Investigate lava contact, damage cadence, protection and escape separately;
water behavior alone is not lava acceptance.

## Repair

The missing animation and active drowning paths are identified in source;
implementation and original-game comparison remain pending. Reuse SV_CheckWater,
SV_WaterMove and the existing player damage path. Establish breath timing,
effects, equipment transitions and save/load behavior from the matched reference
before choosing state or damage rules. Preserve the current underwater
visual effects: the maintainer explicitly approves their appearance and requests no
changes to them. Reuse existing contents and movement state, avoid redundant
per-frame work and allocations, and measure CPU/memory on the baseline target.

## Verification

Open. Source paths reviewed; no runtime change or executed water regression is
claimed. Maintainer screenshot preserved; independent reproduction, matched reference
matrix and measured candidate acceptance remain pending. The screenshot alone
does not establish movement physics, spell state or torch fuel behavior.

## Prevention

Keep a repeatable water/equipment/effect transition matrix for both legacy BSP
and CHIM worlds. Link failures to their specific issue records. Require measured
baseline resource costs for repairs and preserve visual controls.

## Related reports

- [Readied water movement](PLAYER-READY-WATER-MOVEMENT-38.md)
- [Torch pose and underwater lighting](PLAYER-TORCH-THIRDPERSON-38.md)
- [Lava coverage](BUILD-LAVA-COVERAGE-38.md)


## Maintainer follow-up, 12 October 2026

The maintainer reports walking poses at the water surface and underwater, missing
swim/dive animations, and no observed breath-exhaustion damage. Cover the player
and all relevant NPCs, including future companion following. Compare original
drowning damage, red-screen feedback and audio before choosing behavior; the
original torch-extinguish trigger also remains to be established. Study lava
entry and damage separately. Reuse AmiQuake SV_WaterMove (sv_user.c) and
SV_CheckWater (sv_phys.c) where suitable; existing machinery is not proof that
all integration or animation works, nor proof of zero additional CPU/RAM cost.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-152017`: SHA-256 `e53bd537e39bdae534cd1a83ca7e5c3d3093ef284a94a760eaa18654becaea8e`. Underwater view shows a torch. Still frame cannot establish swimming animation.

## RC1 maintainer evidence, 13 October 2026

The original images remain private. Rounded HUD readings are location aids,
not exact source/package bindings or proof of motion.

- `OWNER-20261013-214815`, SHA-256 `066e1372444d81eb6b40067597bfc5a45b7c5c49d57ca74a023bf93902a54e11`: Third-person player stands upright underwater beside a sloping wall. HUD RC1, Vivec Hlaalu, cell2,-11; global18800,-83022,-480; local-3491,2284,-120; heading160, pitch-8, time12:10. A still does not prove sinking velocity or absence of controls.
- Text report: third-person swimming/diving absent and player sinks. Movement and effects require exact native reproduction.

## Both-view swimming and diving follow-up, 13 October 2026

The latest maintainer report explicitly covers missing swimming animation AND missing diving animation in both first-person and third-person views. The earlier third-person sinking report remains. Verify swimming and diving separately in each view against the original: appropriate first-person hands/equipment and action feedback, third-person body swim/dive poses, actual surface/submerged movement, breath and damage. Do not use a still frame or the existing water-movement dispatch as evidence that swimming or diving gameplay is implemented or accepted. Underwater visual effects remain an approved visual control, not mechanics acceptance.

## Original clip inventory and both-view reference limits, 13 October 2026

The original human/beast third-person sources contain idleswim, swimwalk/swimrun forward/back/left/right, swim turns and water knockdown/knockout/death families. The female override contributes selected locomotion groups; absent swim groups use the common base. npc_anim maps swimwalkforward/idleswim and the full NPC profile includes them, but prepare_player_view selects the move profile, which omits both. This is a player bake/wiring gap despite available original clips, not a lack of original swim assets.

All16 original base-animation NIF/KF members were read without conversion. None contains a standalone dive/diving group. The common first-person source has torch and water knockout groups, but no ordinary swimidle/walk/run loop; beast first-person overrides include ordinary hand-to-hand locomotion, and female first-person overrides are limited. This does not prove that original first-person swimming/diving has no visible movement. Reused idle/movement/weapon groups, camera/arm orientation and water physics can provide that feedback; do not invent a dedicated source dive clip.

The locally available pinned OpenMW source declares0.52-dev. It is distinct from the installed headless0.48 reference binary, and no local0.48 source ref was available. The0.52 source selects swimming movement/idle states, falls back from absent swim groups to available ordinary/weapon movement and idle, and updates first-person neck/camera orientation. Its third-person swim pitch and optional upward corrections have conditional/settings behavior; they must not be transplanted as blanket original0.48 rules. Those source findings are design guidance, not behavioral acceptance.

AmiQuake already provides SV_CheckWater and pitch-directed SV_WaterMove. The latter also applies inherited no-input downward drift; its existence is not Morrowind parity. Preserve these reusable mechanisms while calibrating original water depth, look/up/down inputs and idle behavior. The existing maintainer reports remain open in both views, including diving as a distinct transition/action.

Before acceptance, capture matched installed0.48 and target surface entry, idle swim, forward/back/side swim, look-up/down movement, dive/submerge, surface and land exit at the same scene/pose/clock. Cover human/beast/female, fists/torch states and view switches. Compare first-person camera/hand/equipment feedback and third-person actual pose/orientation separately from movement, fatigue, breath/damage and save/load. Read back baked group coverage and measure baseline costs. No new native comparison, water gameplay implementation or RC2 scope expansion follows from this audit.

## Required RC2 swimming and diving scope, 13 October 2026

The latest maintainer instruction requires reported swimming/diving, gait and combat
repairs in RC2; swimming/diving is no longer deferred by the earlier scope note.
Player water-pose integration and matched installed OpenMW 0.48 reference work
are in progress. Both first-person and third-person visual/state behavior need
actual reference captures; the 0.52 source inventory cannot replace that evidence.
Original clip availability and absence of a standalone dive key do not establish
first-person visual behavior, gameplay parity or repaired native acceptance.
Keep the complete reported water requirements open until exact source, automated,
target/native, package and maintainer evidence is supplied. Release hold remains.

## Native candidate findings, 14 October 2026

All 20 third-person swim companions bake successfully; target native ordinary-collision water selects the swimming body and shows changing swim poses. It also reproduces no-input descent at 42 units/second. Remove inherited Quake artificial idle drift while retaining pitch-directed movement, friction and acceleration; the new behavior and both-view dive/reference/package checks remain pending.

## Post-pin RC2 package observation, 14 October 2026

The extracted RC2 package holds origin (704, -320, -25) for a four-second no-input water control after noclip is disabled. Pitch45 with forward movement descends to origin (832.7, -320, -153.7) at waterlevel 3 and shows changing swim poses. Both readied first-person fists remain visible at default horizontal FOV 90/viewsize 100. Actual OpenMW0.48 reference holds depth and retains first-person fists; no dedicated first-person stroke or blanket body pitch is established. Broader drowning, fatigue, combat, all appearances and maintainer acceptance remain pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

## Renewed maintainer sinking and upright-body report, 14 October 2026

The maintainer again reports sinking and an upright submerged third-person body in
RC2, whose gameplay is the same as final v0.0.39. The original supplied screenshot
is retained privately; no public image or invented appearance/pose identity is
added. The exact owner-running binary, depth, equipment, spell and input state
remain to be bound in a repeatable reproduction.

The earlier four-second no-input depth hold and changing swim-pose observations
remain valid only for their recorded control. They do not establish that the
maintainer scenario is repaired, that an upright body is appropriate at that depth,
or that every race/equipment/view state matches the original.

Reproduce surface entry, no-input depth, forward movement with pitch, dive,
submerged idle and exit, with equipment lowered/readied and both camera views.
Compare the same measured scene in the original reference and target before
claiming a repair; keep depth behavior and visible animation acceptance separate.
No new gameplay acceptance or CHIM cell coverage is recorded.


## Development audit, 14 October 2026

Fresh exact-RC2 Nord/Seyda controls explicitly verify WALK movetype 3, noclip off and waterlevel 3. At local 704,-320,-25, six seconds without input retain the same origin. Physical forward movement with downward pitch changes depth; after release velocity decays to zero and depth holds. Physical shore entry likewise reaches water and holds depth for six seconds. The swim companion is selected without a missing-companion warning. The upright-looking body, the maintainer's sinking scenario and matched original behavior remain unresolved. A failed Vivec destination attempt is not Vivec acceptance.

## Scoped female-Nord mechanical control, 14 October 2026

In the exact v0.0.40-dev1 female-Nord diagnostic, normal WALK movetype 3 with
noclip off enters water from the Seyda shore using physical forward for three
seconds. Height changes from about 39.5 to -66.4 with waterlevel 3. After release,
five seconds without input retain height -66.4.

Physical forward with view pitch 45 degrees descends to -175.3; after release
velocity reaches zero. Forward at pitch -45 degrees ascends to -37.9.
The exact original clips, state readbacks and engine/source binding are retained
privately. These are positive scoped water-motion/depth-hold observations.

The upright-looking submerged body, original inventory-independent swim posture,
surface-entry behavior and matched original comparison remain open. This does
not verify every appearance, the reported maintainer location/state, breath/drowning,
complete gameplay parity or maintainer acceptance. It adds no CHIM cell coverage.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- [ACTOR-DROWNING-NOT-CARRIED-67](ACTOR-DROWNING-NOT-CARRIED-67.md): People and creatures under water never run out of breath or drown; only the player does, so the flood that drowns the Black Dart gang in Old Mournhold: Temple Sewers West cannot work once the water moves
- [ACTOR-HELLO-CLAMPED-61](ACTOR-HELLO-CLAMPED-61.md): An actor's Hello value is cut to 255 although the record holds it in 16 bits (up to 300 in the game data)
- [ACTOR-LOAD-NOT-COUNTED-66](ACTOR-LOAD-NOT-COUNTED-66.md): The carried load of NPCs and creatures was not counted in their fights
- [ACTOR-STATS-FAR-FALLBACK-61](ACTOR-STATS-FAR-FALLBACK-61.md): A being outside the loaded areas still reads its stats from the island-wide actor table
- [ACTOR-STATS-SCATTERED-61](ACTOR-STATS-SCATTERED-61.md): Actor stats are kept in five separate copies, each covering only some beings and some stats
- ACTORS-TOWN-ROOM-RETURN-59 (no report page): A town resident killed before entering a room is alive again on the way back out
- [ALCHEMY-MISSING-61](ALCHEMY-MISSING-61.md): Alchemy is missing: no alchemy window, potions cannot be drunk and ingredients cannot be eaten
- [ARENA-MERGE-54](ARENA-MERGE-54.md): Requested: one arena mode: the main game's arena minigame and the combat playground merged, with NPC against NPC fights to watch
- [ATTACK-TYPE-ANIMS-62](ATTACK-TYPE-ANIMS-62.md): With a sword and best attack off, slash, chop and thrust play the same attack animation
- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- [AW-20260928-19](AW-20260928-19.md): Courtyard barrel incorrectly says empty
- [AW-STATE-32-SLOTS-48](AW-STATE-32-SLOTS-48.md): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- [AW25-06](AW25-06.md): Quicksave shown as empty; save ordering confusing
- [BC-TREE-FLOATING-60](BC-TREE-FLOATING-60.md): A Bitter Coast tree near cell -2,-8 floats above the ground
- [CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66](CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66.md): The census office's two scripted doors of the captain's wing open only once: used a second time, E does nothing (the exit door to Seyda Neen, and the courtyard door into his room)
- [CARRIED-RECORDS-SEARCH-PER-KIND-61](CARRIED-RECORDS-SEARCH-PER-KIND-61.md): With hundreds of kinds of item carried, a place load takes up to a minute: one catalogue search per kind
- [CAST-ANIM-THIRD-PERSON-62](CAST-ANIM-THIRD-PERSON-62.md): The player's third-person body plays no spellcasting animation when casting
- [CAST-LOOK-AFTER-RELEASE-66](CAST-LOOK-AFTER-RELEASE-66.md): A spell's look and cast sound start only when the spell leaves, after the cast animation, and the look is off in a default game
- [CENSUS-CRAB-PLATE-FOCUS-66](CENSUS-CRAB-PLATE-FOCUS-66.md): Census back room: looking at the crab meat on the table, the use key goes to the silver plate under it, so E steals the plate instead of taking the crab meat
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CENSUS-INTRO-NOT-SCRIPTED-62](CENSUS-INTRO-NOT-SCRIPTED-62.md): Opening: the Census and Excise Office and its courtyard run on hand-written story steps, not the game's own character-creation scripts
- [CENSUS-INTRO-SCRIPTS-62](CENSUS-INTRO-SCRIPTS-62.md): The opening in the Census and Excise Office and its courtyard runs on hand-written rules, not on the game's own character-creation scripts
- [CENSUS-OFFICE-HOLDS-OFF-64](CENSUS-OFFICE-HOLDS-OFF-64.md): In the census office the clerk's message boxes do not show and the player is not held during his talk
- [CENSUS-OFFICE-NO-EXIT-64](CENSUS-OFFICE-NO-EXIT-64.md): The player cannot leave the census office after the registration
- [CENSUS-TABLE-TAKE-GRAB-HIM-62](CENSUS-TABLE-TAKE-GRAB-HIM-62.md): Census and Excise Office: taking an item from the table in front of Sellus Gravius makes a guard call out a theft line
- [CENSUS-THEFT-NO-ARREST-65](CENSUS-THEFT-NO-ARREST-65.md): A theft in the census office after the papers brings no guard and no arrest talk
- [CHARGEN-INVENTORY-LOCKED-60](CHARGEN-INVENTORY-LOCKED-60.md): After character creation the inventory key does not open the inventory
- [CHARGEN-NO-STARTING-CLOTHES-60](CHARGEN-NO-STARTING-CLOTHES-60.md): The player has no starting clothes after character creation, also after leaving the Census and Excise Office
- [CHARGEN-TUTORIAL-ITEM-MESSAGES-59](CHARGEN-TUTORIAL-ITEM-MESSAGES-59.md): Character creation: taking the bread, crab meat, candle, lockpick, whiskey, note or dagger in the Census Office shows no tutorial message
- [CHARGENSTATE-START-VALUE-63](CHARGENSTATE-START-VALUE-63.md): A new game sets the CharGenState global to 1, where the original opening script sets it to 10
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- [CHIM-FRAME-SOURCE-CONVERSION-59](CHIM-FRAME-SOURCE-CONVERSION-59.md): On CHIM frame maps the conversion to the game's coordinates says no for most engine callers
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COLLECT-CAPACITY-REJECTED-60](COLLECT-CAPACITY-REJECTED-60.md): After looting a corpse, picking up items fails with an inventory or state capacity message
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- [COMBAT-CHASE-SPEED-FIXED-66](COMBAT-CHASE-SPEED-FIXED-66.md): Every fighter chased, fled and flew at one fixed speed instead of its own Speed and Athletics
- [COMBAT-DAEDROTH-NO-HIT-51](COMBAT-DAEDROTH-NO-HIT-51.md): A daedroth outside the Azura s Coast stronghold cannot be punched: the blows pass through it; its runtime health reads 0.0
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIGHT-CARRIED-TO-NEW-MAP-67](COMBAT-FIGHT-CARRIED-TO-NEW-MAP-67.md): After a map change, the actors of the new place who take the places of the last place's fighters in memory attack the player at once
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-FLEE-RULE-PARTIAL-66](COMBAT-FLEE-RULE-PARTIAL-66.md): Fleeing by the Flee rating was off by default and left out the werewolf case and a spell as the best action
- [COMBAT-HIT-CHANCE-EFFECTS-62](COMBAT-HIT-CHANCE-EFFECTS-62.md): The melee hit chance leaves out Fortify Attack, Blind, Sanctuary, Chameleon and Invisibility, and the player's attributes are counted without their Fortify and Damage
- [COMBAT-HIT-CONTACT-CONE-62](COMBAT-HIT-CONTACT-CONE-62.md): The player's melee swing strikes only the actor exactly under the crosshair, not the nearest one in the original's hit cone, so flyers and small creatures are hard to reach
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-AGGRO-SHOWN-51](COMBAT-NO-AGGRO-SHOWN-51.md): Punching a worshipper shows no hostility when the first blow lands
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PARALYSED-PUNCH-66](COMBAT-PARALYSED-PUNCH-66.md): A paralysed victim of a punch took fatigue damage only and kept its evasion and block
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-RESUMED-FIGHT-TARGETS-PLAYER-68](COMBAT-RESUMED-FIGHT-TARGETS-PLAYER-68.md): A fight between two actors comes back as a fight against the player after a load or when their area joins again
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [COMBAT-SHIELD-EFFECT-NO-ARMOR-61](COMBAT-SHIELD-EFFECT-NO-ARMOR-61.md): A Shield effect on the player does not lower the damage of the blows that land on the player
- [COMBAT-STYLE-PRESETS-62](COMBAT-STYLE-PRESETS-62.md): Requested: combat style presets for fights, such as the dice and best-attack choices, chosen before a fight
- [COMBAT-THINK-COST-68040-54](COMBAT-THINK-COST-68040-54.md): On the slow 68040 preset one combat decision step (think) costs 34 ms with one fighter and 44 ms with four
- [COMBAT-WEAPON-CHOICE-SKILL-66](COMBAT-WEAPON-CHOICE-SKILL-66.md): The weapon a fighter took into a fight ignored its skills: the highest maximum damage won
- [CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66.md): The console's player->getitemcount answers "no such item id" for an item the player carries when no script and no actor names it (the census iron dagger)
- [CONTAINER-BRUSH-ROWS-67](CONTAINER-BRUSH-ROWS-67.md): The containers of the Imperial Prison Ship and the Census and Excise Office cannot be opened: drawn as brushes of their own, their use rows are skipped
- [CONTAINER-LEVELLED-CONTENTS-EMPTY-59](CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md): Containers whose contents are levelled lists open empty
- [CONTAINER-SCRIPT-ACTIVATE-67](CONTAINER-SCRIPT-ACTIVATE-67.md): Containers whose script takes the activation open directly, without their script
- [CONTAINER-STRIP-OPEN-MANY-KINDS-61](CONTAINER-STRIP-OPEN-MANY-KINDS-61.md): With hundreds of kinds of item carried, opening a body or a container holds the game for about 10 seconds
- [CONTAINER-WINDOW-SURVIVES-PLACE-CHANGE-67](CONTAINER-WINDOW-SURVIVES-PLACE-CHANGE-67.md): The container window stays open when the player is moved to another place: it still shows the first container, and a take from it changes that container
- [CORPSE-DISPOSE-MISSING-65](CORPSE-DISPOSE-MISSING-65.md): A corpse's loot window has no way to dispose of the body, so bodies pile up
- [CORPSE-INVENTORY-NOT-OPENABLE-59](CORPSE-INVENTORY-NOT-OPENABLE-59.md): Bodies of dead NPCs and creatures cannot be opened to take what they carried
- [CREATURE-BIPED-ANIMS-62](CREATURE-BIPED-ANIMS-62.md): An actor without walk or attack animations glides and does not fight back (ash slave, corprus stalker, the arena NPC Zennammu)
- [CREATURE-HOSTILE-FLEES-67](CREATURE-HOSTILE-FLEES-67.md): A hostile scrib in the wild runs away from the player instead of attacking
- [CRIME-FINE-GOLD-NOT-TAKEN-62](CRIME-FINE-GOLD-NOT-TAKEN-62.md): Paying a guard's fine clears the bounty but takes no gold: the answer's RemoveItem of the bounty's worth of gold leaves the purse as it was
- [CRIME-KILL-BOUNTY-65](CRIME-KILL-BOUNTY-65.md): Killing a guard puts only 80 gold of bounty on the player
- [CRIME-ONLY-THEFT-62](CRIME-ONLY-THEFT-62.md): Only a theft was a crime: attacking or killing someone in front of witnesses raised no bounty, guards never came to arrest, and the guards' answers to pay the fine or go to jail did nothing
- [CRIME-SAVE-PURSUERS-62](CRIME-SAVE-PURSUERS-62.md): The marks a crime leaves on people are lost on loading a save: guards forget a pursuit, the Alarmed mark and the crime's disposition change go, and a murder is no longer known
- [DAMAGE-RED-HUE-67](DAMAGE-RED-HUE-67.md): Requested: the screen takes a red hue when the player takes damage, as in the original
- [DBG-ARENA-PICKER-62](DBG-ARENA-PICKER-62.md): Requested: dbg arena offers a choose-your-opponent list of every NPC and creature
- [DBG-SUBWORD-ROUTE-DROPPED-62](DBG-SUBWORD-ROUTE-DROPPED-62.md): dbg camera fpview/hands/parts and dbg cast casting/now/ready/spell/start/strike reach their command without their own word
- [DBG-SUPERSPEED-62](DBG-SUPERSPEED-62.md): A bare dbg superspeed does not toggle it, and stamina drains while it is on
- [DBG-WEREWOLF-CHANGES-COUNTS-CALLS-68](DBG-WEREWOLF-CHANGES-COUNTS-CALLS-68.md): The debug werewolf status line counts every werewolf call of a script as a change of form, so a script calling it each frame makes the number climb by thousands
- [DBG-WEREWOLF-STATUS-ARMS-MISREAD-68](DBG-WEREWOLF-STATUS-ARMS-MISREAD-68.md): The werewolf status printed an empty first-person arms set as the player's own, which read as the wrong arms drawn
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [DIALOGUE-ADDON-TOPICS-NOT-PLAYABLE-67](DIALOGUE-ADDON-TOPICS-NOT-PLAYABLE-67.md): Missing: the Tribunal and Bloodmoon dialogue (topics, answers, changes to Morrowind) cannot be played: their speakers and places are not all in the game
- [DIALOGUE-AGGRO-62](DIALOGUE-AGGRO-62.md): A robber whose answer ends in a threat does nothing once the talk closes
- [DIALOGUE-ANSWER-VOICE-MISSING-67](DIALOGUE-ANSWER-VOICE-MISSING-67.md): Missing: an answer with a sound file does not play it
- [DIALOGUE-BACKGROUND-EMPTY-RANK-67](DIALOGUE-BACKGROUND-EMPTY-RANK-67.md): Hul in Balmora answers Background with "I am Hul, Pauper and  of the  ." : the rank and faction words are empty
- [DIALOGUE-CELL-FILTER-SEVERAL-CELLS-68](DIALOGUE-CELL-FILTER-SEVERAL-CELLS-68.md): A voice or greeting line with a place filter is never said by a speaker placed in several places or placed by a script
- [DIALOGUE-CHOICES-62](DIALOGUE-CHOICES-62.md): Dialogue choices are not shown as rows to pick, and the branch after a pick is not filtered as in the original
- [DIALOGUE-COMPANION-SHARE-MISSING-68](DIALOGUE-COMPANION-SHARE-MISSING-68.md): Missing: the talk window has no Companion Share entry for a companion, and there is no share window
- [DIALOGUE-CONDITIONS-PARTIAL-67](DIALOGUE-CONDITIONS-PARTIAL-67.md): Incomplete: the dialogue conditions PcVampire, PcCorprus and PcClothingModifier read their start value, and RankRequirement is not checked in game
- [DIALOGUE-CREATURE-SPEAKERS-66](DIALOGUE-CREATURE-SPEAKERS-66.md): Creatures that speak have no rows in the dialogue table, so their lines cannot be said: Almalexia, Vivec, ghosts, a draugr and rieklings among them
- [DIALOGUE-DISPOSITION-CHARM-ZERO-67](DIALOGUE-DISPOSITION-CHARM-ZERO-67.md): Incomplete: a Charm effect adds nothing to an NPC disposition in a conversation: it is read as 0
- DIALOGUE-GLOBAL-NAMES-CLASH-59 (no report page): Dialogue conditions on a global could read the wrong global name table
- [DIALOGUE-KNOWN-TOPICS-NOT-CHECKED-67](DIALOGUE-KNOWN-TOPICS-NOT-CHECKED-67.md): Incomplete: the topics a talk teaches (an answer, AddTopic) are not checked in a built game: learned, saved, loaded and listed again
- [DIALOGUE-RANK-WITHOUT-FACTION-67](DIALOGUE-RANK-WITHOUT-FACTION-67.md): An answer that asks for a faction rank without naming a faction is given to people without a faction: every one of them answers Background with the faction members' line
- [DIALOGUE-RING-DISPOSITION-CHECK-60](DIALOGUE-RING-DISPOSITION-CHECK-60.md): Disposition after handing Fargoth his ring needs checking against the original
- [DIALOGUE-TEXT-DEFINES-PARTIAL-67](DIALOGUE-TEXT-DEFINES-PARTIAL-67.md): Incomplete: the text defines %PCCrimeLevel, %PCClothingModifier and the global-variable defines are not filled in an answer
- [DIALOGUE-TOPIC-WHO-60](DIALOGUE-TOPIC-WHO-60.md): Shargam gro-Shagdub answers "Who?" about Ralen Hlaalo right after naming him in his rumors
- [DISTRICT-NEW-FIGHT-ATTACKERS-ON-SAME-MAP-RELOAD-67](DISTRICT-NEW-FIGHT-ATTACKERS-ON-SAME-MAP-RELOAD-67.md): After a teleport inside Plaza Brindisi Dorom the guards and high ordinators attack the player together with the fabricants
- [DISTRICT-PLACED-THINGS-NO-ROW-67](DISTRICT-PLACED-THINGS-NO-ROW-67.md): In Mournhold's districts no container, item, activator or door sign can be aimed at: their rows are keyed as a room's, and the game outdoors asks for the cells around the player
- [DOCK-GREETING-OUT-OF-REACH-67](DOCK-GREETING-OUT-OF-REACH-67.md): Since v0.0.67 the dock guard waits at the plank out of the greeting's reach of where the opening walk stops, and the race menu does not open
- [DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68](DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68.md): The dock guard's first walk of a new game can be held about 10 units short of the foot of the plank, where two dock pieces meet
- [DOOR-LOAD-DISABLED-STILL-USED-68](DOOR-LOAD-DISABLED-STILL-USED-68.md): A load door switched off by its script still shows its prompt and can be used
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md): Trapped doors and containers open without their trap
- DROP-CHIM-REFUSED-59 (no report page): Dropping an item on a streamed outdoor map is refused: Cannot place items in this area yet
- [DROP-ONLY-WHAT-IS-CARRIED-68](DROP-ONLY-WHAT-IS-CARRIED-68.md): A scripted Drop puts on the ground what the actor holds of the item and no more; OpenMW makes up the rest (a freed slave leaves one bracer, not two)
- [DROP-REFUSED-CENSUS-ROOM-67](DROP-REFUSED-CENSUS-ROOM-67.md): Dropping an item in the first room of the Census and Excise Office is refused with "Cannot place items in this area yet; kept."
- DROP-ROOM-BRUSH-ENTITY-59 (no report page): Dropping an item in a converted room is refused: Item path or footprint obstructed
- [DROP-STACK-ONE-ROW-PER-UNIT-59](DROP-STACK-ONE-ROW-PER-UNIT-59.md): Dropping a stack drops one piece per key press, each its own ground item, so the map's ground item limit (32) fills with single coins
- [DROPPED-LIGHT-NO-EFFECTS-61](DROPPED-LIGHT-NO-EFFECTS-61.md): A carriable light that is dropped shows no flame and gives no light where it lies
- [ENCUMBRANCE-INCOMPLETE-61](ENCUMBRANCE-INCOMPLETE-61.md): Carry weight is only half there: no burden shown, no message over the limit, Burden and Feather do nothing, and the kinds of item are capped
- [ENDGAME-CHAMBER-COLLAPSE-63](ENDGAME-CHAMBER-COLLAPSE-63.md): The ending in the Heart Chamber cannot play: the heart cannot play its death animation and the chamber's collapse is not animated
- [ENEMY-HEALTH-BAR-62](ENEMY-HEALTH-BAR-62.md): In a fight with a cliff racer the HUD shows no enemy health bar
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [EQUIP-ACTION-REGRESSION-62](EQUIP-ACTION-REGRESSION-62.md): Some weapons, armour and clothing show no Equip action in the inventory (the census office dagger reads "Actions unavailable for this item")
- [EQUIP-SHARDAXE-REFUSED-61](EQUIP-SHARDAXE-REFUSED-61.md): Equipping the iron shardaxe is refused while the iron longsword can be equipped
- [EXPANSION-SCRIPTS-NOT-ATTACHED-66](EXPANSION-SCRIPTS-NOT-ATTACHED-66.md): The scripts of the people, creatures and objects that Tribunal and Bloodmoon place are not attached, also in the expansion rooms the image holds
- [FABRICANTS-STAY-DRAWN-IN-FIGHT-67](FABRICANTS-STAY-DRAWN-IN-FIGHT-67.md): Two verminous fabricants that a script keeps out of the world stay drawn while they fight
- [FACTION-EXPEL-MESSAGE-64](FACTION-EXPEL-MESSAGE-64.md): An expulsion from a faction shows no message to the player
- [FACTION-STATS-PAGE-64](FACTION-STATS-PAGE-64.md): The stats page shows no factions, ranks, reputation or bounty
- [FALL-LANDING-KNOCKDOWN-62](FALL-LANDING-KNOCKDOWN-62.md): A hard landing does not knock the player or an actor down, and an NPC's landing plays no landing sound
- [FIGHT-STANCE-KEY-IGNORED-WHILE-RUNNING-67](FIGHT-STANCE-KEY-IGNORED-WHILE-RUNNING-67.md): While the run key is held, the key that readies the fight stance does nothing
- [FOCUS-EYE-INSIDE-ACTOR-BOX-68](FOCUS-EYE-INSIDE-ACTOR-BOX-68.md): The use key goes to a creature instead of the door under the crosshair when the player stands inside the creature's use box: the Unmarked Shipwreck's trapdoor cannot be used while a dreugh is near
- [GETANGLE-PLAYER-Z-READS-OBJECT-AXIS-67](GETANGLE-PLAYER-Z-READS-OBJECT-AXIS-67.md): A script reading the player's angle on the z axis gets a value 90 degrees off the view
- [GETEFFECT-TABLE-84-OF-143-68](GETEFFECT-TABLE-84-OF-143-68.md): GetEffect knew 84 of the game's 143 magic effects, three of them by another name than their game setting id
- [GETPCSLEEP-NOT-CARRIED-OUT-67](GETPCSLEEP-NOT-CARRIED-OUT-67.md): Resting never wakes the scripts that wait for the player's sleep: the Dark Brotherhood never attacks a resting player
- [GETWATERLEVEL-COLUMN-NOT-ROOM-67](GETWATERLEVEL-COLUMN-NOT-ROOM-67.md): GetWaterLevel reads the water in the player's column, not the room's own level, so it reads 0 in Old Mournhold: Temple Sewers West, whose water lies under every placement: the Black Dart gang's script then sets their health to 0 on arrival and the lit torches switch to burned out
- [GODMODE-COMBAT-DAMAGE-61](GODMODE-COMBAT-DAMAGE-61.md): With god mode on, a fight's blows still take the player's health and kill the player
- [GODMODE-LAVA-DEATH-62](GODMODE-LAVA-DEATH-62.md): The player can die in a lava pool with god mode on
- [GUARD-RESIST-ARREST-NOTHING-61](GUARD-RESIST-ARREST-NOTHING-61.md): Choosing to resist arrest in a guard's conversation does nothing: the guard does not attack
- [HAND-TO-HAND-NO-HIT-64](HAND-TO-HAND-NO-HIT-64.md): Fists rarely land and do almost nothing, even after the stats are raised during the fight
- [HANDS-STATE-LOST-THROUGH-DOORS-67](HANDS-STATE-LOST-THROUGH-DOORS-67.md): A readied spell stance turns into a weapon or fists stance after the player goes through a door into a building
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- [INVENTORY-CATALOGUE-PARTIAL-54](INVENTORY-CATALOGUE-PARTIAL-54.md): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- [INVENTORY-EQUIP-KINDS-NOT-YET-67](INVENTORY-EQUIP-KINDS-NOT-YET-67.md): Arrows and bolts, lockpicks and probes cannot be equipped from the inventory, and repair tools cannot be used
- INVENTORY-ITEM-MODEL-PATH-59 (no report page): The inventory catalogue refuses every item whose world model comes from the item model table (progs/items/)
- [INVENTORY-OPEN-COST-MANY-KINDS-61](INVENTORY-OPEN-COST-MANY-KINDS-61.md): With hundreds of kinds of item the inventory takes seconds to open, and every Tab reads the item file again
- JOURNAL-BOOK-32-QUESTS-59 (no report page): The journal book lists only the quests of the old 32-slot table, although every quest's stage is now kept
- [JOURNAL-LOWER-INDEX-ENTRY-64](JOURNAL-LOWER-INDEX-ENTRY-64.md): A Journal command at or below the quest index adds no entry, no finished or restart mark and no notice
- [LAVA-NO-DAMAGE-63](LAVA-NO-DAMAGE-63.md): Lava does no damage and is not drawn in the Red Mountain lava pool
- [LOADED-ITEMS-NOT-WEIGHED-61](LOADED-ITEMS-NOT-WEIGHED-61.md): After loading a save of another character the carried weight reads 0 until the next place load
- [LOCKED-CONTAINERS-NEVER-OPEN-67](LOCKED-CONTAINERS-NEVER-OPEN-67.md): Locked containers never open: no key, lockpick or Open spell works on them
- [MAGIC-SHELL-ORB-NOT-EGG-67](MAGIC-SHELL-ORB-NOT-EGG-67.md): A spell effect on the player shows the dotted orb instead of the upright egg-shaped shell, and it does not draw properly in first person
- [MAP-CHANGE-TOLD-BY-MODEL-SLOT-68](MAP-CHANGE-TOLD-BY-MODEL-SLOT-68.md): After a map change in a long session, the scripted animations, the animation pickers and the Halloween scene's model names can keep the last map's state, because they tell a new map only by its world model's slot
- [MAP-MENU-BLOCKED-COURTYARD-65](MAP-MENU-BLOCKED-COURTYARD-65.md): In the opening the courtyard announces the map, but the map key stays blocked until the opening ends
- [MAP-PLACES-SHOWN-UNVISITED-67](MAP-PLACES-SHOWN-UNVISITED-67.md): The map shows places the player has never visited (Pelagiad, the Moonmoth Legion fort)
- [MARKS-SUMMON-CARRIERS-NOT-LIVE-63](MARKS-SUMMON-CARRIERS-NOT-LIVE-63.md): The guarded items whose taking summons a guardian are not live references, so the summon never comes
- [MODREGION-KEEPS-UNGIVEN-CHANCES-68](MODREGION-KEEPS-UNGIVEN-CHANCES-68.md): ModRegion with fewer than ten chances kept the region's own chances for the other weathers and allowed a chance over 100
- [MWSCRIPT-ABILITY-EFFECTS-NOT-APPLIED-68](MWSCRIPT-ABILITY-EFFECTS-NOT-APPLIED-68.md): The attribute, skill, health, magicka and fatigue effects of an ability, disease or curse a script adds are not applied, and GetEffect and GetSpellEffects do not see such always-active effects (GetEffect asks only about the player)
- [MWSCRIPT-ACTOR-SETTINGS-NOT-USED-68](MWSCRIPT-ACTOR-SETTINGS-NOT-USED-68.md): SetHello, SetFlee and ModFlee keep their value but nothing uses it: the greeting distance and the decision to flee stay those of the game data
- [MWSCRIPT-ADDITEM-NO-EQUIP-68](MWSCRIPT-ADDITEM-NO-EQUIP-68.md): A person given an item by a script or a dialogue result does not put it on when it is better than what it wears
- [MWSCRIPT-AIWANDER-NOT-SAVED-68](MWSCRIPT-AIWANDER-NOT-SAVED-68.md): A wander a script gives an actor is not kept in a saved game and is centred on the placed spot; after a follow or escort ends the package reads as travel; Face turns at once
- [MWSCRIPT-CAST-PARTIAL-68](MWSCRIPT-CAST-PARTIAL-68.md): A script's Cast lands on the player only for stat and cure spells, with no resistance to its damage and no bolt; ExplodeSpell sends no bolt for Target effects
- [MWSCRIPT-CELLCHANGED-OUTDOOR-STEP-68](MWSCRIPT-CELLCHANGED-OUTDOOR-STEP-68.md): CellChanged does not read 1 when the player walks from one outdoor cell into the next within the same map
- [MWSCRIPT-CELLCHANGED-VOLATILE-54](MWSCRIPT-CELLCHANGED-VOLATILE-54.md): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
- [MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68](MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68.md): GetAttacked, HitOnMe, HurtStandingActor and HurtCollidingActor count only what the player does or where the player stands, not other people and creatures
- [MWSCRIPT-CONSOLE-LOCAL-NAMES-63](MWSCRIPT-CONSOLE-LOCAL-NAMES-63.md): Show and ShowVars cannot name a script's local variables: Show reads globals only, ShowVars lists the locals by slot number, and ToggleScripts flips the saved scripts switch
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- [MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68](MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68.md): Maximum magicka and maximum fatigue do not follow an attribute a script changes (Intelligence; Strength, Willpower, Agility, Endurance)
- [MWSCRIPT-DISABLE-LOST-LEDGER-FULL-66](MWSCRIPT-DISABLE-LOST-LEDGER-FULL-66.md): When the world change list is full, a script's Disable or SetDelete is not done
- [MWSCRIPT-FATIGUE-KNOCKOUT-FIGHT-ONLY-68](MWSCRIPT-FATIGUE-KNOCKOUT-FIGHT-ONLY-68.md): An actor whose fatigue a script takes below zero falls unconscious only while it fights, and a script's change of the player's fatigue is lost while he fights
- [MWSCRIPT-FORCED-STANCE-ACTORS-68](MWSCRIPT-FORCED-STANCE-ACTORS-68.md): ForceSneak and ForceRun on a person or creature change only part of its behaviour: no sneaking stance or speed, and no run while following or escorting
- [MWSCRIPT-FORCEGREETING-TALK-RULES-68](MWSCRIPT-FORCEGREETING-TALK-RULES-68.md): A script's ForceGreeting opens no conversation with a creature or with a person who is fighting, knocked down or has nothing to say
- [MWSCRIPT-INERT-SEEN-62](MWSCRIPT-INERT-SEEN-62.md): Scripts whose only effect is a message box, a door or item use they take over, or a local the dialogue reads were left out of the build as doing nothing
- [MWSCRIPT-INTERIOR-PLACEMENTS-48](MWSCRIPT-INTERIOR-PLACEMENTS-48.md): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- [MWSCRIPT-LATER-MASTER-SCRIPT-61](MWSCRIPT-LATER-MASTER-SCRIPT-61.md): An object placed in Vvardenfell whose record gets its script from a later master is not attached
- [MWSCRIPT-MEMBER-LOOKUP-COST-66](MWSCRIPT-MEMBER-LOOKUP-COST-66.md): A script reading or writing another object's variable walks the instance table and the parking store for the object: with the tables sized for the whole game the walk grows to hundreds of instances and thousands of parked objects, in 307 every-frame operations
- [MWSCRIPT-MEMBER-QUIET-READER-66](MWSCRIPT-MEMBER-QUIET-READER-66.md): A script that reads another object's variable can sleep through a change that object's own script makes to it: such a change does not wake quiet scripts
- [MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66](MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66.md): A script's read or write of another object's local variable finds nothing: the engine takes the object row's id as its script, so the read gives 0 and the write is dropped (Dagoth Ur's shield never follows the Heart's count)
- [MWSCRIPT-MISSING-FUNCTIONS-63](MWSCRIPT-MISSING-FUNCTIONS-63.md): Game scripts call MWScript functions the interpreter does not carry out yet: those calls do nothing and read 0 (69 scripts after the first v0.0.63 batch, most of them in Mournhold and Solstheim)
- [MWSCRIPT-NPC-STATS-SKIP-FIGHT-68](MWSCRIPT-NPC-STATS-SKIP-FIGHT-68.md): An attribute or skill a script sets or changes on an NPC or creature does not reach its fighting, which keeps the game data's values
- [MWSCRIPT-OLD-CONFIG-OFF-57](MWSCRIPT-OLD-CONFIG-OFF-57.md): An install whose saved config holds aw_mwscript 0 keeps compiled scripts off after the default turned on
- [MWSCRIPT-ONPCHITME-NEVER-SET-68](MWSCRIPT-ONPCHITME-NEVER-SET-68.md): The script variable OnPCHitMe is never set: a script that waits for the player to strike its actor never sees the blow
- [MWSCRIPT-PLACE-NO-MODEL-62](MWSCRIPT-PLACE-NO-MODEL-62.md): A script cannot place an NPC or a creature whose record has no placed reference in Vvardenfell
- [MWSCRIPT-PLACE-OTHER-KINDS-62](MWSCRIPT-PLACE-OTHER-KINDS-62.md): A script cannot place an activator, a container or a levelled creature list yet
- [MWSCRIPT-PLAYBINK-SKIP-FLAG-68](MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md): A video started by a script can always be skipped, also the ones the original plays to the end without a skip
- [MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68](MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68.md): PlayGroup and LoopGroup play only on a person or creature with a converted skeleton: animated objects and the player do not play the group, and the start mode is not read
- [MWSCRIPT-PLAYGROUP-FRAME-OBJECTS-68](MWSCRIPT-PLAYGROUP-FRAME-OBJECTS-68.md): A script's PlayGroup or LoopGroup on an object drawn as a placement of an outdoor frame (Mournhold's districts) changes nothing: Azura in the Temple Courtyard keeps her placed look through her appearance and departure at the end of Tribunal's main quest
- [MWSCRIPT-POSITION-ROOM-ROTATION-68](MWSCRIPT-POSITION-ROOM-ROTATION-68.md): A script's Position ignores its rotation argument and always moves the player to the outdoor point, also from inside a room
- [MWSCRIPT-POSITIONCELL-NPC-62](MWSCRIPT-POSITIONCELL-NPC-62.md): A script or a dialogue answer that moves an NPC or a creature to another place (PositionCell) does nothing
- [MWSCRIPT-POSITIONCELL-OUTDOOR-62](MWSCRIPT-POSITIONCELL-OUTDOOR-62.md): An NPC or a creature a script sends outdoors appears there only while its home area is loaded
- MWSCRIPT-REFUSED-SCRIPT-COUNT-58 (no report page): The compiled game scripts are refused at load since the dialogue result scripts joined the file: no script runs
- [MWSCRIPT-REPUTATION-DISPOSITION-PARTIAL-68](MWSCRIPT-REPUTATION-DISPOSITION-PARTIAL-68.md): ModReputation changes only the player's reputation, not a person's, and GetDisposition reads the base value without the race, faction, reputation and personality terms
- [MWSCRIPT-RESURRECT-LOADED-ONLY-68](MWSCRIPT-RESURRECT-LOADED-ONLY-68.md): Resurrect brings back only an NPC or creature loaded in the player's map, not one elsewhere and not the player
- [MWSCRIPT-ROTATE-NO-ENTITY-59](MWSCRIPT-ROTATE-NO-ENTITY-59.md): A script's Rotate on a streamed outdoor object without an entity is not carried out: the object does not turn
- [MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66](MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66.md): A script's SetHealth 0 leaves the actor alive: its health reads 0 but it stays standing and fighting (Dagoth Ur after the end script, the dreamer workers after the Heart)
- [MWSCRIPT-SMALL-DIFFERENCES-68](MWSCRIPT-SMALL-DIFFERENCES-68.md): Small differences of script functions: GetPCTraveling always 0, GetWeaponType for lockpicks and probes, GetInterior in the Mournhold districts, GetDetected by creatures, PlayBink always skippable, PCExpell without its message, PayFine keeps the weapon out, SetPCCrimeLevel 0 keeps witness marks
- MWSCRIPT-STANDING-NOT-SAVED-57 (no report page): The players standing the scripts change (crime level, reputation, faction ranks, expelled marks, faction reputation) is not in saved games
- [MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68](MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68.md): A script's StartCombat is refused once four fighters are in the fight, and an actor not loaded near the player starts no fight
- [MWSCRIPT-STARTSCRIPT-NO-TARGET-68](MWSCRIPT-STARTSCRIPT-NO-TARGET-68.md): A global script started from an object's script or a conversation does not take that object or speaker as its own, so its calls that name no object act on nothing
- [MWSCRIPT-STATE-NOT-SAVED-48](MWSCRIPT-STATE-NOT-SAVED-48.md): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- [MWSCRIPT-STOPCOMBAT-OTHER-SIDE-68](MWSCRIPT-STOPCOMBAT-OTHER-SIDE-68.md): A script's StopCombat ends only the actor's own fight: the actor it fought and that actor's allies go on attacking it
- [MWSCRIPT-STOPCOMBAT-UNWIRED-62](MWSCRIPT-STOPCOMBAT-UNWIRED-62.md): A script's StopCombat never ended a fight: the combat layer's end of one actor's fight was never connected to it
- [MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68](MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68.md): Disable/EnableTeleporting and Disable/EnableLevitation are kept and saved but nothing reads them: the engine has no Mark, Recall, Intervention or Levitate for them to stop
- [MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61](MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61.md): Scripts of records that are never placed in a cell (items carried, given or sold, actors from levelled lists) are compiled but never run
- [MWSCRIPT-WATER-LEVEL-STATIC-67](MWSCRIPT-WATER-LEVEL-STATIC-67.md): The water levers of Old Mournhold do not move the water: SetWaterLevel and ModWaterLevel are not carried out, because a room's water is fixed in its converted map
- [NEWGAME-OPENING-UNRESTRICTED-64](NEWGAME-OPENING-UNRESTRICTED-64.md): After New Game the opening runs as a free game: the dock guard stays idle on the pier, the race menu never opens, the pier and the census office hold nothing
- [NEWGAME-STATE-RESET-62](NEWGAME-STATE-RESET-62.md): A New Game started from the menu after playing leaves the fireplace of the Census and Excise Office unlit
- [OBJECT-ENABLE-NOT-DRAWN-65](OBJECT-ENABLE-NOT-DRAWN-65.md): Objects switched back on by a script stay invisible: the release papers in the census office can be read but are not drawn on the table
- [ONPCHITME-PEACEFUL-ACTOR-FIGHTS-BACK-68](ONPCHITME-PEACEFUL-ACTOR-FIGHTS-BACK-68.md): An actor whose script answers the player's blow and whose Fight is 0 fights back when struck, where the original leaves the answer to the script
- [OPENING-CAPTAIN-HINT-SUBTITLE-63](OPENING-CAPTAIN-HINT-SUBTITLE-63.md): The hint about talking to the captain shows as a subtitle instead of the original message box with an Ok button
- [OPENING-FIGHTING-ON-BEFORE-PAPERS-66](OPENING-FIGHTING-ON-BEFORE-PAPERS-66.md): In the opening, fighting is already switched on before the release papers are taken; the original keeps it off from the ship until the papers
- [OPENING-HOLDS-OFF-NEWGAME-64](OPENING-HOLDS-OFF-NEWGAME-64.md): A New Game clears the opening's state right after setting it: the dock guard does not meet the player and no race can be chosen
- [OPENING-SHIP-BLOCKER-NOT-CONVERTED-63](OPENING-SHIP-BLOCKER-NOT-CONVERTED-63.md): The invisible blocker inside the prison ship, one of the opening's 23 blockers, is not converted; the 22 outdoor ones are
- [OPENING-SHIP-GUARD-STEPS-63](OPENING-SHIP-GUARD-STEPS-63.md): On the prison ship the guard waits for the cellmate's warning before he speaks, and the movement hint is a box to close with Enter instead of the original message box
- [OPENING-VANITY-CAMERA-64](OPENING-VANITY-CAMERA-64.md): The idle camera orbit and the view switch run on the prison ship and the pier before the race is chosen
- [OPENING-WEATHER-NOT-CLOUDY-63](OPENING-WEATHER-NOT-CLOUDY-63.md): A new game does not start with the Bitter Coast weather set to cloudy, as the original opening script does
- [OUTDOOR-CONTAINER-AIM-66](OUTDOOR-CONTAINER-AIM-66.md): Containers outdoors (sacks, barrels, crates, chests by the huts and camps) cannot be aimed at, so they never open
- [OWNED-FACTION-RANK-GLOBAL-IGNORED-67](OWNED-FACTION-RANK-GLOBAL-IGNORED-67.md): A faction-owned container or item is free to take for any member of the faction, whatever rank its placement asks, and a placement freed by a global variable stays owned
- [PERSUASION-BROKEN-62](PERSUASION-BROKEN-62.md): Persuasion in dialogue does nothing: Admire and Intimidate return to the topic list, Taunt shows nothing
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- PICKUP-PLACED-E-NO-TAKE-58 (no report page): The activate key on a placed item in reach takes nothing
- PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59 (no report page): Outdoors no placed items are drawn after a teleport or load: the table is read before the player stands at the arrival
- PLACED-ITEMS-ROOM-RESET-59 (no report page): Entering a room with placed items drawn resets the machine to the boot screen
- [PLACED-PIT-AXE-NO-FOCUS-61](PLACED-PIT-AXE-NO-FOCUS-61.md): The iron shardaxe in the Seyda Neen pit is drawn but shows no item box and cannot be taken
- [PLAYER-ANIM-GROUPS-NOT-PLAYED-66](PLAYER-ANIM-GROUPS-NOT-PLAYED-66.md): The player body does not play every animation group of the original player files
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-FORTIFY-END-AS-DAMAGE-61](PLAYER-FORTIFY-END-AS-DAMAGE-61.md): When a Fortify Attribute effect on the player ends, the character sheet keeps it as a raised modifier and records the drop as damage
- [PLAYER-HEALTH-OVER-MAX-63](PLAYER-HEALTH-OVER-MAX-63.md): The player starts with health above its maximum (100 of 40) and restoring the stats keeps it there
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [PLAYER-START-SPELLS-NOT-KNOWN-61](PLAYER-START-SPELLS-NOT-KNOWN-61.md): Character creation never puts the race, birthsign and class spells and abilities on the player record, so they cannot be cast or apply
- [PLAYER-WALK-SPEED-SLOW-51](PLAYER-WALK-SPEED-SLOW-51.md): The starting walk speed feels very slow; check it against the original and OpenMW
- [POWER-COOLDOWN-NOT-SAVED-66](POWER-COOLDOWN-NOT-SAVED-66.md): Power cooldowns are not saved and not reset by a new game: a save and reload makes a used power ready again
- [PRISON-SHIP-ITEMS-TAKEABLE-65](PRISON-SHIP-ITEMS-TAKEABLE-65.md): On the prison ship the spoons, plates and other dishes can be taken with the activate key
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- [QUICKLOAD-EMPTY-ROOM-SPAWN-BLOCKED-67](QUICKLOAD-EMPTY-ROOM-SPAWN-BLOCKED-67.md): A quick load into a room without scenery reports a blocked spawn although the player is restored in place
- [RACE-RESIST-NOT-ON-SPELL-DAMAGE-64](RACE-RESIST-NOT-ON-SPELL-DAMAGE-64.md): A race ability that resists an element does not reduce spell damage of that element
- [RANDOM-STREAMS-SAME-EVERY-BOOT-67](RANDOM-STREAMS-SAME-EVERY-BOOT-67.md): Every session rolls the same fight dice and script random numbers, because the game's random streams start from fixed values at each start of the game
- [READY-MAGIC-SHOWS-WEAPON-65](READY-MAGIC-SHOWS-WEAPON-65.md): Readying magic (R by default) raises the equipped weapon instead of the spell-casting hands
- [REGION-INDEX-BASE-ONLY-68](REGION-INDEX-BASE-ONLY-68.md): In an image with the expansions, a script's ChangeWeather and ModRegion changed another region than the one it names: the end of the main quest changed the Grazelands' weather instead of Red Mountain's, and Mournhold's weather lines did nothing
- [RENDER-METADATA-29](RENDER-METADATA-29.md): Native renderer metadata warns as an unknown QuakeC field
- [RESIST-NORMAL-WEAPONS-61](RESIST-NORMAL-WEAPONS-61.md): Ghosts and other creatures that resist normal weapons take full damage from ordinary weapons, with no "no effect" message
- [REST-CENSUS-NO-CELL-ID-61](REST-CENSUS-NO-CELL-ID-61.md): The rest window offers Rest in the Census and Excise Office, a cell the game marks as no sleeping
- [REST-CUT-NO-CREATURE-67](REST-CUT-NO-CREATURE-67.md): A wilderness rest that is cut short brings no creature and no message
- [REST-CUT-TOO-OFTEN-67](REST-CUT-TOO-OFTEN-67.md): Wilderness rests are cut short by a creature far more often than the original's one in four
- [REST-OWNED-BED-ALWAYS-REFUSED-62](REST-OWNED-BED-ALWAYS-REFUSED-62.md): Someone else's bed was always refused; in the original sleeping in it is a crime only when someone sees it
- [ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68](ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68.md): After a visit to the courtyard, the Census and Excise Office's back room answers the use key with the town's outdoor rows, so its items have no focus row
- [ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67](ROOM-HALL-OF-MINISTRY-RATS-NOT-DISABLED-67.md): Mournhold Temple: Hall of Ministry holds seven Infected Rats at the start of a new game, and one attacks: their script should keep them away until the Crimson Plague quest
- [ROOM-NORENEN-DUR-ATRONACHS-DIE-67](ROOM-NORENEN-DUR-ATRONACHS-DIE-67.md): Norenen-dur, Basilica of Divine Whispers: two of its three atronachs are dead seconds after they attack, without the player striking
- [ROOM-SCRIPTED-ACTIVATOR-NO-USE-68](ROOM-SCRIPTED-ACTIVATOR-NO-USE-68.md): Inside a room a scripted activator drawn as a room placement shows its name but takes no use: the Halls of Penumbra's ice wall cannot be used with the Flaming Eye, so The Ritual of the Sun cannot go on
- [SAVE-ACTOR-BLOCK-OVERFLOW-59](SAVE-ACTOR-BLOCK-OVERFLOW-59.md): A full actor record pool (128 actors) can exceed the save's 32 KB actor block, which would refuse the save (calculated, not measured)
- [SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66](SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66.md): The world change list holds at most 8,192 actor rows while the game places about 13,800 actor references
- [SAVE-ACTOR-ROWS-EXPANSION-ROOMS-66](SAVE-ACTOR-ROWS-EXPANSION-ROOMS-66.md): A save is refused once an NPC was in a room of an expansion: the saved actor rows took place numbers up to the base game's rooms only, and the expansions' rooms are numbered after them
- [SAVE-AUTOSAVE-NOT-WRITTEN-67](SAVE-AUTOSAVE-NOT-WRITTEN-67.md): Autosaves are not written at all in a played game of the v0.0.66 release
- SAVE-CHANGES-FULL-REFUSES-SAVE-59 (no report page): When the world change list is full (2,048 entries for all actors and objects), the whole save is refused and the previous one kept
- [SAVE-CRIME-MARKS-32-ROWS-66](SAVE-CRIME-MARKS-32-ROWS-66.md): The crime marks table holds 32 NPCs, the 33rd witness takes a bystander's row, and a save keeps at most those 32
- [SAVE-EFFECTS-BLOCK-SIZE-61](SAVE-EFFECTS-BLOCK-SIZE-61.md): Loading a save with a spell effect active loses the effects and the made spells, enchanted items, soul gems and other blocks saved after them
- [SAVE-EQUIPMENT-29](SAVE-EQUIPMENT-29.md): Quickload returns with hands and torch put away
- [SAVE-EXPORT-FAILURE-ACCEPTED-65](SAVE-EXPORT-FAILURE-ACCEPTED-65.md): A save is written as good although the changed actors or script values failed to go into it
- [SAVE-INSIDE-SCRIPT-STEP-66](SAVE-INSIDE-SCRIPT-STEP-66.md): A save requested from the console or a menu during a running script step is taken at once instead of at a settled point
- [SAVE-ITEM-INSTANCES-ONE-PER-KIND-66](SAVE-ITEM-INSTANCES-ONE-PER-KIND-66.md): The player's items are saved per kind with one condition and charge, so two copies of the same item cannot keep different states
- [SAVE-ITEM-SCRIPT-LOCALS-66](SAVE-ITEM-SCRIPT-LOCALS-66.md): The script values of items were not saved, and a worn item lost them at every map change
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-LOCALS-BOUND-UNDER-GAME-66](SAVE-LOCALS-BOUND-UNDER-GAME-66.md): The saved script locals are bounded at 8,192 values while the base game alone declares 7,388
- [SAVE-MADE-RECORDS-64-CAP-66](SAVE-MADE-RECORDS-64-CAP-66.md): Made spells, enchanted items, potions and filled soul gems are capped at 64 each in the saved game
- [SAVE-REVEALED-PLACES-128-CAP-66](SAVE-REVEALED-PLACES-128-CAP-66.md): The places a script reveals on the map stop at 128 while the dialogue results alone call ShowMap 249 times
- [SAVE-SCRIPT-ROW-HINT-ONLY-65](SAVE-SCRIPT-ROW-HINT-ONLY-65.md): A saved script's values are matched to the compiled script only by its row: a rebuild in another order drops them
- [SAVE-STATE-FIXED-CAPS-66](SAVE-STATE-FIXED-CAPS-66.md): The save keeps the changes since a new game in fixed-size parts that are too small for the game, so a save can lose state or be refused
- SAVE-TAKEN-DISABLED-ONE-FLAG-59 (no report page): A taken object and an object a script disabled share one flag in the save, so one cannot be told from the other
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62](SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62.md): An actor a script enables in a loaded area is not drawn: the falling mage near Seyda Neen falls and dies unseen, his body searchable but invisible
- [SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61](SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61.md): A looping script sound keeps playing after a script disables its object
- [SCRIPTED-EVENT-FALLING-MAGE-61](SCRIPTED-EVENT-FALLING-MAGE-61.md): The falling mage north of Seyda Neen does not fall: he is in the world from the start and his scripted fall does not run
- [SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62](SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62.md): The falling mage near Seyda Neen plays out past the default draw distance: on his platform and for most of his fall he is too far up to be drawn from anywhere the player can stand when his event starts
- [SCROLL-CAST-MISSING-64](SCROLL-CAST-MISSING-64.md): Scrolls cannot be cast: a scroll opens like a book and its spell never takes effect
- [SELLUS-GRAVIUS-GREETING-ONLY-64](SELLUS-GRAVIUS-GREETING-ONLY-64.md): Using Sellus Gravius gives only his greeting line instead of his dialogue
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [SERVICE-REFUSAL-UNCLOTHED-60](SERVICE-REFUSAL-UNCLOTHED-60.md): Arrille refuses to barter at disposition 80 (player without clothes)
- [SETPOS-MOVER-NO-ENTITY-68](SETPOS-MOVER-NO-ENTITY-68.md): SetPos does nothing on a scripted object drawn as a room placement without its own entity: the floating crates of Old Mournhold, Forgotten Sewer stay on the floor when the water rises
- [SKILL-BOOKS-MISSING-62](SKILL-BOOKS-MISSING-62.md): Reading a skill book does not raise its skill: the original raises it by one on the first read
- [SKILL-RAISE-NOT-SEEN-62](SKILL-RAISE-NOT-SEEN-62.md): In a playtest of v0.0.61 no skill was ever seen to rise: no skill-increased line and no sound in normal play
- [SPELL-EFFECTS-TABLE-CUT-64](SPELL-EFFECTS-TABLE-CUT-64.md): Game spells cast nothing: the actor table read only the first 32 sections of the compiled scripts file
- [STEAL-WITNESSED-NO-CRIME-60](STEAL-WITNESSED-NO-CRIME-60.md): Taking an owned item in full view of its owner or other people has no consequence
- [STORM-WALK-NOT-SLOWED-68](STORM-WALK-NOT-SLOWED-68.md): Walking into an ash storm, blight storm or blizzard is not slowed, the weathers have no sounds, and guards put their torches away in ash storms
- [SWEEP-ARENA-PIT-TWO-FAIL-54](SWEEP-ARENA-PIT-TWO-FAIL-54.md): dbg sweep reports two failing entities in the Vivec Arena Pit (map vai000) in every session of the Arena Pit images
- [SWIM-PLAYER-DOES-NOT-STAY-AT-DEPTH-68](SWIM-PLAYER-DOES-NOT-STAY-AT-DEPTH-68.md): A player placed deep in the water does not stay at that depth: moments later the player is near the surface or above the water
- [TAKEN-LIGHT-FLAME-STAYS-60](TAKEN-LIGHT-FLAME-STAYS-60.md): Picking up a lit candle leaves its flame floating where it stood
- [TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61](TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61.md): The flames and night lights of carriable lights outdoors are not tied to the item
- [TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61](TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61.md): A carriable light placed outdoors (a lantern in Seyda Neen) cannot be taken
- TALK-PROMPT-NOT-TALKABLE-54 (no report page): The Talk prompt shows for any target with a voice string: hostile, dead, knocked out or without dialogue
- [THIRDPERSON-ANIMS-AUDIT-62](THIRDPERSON-ANIMS-AUDIT-62.md): Third-person actions are not all mapped to the original's animation groups
- [TORCH-HIDES-HELM-62](TORCH-HIDES-HELM-62.md): Holding a torch makes the worn helm disappear from the third-person body and the inventory figure; it returns when the torch is put away
- [TOWN-OUTDOOR-SCRIPTS-NOT-ATTACHED-66](TOWN-OUTDOOR-SCRIPTS-NOT-ATTACHED-66.md): On a town map, scripted objects without an entity are never attached, so their scripts do not run (the falling mage's journal near Seyda Neen)
- [TP-BEING-TRIBUNAL-FALLS-THROUGH-67](TP-BEING-TRIBUNAL-FALLS-THROUGH-67.md): Teleporting to a character in some Tribunal interiors drops the player through the floor (the pawnbroker Ten-Tongues Weerhat, the Assassin)
- [TP-DRAW-WEAPON-LAGS-67](TP-DRAW-WEAPON-LAGS-67.md): In third person, drawing or sheathing the weapon or fists starts late, also when the player stands still
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- [UI-HUD-TOGGLE-KEY-51](UI-HUD-TOGGLE-KEY-51.md): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [UNDERWATER-BREATH-62](UNDERWATER-BREATH-62.md): Underwater there is no breath meter and no drowning, and Water Breathing is not applied
- [VIEW-VANITY-UNDOES-SET-VIEW-67](VIEW-VANITY-UNDOES-SET-VIEW-67.md): A turn of the view the game makes while the idle camera orbits is undone: the view goes back to where it faced when the orbit began
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-RIPPLES-UNDER-ACTORS-MISSING-68](WATER-RIPPLES-UNDER-ACTORS-MISSING-68.md): No ripples on the water: a swimmer at the surface or a player walking on water leaves no rings of ripples, which the original draws
- [WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md): Water Walking cast deep under the water is applied and lifts the player to the surface, where the original refuses the effect
- [WATER-WALKING-NOT-ON-SURFACE-68](WATER-WALKING-NOT-ON-SURFACE-68.md): Water Walking does not hold the player on the water: the effect is in the effects table, but the movement does not read it, so the player swims as without it
- [WEAPON-STRIKE-ENCHANT-NOT-CAST-61](WEAPON-STRIKE-ENCHANT-NOT-CAST-61.md): A weapon's Cast When Strikes enchantment is not cast when the weapon hits
- [WEATHER-STATE-NOT-SAVED-66](WEATHER-STATE-NOT-SAVED-66.md): The current weather and its change in progress are not saved: a load rolls the weather again
- [WEREWOLF-BODY-NOT-DRAWN-63](WEREWOLF-BODY-NOT-DRAWN-63.md): A player turned into a werewolf by a script keeps his own body: the werewolf model is not drawn
- [WEREWOLF-RUN-SPEED-63](WEREWOLF-RUN-SPEED-63.md): A player in werewolf form runs at his normal run speed: the werewolf run multiplier is not applied
- [WEREWOLF-SET-KEPT-WITH-TORCH-68](WEREWOLF-SET-KEPT-WITH-TORCH-68.md): With a torch carried, taking the werewolf robe off by hand kept the werewolf's body and arms in memory until the torch was put away
- [WEREWOLF-TABLES-STAY-LOADED-68](WEREWOLF-TABLES-STAY-LOADED-68.md): After the change back from the werewolf form its two animation tables stay loaded until the game is closed
- [WEREWOLF-TRANSFORM-RULES-PARTIAL-68](WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md): Turning into a werewolf changes only the stats and takes the gear off: health, the readied spell, temporary effects, the closed windows and the witnesses of the change are not carried
- [WORLD-BUTTONS-62](WORLD-BUTTONS-62.md): Buttons and levers that should act do nothing, for example the Ghostgate gate buttons on both sides
- [WORLD-OBJECT-STATE-NOT-SAVED-59](WORLD-OBJECT-STATE-NOT-SAVED-59.md): World objects taken or moved are not remembered: they come back when the cell or room reloads, and saves do not keep them

Related bugs in other categories:

- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains

<!-- END GENERATED CATEGORY -->
