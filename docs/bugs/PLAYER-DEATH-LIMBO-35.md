# PLAYER-DEATH-LIMBO-35: After the player dies there is no way out

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | player death handling (engine/QuakeC), death screen and menus |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35 (last seen) |
| Severity | medium: A lost fight ends the session; the player has to restart the emulator |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3cbe85a |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Open (maintainer playtest of v0.0.35). 10 October 2026: repaired in source on v0.0.36-dev (gated); the in-game check is pending.

## Symptom

When the player dies, the game stays in a limbo: no reload, no retry, no way back to the menu. The view stays in first
person and nothing marks the death.

In that state the player can still talk to NPCs, including the hostile one that won the fight, and they answer.
A dead player must not interact at all (talk, activate, attack).

The original (Morrowind, and OpenMW as the reference) plays a short death scene instead: the camera moves to a third-person
view, the player's character falls with its death animation, the death music plays, and then the game offers to load the
last save or return to the main menu. Camera distance and timing, the fall animation, the music cue and the menu's
wording and choices are to be taken from the OpenMW source and a headless OpenMW capture of the same fight, not guessed
(see [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md)).

## Where

Player death handling (engine and QuakeC), the death screen and the menus. What already exists:

- the third-person camera: Quake's chase camera is in the engine (`engine/aga/src/chase.c`: `chase_active`,
  `chase_back`, `chase_up`), and with it on, the client already draws the player's own entity (`cl_main.c`);
- the death music: the death track is looked up at start-up (music player, `aw_music.c`) and played on death.

What is missing: a full-body model of the player's own character (race, sex, head, worn equipment) with the original's
death animation (the player is drawn only as first-person hands today), the death sequence that switches the camera,
plays the fall and blocks every interaction, and the menu at its end.

## How it happened

To be found: the death state has no exit path in the first combat layer.

## Why it was not caught

No scripted test covers it; found in play.

## Reproduction

Always: lose a fight and die.

## Repair

v0.0.36-dev (engine/aga/src/aw_view.c, aw_view_rules.c; docs/THIRD_PERSON.md), following the original as OpenMW 0.51
reproduces it (mwmechanics/character.cpp playRandomDeath -> useDeathCamera; mwmechanics/actors.cpp: when the death
animation has finished, mwstate/statemanagerimp.cpp askLoadRecent):

- On death every interaction stops: movement, attack, the use key (talk, activate), the QuakeC impulses and waiting
  (one lock in the input layer, aw_intro.c).
- The camera moves behind the player (the death camera) and the player's body plays its death animation; the death
  track plays for every death, in a fight or not.
- When the animation has finished: the original question from the game's own settings (sLoadLastSaveMsg, sYes,
  sNo): Yes loads the most recent save, No opens the main menu; with no save, straight to the main menu.
- AmiWind extension, a build-config switch on by default (`--death-retry on|off`, cvar `aw_death_retry`): after a
  lost fight a third button, Retry fight, puts the player and the opponents back where the fight began, with the
  health and fatigue they had then (aw_combat.c AW_CombatRetry).

Project rule added the same day ("dead in a fight, you cannot talk to anyone or interact or even see their names"):
one predicate, `AW_PlayerDead()` (engine/aga/src/quakedef.h: the single-player player's health is gone), is asked
by every path that shows or starts an interaction: the focus name (aw_scene.c AW_SceneTargetName: NPC names, the
travel driver, plants), the prompts (AW_SceneDraw: doors, opening hints, "E: Talk"/"E: Pick"), the use key
(AW_SceneUse: doors, travel, harvest; the input layer: E, impulses, attack, jump, movement, waiting), the
crosshair (view.c, also the companion pick's red crosshair), the enemy health bar (aw_combat.c), the context button
(+aw_alt) and every voice line (aw_anim.c AW_VoiceSay); the subtitle on screen is cleared at death. The QuakeC
greeting already skipped a dead player. The HUD bars stay, as in the original (OpenMW Player::activate refuses a
dead player, Actors greet only a living one; the third-person death view has no crosshair).

## Verification

Source and gate: tests/aga_view_test.c (the death sequence: no choice while falling, the choices with and without a
save and retry, main menu with neither), tests/aga_combat_test.c (retry restores positions and health, a second
death plays the death track again), tests/test_third_person.py (the input lock in every input path, the hooks, and
every name/hint/crosshair/voice/greeting/use path asking AW_PlayerDead), tests/aga_player_dead_test.c (the
predicate), tests/aga_companion_test.c (no pick target while dead).
To do: an in-game check (die in a fight in a MiniWind sandbox or the next dev build; the prompt, load, main menu
and retry work).

## Prevention

A scripted check in the headless harness for the same case.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
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
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

Related bugs in other categories:

- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies

<!-- END GENERATED CATEGORY -->
