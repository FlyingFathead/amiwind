# COMBAT-NODICE-READOUT-40: No-dice combat readout labels living targets already down

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 14 October 2026, in v0.0.40-dev1 |
| Where | Combat console readout: aw_combat.c print_swing and no-dice sentinel |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev1 (last seen) |
| Severity | low: The diagnostic falsely describes a live no-dice swing as already down and hides its actual outcome. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | Source-only audit; exact inspected file hashes are retained, but a separate Git commit binding was not established. |
| Platform or emulator | not in game (Source-confirmed diagnostic control flow; corrected native message not verified.) |

<!-- END GENERATED FACTS -->

## Symptom

With combat readout enabled and dice disabled, a swing against a living target
can print "already down" instead of its actual no-dice outcome. This diagnostic
message does not establish that the target was already knocked down or that
damage failed.

## Where

Combat readout in engine/aga/src/aw_combat.c, print_swing, and the no-dice
sentinel emitted by engine/aga/src/aw_combat_rules.c.

## How it happened

AW_CombatSwing uses roll -1 for an already dead victim and roll -2 for a living
no-dice swing. print_swing handles every negative roll as "already down" and
returns before its separate -2 branch. The intended no-dice output is therefore
unreachable. The rules can still apply the actual fatigue or health damage.

## Why it was not caught

The diagnostic branch did not have a print regression distinguishing these two
negative sentinels. Rules-only damage checks do not verify console output.
Misleading wording must not be used as proof of a failed outgoing hit.

## Reproduction

Enable readout, disable combat dice, and swing in reach at a living target.
Compare the actual fighter state and AW_CombatSwing result with print_swing.
Keep a dead-victim -1 control, normal dice results and successful blocks separate.

## Repair

The new source excludes the valid -2 no-dice sentinel from the generic negative
refusal, then uses the existing AmiQuake console printer and resolved combat
result. Dead-victim -1 keeps its refusal. Combat rules, balance, damage, random
state and normal dice behavior are unchanged.

## Verification

The new fixture includes the actual print_swing implementation and resolves
living no-dice fatigue/health swings through the real rules. It captures the
actual outcome and amount, with dead-victim -1, ordinary hit/miss/block and
readout-disabled controls; printing leaves the resolved result and fighter
state unchanged. The preceding runtime fails; the candidate passes under UBSan.
All 22 bounded combat-module checks pass. Exact new target/full gate/native
readout and owner acceptance remain pending. The earlier misleading native
message is not proof of outgoing damage failure or corrected native behavior.

## Prevention

Test every diagnostic sentinel through the actual formatter, alongside rules
state. Preserve the distinction between a miss, already-down refusal, fatigue
damage, health damage and a successful block.

## Later exact live readout check, 14 October 2026

The exact later Amiga target/FPU and nonroot full suite pass: 4,079 checks,
4,073 passes, no unexpected failures/errors, three Windows skips and three
tracked expected failures.

The live diagnostic correctly prints armed no-dice health HIT outcomes against
Eldafire, including 13.4 and 13.2 health, and real unarmed no-dice fatigue outcomes
against Fargoth, including 5.3 and 0.5 fatigue. Fargoth's subsequent state reads
149/154 fatigue. The prior already-down mislabel no longer replaces these live
outcomes. Recovery and intervening attacks keep later bar snapshots separate
from immediate resolved damage.

These no-dice controls are an explicit diagnostic extension. They do not prove
a normal-dice bare-fist hit, full balance/original parity, every formatting case
or a shipped correction. Existing dead and normal-dice automated controls remain
separate; the canonical issue stays open.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
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
