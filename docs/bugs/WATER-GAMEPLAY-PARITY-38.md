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

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
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

- ACTOR-HELLO-CLAMPED-61 (no report page): An actor's Hello value is cut to 255 although the record holds it in 16 bits (up to 300 in the game data)
- ACTOR-STATS-FAR-FALLBACK-61 (no report page): A being outside the loaded areas still reads its stats from the island-wide actor table
- [ACTOR-STATS-SCATTERED-61](ACTOR-STATS-SCATTERED-61.md): Actor stats are kept in five separate copies, each covering only some beings and some stats
- ACTORS-TOWN-ROOM-RETURN-59 (no report page): A town resident killed before entering a room is alive again on the way back out
- ALCHEMY-MISSING-61 (no report page): Alchemy is missing: no alchemy window, potions cannot be drunk and ingredients cannot be eaten
- ARENA-MERGE-54 (no report page): Requested: one arena mode: the main game's arena minigame and the combat playground merged, with NPC against NPC fights to watch
- ATTACK-TYPE-ANIMS-62 (no report page): With a sword and best attack off, slash, chop and thrust play the same attack animation
- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- [AW-STATE-32-SLOTS-48](AW-STATE-32-SLOTS-48.md): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- BC-TREE-FLOATING-60 (no report page): A Bitter Coast tree near cell -2,-8 floats above the ground
- [CARRIED-RECORDS-SEARCH-PER-KIND-61](CARRIED-RECORDS-SEARCH-PER-KIND-61.md): With hundreds of kinds of item carried, a place load takes up to a minute: one catalogue search per kind
- CAST-ANIM-THIRD-PERSON-62 (no report page): The player's third-person body plays no spellcasting animation when casting
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- CENSUS-INTRO-NOT-SCRIPTED-62 (no report page): Opening: the Census and Excise Office and its courtyard run on hand-written story steps, not the game's own character-creation scripts
- [CENSUS-INTRO-SCRIPTS-62](CENSUS-INTRO-SCRIPTS-62.md): The opening in the Census and Excise Office and its courtyard runs on hand-written rules, not on the game's own character-creation scripts
- CENSUS-TABLE-TAKE-GRAB-HIM-62 (no report page): Census and Excise Office: taking an item from the table in front of Sellus Gravius makes a guard call out a theft line
- CHARGEN-INVENTORY-LOCKED-60 (no report page): After character creation the inventory key does not open the inventory
- CHARGEN-NO-STARTING-CLOTHES-60 (no report page): The player has no starting clothes after character creation, also after leaving the Census and Excise Office
- CHARGEN-TUTORIAL-ITEM-MESSAGES-59 (no report page): Character creation: taking the bread, crab meat, candle, lockpick, whiskey, note or dagger in the Census Office shows no tutorial message
- CHARGENSTATE-START-VALUE-63 (no report page): A new game sets the CharGenState global to 1, where the original opening script sets it to 10
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- [CHIM-FRAME-SOURCE-CONVERSION-59](CHIM-FRAME-SOURCE-CONVERSION-59.md): On CHIM frame maps the conversion to the game's coordinates says no for most engine callers
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COLLECT-CAPACITY-REJECTED-60](COLLECT-CAPACITY-REJECTED-60.md): After looting a corpse, picking up items fails with an inventory or state capacity message
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- [COMBAT-DAEDROTH-NO-HIT-51](COMBAT-DAEDROTH-NO-HIT-51.md): A daedroth outside the Azura s Coast stronghold cannot be punched: the blows pass through it; its runtime health reads 0.0
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- COMBAT-HIT-CHANCE-EFFECTS-62 (no report page): The melee hit chance leaves out Fortify Attack, Blind, Sanctuary, Chameleon and Invisibility, and the player's attributes are counted without their Fortify and Damage
- COMBAT-HIT-CONTACT-CONE-62 (no report page): The player's melee swing strikes only the actor exactly under the crosshair, not the nearest one in the original's hit cone, so flyers and small creatures are hard to reach
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- COMBAT-NO-AGGRO-SHOWN-51 (no report page): Punching a worshipper shows no hostility when the first blow lands
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- COMBAT-SHIELD-EFFECT-NO-ARMOR-61 (no report page): A Shield effect on the player does not lower the damage of the blows that land on the player
- COMBAT-STYLE-PRESETS-62 (no report page): Requested: combat style presets for fights, such as the dice and best-attack choices, chosen before a fight
- COMBAT-THINK-COST-68040-54 (no report page): On the slow 68040 preset one combat decision step (think) costs 34 ms with one fighter and 44 ms with four
- [CONTAINER-LEVELLED-CONTENTS-EMPTY-59](CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md): Containers whose contents are levelled lists open empty
- [CONTAINER-STRIP-OPEN-MANY-KINDS-61](CONTAINER-STRIP-OPEN-MANY-KINDS-61.md): With hundreds of kinds of item carried, opening a body or a container holds the game for about 10 seconds
- [CORPSE-INVENTORY-NOT-OPENABLE-59](CORPSE-INVENTORY-NOT-OPENABLE-59.md): Bodies of dead NPCs and creatures cannot be opened to take what they carried
- CREATURE-BIPED-ANIMS-62 (no report page): An actor without walk or attack animations glides and does not fight back (ash slave, corprus stalker, the arena NPC Zennammu)
- CRIME-FINE-GOLD-NOT-TAKEN-62 (no report page): Paying a guard's fine clears the bounty but takes no gold: the answer's RemoveItem of the bounty's worth of gold leaves the purse as it was
- CRIME-ONLY-THEFT-62 (no report page): Only a theft was a crime: attacking or killing someone in front of witnesses raised no bounty, guards never came to arrest, and the guards' answers to pay the fine or go to jail did nothing
- CRIME-SAVE-PURSUERS-62 (no report page): The marks a crime leaves on people are lost on loading a save: guards forget a pursuit, the Alarmed mark and the crime's disposition change go, and a murder is no longer known
- DBG-ARENA-PICKER-62 (no report page): Requested: dbg arena offers a choose-your-opponent list of every NPC and creature
- DBG-SUBWORD-ROUTE-DROPPED-62 (no report page): dbg camera fpview/hands/parts and dbg cast casting/now/ready/spell/start/strike reach their command without their own word
- DBG-SUPERSPEED-62 (no report page): A bare dbg superspeed does not toggle it, and stamina drains while it is on
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- DIALOGUE-AGGRO-62 (no report page): A robber whose answer ends in a threat does nothing once the talk closes
- DIALOGUE-CHOICES-62 (no report page): Dialogue choices are not shown as rows to pick, and the branch after a pick is not filtered as in the original
- DIALOGUE-GLOBAL-NAMES-CLASH-59 (no report page): Dialogue conditions on a global could read the wrong global name table
- DIALOGUE-RING-DISPOSITION-CHECK-60 (no report page): Disposition after handing Fargoth his ring needs checking against the original
- DIALOGUE-TOPIC-WHO-60 (no report page): Shargam gro-Shagdub answers "Who?" about Ralen Hlaalo right after naming him in his rumors
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md): Trapped doors and containers open without their trap
- DROP-CHIM-REFUSED-59 (no report page): Dropping an item on a streamed outdoor map is refused: Cannot place items in this area yet
- DROP-ROOM-BRUSH-ENTITY-59 (no report page): Dropping an item in a converted room is refused: Item path or footprint obstructed
- DROP-STACK-ONE-ROW-PER-UNIT-59 (no report page): Dropping a stack drops one piece per key press, each its own ground item, so the map's ground item limit (32) fills with single coins
- [DROPPED-LIGHT-NO-EFFECTS-61](DROPPED-LIGHT-NO-EFFECTS-61.md): A carriable light that is dropped shows no flame and gives no light where it lies
- [ENCUMBRANCE-INCOMPLETE-61](ENCUMBRANCE-INCOMPLETE-61.md): Carry weight is only half there: no burden shown, no message over the limit, Burden and Feather do nothing, and the kinds of item are capped
- ENEMY-HEALTH-BAR-62 (no report page): In a fight with a cliff racer the HUD shows no enemy health bar
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [EQUIP-ACTION-REGRESSION-62](EQUIP-ACTION-REGRESSION-62.md): Some weapons, armour and clothing show no Equip action in the inventory (the census office dagger reads "Actions unavailable for this item")
- EQUIP-SHARDAXE-REFUSED-61 (no report page): Equipping the iron shardaxe is refused while the iron longsword can be equipped
- [FALL-LANDING-KNOCKDOWN-62](FALL-LANDING-KNOCKDOWN-62.md): A hard landing does not knock the player or an actor down, and an NPC's landing plays no landing sound
- [GODMODE-COMBAT-DAMAGE-61](GODMODE-COMBAT-DAMAGE-61.md): With god mode on, a fight's blows still take the player's health and kill the player
- GODMODE-LAVA-DEATH-62 (no report page): The player can die in a lava pool with god mode on
- GUARD-RESIST-ARREST-NOTHING-61 (no report page): Choosing to resist arrest in a guard's conversation does nothing: the guard does not attack
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- INVENTORY-CATALOGUE-PARTIAL-54 (no report page): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- INVENTORY-ITEM-MODEL-PATH-59 (no report page): The inventory catalogue refuses every item whose world model comes from the item model table (progs/items/)
- [INVENTORY-OPEN-COST-MANY-KINDS-61](INVENTORY-OPEN-COST-MANY-KINDS-61.md): With hundreds of kinds of item the inventory takes seconds to open, and every Tab reads the item file again
- JOURNAL-BOOK-32-QUESTS-59 (no report page): The journal book lists only the quests of the old 32-slot table, although every quest's stage is now kept
- [LOADED-ITEMS-NOT-WEIGHED-61](LOADED-ITEMS-NOT-WEIGHED-61.md): After loading a save of another character the carried weight reads 0 until the next place load
- MWSCRIPT-CELLCHANGED-VOLATILE-54 (no report page): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
- MWSCRIPT-CONSOLE-LOCAL-NAMES-63 (no report page): Show and ShowVars cannot name a script's local variables: Show reads globals only, ShowVars lists the locals by slot number, and ToggleScripts flips the saved scripts switch
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INERT-SEEN-62 (no report page): Scripts whose only effect is a message box, a door or item use they take over, or a local the dialogue reads were left out of the build as doing nothing
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-LATER-MASTER-SCRIPT-61 (no report page): An object placed in Vvardenfell whose record gets its script from a later master is not attached
- MWSCRIPT-MISSING-FUNCTIONS-63 (no report page): Game scripts call MWScript functions the interpreter does not carry out yet: those calls do nothing and read 0 (69 scripts after the first v0.0.63 batch, most of them in Mournhold and Solstheim)
- MWSCRIPT-OLD-CONFIG-OFF-57 (no report page): An install whose saved config holds aw_mwscript 0 keeps compiled scripts off after the default turned on
- [MWSCRIPT-PLACE-NO-MODEL-62](MWSCRIPT-PLACE-NO-MODEL-62.md): A script cannot place an NPC or a creature whose record has no placed reference in Vvardenfell
- [MWSCRIPT-PLACE-OTHER-KINDS-62](MWSCRIPT-PLACE-OTHER-KINDS-62.md): A script cannot place an activator, a container or a levelled creature list yet
- MWSCRIPT-POSITIONCELL-NPC-62 (no report page): A script or a dialogue answer that moves an NPC or a creature to another place (PositionCell) does nothing
- [MWSCRIPT-POSITIONCELL-OUTDOOR-62](MWSCRIPT-POSITIONCELL-OUTDOOR-62.md): An NPC or a creature a script sends outdoors appears there only while its home area is loaded
- MWSCRIPT-REFUSED-SCRIPT-COUNT-58 (no report page): The compiled game scripts are refused at load since the dialogue result scripts joined the file: no script runs
- MWSCRIPT-ROTATE-NO-ENTITY-59 (no report page): A script's Rotate on a streamed outdoor object without an entity is not carried out: the object does not turn
- MWSCRIPT-STANDING-NOT-SAVED-57 (no report page): The players standing the scripts change (crime level, reputation, faction ranks, expelled marks, faction reputation) is not in saved games
- [MWSCRIPT-STATE-NOT-SAVED-48](MWSCRIPT-STATE-NOT-SAVED-48.md): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- MWSCRIPT-STOPCOMBAT-UNWIRED-62 (no report page): A script's StopCombat never ended a fight: the combat layer's end of one actor's fight was never connected to it
- [MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61](MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61.md): Scripts of records that are never placed in a cell (items carried, given or sold, actors from levelled lists) are compiled but never run
- [NEWGAME-STATE-RESET-62](NEWGAME-STATE-RESET-62.md): A New Game started from the menu after playing leaves the fireplace of the Census and Excise Office unlit
- OPENING-CAPTAIN-HINT-SUBTITLE-63 (no report page): The hint about talking to the captain shows as a subtitle instead of the original message box with an Ok button
- OPENING-SHIP-BLOCKER-NOT-CONVERTED-63 (no report page): The invisible blocker inside the prison ship, one of the opening's 23 blockers, is not converted; the 22 outdoor ones are
- OPENING-SHIP-GUARD-STEPS-63 (no report page): On the prison ship the guard waits for the cellmate's warning before he speaks, and the movement hint is a box to close with Enter instead of the original message box
- OPENING-WEATHER-NOT-CLOUDY-63 (no report page): A new game does not start with the Bitter Coast weather set to cloudy, as the original opening script does
- PERSUASION-BROKEN-62 (no report page): Persuasion in dialogue does nothing: Admire and Intimidate return to the topic list, Taunt shows nothing
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- PICKUP-PLACED-E-NO-TAKE-58 (no report page): The activate key on a placed item in reach takes nothing
- PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59 (no report page): Outdoors no placed items are drawn after a teleport or load: the table is read before the player stands at the arrival
- PLACED-ITEMS-ROOM-RESET-59 (no report page): Entering a room with placed items drawn resets the machine to the boot screen
- PLACED-PIT-AXE-NO-FOCUS-61 (no report page): The iron shardaxe in the Seyda Neen pit is drawn but shows no item box and cannot be taken
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- PLAYER-FORTIFY-END-AS-DAMAGE-61 (no report page): When a Fortify Attribute effect on the player ends, the character sheet keeps it as a raised modifier and records the drop as damage
- PLAYER-HEALTH-OVER-MAX-63 (no report page): The player starts with health above its maximum (100 of 40) and restoring the stats keeps it there
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [PLAYER-START-SPELLS-NOT-KNOWN-61](PLAYER-START-SPELLS-NOT-KNOWN-61.md): Character creation never puts the race, birthsign and class spells and abilities on the player record, so they cannot be cast or apply
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- RESIST-NORMAL-WEAPONS-61 (no report page): Ghosts and other creatures that resist normal weapons take full damage from ordinary weapons, with no "no effect" message
- REST-CENSUS-NO-CELL-ID-61 (no report page): The rest window offers Rest in the Census and Excise Office, a cell the game marks as no sleeping
- REST-OWNED-BED-ALWAYS-REFUSED-62 (no report page): Someone else's bed was always refused; in the original sleeping in it is a crime only when someone sees it
- SAVE-ACTOR-BLOCK-OVERFLOW-59 (no report page): A full actor record pool (128 actors) can exceed the save's 32 KB actor block, which would refuse the save (calculated, not measured)
- SAVE-CHANGES-FULL-REFUSES-SAVE-59 (no report page): When the world change list is full (2,048 entries for all actors and objects), the whole save is refused and the previous one kept
- SAVE-EFFECTS-BLOCK-SIZE-61 (no report page): Loading a save with a spell effect active loses the effects and the made spells, enchanted items, soul gems and other blocks saved after them
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- SAVE-TAKEN-DISABLED-ONE-FLAG-59 (no report page): A taken object and an object a script disabled share one flag in the save, so one cannot be told from the other
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62 (no report page): An actor a script enables in a loaded area is not drawn: the falling mage near Seyda Neen falls and dies unseen, his body searchable but invisible
- SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61 (no report page): A looping script sound keeps playing after a script disables its object
- [SCRIPTED-EVENT-FALLING-MAGE-61](SCRIPTED-EVENT-FALLING-MAGE-61.md): The falling mage north of Seyda Neen does not fall: he is in the world from the start and his scripted fall does not run
- [SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62](SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62.md): The falling mage near Seyda Neen plays out past the default draw distance: on his platform and for most of his fall he is too far up to be drawn from anywhere the player can stand when his event starts
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- SERVICE-REFUSAL-UNCLOTHED-60 (no report page): Arrille refuses to barter at disposition 80 (player without clothes)
- SKILL-BOOKS-MISSING-62 (no report page): Reading a skill book does not raise its skill: the original raises it by one on the first read
- SKILL-RAISE-NOT-SEEN-62 (no report page): In a playtest of v0.0.61 no skill was ever seen to rise: no skill-increased line and no sound in normal play
- STEAL-WITNESSED-NO-CRIME-60 (no report page): Taking an owned item in full view of its owner or other people has no consequence
- SWEEP-ARENA-PIT-TWO-FAIL-54 (no report page): dbg sweep reports two failing entities in the Vivec Arena Pit (map vai000) in every session of the Arena Pit images
- TAKEN-LIGHT-FLAME-STAYS-60 (no report page): Picking up a lit candle leaves its flame floating where it stood
- [TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61](TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61.md): The flames and night lights of carriable lights outdoors are not tied to the item
- TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61 (no report page): A carriable light placed outdoors (a lantern in Seyda Neen) cannot be taken
- TALK-PROMPT-NOT-TALKABLE-54 (no report page): The Talk prompt shows for any target with a voice string: hostile, dead, knocked out or without dialogue
- THIRDPERSON-ANIMS-AUDIT-62 (no report page): Third-person actions are not all mapped to the original's animation groups
- TORCH-HIDES-HELM-62 (no report page): Holding a torch makes the worn helm disappear from the third-person body and the inventory figure; it returns when the torch is put away
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- UI-HUD-TOGGLE-KEY-51 (no report page): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- UNDERWATER-BREATH-62 (no report page): Underwater there is no breath meter and no drowning, and Water Breathing is not applied
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- WEAPON-STRIKE-ENCHANT-NOT-CAST-61 (no report page): A weapon's Cast When Strikes enchantment is not cast when the weapon hits
- WEREWOLF-BODY-NOT-DRAWN-63 (no report page): A player turned into a werewolf by a script keeps his own body: the werewolf model is not drawn
- WEREWOLF-RUN-SPEED-63 (no report page): A player in werewolf form runs at his normal run speed: the werewolf run multiplier is not applied
- WORLD-BUTTONS-62 (no report page): Buttons and levers that should act do nothing, for example the Ghostgate gate buttons on both sides
- WORLD-OBJECT-STATE-NOT-SAVED-59 (no report page): World objects taken or moved are not remembered: they come back when the cell or room reloads, and saves do not keep them

Related bugs in other categories:

- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains

<!-- END GENERATED CATEGORY -->
