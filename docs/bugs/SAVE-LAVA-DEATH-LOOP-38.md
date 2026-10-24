# SAVE-LAVA-DEATH-LOOP-38: Lava fall can leave an autosave that reloads into repeated death

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | Maintainer v0.0.38 playtest: teleport, lava contact and death screen |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | high: The most recent automatic save may repeatedly kill the player on reload. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.38 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Reported during the maintainer playtest; exact running image binding needs confirmation. |
| Platform or emulator | unknown (Earlier maintainer session was WinUAE; emulator not restated for this specific report.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

Maintainer reports an autosave death loop after falling into a lava pool. The autosave trigger, timing and saved health/contents are not yet established.

## Where

Maintainer-reported v0.0.38 gameplay on 13 October 2026. Exact map, pose and save identity remain to be recorded.

## How it happened

Cause unknown. Teleport saving, unsafe lava autosaves and death-menu tint are recorded independently so one repair cannot silently close another.

## Why it was not caught

No exact-package regression currently binds safe teleport arrival, hazardous autosave reload and readable death-menu composition together.

## Reproduction

Use a disposable gameplay copy. Record the source/image, destination, health, movement and water/lava state, save timestamp and menu state before and after the action. Repeat a normal safe arrival and ordinary death as controls. Preserve the original failing save privately.

## Repair

Reproduce with a fresh test save and compare the existing save and arrival machinery. Preserve a recoverable safe checkpoint; do not overwrite it with a dead, falling-into-lava or actively burning state. Determine whether the unsafe snapshot comes from teleport, periodic save or another trigger before changing policy.

## Verification

The original maintainer trigger still needs exact-image reproduction. Source
correction and compiled regression evidence are recorded below; these do not
establish native or maintainer acceptance. Compare original/OpenMW behavior and
verify the exact candidate on the target engine.

## Candidate diagnosis and verification, 13 October 2026

AW_SaveAllowed only checked that the player was alive and walking. AW_SaveTick could therefore write an automatic checkpoint while falling or standing in lava. The candidate reuses Quake FL_ONGROUND, vertical velocity and SV_CheckWater waterlevel/watertype, plus the existing combat/modal state. Only pending/due autosaves run these checks. The real AWS4 writer regression verifies prior saves remain newest through loading, falling, lava, death, slime, deep water, combat and modal states, then a safe arrival writes a new slot. Manual save policy and existing save bytes are unchanged.

## Prevention

Add a regression for the demonstrated cause, then a target-native safe/unsafe transition check. Keep save integrity, game-state behavior and UI visibility as separate acceptance results.

## Exact RC1 evidence, 13 October 2026

The same exact-package session entered lava (watertype -5), took damage and died without subsequent save messages. Reload returned to the prior sequence-3 arrival checkpoint, health 55, watertype -1, and subsequent observation retained health 55. Three AWS saves decode and match the exact catalogue/content. This is a scoped native observation; existing unsafe saves, other liquid/fall cases and maintainer acceptance remain open. AWS alone contains no ground/content/movement flags.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

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
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
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
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

<!-- END GENERATED CATEGORY -->
