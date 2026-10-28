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

- ARENA-MERGE-54 (no report page): Requested: one arena mode: the main game's arena minigame and the combat playground merged, with NPC against NPC fights to watch
- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW-STATE-32-SLOTS-48 (no report page): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- COMBAT-DAEDROTH-NO-HIT-51 (no report page): A daedroth outside the Azura s Coast stronghold cannot be punched: the blows pass through it; its runtime health reads 0.0
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- COMBAT-NO-AGGRO-SHOWN-51 (no report page): Punching a worshipper shows no hostility when the first blow lands
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- COMBAT-THINK-COST-68040-54 (no report page): On the slow 68040 preset one combat decision step (think) costs 34 ms with one fighter and 44 ms with four
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- INVENTORY-CATALOGUE-PARTIAL-54 (no report page): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- MWSCRIPT-CELLCHANGED-VOLATILE-54 (no report page): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-STATE-NOT-SAVED-48 (no report page): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- TALK-PROMPT-NOT-TALKABLE-54 (no report page): The Talk prompt shows for any target with a voice string: hostile, dead, knocked out or without dialogue
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- UI-HUD-TOGGLE-KEY-51 (no report page): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)

Related bugs in other categories:

- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains

<!-- END GENERATED CATEGORY -->
