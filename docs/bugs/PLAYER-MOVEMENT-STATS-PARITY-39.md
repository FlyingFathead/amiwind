# PLAYER-MOVEMENT-STATS-PARITY-39: Walking/running use fixed debug speeds and do not apply original stats or running fatigue

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Roadmap maxstats is explicitly proposed, not an available command. One affected catalogue-doc test passes after prose correction; failed full suite retained, no handler/movement implementation.
- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Maintainer renewed turbo-traversal report. Source math study documents defaults, original GMST/OpenMW dependencies and matched timing gate. Numeric results are not native timing or a repair.
- Reported with v0.0.48-dev2 at 2026-10-23 02:54 +0300: Maintainer: crossing the island as with boots of blinding speed; original speeds by default, old ones as dbg superspeed. Repaired in source (edf2509d); jump height open.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Normal walking/running, character Speed/Athletics and fatigue; debug movement presets |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1, v0.0.39, v0.0.40-dev1, v0.0.48-dev1 (last seen) |
| Severity | high: Maintainer-visible mechanics or diagnostic requirement; original parity and candidate native verification remain pending. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Deferred by the maintainer | 2026-10-25: the maintainer deferred it to v0.0.52 (v0.0.51 ships its dev3, everything else moves to v0.0.52) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer named RC1; the exact running binary was not independently read back for this report. The mutable RC2 source candidate has not been compiled or packaged. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Proposed debug option documentation correction, 13 October 2026](#proposed-debug-option-documentation-correction-13-october-2026)
- [Source study, 14 October 2026](#source-study-14-october-2026)
- [Reported again and repaired in source, 23 October 2026](#reported-again-and-repaired-in-source-23-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Open maintainer report: default walking/running feels overpowered. Faithful gameplay should use the original Speed, Athletics, encumbrance and running-fatigue formulas. The latest clarification retains convenient fast, less strict debug builds; no immediate replacement of the debug preset or movement repair is claimed.

## Where

Normal walking/running, character Speed/Athletics and fatigue; debug movement presets. Reported on 13 October 2026 during the RC1 inspection.

## How it happened

AmiQuake CL_BaseMove in cl_input.c multiplies fixed input speeds by cl_movespeedkey; SV_AirMove in sv_user.c applies the ordinary direction/maximum-speed handling, friction and acceleration. The RC1 default.cfg sets walking120 and run factor1.8, hence216 units/s, independent of character Speed or Athletics. Diagonal input is only capped by the inherited320 maximum. The world is scaled0.25. The same relevant source is present in published v0.0.38 and RC1, so this is an established parity gap rather than a proven new regression. No running-fatigue debit exists; aw_combat.c updates attack/hit costs and fatigue recovery.

Original data and local OpenMW source give unloaded walk =100 + Speed (original units/s), multiplied by (1 -0.3 * normalized encumbrance). Run = walk * (1.75 + Athletics/100). Divide world distances/speeds by four for the current0.25 scale. At Speed100/Athletics100 and zero encumbrance these are50 and137.5 scaled units/s; they are reference formula results, not native measurements. Over-capacity actors cannot move. Original running fatigue loss is (5 +2 * normalized encumbrance) per second of moving run, with movement input factor; passive recovery is2.5 +0.02 * Endurance per second. These are separate debit/credit terms. Walking does not receive the running debit. Original godmode skips the movement fatigue debit; granting maximum debug movement speed is a maintainer-requested debug extension.

## Why it was not caught

Earlier file, model-budget and scoped native checks did not exercise this exact
requirement. Source implementation and package/native acceptance are separate.

## Reproduction

Compare measured distance and fatigue over equal simulated-time intervals in matched original and target scenes: Speed/Athletics low, middle and100; unloaded, partial/full encumbrance and over capacity; forward, sideways and diagonal; standing, walk and run; both views and normal emulator pacing. Separate gross running cost from net fatigue after recovery. Exclude noclip, menus, death/knockout and scripted movement from ordinary running-debit tests.

## Repair

No movement implementation in this documentation change. Reuse Quake input, acceleration, friction, collision and AW_WalkPlayer support machinery; select a stat-derived ground wish speed before ordinary acceleration without changing debug flight. Establish inventory/capacity inputs explicitly: unsupported encumbrance must remain a named limit, not be reported as complete parity. Keep a clear faithful gameplay mode and the convenient debug preset. Add dbg maxstats on/off, true/false and1/0 as requested; maxstats or godmode enables maximum debug walking/running and disabling both restores normal effective values. Prefer a transient effective-stat override so toggling never destroys real character stats or saved state. Use100 Speed/Athletics as the faithful unfortified reference; specify any separate debug-speed cap explicitly so convenient fast mode is not silently slowed by that reference.

## Verification

Original game settings were read from the same original master used by RC1. OpenMW npc.cpp getWalkSpeed/getRunSpeed/getMaxSpeed and character.cpp moving-fatigue code were inspected. No movement code, target compile, matched native A/B, maximum-stat command or acceptance is claimed. Existing character stat storage is available; carried inventory encumbrance is not integrated into player movement.

## Prevention

Test directional normalization, run-only debit, recovery ordering, low/high stats, over-capacity refusal and idempotent on/off aliases. Test maxstats/godmode overlap and off restoring the unmodified character, including save/load and scene changes. Measure baseline CPU/RAM and original/native motion before adoption.

## Proposed debug option documentation correction, 13 October 2026

The source4b968c2 suite rejects a roadmap mention that looks like an available maxstats console invocation, although the requested option has no catalogue entry or implementation. The roadmap now calls it an explicitly proposed option and describes the requested aliases and future godmode-speed extension without presenting a working invocation. The existing godmode immunity toggle remains separate. This is a documentation correction only, not implementation of maximum stats, original movement formulas or running fatigue. The one affected catalogue-documentation check now passes against an immutable dependency snapshot. Retain the failed full suite receipt; this result does not turn that run into a full-suite pass or add an implemented command.

## Source study, 14 October 2026

The renewed maintainer report describes turbo traversal. [Movement speed study](../MOVEMENT_SPEED_STUDY.md) records generated120/216 ground targets, the diagonal gain, 0.7 water factor, original-data/OpenMW formulas and a matched timing gate. The earlier unit-race50/137.5 example precedes actor/race scaling and is not a universal final speed; the default OpenMW reference applies Nord male weight1.25 to horizontal motion. Modified stats, load/effects, direction and gross-versus-net fatigue are explicit. No movement setting changed, and no native timing or maintainer acceptance is established. Keep this issue OPEN.

## Reported again and repaired in source, 23 October 2026

The maintainer, 23 October 2026 (~02:35 +0300, desktop chat): "we should probably make our character traverse at the
beginner speeds with the variables set by the game, right now you can just go around the island with something akin
to the boots of blinding speed or having taken enough potions etc"; "we could add like `dbg superspeed on` (also
`superspeed on`) into the console, otherwise you'd traverse in Morrowind's parameter's set speed(s) and our current
speed thing would be the "superspeed" setting"; "I need for debugging reasons that the athletics+whatever the else,
that they are as they are now in that debug superspeed mode". He added that the speed must follow the character as it
changes (levelling, skill gains, later effects), that encumbrance, paralysis and other effects belong to the same
rule, and that running and jumping cost fatigue that returns over time.

Fixed in source on branch v0.0.48-player-speed (edf2509d), not shipped at the time of writing:

- Walking, running and swimming use the original's rules (OpenMW 0.51 getWalkSpeed / getRunSpeed / swim speed /
  getMaxSpeed, race weight, strafing x 0.75, input amount), with the master file's own game settings, read from the
  LIVE character sheet every frame: Speed, Athletics, Strength, the carried load and the race weight. A new Nord male
  Barbarian walks 46.9 and runs 98.4 units/s (the old fixed speeds were 120 and 216, 2.56 and 2.19 times faster);
  Speed 100 / Athletics 100 gives 62.5 / 171.9. Over capacity the player cannot move; knocked down or out, no movement.
- Running and swimming cost fatigue per second, a jump costs fFatigueJumpBase; never below 0; godmode free. The
  existing fatigue return is unchanged.
- `superspeed` / `dbg superspeed on|off` (default off, not saved) keeps the previous movement byte for byte, with no
  fatigue cost.
- Every OpenMW factor is in one input structure; the ones the engine has no system for yet (sneaking, paralysis,
  Feather/Burden, Fortify/Drain, Swift Swim, Levitate, Slowfall, Water Walking) are fields at 0 = no effect, listed
  "later" in [PLAYER_MOVEMENT.md](../PLAYER_MOVEMENT.md#movement-speed).
- Tests: `tests/aga_move_rules_test.c` (hand-worked OpenMW values), `tests/aga_move_test.c` (superspeed gives the old
  120 / 216 / 169.7 / 84, raising Athletics or Speed raises the speed at once, load, fatigue, the command).

Still open: the jump height and in-air control ([PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md)),
in-game timing against the original, and the maintainer's check in a build. Keep this issue OPEN until then.

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

- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation

<!-- END GENERATED CATEGORY -->
