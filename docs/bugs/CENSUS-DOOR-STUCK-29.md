# CENSUS-DOOR-STUCK-29: opening the hall door can trap the player

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 6 October 2026, in v0.0.29-rc1 |
| Where | Census and Excise Office hall door |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.29-rc2 |
| Severity | high: Opening the door traps the player inside its hull. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [6 October 2026 activation guard candidate](#6-october-2026-activation-guard-candidate)
- [Report and expected behavior](#report-and-expected-behavior)
- [Reproduction and cause](#reproduction-and-cause)
- [Repair and acceptance](#repair-and-acceptance)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## 6 October 2026 activation guard candidate

The proposed overlap guard is now implemented in the next source candidate.
Actual RC1 map hulls plus actual `AW_OpeningUse` verify refusal for the player
and a solid NPC, unchanged actor pose/closed yaw/story flag, no false sound or
relink, and successful opening once both bodies are clear. Five focused existing
checks pass in Linux Docker. The open door remains SOLID_BSP.

This checks the final pose of the existing instant rotation. Saved-open restore,
already-trapped saves, native passage acceptance and packaged integration remain
pending. First shipped fixed version remains **none**.

Updated 2026-10-06T13:34:07+00:00. Status: **cause reproduced in actual collision code; repair
in progress; no shipped fix yet**.

| Field | Recorded value |
| --- | --- |
| Reported version | v0.0.29-rc1 private playtest, WinUAE |
| Reported date / game clock | 6 October 2026 / 10:16 |
| Area | Census and Excise Office interior, hall door |
| Displayed local XYZ | 65, 52, 65; interior global coordinate unavailable |
| Displayed direction / pitch | N 008 / 20; compass heading is not raw engine yaw |
| Fixed | N |
| First shipped fixed version | None |
| Intended fix checkpoint | Next candidate after published RC1; exact release designation pending |
| Maintainer | Collision/runtime maintenance |
| Release gate | Safe passage after opening, with original collision and save behavior preserved |

## Report and expected behavior

After opening the hall door, the playtester could no longer move normally at
the captured position. Opening a door must not place its solid hull inside the
player. Keep the closed/open door collision; do not hide this with noclip,
coordinate-specific teleportation, or removing architectural collision.

## Reproduction and cause

The read-only replay used the exact shipped census BSP, SHA-256
`2145d7a0abf0be4a49218d62b11a5ab8f114910f308c185184edb248eac71d7d`,
the RC1 model decoder and actual `SV_ClipMoveToEntity`/math routines compiled
inside Linux Docker. This was a geometry replay, not a new emulator run.

The HUD truncates position to integers. Replaying Z=65 literally also contacts
a floor brush, so it is not the complete standing pose. An actual downward
hull trace finds **(65,52,65.549949646)**, which displays the reported integers.
At that position the closed scene has no overlapping world/inline brush. The
existing open action changes door reference **172860**, inline model ***2**,
from yaw **-180** to **-90**, then relinks it without checking the player.
The open scene gains exactly one overlap: that hall door.

All 64 sampled positions within [65,66) x [52,53) x [65,66) are outside the
closed door hull and inside its open hull. This sampling tests the door-specific
result; floor validity is established separately by the standing-pose trace.
The direct replay therefore reproduces rotation of the door onto the player.

## Repair and acceptance

The repair in progress checks whether the proposed open pose overlaps the
player or a solid actor before committing it. If blocked, keep the existing
closed angle and story flag, avoid a false opening sound, and provide a brief
step-aside message. A clear approach must still open normally. The check must
not alter unrelated movement/collision code or change the original door mesh.

Saved-open restoration is a separate ordering case: the open door can be
restored before the saved player pose. An activation guard alone must not be
reported as repairing an already-trapped save. Test that case explicitly.

Required regression evidence:

- Actual shipped hull at the valid reported standing position: closed clear,
  proposed opening obstructed, rejected opening leaves pose/state unchanged.
- A clear player position opens once, emits its opening cue once, and permits
  travel through the doorway in both directions.
- Nearby solid actor and already-open cases retain correct behavior.
- Save/reload in valid closed/open states preserves geometry, actor position
  and story progression; document handling of existing trapped saves separately.
- Target playtest with ordinary controls confirms passage and no renewed trap.

When shipped and verified, update the fixed flag, exact first fixed version,
package identity and target evidence together. Source tests alone do not close it.

See [the issue index](../BUGS.md) and [RC1 issues](../BUGS-v0.0.29-RC1.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW-STATE-32-SLOTS-48 (no report page): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
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
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
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
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- UI-HUD-TOGGLE-KEY-51 (no report page): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

<!-- END GENERATED CATEGORY -->
