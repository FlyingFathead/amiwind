# CENSUS-DOOR-STUCK-29: opening the hall door can trap the player

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 6 October 2026, in v0.0.29-rc1 |
| Where | Census and Excise Office hall door |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.29-rc2 |
| Severity | high: Opening the door traps the player inside its hull. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |

<!-- END GENERATED FACTS -->

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
| Owner | Collision/runtime maintenance |
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

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

<!-- END GENERATED CATEGORY -->
