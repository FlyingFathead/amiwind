# COMBAT-FATIGUE-HEALTH-DAMAGE-39: Clarify Eldafire bare-fist fatigue damage versus armed guard health damage

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Seyda Neen: Eldafire unarmed combat and armed guard control |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | low: Clarified expected combat behavior; no demonstrated health-damage regression. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

The maintainer observes Eldafire bare-fist hits lowering the green fatigue bar while the red health bar remains unchanged, and confirms the armed guard can kill the player. Upright unarmed fatigue damage is expected; this observation does not prove a health-damage regression.

## Where

Seyda Neen: Eldafire unarmed combat and armed guard control. Reported in v0.0.39-rc1 on 13 October 2026.
Exact running binary, map pose and appearance details require capture/readback.

## How it happened

The clarified upright bare-fist observation follows the existing hand-to-hand fatigue rule; it does not establish swapped HUD bars.

## Why it was not caught

The initial report did not identify the attacker or weapon. The maintainer subsequently identified Eldafire using bare fists and confirmed that the armed guard can kill the player.

## Reproduction

Compare Eldafire bare-fist hits while upright, natural knockout when fatigue becomes negative, and a subsequent landed punch while knocked out. Keep the armed guard health-damage case as a control. Avoid confusing attack fatigue cost with incoming landed hits.

## Repair

No damage-rule change is warranted by this observation. Preserve the original distinction between fatigue damage while upright and health damage while knocked out.

## Verification

Source comparison finds the combat bridge/rules unchanged from published v0.0.38 through RC1. AW_CombatSwing selects fatigue for upright unarmed victims and health while knocked out, matching OpenMW getHandToHandDamage. The maintainer confirms armed guard lethality. Natural player knockout followed by a landed unarmed health hit remains a separate native check; it has not been claimed verified.

## Prevention

Check armed health damage and unarmed fatigue, knockout and subsequent health damage separately; do not infer landed hits from fatigue alone because attacking also costs fatigue.

## Later native chance and source audit, 14 October 2026

The later diagnostic's first-contact chance 19 followed by 1 or 2 reflects the
bridge's initial unaware target followed by normal aware evasion; a small fatigue
change can round the remaining low-skill chance to zero. The inspected awareness
policy and hit formula match the earlier retained source. No new hit-streak
penalty or hit-chance regression is established. The numerical example matching
these transitions is an inference, not a captured complete player sheet;
original-game detection parity remains unverified.

Each swing costs attacker fatigue, and both sheets recover over time. A later
bar snapshot cannot prove or disprove a small landed hit. Capture actual skill,
attributes, target identity, awareness, dice state, immediate result and recovery
time separately. The Fargoth dice-on control records misses, not outgoing damage.

A separate misleading no-dice diagnostic is tracked under
[COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md). It does not establish
failed damage: the rules still apply genuine fatigue or health damage while the
formatter labels a living no-dice target already down. No corrected print or
native damage acceptance is claimed.

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
