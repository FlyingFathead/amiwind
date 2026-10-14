# COMBAT-BLOCKING-36: Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | Engine and QuakeC: combat blocking, block animations, input bindings |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev5 (last seen) |
| Severity | low: Feature request: Block is a Morrowind skill that has no effect in AmiWind yet |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev5_full-coast-arena-seyda-dev5_6c29a23 (playtest v0.0.36-dev5) |
| Platform or emulator | FS-UAE, JIT (dev5 playtest build) |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Open feature request from the owner on 11 October 2026, after playing the v0.0.36-dev5 playtest build on FS-UAE with JIT (widened the same day). Target: v0.0.37 or later.
Repaired in source on v0.0.36-blocking for v0.0.36-rc1 (owner order: into rc1), not yet in a build.

## Symptom

Block is a Morrowind skill, but in AmiWind the player cannot block on purpose and has no block button, and
NPCs seemed never to block: no block animation was seen in a fight.

## Where

Engine: the combat code (`engine/aga/src/aw_combat.c`, `aw_combat_rules.c`), the input (`cl_input.c`,
`config/keymaps.cfg`, the Controls menu in `aw_menu.c`), the third-person body (`aw_view.c`,
`tools/prepare_player_view.py`) and the HUD (`aw_ui.c`).

## How it happened

The original game has no block button: blocking is automatic whenever a shield is equipped (UESP Block page;
OpenMW `combat.cpp` blockMeleeAttack has no input). The v0.0.35 combat merge implemented that automatic rule
for every fighter, with the NPC block animation of the animation kit, and kept the right mouse button for a
held block that was not built. The rule only lets fighters with a shield and a one-handed weapon block, at
10 to 50 %, and only after the attacker's hit roll succeeded: most residents carry no shield, and the new
character has none, so blocks were rare and the player never saw one.

## Why it was not caught

A missing feature (the held block), and a rare event on the NPC side, not a fault: no smoke counted blocks.

## Reproduction

Always: start a fight. The right button does nothing in a fight, and an NPC without a shield never blocks.

## Repair

- Hold to block (an AmiWind extension, the default by owner decision, `aw_combat_block 1`): the right mouse
  button (the Block action in Options > Controls) raises the shield while it is held. Each blow is still
  decided by the original formula and settings (Block skill, Agility, Luck, swing, fatigue, facing, the
  10..50 % clamp); the button decides when the player blocks. No swing while guarding. Without a usable shield
  the console says so. `aw_combat_block 0` (Blocking: Automatic) keeps the original automatic block
  (DON'T DELETE ANY METHOD). Console: `dbg combat block hold|auto`; `dbg combat` counts the blocks.
- Visible: the third-person body now carries the original block animation (base_anim "shield: block start"
  to "block stop") and plays it while guarding (held at the block's hit key) and after a blocked blow; first
  person shows "Guard" under the crosshair, the shield's sound and a view kick on a block. A first-person
  shield model is a later step.
- NPCs: unchanged, the original automatic rule with their block animation and the shield's sound.
- Fidelity: the stand-still block bonus now follows the forward key, as in the original (`combat.cpp`:
  movement forward <= 0), not any movement.
- Companion pick: unchanged; pick mode takes the left button and the right button, and outside pick mode the
  right button blocks.

## Verification

`tests/aga_combat_test.c` (the engine layer with a synthetic server, 40 blows each): blocks while held, none
while not held under hold-to-block, blocks without the button under the automatic rule, no guard without a
shield, the attack masked while guarding. `tests/test_combat.py`
`test_blocking_hold_to_block_default_and_original_kept` pins the default, the bindings, the menu, the body
group and the docs. Pending: the gate with its boot smoke, a MiniWind fight with the `sword_shield` loadout
counting BLOCKED lines, and the owner's playtest.

## Prevention

The default bindings and the block default are pinned by tests; `dbg combat` reports blocks per fight so a
smoke can count them.

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
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

Related bugs in other categories:

- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered

<!-- END GENERATED CATEGORY -->
