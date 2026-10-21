# INTRO-CAMERA-GATING-38: Opening cameras expose an unselected player race

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev |
| Where | Prison ship and deck before character race selection |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev (last seen) |
| Severity | medium: Breaks opening character continuity by revealing an unselected body. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Platform or emulator | unknown (Maintainer did not identify the emulator in this report.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

The maintainer reports that idling into the vanity camera or pressing Tab before race
selection shows a default Argonian on the prison ship and its deck. This breaks
character continuity. The report identifies the latest development build;
the exact running version and emulator have not been independently confirmed.
The maintainer says the displayed body is appropriate after race selection.

## Where

Opening character creation, third-person view and idle vanity camera.

## How it happened

Cause remains under investigation. The existing AmiQuake-derived view integration
in engine/aga/src/aw_view.c checks body availability for POV and idle orbit;
playing() excludes AW_IntroUse(), but that alone does not establish the required
story-stage policy. Existing aw_view_third and aw_view_vanity switches are not
evidence of separate scene permission gates.

## Why it was not caught

No verified opening-sequence camera gate matrix is attached to this report.
Ordinary third-person rendering checks do not establish character-creation gating.

## Reproduction

Start a new game. Before race selection, try Tab and wait for idle vanity on the
prison ship and deck. Compare the displayed body before and after selecting race.
This is maintainer-reported; independent native reproduction remains pending.

## Repair

Pending. Establish the original Morrowind script and OpenMW permission transitions
for third-person and vanity independently. Reuse the existing view state machine
and story state rather than creating a second camera system. Cover automatic
orbit, Tab tap/hold, saved settings, explicit commands, new game and load/arrival.
The dbg aw hors 0 opening bypass must establish coherent post-opening permissions.
Do not guess that race selection unlocks both modes: verify the original first.

## Verification

No repair, matching OpenMW comparison or fixed-package acceptance yet. Required:
original script evidence, matched native opening-stage checks, bypass and save/load
regressions, and normal post-opening camera controls.

## Prevention

Test both camera permissions at each opening milestone and through debug bypasses.
Keep player-body availability distinct from permission to display that body.


## Candidate investigation, 12 October 2026

Original CharGen disables both view switching and vanity; CharGenClassNPC enables
both after its papers instruction (state 30 to -1), inside the Census office.
The source candidate derives permission from existing persistent story state,
keeps camera preferences separate, cancels pending POV/orbit input while locked,
and rejects explicit vanity startup. Completed character presets, including Hors,
retain permissions without adding a save-format field. The existing Quake chase
camera and view state machine are reused. Twenty-six focused Docker checks pass,
including story-stage and Hors assertions. The integrated RC1 source also
passed Amiga compilation on 13 October 2026. Native opening-stage checks and
matched OpenMW runtime acceptance remain required.

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
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
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

<!-- END GENERATED CATEGORY -->
